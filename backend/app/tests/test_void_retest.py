import os
import tempfile

import pytest


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app import seed
    from app.services.billing_service import BillingService, ReadingVoidedError, ReadingNotFoundError

    # config reads DATA_DIR at import time; reload it before opening a connection
    import importlib

    import app.config as config

    importlib.reload(config)
    import app.db as db

    importlib.reload(db)
    import app.repositories.readings as readings_repo
    import app.repositories.runs as runs_repo
    import app.repositories.settings as settings_repo
    import app.repositories.tiers as tiers_repo
    import app.services.billing_service as billing_service

    importlib.reload(readings_repo)
    importlib.reload(runs_repo)
    importlib.reload(settings_repo)
    importlib.reload(tiers_repo)
    importlib.reload(billing_service)
    importlib.reload(seed)
    seed.init_db()
    with billing_service.BillingService() as s:
        yield s, billing_service


def test_voided_reading_excluded_from_default_list(svc):
    s, _ = svc
    s.void_reading(1, "抄表串户")
    assert [r["id"] for r in s.list_readings()] == [2]
    assert {r["id"] for r in s.list_readings(include_voided=True)} == {1, 2}


def test_void_records_reason_and_timestamp(svc):
    s, _ = svc
    row = s.void_reading(1, "  表计故障  ")
    assert row["voided"] == 1
    assert row["void_reason"] == "表计故障"
    assert row["voided_at"]


def test_detail_still_returns_full_fields_after_void(svc):
    s, _ = svc
    s.void_reading(1, "串户")
    detail = s.get_reading(1)
    assert detail["voided"] == 1
    assert detail["void_reason"] == "串户"
    assert detail["kwh"] == 120


def test_cannot_void_twice(svc):
    s, bsm = svc
    s.void_reading(1, "原因")
    with pytest.raises(bsm.ReadingVoidedError):
        s.void_reading(1, "再次作废")


def test_void_missing_reading(svc):
    s, bsm = svc
    with pytest.raises(bsm.ReadingNotFoundError):
        s.void_reading(999, "原因")


def test_retest_creates_new_run_referencing_reading_and_keeps_old(svc):
    s, _ = svc
    before = {r["id"] for r in s.list_history()}
    out = s.retest_reading(2)
    run = s.get_run(out["run_id"])
    assert run["kind"] == "retest"
    assert run["reading_id"] == 2
    assert out["reading_id"] == 2
    # old run remains
    assert before.issubset({r["id"] for r in s.list_history()})
    # a second retest creates yet another run, never overwriting
    out2 = s.retest_reading(2)
    assert out2["run_id"] != out["run_id"]
    assert s.get_run(out["run_id"]) is not None


def test_retest_rejected_for_voided_reading(svc):
    s, bsm = svc
    s.void_reading(1, "串户")
    with pytest.raises(bsm.ReadingVoidedError):
        s.retest_reading(1)
