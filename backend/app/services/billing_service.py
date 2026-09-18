from app.db import connect
from app.engines.peak_compare import compare_plain_vs_peak
from app.engines.tier_progressive import calc_bill
from app.repositories import accounts as accounts_repo
from app.repositories import readings as readings_repo
from app.repositories import runs as runs_repo
from app.repositories import settings as settings_repo
from app.repositories import tiers as tiers_repo


class ReadingNotFound(LookupError):
    pass


class ReadingAlreadyVoided(ValueError):
    pass


class BillingService:
    def __init__(self):
        self._conn = connect()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def list_accounts(self):
        return accounts_repo.list_all(self._conn)

    def get_account(self, account_id: int):
        return accounts_repo.get(self._conn, account_id)

    def list_tiers(self):
        return tiers_repo.list_ordered(self._conn)

    def list_readings(self, include_voided: bool = False):
        return readings_repo.list_all(self._conn, include_voided=include_voided)

    def get_reading(self, reading_id: int):
        row = readings_repo.get(self._conn, reading_id)
        if not row:
            raise ReadingNotFound(reading_id)
        return row

    def readings_for_account(self, account_id: int, include_voided: bool = False):
        return readings_repo.for_account(
            self._conn, account_id, include_voided=include_voided
        )

    def void_reading(self, reading_id: int, reason: str):
        reading = readings_repo.get(self._conn, reading_id)
        if not reading:
            raise ReadingNotFound(reading_id)
        if reading["voided"]:
            raise ReadingAlreadyVoided(reading_id)
        row = readings_repo.mark_voided(self._conn, reading_id, reason.strip())
        # 理论上前置校验后不会为 None，防御并发下重复作废
        if not row:
            raise ReadingAlreadyVoided(reading_id)
        return row

    def rerun_reading(self, reading_id: int):
        """基于一条有效抄表生成新的测算运行；旧运行保留不动。"""
        reading = readings_repo.get(self._conn, reading_id)
        if not reading:
            raise ReadingNotFound(reading_id)
        if reading["voided"]:
            raise ReadingAlreadyVoided(reading_id)
        tiers = tiers_repo.as_calc_rows(self._conn)
        pf = settings_repo.peak_factor(self._conn)
        factor = pf if reading["peak"] else 1.0
        result = calc_bill(reading["kwh"], tiers, factor)
        payload = {
            "kwh": reading["kwh"],
            "peak": bool(reading["peak"]),
            "account_id": reading["account_id"],
            "reading_id": reading["id"],
            "rerun": True,
        }
        run_id = runs_repo.insert(
            self._conn,
            "rerun",
            payload,
            result,
            reading["account_id"],
            reading_id=reading["id"],
        )
        return {"run_id": run_id, "reading_id": reading["id"], **result}

    def settings_map(self):
        return settings_repo.get_map(self._conn)

    def run_bill(self, kwh: float, peak: bool, account_id: int | None, persist: bool):
        tiers = tiers_repo.as_calc_rows(self._conn)
        pf = settings_repo.peak_factor(self._conn)
        factor = pf if peak else 1.0
        result = calc_bill(kwh, tiers, factor)
        run_id = None
        if persist:
            run_id = runs_repo.insert(
                self._conn,
                "bill",
                {"kwh": kwh, "peak": peak, "account_id": account_id},
                result,
                account_id,
            )
        return {"run_id": run_id, **result}

    def run_compare(self, kwh: float, persist: bool):
        tiers = tiers_repo.as_calc_rows(self._conn)
        pf = settings_repo.peak_factor(self._conn)
        result = compare_plain_vs_peak(kwh, tiers, pf)
        run_id = None
        if persist:
            run_id = runs_repo.insert(self._conn, "compare", {"kwh": kwh}, result, None)
        return {"run_id": run_id, **result}

    def list_history(self, limit: int = 50):
        return runs_repo.list_recent(self._conn, limit)

    def get_run(self, run_id: int):
        return runs_repo.get(self._conn, run_id)

    def dashboard_stats(self):
        accounts = accounts_repo.list_all(self._conn)
        valid_readings = readings_repo.list_all(self._conn, include_voided=False)
        all_readings = readings_repo.list_all(self._conn, include_voided=True)
        clean = [a for a in accounts if "种子" not in a.get("name", "")]
        dirty = [a for a in accounts if "种子" in a.get("name", "")]
        return {
            "account_count": len(accounts),
            "reading_count": len(valid_readings),
            "voided_reading_count": len(all_readings) - len(valid_readings),
            "clean_accounts": len(clean),
            "dirty_accounts": len(dirty),
            "recent_runs": len(runs_repo.list_recent(self._conn, 5)),
        }
