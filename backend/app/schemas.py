from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator

from app.scoring import format_score
from app.security import MAX_PASSWORD_BYTES


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------


class UserOut(ORMModel):
    id: int
    name: str
    email: str | None
    username: str | None
    role: str


class SignupIn(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Họ tên không được để trống.")
        return value

    @field_validator("password")
    @classmethod
    def _password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Mật khẩu tối đa {MAX_PASSWORD_BYTES} byte.")
        return value


class LoginIn(BaseModel):
    identifier: Annotated[str, Field(min_length=1, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class OkOut(BaseModel):
    ok: bool = True


# ---------- Competitions (admin) ----------


class CompetitionCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]

    @field_validator("name")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tên cuộc thi không được để trống.")
        return value


class CompetitionUpdate(BaseModel):
    name: Annotated[str | None, Field(min_length=1, max_length=200)] = None
    ranking_published: bool | None = None

    @field_validator("name")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Tên cuộc thi không được để trống.")
        return value


class AdminCompetitionOut(BaseModel):
    id: int
    name: str
    ranking_published: bool
    ground_truth_version: int
    has_ground_truth: bool
    registration_count: int
    submission_count: int
    created_at: datetime
    updated_at: datetime


class ScoreMixin(BaseModel):
    @field_serializer("best_score", check_fields=False)
    def _ser_best(self, value: Decimal | None) -> str | None:
        return None if value is None else format_score(value)


class RegistrationUserOut(ORMModel):
    id: int
    name: str
    email: str | None


class RegistrationOut(ScoreMixin):
    id: int
    user: RegistrationUserOut
    created_at: datetime
    submission_count: int
    best_score: Decimal | None


class GroundTruthMetaOut(ORMModel):
    filename: str
    size_bytes: int
    row_count: int
    checksum_sha256: str
    version: int
    uploaded_at: datetime


class GroundTruthRowOut(BaseModel):
    uuid: str
    is_spoof: bool


class GroundTruthPreviewOut(BaseModel):
    metadata: GroundTruthMetaOut
    page: int
    page_size: int
    total: int
    items: list[GroundTruthRowOut]


class GroundTruthReplaceOut(BaseModel):
    metadata: GroundTruthMetaOut
    ground_truth_version: int
    submissions_deleted: int


# ---------- Ranking ----------


class RankingEntryOut(ScoreMixin):
    rank: int
    user_id: int
    name: str
    best_score: Decimal
    submission_count: int
    best_submitted_at: datetime


class RankingOut(BaseModel):
    competition_id: int
    competition_name: str
    published: bool
    entries: list[RankingEntryOut]


# ---------- Competitions (candidate) ----------


class CandidateCompetitionOut(BaseModel):
    id: int
    name: str
    ranking_published: bool
    has_ground_truth: bool
    created_at: datetime
    registered: bool
    registered_at: datetime | None


class CompetitionListOut(BaseModel):
    registered: list[CandidateCompetitionOut]
    unregistered: list[CandidateCompetitionOut]


class CandidateCompetitionDetailOut(CandidateCompetitionOut, ScoreMixin):
    ground_truth_version: int
    my_submission_count: int
    best_score: Decimal | None


class RegistrationStateOut(BaseModel):
    competition_id: int
    registered: bool
    registered_at: datetime
    created: bool


class SubmissionOut(BaseModel):
    id: int
    attempt_number: int
    score: Decimal
    ground_truth_version: int
    submitted_at: datetime

    @field_serializer("score")
    def _ser_score(self, value: Decimal) -> str:
        return format_score(value)
