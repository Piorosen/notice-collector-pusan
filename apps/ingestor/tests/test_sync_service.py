from datetime import datetime, timedelta

from app.models import SyncJob
from app.services.sync_service import cleanup_stale_running_jobs


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.committed = False

    def scalars(self, _stmt):
        return _FakeScalarResult(self.rows)

    def commit(self):
        self.committed = True


def test_cleanup_stale_running_jobs_marks_timeout():
    stale = SyncJob(target="notices", status="running", updated_at=datetime.utcnow() - timedelta(minutes=15))
    db = _FakeDB([stale])

    changed = cleanup_stale_running_jobs(db, stale_minutes=10)

    assert changed == 1
    assert stale.status == "failed"
    assert "stale heartbeat timeout (10m)" in (stale.message or "")
    assert stale.error_summary and "stale_minutes" in stale.error_summary
    assert db.committed is True
