"""作废与重测的服务层测试：每个会话使用独立临时库，不触碰真实数据。"""

import os
import tempfile

import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="ladderbill-test-")

from pydantic import ValidationError

from app.schemas.entities import VoidReadingRequest
from app.seed import init_db
from app.services.billing_service import (
    BillingService,
    ReadingAlreadyVoided,
    ReadingNotFound,
)


@pytest.fixture(scope="module", autouse=True)
def _seeded_db():
    init_db()


def test_default_list_excludes_voided_after_void():
    with BillingService() as svc:
        assert len(svc.list_readings()) == 2
        svc.void_reading(1, "抄表员录入错误")
        valid = svc.list_readings()
        all_rows = svc.list_readings(include_voided=True)
    assert [r["id"] for r in valid] == [2]
    assert {r["id"] for r in all_rows} == {1, 2}


def test_detail_returns_full_fields_and_reason_even_when_voided():
    with BillingService() as svc:
        row = svc.get_reading(1)
    assert row["voided"] == 1
    assert row["void_reason"] == "抄表员录入错误"
    assert row["voided_at"]
    assert set(row) >= {"id", "account_id", "kwh", "peak", "voided", "void_reason", "voided_at"}


def test_void_requires_non_blank_reason():
    for bad in ("", "   "):
        with pytest.raises(ValidationError):
            VoidReadingRequest(reason=bad)


def test_void_twice_is_conflict():
    with BillingService() as svc:
        with pytest.raises(ReadingAlreadyVoided):
            svc.void_reading(1, "再次作废")


def test_void_missing_reading_raises():
    with BillingService() as svc:
        with pytest.raises(ReadingNotFound):
            svc.void_reading(999, "不存在")


def test_rerun_creates_new_run_referencing_reading_and_keeps_old():
    with BillingService() as svc:
        before = [r for r in svc.list_history(200) if r["reading_id"] == 2]
        out = svc.rerun_reading(2)
        after = [r for r in svc.list_history(200) if r["reading_id"] == 2]
        new_run = svc.get_run(out["run_id"])
    # 新运行引用抄表 id，旧运行保留不覆盖
    assert len(after) == len(before) + 1
    assert new_run["reading_id"] == 2
    assert new_run["kind"] == "rerun"
    assert out["reading_id"] == 2
    # 种子抄表 2：400kWh 尖峰 ×1.2 → 309.60
    assert out["total"] == 309.60


def test_rerun_forbidden_on_voided_reading():
    with BillingService() as svc:
        with pytest.raises(ReadingAlreadyVoided):
            svc.rerun_reading(1)


def test_rerun_missing_reading_raises():
    with BillingService() as svc:
        with pytest.raises(ReadingNotFound):
            svc.rerun_reading(998)


def test_account_readings_default_filters_voided():
    with BillingService() as svc:
        valid = svc.readings_for_account(1)
        all_rows = svc.readings_for_account(1, include_voided=True)
    assert valid == []
    assert len(all_rows) == 1 and all_rows[0]["voided"] == 1


def test_dashboard_counts_only_valid_readings():
    with BillingService() as svc:
        stats = svc.dashboard_stats()
    assert stats["reading_count"] == 1
    assert stats["voided_reading_count"] == 1
