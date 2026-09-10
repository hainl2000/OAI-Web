import hashlib

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.csv_utils import CsvValidationError, parse_labels_csv
from app.errors import ApiError
from app.models import Competition, CompetitionGroundTruth, GroundTruthRow, Submission, User
from app.services.csv_errors import csv_error_to_api

INSERT_BATCH = 5_000


def count_submissions(db: Session, competition_id: int) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(Submission).where(Submission.competition_id == competition_id)
        )
        or 0
    )


def replace_ground_truth(
    db: Session,
    competition: Competition,
    *,
    data: bytes,
    filename: str,
    uploaded_by: User | None,
    confirm_reset: bool,
) -> tuple[CompetitionGroundTruth, int]:
    """Validate the whole file first, then swap answer key + wipe scores in one transaction.

    Returns ``(ground_truth, submissions_deleted)``.
    """
    settings = get_settings()
    try:
        parsed = parse_labels_csv(data, max_bytes=settings.csv_max_bytes, max_rows=settings.csv_max_rows)
    except CsvValidationError as exc:
        raise csv_error_to_api(exc) from exc

    existing_submissions = count_submissions(db, competition.id)
    if existing_submissions > 0 and not confirm_reset:
        raise ApiError(
            409,
            "score_reset_confirmation_required",
            "Cuộc thi đã có lượt nộp. Cần xác nhận reset bảng điểm trước khi thay đáp án.",
            submissions_to_delete=existing_submissions,
        )

    try:
        # Lock the competition row so concurrent replacements / submissions serialize.
        locked = db.execute(
            select(Competition).where(Competition.id == competition.id).with_for_update()
        ).scalar_one()

        db.execute(delete(GroundTruthRow).where(GroundTruthRow.competition_id == locked.id))
        deleted = db.execute(delete(Submission).where(Submission.competition_id == locked.id)).rowcount

        locked.ground_truth_version += 1

        ground_truth = db.scalar(
            select(CompetitionGroundTruth).where(CompetitionGroundTruth.competition_id == locked.id)
        )
        if ground_truth is None:
            ground_truth = CompetitionGroundTruth(competition_id=locked.id)
            db.add(ground_truth)
        ground_truth.filename = filename or "ground_truth.csv"
        ground_truth.content = data
        ground_truth.size_bytes = len(data)
        ground_truth.row_count = parsed.row_count
        ground_truth.checksum_sha256 = hashlib.sha256(data).hexdigest()
        ground_truth.version = locked.ground_truth_version
        ground_truth.uploaded_by_id = uploaded_by.id if uploaded_by else None
        ground_truth.uploaded_at = func.now()

        rows = [
            {"competition_id": locked.id, "uuid": key, "is_spoof": value}
            for key, value in parsed.labels.items()
        ]
        for start in range(0, len(rows), INSERT_BATCH):
            db.execute(insert(GroundTruthRow), rows[start : start + INSERT_BATCH])

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(ground_truth)
    db.refresh(competition)
    return ground_truth, int(deleted or 0)


def load_truth_labels(db: Session, competition_id: int) -> dict:
    result = db.execute(
        select(GroundTruthRow.uuid, GroundTruthRow.is_spoof).where(
            GroundTruthRow.competition_id == competition_id
        )
    )
    return {row.uuid: row.is_spoof for row in result}
