from sqlalchemy import func, select

from app.models import GroundTruthRow, Submission
from tests.helpers import make_csv, register, setup_competition_with_truth, submit, truth_rows, upload_ground_truth


def _seed_scores(admin_client, candidate_factory):
    competition, rows = setup_competition_with_truth(admin_client, truth_rows(2, 2))
    cid = competition["id"]
    a = candidate_factory("A", "a@example.com")
    b = candidate_factory("B", "b@example.com")
    register(a, cid)
    register(b, cid)
    assert submit(a, cid, make_csv(rows)).status_code == 201
    assert submit(a, cid, make_csv(rows)).status_code == 201
    assert submit(b, cid, make_csv(rows)).status_code == 201
    admin_client.patch(f"/api/v1/admin/competitions/{cid}", json={"ranking_published": True})
    return competition, rows, a, b


def test_replacement_without_confirmation_keeps_everything(admin_client, candidate_factory, db_session):
    competition, rows, a, _ = _seed_scores(admin_client, candidate_factory)
    cid = competition["id"]
    old_download = admin_client.get(f"/api/v1/admin/competitions/{cid}/ground-truth/download").content

    response = upload_ground_truth(admin_client, cid, make_csv(truth_rows(1, 1)))
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "score_reset_confirmation_required"
    assert detail["submissions_to_delete"] == 3

    assert db_session.scalar(select(func.count()).select_from(Submission)) == 3
    assert admin_client.get(f"/api/v1/admin/competitions/{cid}/ground-truth/download").content == old_download
    assert admin_client.get("/api/v1/admin/competitions").json()[0]["ground_truth_version"] == 1
    assert len(a.get(f"/api/v1/competitions/{cid}/submissions/me").json()) == 2


def test_invalid_new_file_keeps_old_answer_key_and_scores(admin_client, candidate_factory, db_session):
    competition, rows, a, _ = _seed_scores(admin_client, candidate_factory)
    cid = competition["id"]
    bad = make_csv(rows[:2] + [(rows[0][0], True)])  # duplicate uuid
    response = upload_ground_truth(admin_client, cid, bad, confirm=True)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "csv_duplicate_uuid"

    assert db_session.scalar(select(func.count()).select_from(Submission)) == 3
    truth = {row.uuid: row.is_spoof for row in db_session.execute(select(GroundTruthRow.uuid, GroundTruthRow.is_spoof))}
    assert truth == dict(rows)
    listing = admin_client.get("/api/v1/admin/competitions").json()[0]
    assert listing["ground_truth_version"] == 1
    assert listing["submission_count"] == 3


def test_confirmed_replacement_resets_scores_but_keeps_registrations_and_toggle(
    admin_client, candidate_factory, db_session
):
    competition, rows, a, b = _seed_scores(admin_client, candidate_factory)
    cid = competition["id"]
    new_rows = truth_rows(3, 1)

    response = upload_ground_truth(admin_client, cid, make_csv(new_rows), confirm=True, filename="v2.csv")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["submissions_deleted"] == 3
    assert body["ground_truth_version"] == 2
    assert body["metadata"]["version"] == 2
    assert body["metadata"]["row_count"] == 4

    assert db_session.scalar(select(func.count()).select_from(Submission)) == 0
    truth = {row.uuid: row.is_spoof for row in db_session.execute(select(GroundTruthRow.uuid, GroundTruthRow.is_spoof))}
    assert truth == dict(new_rows)

    registrations = admin_client.get(f"/api/v1/admin/competitions/{cid}/registrations").json()
    assert {r["user"]["email"] for r in registrations} == {"a@example.com", "b@example.com"}
    assert all(r["submission_count"] == 0 and r["best_score"] is None for r in registrations)

    listing = admin_client.get("/api/v1/admin/competitions").json()[0]
    assert listing["ranking_published"] is True
    assert listing["ground_truth_version"] == 2

    # Candidate history is empty, public ranking stays published but empty.
    assert a.get(f"/api/v1/competitions/{cid}/submissions/me").json() == []
    public = admin_client.get(f"/api/v1/public/competitions/{cid}/ranking").json()
    assert public["published"] is True and public["entries"] == []

    # Attempt numbering restarts from 1 with the new answer key.
    again = submit(a, cid, make_csv(new_rows))
    assert again.status_code == 201
    assert again.json()["attempt_number"] == 1
    assert again.json()["ground_truth_version"] == 2
    public = admin_client.get(f"/api/v1/public/competitions/{cid}/ranking").json()
    assert [e["name"] for e in public["entries"]] == ["A"]


def test_first_upload_needs_no_confirmation_and_replacement_without_scores_is_silent(admin_client):
    competition, rows = setup_competition_with_truth(admin_client)
    response = upload_ground_truth(admin_client, competition["id"], make_csv(truth_rows(1, 1)))
    assert response.status_code == 200
    assert response.json()["ground_truth_version"] == 2
    assert response.json()["submissions_deleted"] == 0
