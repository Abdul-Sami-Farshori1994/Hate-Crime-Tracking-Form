from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import QuestionType, UserRole
from answer_normalize import ANSWER_MAX_LENGTH
from password_policy import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, validate_password_complexity


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SessionResponse(BaseModel):
    role: str
    username: str
    access_token: str | None = None
    mfa_required: bool = False
    mfa_setup_required: bool = False
    provisioning_uri: str | None = None


class MfaCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class TokenPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sub: str | None = None
    uid: int | None = None
    role: str | None = None
    tv: int | None = None

    @field_validator("uid", mode="before")
    @classmethod
    def coerce_uid(cls, v: object) -> int | None:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return None

    @field_validator("tv", mode="before")
    @classmethod
    def coerce_tv(cls, v: object) -> int | None:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool
    created_by_id: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class FormPageRead(BaseModel):
    id: int
    title: str
    description: str | None
    order_index: int

    model_config = {"from_attributes": True}


class FormPageCreate(BaseModel):
    title: str = Field(default="New page", min_length=1, max_length=500)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)


class FormPageUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)


class FormPageWithQuestions(BaseModel):
    id: int
    title: str
    description: str | None
    order_index: int
    questions: list["QuestionRead"]

    model_config = {"from_attributes": True}


class QuestionRead(BaseModel):
    id: int
    page_id: int
    question_text: str
    question_type: QuestionType
    options: list[Any] | dict[str, Any] | None = None
    is_required: bool
    order_index: int
    ms_forms_id: str | None = None
    help_text: str | None = None
    global_order: int | None = None

    model_config = {"from_attributes": True}


class QuestionBranchRead(BaseModel):
    source_ms_forms_id: str
    option_value: str
    target_ms_forms_id: str

    model_config = {"from_attributes": True}


class QuestionBranchRuleAdminRead(BaseModel):
    id: int
    option_value: str
    target_question_id: int | None = None
    target_question_text: str | None = None


class QuestionEditorRead(QuestionRead):
    branch_rules: list[QuestionBranchRuleAdminRead] = []
    is_hidden: bool = False


class FormPageEditorRead(BaseModel):
    id: int
    title: str
    description: str | None
    order_index: int
    questions: list[QuestionEditorRead]
    is_hidden: bool = False

    model_config = {"from_attributes": True}


class HiddenSectionSummary(BaseModel):
    id: int
    title: str
    description: str | None
    order_index: int
    question_count: int


class HiddenQuestionSummary(BaseModel):
    id: int
    page_id: int
    page_title: str
    question_text: str
    question_type: QuestionType


class HiddenFormStructureRead(BaseModel):
    sections: list[HiddenSectionSummary]
    questions: list[HiddenQuestionSummary]


class BranchRuleWrite(BaseModel):
    option_value: str = Field(min_length=1, max_length=2000)
    target_question_id: int = Field(ge=1)


class BranchRulesReplaceRequest(BaseModel):
    rules: list[BranchRuleWrite] = Field(default_factory=list)


class FormFlowResponse(BaseModel):
    pages: list[FormPageRead]
    questions: list[QuestionRead]
    branches: list[QuestionBranchRead]
    entry_ms_forms_id: str | None = None


class QuestionUpdate(BaseModel):
    question_text: str | None = None
    question_type: QuestionType | None = None
    options: list[Any] | dict[str, Any] | None = None
    is_required: bool | None = None
    order_index: int | None = None
    page_id: int | None = None

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: QuestionType | None) -> QuestionType | None:
        if v is not None and v not in QuestionType:
            raise ValueError(f"Unknown question_type: {v}")
        return v


class QuestionCreate(BaseModel):
    page_id: int | None = None
    question_text: str = Field(default="New question", min_length=1)
    question_type: QuestionType = QuestionType.text
    options: list[Any] | dict[str, Any] | None = None
    is_required: bool = False
    order_index: int | None = Field(default=None, ge=0)


class QuestionReorderItem(BaseModel):
    id: int
    page_id: int
    order_index: int = Field(ge=0)


class QuestionReorderRequest(BaseModel):
    items: list[QuestionReorderItem] = Field(min_length=1)


class AnswerItem(BaseModel):
    question_id: int
    answer_value: str = Field(min_length=0, max_length=ANSWER_MAX_LENGTH)


class ResponseSubmitRequest(BaseModel):
    answers: list[AnswerItem]
    consent_acknowledged: bool = False


class AnalyticsBar(BaseModel):
    label: str
    count: int


class AnalyticsQuestionBlock(BaseModel):
    question_id: int
    question_text: str
    question_type: str
    question_number: int
    chart_type: Literal["summary", "pie", "bar"]
    total_responses: int
    breakdown: list[AnalyticsBar]
    latest_responses: list[str] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    questions: list[AnalyticsQuestionBlock]
    total_sessions: int = 0


class ResponseAnswerDetail(BaseModel):
    question_id: int
    question_text: str
    question_type: str
    answer_value: str


class ResponseSessionSummary(BaseModel):
    session_id: str
    respondent_name: str | None = None
    submitted_at: datetime
    answer_count: int


class ResponseSessionListResponse(BaseModel):
    items: list[ResponseSessionSummary]
    next_cursor: str | None = None
    total_count: int


class ResponseSessionDetail(BaseModel):
    session_id: str
    respondent_name: str | None = None
    submitted_at: datetime
    answers: list[ResponseAnswerDetail]


class AuditEventRead(BaseModel):
    id: int
    user_id: int | None
    action: str
    resource_type: str
    resource_id: str | None
    detail: dict[str, Any] | list[Any] | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FormAccessRead(BaseModel):
    username: str
    is_active: bool


class FormAccessUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(
        default=None,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_password_complexity(v)
