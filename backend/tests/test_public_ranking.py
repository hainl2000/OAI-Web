from tests.helpers import flip, make_csv, register, setup_competition_with_truth, submit, truth_rows


def test_public_ranking_hidden_by_default_and_visible_when_published(client, admin_client, candidate_factory):
    competition, rows = setup_competition_with_truth(admin_client, truth_rows(2, 2))
    cid = competition["id"]
    alice = candidate_factory("Nguyễn Thị Alice", "alice@example.com")
    bob = candidate_factory("Trần Văn Bob", "bob@example.com")
    register(alice, cid)
    register(bob, cid)
    assert submit(alice, cid, make_csv(rows)).status_code == 201
    assert submit(bob, cid, make_csv(flip(rows, 1))).status_code == 201

    hidden = client.get(f"/api/v1/public/competitions/{cid}/ranking")
    assert hidden.status_code == 200
    body = hidden.json()
    assert body["published"] is False
    assert body["entries"] == []
    assert "Alice" not in hidden.text and "alice@example.com" not in hidden.text

    # Admin always sees the full ranking.
    admin_view = admin_client.get(f"/api/v1/admin/competitions/{cid}/ranking").json()
    assert len(admin_view["entries"]) == 2

    admin_client.patch(f"/api/v1/admin/competitions/{cid}", json={"ranking_published": True})
    shown = client.get(f"/api/v1/public/competitions/{cid}/ranking")
    body = shown.json()
    assert body["published"] is True
    assert body["competition_name"] == competition["name"]
    assert [e["name"] for e in body["entries"]] == ["Nguyễn Thị Alice", "Trần Văn Bob"]
    assert body["entries"][0]["rank"] == 1 and body["entries"][1]["rank"] == 2
    assert body["entries"][0]["best_score"] == "1.000000"
    assert body["entries"][0]["submission_count"] == 1
    assert "best_submitted_at" in body["entries"][0]
    assert "email" not in body["entries"][0]
    assert "alice@example.com" not in shown.text

    admin_client.patch(f"/api/v1/admin/competitions/{cid}", json={"ranking_published": False})
    assert client.get(f"/api/v1/public/competitions/{cid}/ranking").json()["entries"] == []


def test_public_ranking_unknown_competition(client):
    response = client.get("/api/v1/public/competitions/424242/ranking")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "competition_not_found"
