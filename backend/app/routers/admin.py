from fastapi import APIRouter, File, Form, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import AdminUser, DbSession
from app.errors import ApiError
from app.models import Competition, CompetitionGroundTruth, GroundTruthRow, Registration, Submission, User
from app.schemas import (
    AdminCompetitionOut,
    CompetitionCreate,
    CompetitionUpdate,
    GroundTruthPreviewOut,
    GroundTruthReplaceOut,
    GroundTruthRowOut,
    RankingEntryOut,
    RankingOut,
    RegistrationOut,
    RegistrationUserOut,
)
from app.services.ground_truth import replace_ground_truth
from app.services.ranking import compute_ranking

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_competition_or_404(db: Session, competition_id: int) -> Competition:
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise ApiError(404, "competition_not_found", "Không tìm thấy cuộc thi.")
    return competition


def _admin_competition_out(db: Session, competition: Competition) -> AdminCompetitionOut:
    registration_count = db.scalar(
        select(func.count()).select_from(Registration).where(Registration.competition_id == competition.id)
    )
    submission_count = db.scalar(
        select(func.count()).select_from(Submission).where(Submission.competition_id == competition.id)
    )
    has_gt = (
        db.scalar(
            select(CompetitionGroundTruth.id).where(CompetitionGroundTruth.competition_id == competition.id)
        )
        is not None
    )
    return AdminCompetitionOut(
        id=competition.id,
        name=competition.name,
        ranking_published=competition.ranking_published,
        ground_truth_version=competition.ground_truth_version,
        has_ground_truth=has_gt,
        registration_count=int(registration_count or 0),
        submission_count=int(submission_count or 0),
        created_at=competition.created_at,
        updated_at=competition.updated_at,
    )


@router.get("/competitions", response_model=list[AdminCompetitionOut])
def list_competitions(_: AdminUser, db: DbSession) -> list[AdminCompetitionOut]:
    competitions = db.scalars(select(Competition).order_by(Competition.created_at.desc(), Competition.id.desc()))
    return [_admin_competition_out(db, c) for c in competitions]


@router.post("/competitions", response_model=AdminCompetitionOut, status_code=status.HTTP_201_CREATED)
def create_competition(payload: CompetitionCreate, _: AdminUser, db: DbSession) -> AdminCompetitionOut:
    competition = Competition(name=payload.name)
    db.add(competition)
    db.commit()
    db.refresh(competition)
    return _admin_competition_out(db, competition)


@router.patch("/competitions/{competition_id}", response_model=AdminCompetitionOut)
def update_competition(
    competition_id: int, payload: CompetitionUpdate, _: AdminUser, db: DbSession
) -> AdminCompetitionOut:
    competition = _get_competition_or_404(db, competition_id)
    if payload.name is None and payload.ranking_published is None:
        raise ApiError(422, "nothing_to_update", "Cần cung cấp `name` hoặc `ranking_published`.")
    if payload.name is not None:
        competition.name = payload.name
    if payload.ranking_published is not None:
        competition.ranking_published = payload.ranking_published
    db.commit()
    db.refresh(competition)
    return _admin_competition_out(db, competition)


@router.get("/competitions/{competition_id}/registrations", response_model=list[RegistrationOut])
def list_registrations(competition_id: int, _: AdminUser, db: DbSession) -> list[RegistrationOut]:
    competition = _get_competition_or_404(db, competition_id)
    stats_subq = (
        select(
            Submission.user_id.label("user_id"),
            func.count().label("submission_count"),
            func.max(Submission.score).label("best_score"),
        )
        .where(Submission.competition_id == competition.id)
        .group_by(Submission.user_id)
        .subquery()
    )
    stmt = (
        select(Registration, User, stats_subq.c.submission_count, stats_subq.c.best_score)
        .join(User, User.id == Registration.user_id)
        .outerjoin(stats_subq, stats_subq.c.user_id == Registration.user_id)
        .where(Registration.competition_id == competition.id)
        .order_by(Registration.created_at.asc(), Registration.id.asc())
    )
    return [
        RegistrationOut(
            id=registration.id,
            user=RegistrationUserOut.model_validate(user),
            created_at=registration.created_at,
            submission_count=int(count or 0),
            best_score=best,
        )
        for registration, user, count, best in db.execute(stmt)
    ]


@router.put("/competitions/{competition_id}/ground-truth", response_model=GroundTruthReplaceOut)
async def put_ground_truth(
    competition_id: int,
    admin: AdminUser,
    db: DbSession,
    file: UploadFile = File(...),
    confirm_reset: bool = Form(False),
) -> GroundTruthReplaceOut:
    competition = _get_competition_or_404(db, competition_id)
    settings = get_settings()
    try:
        data = await file.read(settings.csv_max_bytes + 1)
    finally:
        await file.close()
    if len(data) > settings.csv_max_bytes:
        raise ApiError(
            422,
            "csv_too_large",
            f"File vượt quá kích thước tối đa {settings.csv_max_bytes // (1024 * 1024)} MB.",
            max_bytes=settings.csv_max_bytes,
        )
    ground_truth, deleted = replace_ground_truth(
        db,
        competition,
        data=data,
        filename=file.filename or "ground_truth.csv",
        uploaded_by=admin,
        confirm_reset=confirm_reset,
    )
    return GroundTruthReplaceOut(
        metadata=ground_truth,
        ground_truth_version=competition.ground_truth_version,
        submissions_deleted=deleted,
    )


def _get_ground_truth_or_404(db: Session, competition_id: int) -> CompetitionGroundTruth:
    ground_truth = db.scalar(
        select(CompetitionGroundTruth).where(CompetitionGroundTruth.competition_id == competition_id)
    )
    if ground_truth is None:
        raise ApiError(404, "ground_truth_not_found", "Cuộc thi chưa có đáp án.")
    return ground_truth


@router.get("/competitions/{competition_id}/ground-truth", response_model=GroundTruthPreviewOut)
def get_ground_truth(
    competition_id: int,
    _: AdminUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> GroundTruthPreviewOut:
    competition = _get_competition_or_404(db, competition_id)
    ground_truth = _get_ground_truth_or_404(db, competition.id)
    total = int(
        db.scalar(
            select(func.count()).select_from(GroundTruthRow).where(GroundTruthRow.competition_id == competition.id)
        )
        or 0
    )
    rows = db.execute(
        select(GroundTruthRow.uuid, GroundTruthRow.is_spoof)
        .where(GroundTruthRow.competition_id == competition.id)
        .order_by(GroundTruthRow.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return GroundTruthPreviewOut(
        metadata=ground_truth,
        page=page,
        page_size=page_size,
        total=total,
        items=[GroundTruthRowOut(uuid=str(row.uuid), is_spoof=row.is_spoof) for row in rows],
    )


@router.get("/competitions/{competition_id}/ground-truth/download")
def download_ground_truth(competition_id: int, _: AdminUser, db: DbSession) -> Response:
    competition = _get_competition_or_404(db, competition_id)
    ground_truth = _get_ground_truth_or_404(db, competition.id)
    safe_name = ground_truth.filename.replace('"', "").replace("\r", "").replace("\n", "") or "ground_truth.csv"
    return Response(
        content=ground_truth.content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/competitions/{competition_id}/ranking", response_model=RankingOut)
def admin_ranking(competition_id: int, _: AdminUser, db: DbSession) -> RankingOut:
    competition = _get_competition_or_404(db, competition_id)
    entries = [RankingEntryOut(**row.__dict__) for row in compute_ranking(db, competition.id)]
    return RankingOut(
        competition_id=competition.id,
        competition_name=competition.name,
        published=competition.ranking_published,
        entries=entries,
    )
