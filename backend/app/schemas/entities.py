from pydantic import BaseModel, Field, field_validator


class AccountOut(BaseModel):
    id: int
    name: str
    meter_no: str
    note: str | None = None


class TierOut(BaseModel):
    id: int
    up_to: float | None
    price: float
    sort_order: int


class ReadingOut(BaseModel):
    id: int
    account_id: int
    kwh: float
    peak: int
    voided: int = 0
    void_reason: str | None = None
    voided_at: str | None = None


class VoidReadingRequest(BaseModel):
    # 作废原因必填，不允许纯空白串
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("作废原因不能为空")
        return v.strip()
