from fastapi import APIRouter, HTTPException, Query

from app.schemas.readings import VoidReadingRequest
from app.services.billing_service import (
    BillingService,
    ReadingNotFoundError,
    ReadingVoidedError,
)

router = APIRouter(tags=["readings"])


@router.get("/readings")
def list_readings(include_voided: bool = Query(False, description="是否包含已作废抄表")):
    with BillingService() as svc:
        items = svc.list_readings(include_voided)
        total_kwh = sum(r["kwh"] for r in items)
        return {"items": items, "total_kwh": total_kwh}


@router.get("/readings/{reading_id}")
def get_reading(reading_id: int):
    with BillingService() as svc:
        row = svc.get_reading(reading_id)
        if not row:
            raise HTTPException(404, "reading not found")
        return row


@router.post("/readings/{reading_id}/void")
def void_reading(reading_id: int, body: VoidReadingRequest):
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(422, "void reason is required")
    with BillingService() as svc:
        try:
            return svc.void_reading(reading_id, reason)
        except ReadingNotFoundError:
            raise HTTPException(404, "reading not found")
        except ReadingVoidedError:
            raise HTTPException(409, "reading already voided")


@router.post("/readings/{reading_id}/retest")
def retest_reading(reading_id: int):
    with BillingService() as svc:
        try:
            return svc.retest_reading(reading_id)
        except ReadingNotFoundError:
            raise HTTPException(404, "reading not found")
        except ReadingVoidedError:
            raise HTTPException(409, "voided readings cannot be retested")
