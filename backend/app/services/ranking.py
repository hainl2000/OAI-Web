from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Submission, User


@dataclass
class RankingRow:
    rank: int
    user_id: int
    name: str
    best_score: Decimal
    submission_count: int
    best_submitted_at: datetime


def compute_ranking(db: Session, competition_id: int) -> list[RankingRow]:
    """Best score per candidate; ties broken by earliest best submission, then user id."""
    best_stmt = (
        select(Submission.user_id, Submission.score, Submission.submitted_at, User.name)
        .join(User, User.id == Submission.user_id)
        .where(Submission.competition_id == competition_id)
        .distinct(Submission.user_id)
        .order_by(
            Submission.user_id,
            Submission.score.desc(),
            Submission.submitted_at.asc(),
            Submission.id.asc(),
        )
    )
    counts_stmt = (
        select(Submission.user_id, func.count().label("n"))
        .where(Submission.competition_id == competition_id)
        .group_by(Submission.user_id)
    )
    counts = {row.user_id: int(row.n) for row in db.execute(counts_stmt)}

    rows = [
        (row.user_id, Decimal(row.score), row.submitted_at, row.name)
        for row in db.execute(best_stmt)
    ]
    rows.sort(key=lambda r: (-r[1], r[2], r[0]))
    return [
        RankingRow(
            rank=index,
            user_id=user_id,
            name=name,
            best_score=score,
            submission_count=counts.get(user_id, 0),
            best_submitted_at=submitted_at,
        )
        for index, (user_id, score, submitted_at, name) in enumerate(rows, start=1)
    ]
