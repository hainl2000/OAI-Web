import io
import uuid as uuid_lib

from fastapi.testclient import TestClient


def make_csv(
    rows, *, header=("uuid", "is_spoof"), bom: bool = False, newline: str = "\n"
) -> bytes:
    """Build a CSV. ``rows`` is an iterable of (uuid, label) where label may be bool or str."""
    lines = [",".join(header)]
    for key, label in rows:
        if isinstance(label, bool):
            label = "TRUE" if label else "FALSE"
        if header[0] == "uuid":
            lines.append(f"{key},{label}")
        else:
            lines.append(f"{label},{key}")
    text = newline.join(lines) + newline
    data = text.encode("utf-8")
    return (b"\xef\xbb\xbf" + data) if bom else data


def truth_rows(n_spoof: int, n_live: int):
    rows = [(uuid_lib.uuid4(), True) for _ in range(n_spoof)]
    rows += [(uuid_lib.uuid4(), False) for _ in range(n_live)]
    return rows


def create_competition(admin: TestClient, name: str = "Cuộc thi 1") -> dict:
    response = admin.post("/api/v1/admin/competitions", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def upload_ground_truth(admin: TestClient, competition_id: int, data: bytes, *, confirm: bool = False, filename="truth.csv"):
    return admin.put(
        f"/api/v1/admin/competitions/{competition_id}/ground-truth",
        files={"file": (filename, io.BytesIO(data), "text/csv")},
        data={"confirm_reset": "true"} if confirm else {},
    )


def register(candidate: TestClient, competition_id: int):
    response = candidate.put(f"/api/v1/competitions/{competition_id}/registration")
    assert response.status_code == 200, response.text
    return response.json()


def submit(candidate: TestClient, competition_id: int, data: bytes, filename="pred.csv"):
    return candidate.post(
        f"/api/v1/competitions/{competition_id}/submissions",
        files={"file": (filename, io.BytesIO(data), "text/csv")},
    )


def setup_competition_with_truth(admin: TestClient, rows=None, name="Cuộc thi 1"):
    rows = rows if rows is not None else truth_rows(3, 3)
    competition = create_competition(admin, name)
    response = upload_ground_truth(admin, competition["id"], make_csv(rows))
    assert response.status_code == 200, response.text
    return competition, rows


def flip(rows, n: int):
    """Return a copy of rows with the first ``n`` labels inverted."""
    out = []
    for index, (key, label) in enumerate(rows):
        out.append((key, (not label) if index < n else label))
    return out
