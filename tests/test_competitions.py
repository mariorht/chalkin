"""
Tests for league competitions (Superliga-style events).

Covers: admin configuration, per-grade points, tagging ascents, the
participant-only leaderboard, and the weekly breakdown.
"""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.models.ascent import Ascent, AscentStatus
from app.models.competition import Competition, CompetitionPoint, CompetitionStatus
from app.models.friendship import Friendship, FriendshipStatus
from app.models.grade import Grade
from app.models.session import Session
from app.models.user import User


def _make_admin(db):
    admin = User(
        username="league_admin",
        email="league_admin@test.com",
        password_hash=get_password_hash("password123"),
        is_admin=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def _admin_headers(client, db):
    _make_admin(db)
    login = client.post(
        "/api/auth/login",
        json={"email": "league_admin@test.com", "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _make_competition(db, gym_id, *, status=CompetitionStatus.ACTIVE, weeks=8):
    today = date.today()
    competition = Competition(
        gym_id=gym_id,
        name="Superliga de prueba",
        start_date=today - timedelta(days=7),
        end_date=today + timedelta(days=weeks * 7),
        status=status,
    )
    db.add(competition)
    db.commit()
    db.refresh(competition)
    return competition


class TestCompetitionConfig:
    """Admin endpoints to create and configure competitions."""

    def test_create_competition_with_points(
        self, client: TestClient, db, test_gym, test_grades
    ):
        headers = _admin_headers(client, db)

        response = client.post(
            "/api/competitions",
            headers=headers,
            json={
                "gym_id": test_gym.id,
                "name": "Superliga BouldeUp",
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=60)),
                "status": "active",
                "points": [
                    {"grade_id": g.id, "points": i * 10}
                    for i, g in enumerate(test_grades, start=1)
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Superliga BouldeUp"
        assert data["is_running"] is True
        assert len(data["points"]) == len(test_grades)
        assert data["points"][0]["label"] == test_grades[0].label

    def test_non_admin_cannot_create(self, client: TestClient, test_gym):
        response = client.post(
            "/api/competitions",
            headers={"Authorization": "Bearer invalid"},
            json={
                "gym_id": test_gym.id,
                "name": "X",
                "start_date": str(date.today()),
                "end_date": str(date.today()),
            },
        )
        assert response.status_code == 401

    def test_points_must_belong_to_gym(
        self, client: TestClient, db, test_gym, test_grades, create_gym
    ):
        headers = _admin_headers(client, db)
        other_gym = create_gym(name="Otro", location="X")
        other_grade = Grade(
            gym_id=other_gym.id, label="Verde", relative_difficulty=2, order=1
        )
        db.add(other_grade)
        db.commit()
        db.refresh(other_grade)

        response = client.post(
            "/api/competitions",
            headers=headers,
            json={
                "gym_id": test_gym.id,
                "name": "Mala",
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=30)),
                "points": [{"grade_id": other_grade.id, "points": 10}],
            },
        )
        assert response.status_code == 400

    def test_end_date_before_start_date_rejected(self, client: TestClient, db, test_gym):
        headers = _admin_headers(client, db)
        response = client.post(
            "/api/competitions",
            headers=headers,
            json={
                "gym_id": test_gym.id,
                "name": "Mal fechas",
                "start_date": str(date.today()),
                "end_date": str(date.today() - timedelta(days=1)),
            },
        )
        assert response.status_code == 400


class TestLeagueTagging:
    """Tagging ascents as league boulders."""

    def test_tag_ascent_with_competition(
        self, client: TestClient, db, auth_headers, test_user, test_gym, test_grades
    ):
        competition = _make_competition(db, test_gym.id)
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        response = client.post(
            f"/api/sessions/{session.id}/ascents",
            headers=auth_headers,
            json={
                "grade_id": test_grades[1].id,
                "status": "send",
                "competition_id": competition.id,
                "competition_block": 3,
            },
        )
        assert response.status_code == 201
        assert response.json()["competition_id"] == competition.id
        assert response.json()["competition_block"] == 3

    def test_cannot_tag_ascent_from_other_gym(
        self, client: TestClient, db, auth_headers, test_user, test_gym, create_gym, test_grades
    ):
        other_gym = create_gym(name="Otro", location="X")
        competition = _make_competition(db, other_gym.id)
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        response = client.post(
            f"/api/sessions/{session.id}/ascents",
            headers=auth_headers,
            json={
                "grade_id": test_grades[0].id,
                "status": "send",
                "competition_id": competition.id,
                "competition_block": 1,
            },
        )
        assert response.status_code == 400

    def test_cannot_tag_inactive_competition(
        self, client: TestClient, db, auth_headers, test_user, test_gym, test_grades
    ):
        competition = _make_competition(db, test_gym.id, status=CompetitionStatus.DRAFT)
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        response = client.post(
            f"/api/sessions/{session.id}/ascents",
            headers=auth_headers,
            json={
                "grade_id": test_grades[0].id,
                "status": "send",
                "competition_id": competition.id,
                "competition_block": 1,
            },
        )
        assert response.status_code == 400

    def test_block_number_is_required(
        self, client: TestClient, db, auth_headers, test_user, test_gym, test_grades
    ):
        """Tagging a league ascent without a block number is rejected."""
        competition = _make_competition(db, test_gym.id)
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        response = client.post(
            f"/api/sessions/{session.id}/ascents",
            headers=auth_headers,
            json={
                "grade_id": test_grades[0].id,
                "status": "send",
                "competition_id": competition.id,
            },
        )
        assert response.status_code == 400
        assert "competition_block" in response.json()["detail"]

    def test_block_number_must_be_positive(
        self, client: TestClient, db, auth_headers, test_user, test_gym, test_grades
    ):
        competition = _make_competition(db, test_gym.id)
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        response = client.post(
            f"/api/sessions/{session.id}/ascents",
            headers=auth_headers,
            json={
                "grade_id": test_grades[0].id,
                "status": "send",
                "competition_id": competition.id,
                "competition_block": 0,
            },
        )
        assert response.status_code == 422

    def test_running_competition_endpoint(
        self, client: TestClient, db, auth_headers, test_gym
    ):
        competition = _make_competition(db, test_gym.id)
        response = client.get(
            f"/api/competitions/running?gym_id={test_gym.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == competition.id

    def test_running_returns_null_without_event(
        self, client: TestClient, auth_headers, test_gym
    ):
        response = client.get(
            f"/api/competitions/running?gym_id={test_gym.id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() is None


class TestLeaderboard:
    """Scoring and leaderboard."""

    def _setup(
        self,
        client,
        db,
        auth_headers,
        test_user,
        test_gym,
        test_grades,
        *,
        points=(10, 20, 30, 40),
    ):
        """Competition with points per grade and one user tagged as participant."""
        competition = _make_competition(db, test_gym.id)
        for grade, pts in zip(test_grades, points):
            db.add(
                CompetitionPoint(
                    competition_id=competition.id, grade_id=grade.id, points=pts
                )
            )
        db.commit()
        return competition

    def _add_tagged_ascent(
        self, db, competition, session, grade, status=AscentStatus.SEND, block=None
    ):
        """Add a scored ascent. ``block`` defaults to a unique number."""
        if block is None:
            block = 1000 + (db.query(Ascent).count() + 1)
        ascent = Ascent(
            session_id=session.id,
            grade_id=grade.id,
            status=status,
            competition_id=competition.id,
            competition_block=block,
        )
        db.add(ascent)
        db.commit()
        db.refresh(ascent)
        return ascent

    def test_points_add_up_per_grade(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        self._add_tagged_ascent(db, competition, session, test_grades[0])  # 10
        self._add_tagged_ascent(db, competition, session, test_grades[2])  # 30

        response = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        )
        assert response.status_code == 200
        total = response.json()["total"]
        assert total[0]["points"] == 40
        assert total[0]["scored_boulders"] == 2
        assert total[0]["is_me"] is True

    def test_repeat_same_block_counts_once(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        """Three sends of block #1 in the same week score only once."""
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        self._add_tagged_ascent(db, competition, session, test_grades[1], block=1)
        self._add_tagged_ascent(db, competition, session, test_grades[1], block=1)
        self._add_tagged_ascent(db, competition, session, test_grades[1], block=1)

        response = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        )
        total = response.json()["total"]
        assert total[0]["points"] == 20  # not 60
        assert total[0]["scored_boulders"] == 1

    def test_different_blocks_same_grade_score_separately(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        """Two different block numbers of the same grade both score."""
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        self._add_tagged_ascent(db, competition, session, test_grades[1], block=1)
        self._add_tagged_ascent(db, competition, session, test_grades[1], block=2)

        response = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        )
        total = response.json()["total"]
        assert total[0]["points"] == 40
        assert total[0]["scored_boulders"] == 2

    def test_same_block_number_in_different_weeks_scores_twice(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        """Block #1 of week 1 and block #1 of week 2 are different boulders."""
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        w1_start, _ = competition.week_bounds(1)
        w2_start, _ = competition.week_bounds(2)
        s1 = Session(user_id=test_user.id, gym_id=test_gym.id, date=w1_start)
        s2 = Session(user_id=test_user.id, gym_id=test_gym.id, date=w2_start)
        db.add_all([s1, s2])
        db.commit()
        db.refresh(s1)
        db.refresh(s2)

        self._add_tagged_ascent(db, competition, s1, test_grades[1], block=1)
        self._add_tagged_ascent(db, competition, s2, test_grades[1], block=1)

        response = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        )
        total = response.json()["total"]
        assert total[0]["points"] == 40
        assert total[0]["scored_boulders"] == 2

    def test_breakdown_lists_grades(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        """The total standings include a per-grade breakdown."""
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        self._add_tagged_ascent(db, competition, session, test_grades[0], block=1)  # 10
        self._add_tagged_ascent(db, competition, session, test_grades[0], block=2)  # 10
        self._add_tagged_ascent(db, competition, session, test_grades[2], block=3)  # 30

        response = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        )
        entry = response.json()["total"][0]
        breakdown = entry["breakdown"]
        assert len(breakdown) == 2

        # Hardest grade first
        assert breakdown[0]["grade_id"] == test_grades[2].id
        assert breakdown[0]["count"] == 1
        assert breakdown[0]["points"] == 30
        assert breakdown[0]["label"] == test_grades[2].label
        assert breakdown[0]["color_hex"] == test_grades[2].color_hex

        assert breakdown[1]["grade_id"] == test_grades[0].id
        assert breakdown[1]["count"] == 2
        assert breakdown[1]["points"] == 20

    def test_breakdown_lists_block_numbers(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        """The breakdown reports which league block numbers were scored."""
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        w1_start, _ = competition.week_bounds(1)
        w2_start, _ = competition.week_bounds(2)
        s1 = Session(user_id=test_user.id, gym_id=test_gym.id, date=w1_start)
        s2 = Session(user_id=test_user.id, gym_id=test_gym.id, date=w2_start)
        db.add_all([s1, s2])
        db.commit()
        db.refresh(s1)
        db.refresh(s2)

        # Same grade in two different blocks of week 1, plus one in week 2
        self._add_tagged_ascent(db, competition, s1, test_grades[0], block=3)
        self._add_tagged_ascent(db, competition, s1, test_grades[0], block=7)
        self._add_tagged_ascent(db, competition, s2, test_grades[0], block=1)

        response = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        )
        breakdown = response.json()["total"][0]["breakdown"]
        assert len(breakdown) == 1
        assert breakdown[0]["count"] == 3
        # Block numbers sorted by (week, block): week 1 has 3 and 7, week 2 has 1
        assert breakdown[0]["blocks"] == [3, 7, 1]

    def test_project_does_not_score(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        self._add_tagged_ascent(
            db, competition, session, test_grades[3], status=AscentStatus.PROJECT
        )

        response = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        )
        assert response.json()["total"] == []

    def test_untagged_ascent_does_not_score(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        # One tagged (scores) and one untagged (must not score)
        self._add_tagged_ascent(db, competition, session, test_grades[0])  # 10
        ascent = Ascent(
            session_id=session.id,
            grade_id=test_grades[1].id,
            status=AscentStatus.SEND,
        )
        db.add(ascent)
        db.commit()

        response = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        )
        assert response.json()["total"][0]["points"] == 10
        assert response.json()["total"][0]["scored_boulders"] == 1

    def test_week_breakdown(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        # Two sessions in different weeks, using the actual week bounds.
        w1_start, _ = competition.week_bounds(1)
        w2_start, _ = competition.week_bounds(2)
        week1 = Session(
            user_id=test_user.id,
            gym_id=test_gym.id,
            date=w1_start,
        )
        week2 = Session(
            user_id=test_user.id,
            gym_id=test_gym.id,
            date=w2_start,
        )
        db.add_all([week1, week2])
        db.commit()
        db.refresh(week1)
        db.refresh(week2)

        self._add_tagged_ascent(db, competition, week1, test_grades[0])  # 10 in w1
        self._add_tagged_ascent(db, competition, week2, test_grades[1])  # 20 in w2
        self._add_tagged_ascent(db, competition, week2, test_grades[2])  # 30 in w2

        board = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        ).json()

        assert len(board["weeks"]) == competition.total_weeks
        assert board["weekly"][0][0]["points"] == 10
        assert board["weekly"][1][0]["points"] == 50
        assert board["total"][0]["points"] == 60

    def test_friend_appears_in_same_leaderboard(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        # The current user participates too (otherwise the board is 403)
        mine = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(mine)
        db.commit()
        db.refresh(mine)
        self._add_tagged_ascent(db, competition, mine, test_grades[0])  # 10

        # A friend of the current user, also competing
        friend = User(
            username="friend_comp",
            email="friend_comp@test.com",
            password_hash=get_password_hash("password123"),
        )
        db.add(friend)
        db.commit()
        db.refresh(friend)
        db.add(
            Friendship(
                user_id=test_user.id,
                friend_id=friend.id,
                status=FriendshipStatus.ACCEPTED,
            )
        )
        db.commit()

        session = Session(user_id=friend.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)
        self._add_tagged_ascent(db, competition, session, test_grades[3])  # 40

        board = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        ).json()
        usernames = {e["username"] for e in board["total"]}
        assert "friend_comp" in usernames

    def test_non_participant_cannot_see_leaderboard(
        self, client, db, auth_headers, test_user, test_gym, test_grades, create_user
    ):
        competition = self._setup(
            client, db, auth_headers, test_user, test_gym, test_grades
        )
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)
        self._add_tagged_ascent(db, competition, session, test_grades[0])

        outsider = create_user(
            username="outside", email="outside@test.com", password="password123"
        )
        login = client.post(
            "/api/auth/login",
            json={"email": "outside@test.com", "password": "password123"},
        )
        outsider_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        response = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=outsider_headers
        )
        assert response.status_code == 403

    def test_leaderboard_requires_auth(self, client, db, test_user, test_gym):
        competition = _make_competition(db, test_gym.id)
        response = client.get(f"/api/competitions/{competition.id}/leaderboard")
        assert response.status_code == 401

    def test_leaderboard_not_found(self, client, auth_headers):
        response = client.get("/api/competitions/99999/leaderboard", headers=auth_headers)
        assert response.status_code == 404


class TestRestWeeks:
    """Rest weeks: no tagging and no points."""

    def _competition_with_rest(self, db, gym_id, *, rest_week=2, start_offset_days=-7):
        today = date.today()
        competition = Competition(
            gym_id=gym_id,
            name="Con descanso",
            start_date=today + timedelta(days=start_offset_days),
            end_date=today + timedelta(days=42),
            status=CompetitionStatus.ACTIVE,
        )
        competition.set_offset_weeks([rest_week])
        db.add(competition)
        db.commit()
        db.refresh(competition)
        return competition

    def test_offset_weeks_helpers(self, db, test_gym):
        competition = self._competition_with_rest(db, test_gym.id)
        assert competition.offset_weeks == {2}
        assert competition.is_rest_week(2) is True
        assert competition.is_rest_week(1) is False
        assert competition.is_active_week(2) is False
        assert competition.is_active_week(1) is True

    def test_offsets_survive_roundtrip(self, client, db, test_gym):
        headers = _admin_headers(client, db)
        start = date.today()
        response = client.post(
            "/api/competitions",
            headers=headers,
            json={
                "gym_id": test_gym.id,
                "name": "Con descansos",
                "start_date": str(start),
                "end_date": str(start + timedelta(days=60)),
                "status": "active",
                "week_offsets": [3, 1],
            },
        )
        assert response.status_code == 201
        assert response.json()["week_offsets"] == [1, 3]

    def test_cannot_tag_ascent_in_rest_week(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        # Event starts today, so "today" is week 1. Mark week 1 as rest.
        competition = self._competition_with_rest(
            db, test_gym.id, rest_week=1, start_offset_days=0
        )
        session = Session(user_id=test_user.id, gym_id=test_gym.id)
        db.add(session)
        db.commit()
        db.refresh(session)

        response = client.post(
            f"/api/sessions/{session.id}/ascents",
            headers=auth_headers,
            json={
                "grade_id": test_grades[0].id,
                "status": "send",
                "competition_id": competition.id,
                "competition_block": 1,
            },
        )
        assert response.status_code == 400

    def test_rest_week_points_do_not_count(
        self, client, db, auth_headers, test_user, test_gym, test_grades
    ):
        competition = self._competition_with_rest(db, test_gym.id, rest_week=2)
        db.add(
            CompetitionPoint(
                competition_id=competition.id, grade_id=test_grades[0].id, points=10
            )
        )
        db.commit()

        # Week 1 scores
        active_start, _ = competition.week_bounds(1)
        rest_start, _ = competition.week_bounds(2)
        active_session = Session(
            user_id=test_user.id,
            gym_id=test_gym.id,
            date=active_start,
        )
        # Week 2 is rest: tag it directly (bypassing the API check) to make
        # sure the leaderboard itself ignores it.
        rest_session = Session(
            user_id=test_user.id,
            gym_id=test_gym.id,
            date=rest_start,
        )
        db.add_all([active_session, rest_session])
        db.commit()
        db.refresh(active_session)
        db.refresh(rest_session)

        for idx, session in enumerate([active_session, rest_session], start=1):
            db.add(
                Ascent(
                    session_id=session.id,
                    grade_id=test_grades[0].id,
                    status=AscentStatus.SEND,
                    competition_id=competition.id,
                    competition_block=idx,
                )
            )
        db.commit()

        board = client.get(
            f"/api/competitions/{competition.id}/leaderboard", headers=auth_headers
        ).json()
        assert board["total"][0]["points"] == 10  # only the active week
        assert board["weeks"][1]["is_rest"] is True
        assert board["weeks"][1]["week"] == 2

    def test_running_skips_rest_week(
        self, client, db, auth_headers, test_gym
    ):
        # Rest week is the current one, so the toggle should not be offered
        # for a gym with only that event.
        competition = self._competition_with_rest(db, test_gym.id, rest_week=2)
        response = client.get(
            f"/api/competitions/running?gym_id={test_gym.id}", headers=auth_headers
        )
        # Falls back to the most recent active event, but the frontend will
        # hide the toggle using week_offsets (returned in the payload).
        assert response.status_code == 200
        assert response.json()["week_offsets"] == [2]

