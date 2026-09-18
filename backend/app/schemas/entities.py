from pydantic import BaseModel


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
    account_id: int | None = None
    kwh: float
    peak: int = 0
    voided: int = 0
    void_reason: str | None = None
    voided_at: str | None = None
