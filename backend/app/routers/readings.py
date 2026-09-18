from fastapi import APIRouter, HTTPException

from app.schemas.entities import VoidReadingRequest
from app.services.billing_service import (
    BillingService,
    ReadingAlreadyVoided,
    ReadingNotFound,
)

router = APIRouter(tags=["readings"])


@router.get("/readings")
def list_readings(include_voided: bool = False):
    # 默认仅返回有效抄表（不参与作废数据的列表合计与测算候选）
    with BillingService() as svc:
        return {"items": svc.list_readings(include_voided=include_voided)}


@router.get("/readings/{reading_id}")
def get_reading(reading_id: int):
    # 详情接口对已作废抄表同样返回完整字段与作废原因
    with BillingService() as svc:
        try:
            return svc.get_reading(reading_id)
        except ReadingNotFound:
            raise HTTPException(404, "reading not found")


@router.post("/readings/{reading_id}/void")
def void_reading(reading_id: int, body: VoidReadingRequest):
    with BillingService() as svc:
        try:
            return svc.void_reading(reading_id, body.reason)
        except ReadingNotFound:
            raise HTTPException(404, "reading not found")
        except ReadingAlreadyVoided:
            raise HTTPException(409, "reading already voided")


@router.post("/readings/{reading_id}/rerun")
def rerun_reading(reading_id: int):
    with BillingService() as svc:
        try:
            return svc.rerun_reading(reading_id)
        except ReadingNotFound:
            raise HTTPException(404, "reading not found")
        except ReadingAlreadyVoided:
            raise HTTPException(409, "cannot rerun a voided reading")
