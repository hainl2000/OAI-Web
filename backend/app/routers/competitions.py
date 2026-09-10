from fastapi import APIRouter, File, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CandidateUser, DbSession
from app.errors import ApiError
from app.models import Competition, CompetitionGroundTruth, Registration, Submission
from app.schemas import (
    CandidateCompetitionDetailOut,
    CandidateCompetitionOut,
    CompetitionListOut,
    RegistrationStateOut,
    SubmissionOut,
)
from app.services.submissions import create_submission, get_registration, list_my_submissions

router = APIRouter(prefix="/competitions", tags=["competitions"])


def _get_competition_or_404(db: Session, competition_id: int) -> Competition:
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise ApiError(404, "competition_not_found", "Không tìm thấy cuộc thi.")
    return competition


def _has_ground_truth(db: Session, competition_id: int) -> bool:
    return (
        db.scalar(select(CompetitionGroundTruth.id).where(CompetitionGroundTruth.competition_id == competition_id))
        is not None
    )


@router.get("", response_model=CompetitionListOut)
def list_competitions(user: CandidateUser, db: DbSession) -> CompetitionListOut:
    stmt = (
        select(Competition, Registration.created_at, CompetitionGroundTruth.id)
        .outerjoin(
            Registration,
            (Registration.competition_id == Competition.id) & (Registration.user_id == user.id),
        )
        .outerjoin(CompetitionGroundTruth, CompetitionGroundTruth.competition_id == Competition.id)
        .order_by(Competition.created_at.desc(), Competition.id.desc())
    )
    registered: list[CandidateCompetitionOut] = []
    unregistered: list[CandidateCompetitionOut] = []
    for competition, registered_at, gt_id in db.execute(stmt):
        item = CandidateCompetitionOut(
            id=competition.id,
            name=competition.name,
            ranking_published=competition.ranking_published,
            has_ground_truth=gt_id is not None,
            created_at=competition.created_at,
            registered=registered_at is not None,
            registered_at=registered_at,
        )
        (registered if item.registered else unregistered).append(item)
    return CompetitionListOut(registered=registered, unregistered=unregistered)


@router.put("/{competition_id}/registration", response_model=RegistrationStateOut)
def register(competition_id: int, user: CandidateUser, db: DbSession) -> RegistrationStateOut:
    competition = _get_competition_or_404(db, competition_id)
    registration = get_registration(db, user.id, competition.id)
    created = False
    if registration is None:
        registration = Registration(user_id=user.id, competition_id=competition.id)
        db.add(registration)
        db.commit()
        db.refresh(registration)
        created = True
    return RegistrationStateOut(
        competition_id=competition.id,
        registered=True,
        registered_at=registration.created_at,
        created=created,
    )


@router.get("/{competition_id}", response_model=CandidateCompetitionDetailOut)
def get_competition(competition_id: int, user: CandidateUser, db: DbSession) -> CandidateCompetitionDetailOut:
    competition = _get_competition_or_404(db, competition_id)
    registration = get_registration(db, user.id, competition.id)
    count, best = db.execute(
        select(func.count(), func.max(Submission.score)).where(
            Submission.user_id == user.id, Submission.competition_id == competition.id
        )
    ).one()
    return CandidateCompetitionDetailOut(
        id=competition.id,
        name=competition.name,
        ranking_published=competition.ranking_published,
        has_ground_truth=_has_ground_truth(db, competition.id),
        created_at=competition.created_at,
        registered=registration is not None,
        registered_at=registration.created_at if registration else None,
        ground_truth_version=competition.ground_truth_version,
        my_submission_count=int(count or 0),
        best_score=best,
    )


@router.post(
    "/{competition_id}/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED
)
async def submit(
    competition_id: int, user: CandidateUser, db: DbSession, file: UploadFile = File(...)
) -> Submission:
    competition = _get_competition_or_404(db, competition_id)
    settings = get_settings()
    try:
        data = await file.read(settings.csv_max_bytes + 1)
    finally:
        # The candidate file is discarded as soon as it has been read into memory.
        await file.close()
    if len(data) > settings.csv_max_bytes:
        raise ApiError(
            422,
            "csv_too_large",
            f"File vượt quá kích thước tối đa {settings.csv_max_bytes // (1024 * 1024)} MB.",
            max_bytes=settings.csv_max_bytes,
        )
    try:
        return create_submission(db, user, competition, data)
    finally:
        del data


@router.get("/{competition_id}/submissions/me", response_model=list[SubmissionOut])
def my_submissions(competition_id: int, user: CandidateUser, db: DbSession) -> list[Submission]:
    competition = _get_competition_or_404(db, competition_id)
    return list_my_submissions(db, user.id, competition.id)
