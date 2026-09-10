from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.csv_utils import CsvValidationError, parse_labels_csv
from app.errors import ApiError
from app.models import Competition, CompetitionGroundTruth, Registration, Submission, User
from app.scoring import compare_uuid_sets, f1_macro
from app.services.csv_errors import csv_error_to_api
from app.services.ground_truth import load_truth_labels

SAMPLE_LIMIT = 10


def get_registration(db: Session, user_id: int, competition_id: int, *, lock: bool = False):
    stmt = select(Registration).where(
        Registration.user_id == user_id, Registration.competition_id == competition_id
    )
    if lock:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def create_submission(db: Session, user: User, competition: Competition, data: bytes) -> Submission:
    """Score a candidate file in-request. The file bytes are never persisted."""
    settings = get_settings()

    registration = get_registration(db, user.id, competition.id, lock=True)
    if registration is None:
        raise ApiError(403, "not_registered", "Bạn chưa đăng ký cuộc thi này.")

    ground_truth = db.scalar(
        select(CompetitionGroundTruth).where(CompetitionGroundTruth.competition_id == competition.id)
    )
    if ground_truth is None:
        raise ApiError(
            409, "ground_truth_not_available", "Cuộc thi chưa có đáp án, chưa thể nộp bài."
        )

    try:
        parsed = parse_labels_csv(data, max_bytes=settings.csv_max_bytes, max_rows=settings.csv_max_rows)
    except CsvValidationError as exc:
        db.rollback()
        raise csv_error_to_api(exc) from exc

    truth = load_truth_labels(db, competition.id)
    diff = compare_uuid_sets(truth, parsed.labels)
    if not diff.matches:
        db.rollback()
        raise ApiError(
            422,
            "uuid_set_mismatch",
            "Tập uuid trong file không khớp với đáp án.",
            missing_count=len(diff.missing),
            extra_count=len(diff.extra),
            missing_sample=diff.missing[:SAMPLE_LIMIT],
            extra_sample=diff.extra[:SAMPLE_LIMIT],
        )

    score = f1_macro(truth, parsed.labels)

    last_attempt = db.scalar(
        select(func.coalesce(func.max(Submission.attempt_number), 0)).where(
            Submission.user_id == user.id, Submission.competition_id == competition.id
        )
    )
    submission = Submission(
        user_id=user.id,
        competition_id=competition.id,
        attempt_number=int(last_attempt or 0) + 1,
        score=score,
        ground_truth_version=competition.ground_truth_version,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def list_my_submissions(db: Session, user_id: int, competition_id: int) -> list[Submission]:
    return list(
        db.scalars(
            select(Submission)
            .where(Submission.user_id == user_id, Submission.competition_id == competition_id)
            .order_by(Submission.attempt_number.desc())
        )
    )
