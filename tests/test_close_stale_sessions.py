"""
Tests for the stale-session closing script.

The script is imported directly (its ``main`` is only run under
``__main__``), so these tests exercise the pure logic against the
in-memory test database.
"""
from datetime import datetime, timedelta

from app.models.session import Session


class TestFindStaleSessions:
    """Tests for find_stale_sessions()."""

    def _make_session(self, db, user_id, started_at, ended_at=None):
        session = Session(
            user_id=user_id,
            started_at=started_at,
            ended_at=ended_at,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def test_finds_only_old_open_sessions(self, db, test_user):
        from close_stale_sessions import find_stale_sessions

        now = datetime.utcnow()
        old_open = self._make_session(db, test_user.id, now - timedelta(days=10))
        recent_open = self._make_session(db, test_user.id, now - timedelta(days=2))
        old_closed = self._make_session(
            db, test_user.id, now - timedelta(days=10), ended_at=now - timedelta(days=9)
        )

        found = find_stale_sessions(db, cutoff=now - timedelta(days=7))

        ids = [s.id for s in found]
        assert old_open.id in ids
        assert recent_open.id not in ids
        assert old_closed.id not in ids

    def test_started_at_is_never_null_because_of_model_default(self, db, test_user):
        """
        ``started_at`` has a column default, so it is never null even if the
        caller passes None. The script can therefore rely on it.
        """
        now = datetime.utcnow()
        session = Session(user_id=test_user.id, started_at=None)
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.started_at is not None


class TestCloseStaleSessions:
    """Tests for close_stale_sessions()."""

    def test_closes_stale_sessions(self, db, test_user):
        from close_stale_sessions import close_stale_sessions

        now = datetime.utcnow()
        stale = Session(
            user_id=test_user.id, started_at=now - timedelta(days=20), ended_at=None
        )
        recent = Session(
            user_id=test_user.id, started_at=now - timedelta(days=1), ended_at=None
        )
        db.add_all([stale, recent])
        db.commit()
        db.refresh(stale)
        db.refresh(recent)

        closed = close_stale_sessions(db, days=7, now=now)
        db.refresh(stale)
        db.refresh(recent)

        assert [s.id for s in closed] == [stale.id]
        assert stale.ended_at is not None
        assert recent.ended_at is None

    def test_dry_run_does_not_modify(self, db, test_user):
        from close_stale_sessions import close_stale_sessions

        now = datetime.utcnow()
        stale = Session(
            user_id=test_user.id, started_at=now - timedelta(days=20), ended_at=None
        )
        db.add(stale)
        db.commit()
        db.refresh(stale)

        found = close_stale_sessions(db, days=7, now=now, dry_run=True)
        db.refresh(stale)

        assert [s.id for s in found] == [stale.id]
        assert stale.ended_at is None

    def test_closes_at_one_hour_after_start(self, db, test_user):
        """A very old open session is closed one hour after it started."""
        from close_stale_sessions import close_stale_sessions

        now = datetime.utcnow()
        started = now - timedelta(days=30)
        stale = Session(user_id=test_user.id, started_at=started, ended_at=None)
        db.add(stale)
        db.commit()
        db.refresh(stale)

        close_stale_sessions(db, days=7, now=now)
        db.refresh(stale)

        assert stale.ended_at == started + timedelta(hours=1)

    def test_nothing_to_close(self, db, test_user):
        from close_stale_sessions import close_stale_sessions

        now = datetime.utcnow()
        session = Session(
            user_id=test_user.id, started_at=now - timedelta(days=1), ended_at=None
        )
        db.add(session)
        db.commit()

        closed = close_stale_sessions(db, days=7, now=now)
        assert closed == []
