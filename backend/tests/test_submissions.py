import uuid as uuid_lib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.models import Submission
from tests.helpers import (
    create_competition,
    flip,
    make_csv,
    register,
    setup_competition_with_truth,
    submit,
    truth_rows,
    upload_ground_truth,
)


def test_cannot_submit_before_registration(admin_client, candidate_client):
    competition, rows = setup_competition_with_truth(admin_client)
    response = submit(candidate_client, competition["id"], make_csv(rows))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "not_registered"


def test_cannot_submit_before_ground_truth(admin_client, candidate_client):
    competition = create_competition(admin_client)
    register(candidate_client, competition["id"])
    response = submit(candidate_client, competition["id"], make_csv(truth_rows(1, 1)))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ground_truth_not_available"
    assert candidate_client.get(f"/api/v1/competitions/{competition['id']}/submissions/me").json() == []


def test_multiple_attempts_history_and_best_score(admin_client, candidate_client):
    competition, rows = setup_competition_with_truth(admin_client, truth_rows(3, 3))
    cid = competition["id"]
    register(candidate_client, cid)

    first = submit(candidate_client, cid, make_csv(flip(rows, 2)))
    assert first.status_code == 201, first.text
    assert first.json()["attempt_number"] == 1
    # spoof: TP=1 FP=0 FN=2 -> 0.5 ; live: TP=3 FP=2 FN=0 -> 0.75 ; macro = 0.625
    assert first.json()["score"] == "0.625000"
    second = submit(candidate_client, cid, make_csv(rows, bom=True, newline="\r\n"))
    assert second.status_code == 201
    assert second.json()["attempt_number"] == 2
    assert second.json()["score"] == "1.000000"
    third = submit(candidate_client, cid, make_csv(flip(rows, 6)))
    assert third.json()["attempt_number"] == 3
    assert third.json()["score"] == "0.000000"

    history = candidate_client.get(f"/api/v1/competitions/{cid}/submissions/me")
    assert history.status_code == 200
    assert [h["attempt_number"] for h in history.json()] == [3, 2, 1]
    assert all(h["ground_truth_version"] == 1 for h in history.json())

    detail = candidate_client.get(f"/api/v1/competitions/{cid}")
    assert detail.status_code == 200
    assert detail.json()["my_submission_count"] == 3
    assert detail.json()["best_score"] == "1.000000"
    assert detail.json()["registered"] is True
    assert detail.json()["has_ground_truth"] is True

    registrations = admin_client.get(f"/api/v1/admin/competitions/{cid}/registrations").json()
    assert registrations[0]["submission_count"] == 3
    assert registrations[0]["best_score"] == "1.000000"


def test_invalid_files_do_not_create_attempts(admin_client, candidate_client):
    competition, rows = setup_competition_with_truth(admin_client, truth_rows(2, 2))
    cid = competition["id"]
    register(candidate_client, cid)

    missing = submit(candidate_client, cid, make_csv(rows[:-1]))
    assert missing.status_code == 422
    assert missing.json()["detail"]["code"] == "uuid_set_mismatch"
    assert missing.json()["detail"]["missing_count"] == 1
    assert missing.json()["detail"]["extra_count"] == 0

    extra = submit(candidate_client, cid, make_csv(rows + [(uuid_lib.uuid4(), True)]))
    assert extra.json()["detail"]["code"] == "uuid_set_mismatch"
    assert extra.json()["detail"]["extra_count"] == 1

    swapped = submit(candidate_client, cid, make_csv(rows[:-1] + [(uuid_lib.uuid4(), True)]))
    assert swapped.json()["detail"]["missing_count"] == 1
    assert swapped.json()["detail"]["extra_count"] == 1

    duplicate = submit(candidate_client, cid, make_csv(rows + [rows[0]]))
    assert duplicate.json()["detail"]["code"] == "csv_duplicate_uuid"

    bad_label = submit(candidate_client, cid, make_csv([(rows[0][0], "maybe")] + rows[1:]))
    assert bad_label.json()["detail"]["code"] == "csv_invalid_label"

    bad_header = submit(candidate_client, cid, b"id,is_spoof\n")
    assert bad_header.json()["detail"]["code"] == "csv_invalid_header"

    assert candidate_client.get(f"/api/v1/competitions/{cid}/submissions/me").json() == []
    ok = submit(candidate_client, cid, make_csv(rows))
    assert ok.status_code == 201
    assert ok.json()["attempt_number"] == 1


def test_oversized_upload_is_rejected(admin_client, candidate_client, monkeypatch):
    from app.config import get_settings

    competition, rows = setup_competition_with_truth(admin_client, truth_rows(1, 1))
    register(candidate_client, competition["id"])
    monkeypatch.setattr(get_settings(), "csv_max_bytes", 10)
    response = submit(candidate_client, competition["id"], make_csv(rows))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "csv_too_large"


def test_ranking_best_score_and_tie_break(admin_client, candidate_factory, db_session):
    competition, rows = setup_competition_with_truth(admin_client, truth_rows(3, 3))
    cid = competition["id"]
    alice = candidate_factory("Alice", "alice@example.com")
    bob = candidate_factory("Bob", "bob@example.com")
    carol = candidate_factory("Carol", "carol@example.com")
    for c in (alice, bob, carol):
        register(c, cid)

    # Bob reaches the perfect score first, Alice matches it later, Carol scores lower.
    assert submit(bob, cid, make_csv(flip(rows, 1))).status_code == 201
    assert submit(bob, cid, make_csv(rows)).status_code == 201
    assert submit(alice, cid, make_csv(rows)).status_code == 201
    assert submit(alice, cid, make_csv(flip(rows, 3))).status_code == 201  # worse later attempt
    assert submit(carol, cid, make_csv(flip(rows, 1))).status_code == 201

    # Make timestamps deterministic: Bob's perfect attempt is earlier than Alice's.
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for sub in db_session.scalars(select(Submission).order_by(Submission.id)):
        db_session.execute(
            update(Submission).where(Submission.id == sub.id).values(submitted_at=base + timedelta(minutes=sub.id))
        )
    db_session.commit()

    ranking = admin_client.get(f"/api/v1/admin/competitions/{cid}/ranking")
    assert ranking.status_code == 200
    body = ranking.json()
    assert body["published"] is False  # admin sees it regardless
    names = [(e["rank"], e["name"], e["best_score"], e["submission_count"]) for e in body["entries"]]
    assert names == [
        (1, "Bob", "1.000000", 2),
        (2, "Alice", "1.000000", 2),
        (3, "Carol", names[2][2], 1),
    ]
    assert names[2][2] < "1.000000"
    # best_submitted_at is the time of the best attempt, not the latest attempt.
    alice_entry = body["entries"][1]
    alice_best = db_session.scalar(
        select(Submission).where(Submission.user_id == alice.user["id"], Submission.attempt_number == 1)
    )
    assert datetime.fromisoformat(alice_entry["best_submitted_at"]) == alice_best.submitted_at


def test_tie_break_falls_back_to_user_id(admin_client, candidate_factory, db_session):
    competition, rows = setup_competition_with_truth(admin_client, truth_rows(2, 2))
    cid = competition["id"]
    second_user = candidate_factory("Hai", "hai@example.com")
    first_user = candidate_factory("Ba", "ba@example.com")
    register(second_user, cid)
    register(first_user, cid)
    assert submit(first_user, cid, make_csv(rows)).status_code == 201
    assert submit(second_user, cid, make_csv(rows)).status_code == 201
    same_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.execute(update(Submission).values(submitted_at=same_time))
    db_session.commit()

    entries = admin_client.get(f"/api/v1/admin/competitions/{cid}/ranking").json()["entries"]
    assert [e["user_id"] for e in entries] == sorted([second_user.user["id"], first_user.user["id"]])


def test_scores_are_stored_exactly(admin_client, candidate_client, db_session):
    rows = [(uuid_lib.uuid4(), True) for _ in range(9)] + [(uuid_lib.uuid4(), False)]
    competition, _ = setup_competition_with_truth(admin_client, rows)
    register(candidate_client, competition["id"])
    response = submit(candidate_client, competition["id"], make_csv([(k, True) for k, _ in rows]))
    assert response.status_code == 201
    assert response.json()["score"] == "0.473684"
    stored = db_session.scalar(select(Submission.score))
    assert str(stored) == "0.47368421052631578947"


def test_submission_after_ground_truth_replacement_records_new_version(admin_client, candidate_client):
    competition, rows = setup_competition_with_truth(admin_client, truth_rows(1, 1))
    cid = competition["id"]
    register(candidate_client, cid)
    new_rows = truth_rows(1, 1)
    assert upload_ground_truth(admin_client, cid, make_csv(new_rows)).status_code == 200
    response = submit(candidate_client, cid, make_csv(new_rows))
    assert response.status_code == 201
    assert response.json()["ground_truth_version"] == 2
    old = submit(candidate_client, cid, make_csv(rows))
    assert old.status_code == 422 and old.json()["detail"]["code"] == "uuid_set_mismatch"
