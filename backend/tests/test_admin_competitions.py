from tests.helpers import create_competition, make_csv, register, truth_rows, upload_ground_truth


def test_create_list_and_defaults(admin_client):
    created = create_competition(admin_client, "  Vòng loại  ")
    assert created["name"] == "Vòng loại"
    assert created["ranking_published"] is False
    assert created["ground_truth_version"] == 0
    assert created["has_ground_truth"] is False
    assert created["registration_count"] == 0

    listing = admin_client.get("/api/v1/admin/competitions")
    assert listing.status_code == 200
    assert [c["id"] for c in listing.json()] == [created["id"]]

    assert admin_client.post("/api/v1/admin/competitions", json={"name": "   "}).status_code == 422


def test_rename_and_toggle_ranking(admin_client):
    competition = create_competition(admin_client)
    url = f"/api/v1/admin/competitions/{competition['id']}"

    renamed = admin_client.patch(url, json={"name": "Chung kết"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Chung kết"
    assert renamed.json()["ranking_published"] is False

    toggled = admin_client.patch(url, json={"ranking_published": True})
    assert toggled.json()["ranking_published"] is True
    assert toggled.json()["name"] == "Chung kết"

    assert admin_client.patch(url, json={}).status_code == 422
    assert admin_client.patch("/api/v1/admin/competitions/9999", json={"name": "x"}).status_code == 404


def test_registration_is_idempotent_and_listed_for_admin(admin_client, candidate_client):
    competition = create_competition(admin_client)
    first = register(candidate_client, competition["id"])
    second = register(candidate_client, competition["id"])
    assert first["created"] is True
    assert second["created"] is False
    assert first["registered_at"] == second["registered_at"]

    listing = admin_client.get(f"/api/v1/admin/competitions/{competition['id']}/registrations")
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 1
    assert rows[0]["user"]["email"] == candidate_client.user["email"]
    assert rows[0]["submission_count"] == 0
    assert rows[0]["best_score"] is None

    detail = admin_client.get("/api/v1/admin/competitions").json()[0]
    assert detail["registration_count"] == 1

    assert candidate_client.put("/api/v1/competitions/9999/registration").status_code == 404


def test_candidate_listing_splits_registered_and_unregistered(admin_client, candidate_client):
    a = create_competition(admin_client, "A")
    b = create_competition(admin_client, "B")
    register(candidate_client, a["id"])

    listing = candidate_client.get("/api/v1/competitions")
    assert listing.status_code == 200
    body = listing.json()
    assert [c["id"] for c in body["registered"]] == [a["id"]]
    assert [c["id"] for c in body["unregistered"]] == [b["id"]]
    assert body["registered"][0]["registered"] is True
    assert body["unregistered"][0]["registered"] is False
    assert body["registered"][0]["has_ground_truth"] is False


def test_ground_truth_upload_preview_download(admin_client):
    competition = create_competition(admin_client)
    cid = competition["id"]
    assert admin_client.get(f"/api/v1/admin/competitions/{cid}/ground-truth").status_code == 404
    assert admin_client.get(f"/api/v1/admin/competitions/{cid}/ground-truth/download").status_code == 404

    rows = truth_rows(2, 3)
    data = make_csv(rows, bom=True)
    response = upload_ground_truth(admin_client, cid, data, filename="dap_an.csv")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ground_truth_version"] == 1
    assert body["submissions_deleted"] == 0
    assert body["metadata"]["row_count"] == 5
    assert body["metadata"]["filename"] == "dap_an.csv"
    assert body["metadata"]["size_bytes"] == len(data)
    assert len(body["metadata"]["checksum_sha256"]) == 64

    preview = admin_client.get(
        f"/api/v1/admin/competitions/{cid}/ground-truth", params={"page": 2, "page_size": 2}
    )
    assert preview.status_code == 200
    p = preview.json()
    assert p["total"] == 5 and p["page"] == 2 and p["page_size"] == 2
    assert [item["uuid"] for item in p["items"]] == [str(rows[2][0]), str(rows[3][0])]
    assert p["items"][0]["is_spoof"] is False
    assert p["metadata"]["version"] == 1

    download = admin_client.get(f"/api/v1/admin/competitions/{cid}/ground-truth/download")
    assert download.status_code == 200
    assert download.content == data
    assert 'filename="dap_an.csv"' in download.headers["content-disposition"]

    listing = admin_client.get("/api/v1/admin/competitions").json()[0]
    assert listing["has_ground_truth"] is True
    assert listing["ground_truth_version"] == 1


def test_ground_truth_upload_rejects_invalid_csv(admin_client):
    competition = create_competition(admin_client)
    response = upload_ground_truth(admin_client, competition["id"], b"uuid,label\nabc,TRUE\n")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "csv_invalid_header"
    assert admin_client.get(f"/api/v1/admin/competitions/{competition['id']}/ground-truth").status_code == 404
