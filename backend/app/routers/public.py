from fastapi import APIRouter

from app.deps import DbSession
from app.errors import ApiError
from app.models import Competition
from app.schemas import RankingEntryOut, RankingOut
from app.services.ranking import compute_ranking

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/competitions/{competition_id}/ranking", response_model=RankingOut)
def public_ranking(competition_id: int, db: DbSession) -> RankingOut:
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise ApiError(404, "competition_not_found", "Không tìm thấy cuộc thi.")
    if not competition.ranking_published:
        # Nothing leaks while the ranking is hidden.
        return RankingOut(
            competition_id=competition.id,
            competition_name=competition.name,
            published=False,
            entries=[],
        )
    entries = [RankingEntryOut(**row.__dict__) for row in compute_ranking(db, competition.id)]
    return RankingOut(
        competition_id=competition.id,
        competition_name=competition.name,
        published=True,
        entries=entries,
    )
