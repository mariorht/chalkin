"""
Tests for social features - friends and feed.
"""
import pytest
from fastapi.testclient import TestClient


class TestUserSearch:
    """Tests for user search endpoint."""

    def test_search_users(self, client: TestClient, auth_headers, create_user):
        """Test searching for users."""
        # Create another user to search for
        create_user(username="searchable_user", email="search@test.com", password="password123")
        
        response = client.get(
            "/api/social/search?q=searchable",
            headers=auth_headers
        )
        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 1
        assert any(u["username"] == "searchable_user" for u in users)

    def test_search_requires_min_chars(self, client: TestClient, auth_headers):
        """Test that search requires minimum 2 characters."""
        response = client.get(
            "/api/social/search?q=a",
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error

    def test_search_excludes_current_user(self, client: TestClient, auth_headers):
        """Test that current user is not in search results."""
        response = client.get(
            "/api/social/search?q=test",  # "testuser" is the default test user
            headers=auth_headers
        )
        assert response.status_code == 200
        users = response.json()
        # The logged in user should not appear
        assert not any(u["username"] == "testuser" for u in users)


class TestFriendRequests:
    """Tests for friend request functionality."""

    def test_send_friend_request(self, client: TestClient, auth_headers, create_user):
        """Test sending a friend request."""
        other_user = create_user(username="friend_candidate", email="friend@test.com", password="password123")
        
        response = client.post(
            "/api/social/friends",
            headers=auth_headers,
            json={"friend_id": other_user.id}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["friend_id"] == other_user.id

    def test_cannot_friend_yourself(self, client: TestClient, auth_headers, test_user):
        """Test that you cannot send friend request to yourself."""
        response = client.post(
            "/api/social/friends",
            headers=auth_headers,
            json={"friend_id": test_user.id}
        )
        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()

    def test_cannot_duplicate_request(self, client: TestClient, auth_headers, create_user):
        """Test that duplicate friend requests are rejected."""
        other_user = create_user(username="duplicate_test", email="dup@test.com", password="password123")
        
        # First request
        client.post(
            "/api/social/friends",
            headers=auth_headers,
            json={"friend_id": other_user.id}
        )
        
        # Duplicate request
        response = client.post(
            "/api/social/friends",
            headers=auth_headers,
            json={"friend_id": other_user.id}
        )
        assert response.status_code == 400

    def test_list_pending_requests(self, client: TestClient, auth_headers, create_user, db):
        """Test listing pending friend requests."""
        # Create user who will send request
        sender = create_user(username="sender_user", email="sender@test.com", password="password123")
        
        # Login as sender and send request
        login_response = client.post(
            "/api/auth/login",
            json={"email": "sender@test.com", "password": "password123"}
        )
        sender_token = login_response.json()["access_token"]
        sender_headers = {"Authorization": f"Bearer {sender_token}"}
        
        # Get the test user's ID (recipient)
        me_response = client.get("/api/auth/me", headers=auth_headers)
        test_user_id = me_response.json()["id"]
        
        # Send request from sender to test user
        client.post(
            "/api/social/friends",
            headers=sender_headers,
            json={"friend_id": test_user_id}
        )
        
        # List requests as test user
        response = client.get(
            "/api/social/friends/requests",
            headers=auth_headers
        )
        assert response.status_code == 200
        requests = response.json()
        assert len(requests) >= 1
        assert any(r["user_username"] == "sender_user" for r in requests)


class TestAcceptRejectFriends:
    """Tests for accepting and rejecting friend requests."""

    def test_accept_friend_request(self, client: TestClient, auth_headers, create_user):
        """Test accepting a friend request."""
        # Create and login as sender
        sender = create_user(username="accept_sender", email="acceptsend@test.com", password="password123")
        login = client.post("/api/auth/login", json={"email": "acceptsend@test.com", "password": "password123"})
        sender_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        
        # Get test user ID
        me = client.get("/api/auth/me", headers=auth_headers)
        test_user_id = me.json()["id"]
        
        # Send request
        req = client.post("/api/social/friends", headers=sender_headers, json={"friend_id": test_user_id})
        
        # Get the request ID
        requests = client.get("/api/social/friends/requests", headers=auth_headers)
        request_id = requests.json()[0]["id"]
        
        # Accept
        response = client.post(f"/api/social/friends/requests/{request_id}/accept", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_reject_friend_request(self, client: TestClient, auth_headers, create_user):
        """Test rejecting a friend request."""
        # Create and login as sender
        sender = create_user(username="reject_sender", email="rejectsend@test.com", password="password123")
        login = client.post("/api/auth/login", json={"email": "rejectsend@test.com", "password": "password123"})
        sender_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        
        # Get test user ID
        me = client.get("/api/auth/me", headers=auth_headers)
        test_user_id = me.json()["id"]
        
        # Send request
        client.post("/api/social/friends", headers=sender_headers, json={"friend_id": test_user_id})
        
        # Get the request ID
        requests = client.get("/api/social/friends/requests", headers=auth_headers)
        request_id = requests.json()[0]["id"]
        
        # Reject
        response = client.post(f"/api/social/friends/requests/{request_id}/reject", headers=auth_headers)
        assert response.status_code == 204


class TestFriendsList:
    """Tests for friends list functionality."""

    def test_list_friends(self, client: TestClient, auth_headers, create_user):
        """Test listing accepted friends."""
        # Create and become friends with another user
        other = create_user(username="list_friend", email="listfriend@test.com", password="password123")
        login = client.post("/api/auth/login", json={"email": "listfriend@test.com", "password": "password123"})
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        
        # Get test user ID
        me = client.get("/api/auth/me", headers=auth_headers)
        test_user_id = me.json()["id"]
        
        # Send request from other to test user
        client.post("/api/social/friends", headers=other_headers, json={"friend_id": test_user_id})
        
        # Accept as test user
        requests = client.get("/api/social/friends/requests", headers=auth_headers)
        request_id = requests.json()[0]["id"]
        client.post(f"/api/social/friends/requests/{request_id}/accept", headers=auth_headers)
        
        # List friends
        response = client.get("/api/social/friends", headers=auth_headers)
        assert response.status_code == 200
        friends = response.json()
        assert len(friends) >= 1
        assert any(f["username"] == "list_friend" for f in friends)

    def test_remove_friend(self, client: TestClient, auth_headers, create_user):
        """Test removing a friend."""
        # Create and become friends
        other = create_user(username="remove_friend", email="removefriend@test.com", password="password123")
        login = client.post("/api/auth/login", json={"email": "removefriend@test.com", "password": "password123"})
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        
        me = client.get("/api/auth/me", headers=auth_headers)
        test_user_id = me.json()["id"]
        
        client.post("/api/social/friends", headers=other_headers, json={"friend_id": test_user_id})
        requests = client.get("/api/social/friends/requests", headers=auth_headers)
        request_id = requests.json()[0]["id"]
        client.post(f"/api/social/friends/requests/{request_id}/accept", headers=auth_headers)
        
        # Remove friend
        response = client.delete(f"/api/social/friends/{other.id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify removed
        friends = client.get("/api/social/friends", headers=auth_headers)
        assert not any(f["username"] == "remove_friend" for f in friends.json())


class TestActivityFeed:
    """Tests for activity feed."""

    def test_get_feed_empty(self, client: TestClient, auth_headers):
        """Test getting empty feed."""
        response = client.get("/api/social/feed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "has_more" in data

    def test_feed_includes_own_sessions(self, client: TestClient, auth_headers, create_gym):
        """Test that feed includes user's own sessions."""
        # Create a gym and session
        gym = create_gym(name="Feed Gym", location="Test Location")
        
        # Create a session
        client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"gym_id": gym.id}
        )
        
        # Check feed
        response = client.get("/api/social/feed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert data["items"][0]["is_own"] == True
        assert data["items"][0]["gym_name"] == "Feed Gym"

    def test_feed_includes_friend_sessions(self, client: TestClient, auth_headers, create_user, create_gym, db):
        """Test that feed includes friends' sessions."""
        # Create friend and their session
        friend = create_user(username="feed_friend", email="feedfriend@test.com", password="password123")
        login = client.post("/api/auth/login", json={"email": "feedfriend@test.com", "password": "password123"})
        friend_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        
        # Create gym and session as friend
        gym = create_gym(name="Friend Gym", location="Friend Location")
        client.post("/api/sessions", headers=friend_headers, json={"gym_id": gym.id})
        
        # Become friends
        me = client.get("/api/auth/me", headers=auth_headers)
        test_user_id = me.json()["id"]
        client.post("/api/social/friends", headers=friend_headers, json={"friend_id": test_user_id})
        requests = client.get("/api/social/friends/requests", headers=auth_headers)
        if requests.json():
            request_id = requests.json()[0]["id"]
            client.post(f"/api/social/friends/requests/{request_id}/accept", headers=auth_headers)
        
        # Check feed includes friend's session
        response = client.get("/api/social/feed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        friend_sessions = [i for i in data["items"] if i["username"] == "feed_friend"]
        assert len(friend_sessions) >= 1

    def test_feed_pagination(self, client: TestClient, auth_headers):
        """Test feed pagination parameters."""
        response = client.get("/api/social/feed?skip=0&limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
        assert isinstance(data["has_more"], bool)

    def test_feed_includes_title_subtitle(self, client: TestClient, auth_headers, create_gym):
        """Test that feed items include title and subtitle fields."""
        gym = create_gym(name="Title Test Gym", location="Test")
        
        # Create session with title and subtitle
        client.post(
            "/api/sessions",
            headers=auth_headers,
            json={
                "gym_id": gym.id,
                "title": "Mi sesión especial",
                "subtitle": "Día de volumen"
            }
        )
        
        response = client.get("/api/social/feed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Find the session we just created
        session_item = next((i for i in data["items"] if i["gym_name"] == "Title Test Gym"), None)
        assert session_item is not None
        assert session_item["title"] == "Mi sesión especial"
        assert session_item["subtitle"] == "Día de volumen"

    def test_feed_includes_gym_location(self, client: TestClient, auth_headers, create_gym):
        """Test that feed items include gym_location field."""
        gym = create_gym(name="Location Test Gym", location="Calle Test 123")
        
        client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"gym_id": gym.id}
        )
        
        response = client.get("/api/social/feed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        session_item = next((i for i in data["items"] if i["gym_name"] == "Location Test Gym"), None)
        assert session_item is not None
        assert session_item["gym_location"] == "Calle Test 123"

    def test_feed_includes_profile_picture(self, client: TestClient, auth_headers, create_gym, test_user, db):
        """Test that feed items include profile_picture field."""
        # Set profile picture for test user
        test_user.profile_picture = "/data/uploads/profiles/test.png"
        db.commit()
        
        gym = create_gym(name="Profile Pic Gym", location="Test")
        
        client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"gym_id": gym.id}
        )
        
        response = client.get("/api/social/feed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        session_item = next((i for i in data["items"] if i["gym_name"] == "Profile Pic Gym"), None)
        assert session_item is not None
        assert session_item["profile_picture"] == "/data/uploads/profiles/test.png"

    def test_feed_profile_picture_null_when_not_set(self, client: TestClient, auth_headers, create_gym):
        """Test that profile_picture is null when user has no picture."""
        gym = create_gym(name="No Pic Gym", location="Test")
        
        client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"gym_id": gym.id}
        )
        
        response = client.get("/api/social/feed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        session_item = next((i for i in data["items"] if i["gym_name"] == "No Pic Gym"), None)
        assert session_item is not None
        assert session_item["profile_picture"] is None


class TestUserProfile:
    """Tests for user profile endpoint."""

    def test_get_user_profile(self, client: TestClient, auth_headers, create_user):
        """Test getting another user's profile."""
        other_user = create_user(username="profile_user", email="profile@test.com", password="password123")
        
        response = client.get(
            f"/api/social/users/{other_user.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == other_user.id
        assert data["username"] == "profile_user"
        assert data["friendship_status"] is None
        assert data["total_sessions"] == 0
        assert data["total_sends"] == 0
        assert data["recent_sessions"] == []

    def test_get_user_profile_not_found(self, client: TestClient, auth_headers):
        """Test getting profile for non-existent user."""
        response = client.get(
            "/api/social/users/99999",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_user_profile_shows_friendship_status(self, client: TestClient, auth_headers, create_user):
        """Test that profile shows correct friendship status."""
        friend = create_user(username="profile_friend", email="profilefriend@test.com", password="password123")
        
        # Send friend request
        client.post(
            "/api/social/friends",
            headers=auth_headers,
            json={"friend_id": friend.id}
        )
        
        # Check profile shows pending status
        response = client.get(
            f"/api/social/users/{friend.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["friendship_status"] == "pending"

    def test_user_profile_includes_home_gym(self, client: TestClient, auth_headers, create_user, create_gym):
        """Test that profile includes home gym information."""
        gym = create_gym(name="Home Gym", location="Home Location")
        user_with_gym = create_user(
            username="gym_user", 
            email="gymuser@test.com", 
            password="password123",
            home_gym_id=gym.id
        )
        
        response = client.get(
            f"/api/social/users/{user_with_gym.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["home_gym_id"] == gym.id
        assert data["home_gym_name"] == "Home Gym"

    def test_user_profile_includes_profile_picture(self, client: TestClient, auth_headers, create_user, db):
        """Test that profile includes profile picture."""
        user = create_user(username="pic_user", email="picuser@test.com", password="password123")
        user.profile_picture = "/data/uploads/profiles/pic.png"
        db.commit()
        
        response = client.get(
            f"/api/social/users/{user.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["profile_picture"] == "/data/uploads/profiles/pic.png"

    def test_user_profile_includes_stats(self, client: TestClient, auth_headers, create_user, create_gym, db):
        """Test that profile includes user statistics."""
        # Create user with session
        other_user = create_user(username="stats_user", email="statsuser@test.com", password="password123")
        login = client.post("/api/auth/login", json={"email": "statsuser@test.com", "password": "password123"})
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        
        gym = create_gym(name="Stats Gym", location="Stats Location")
        
        # Create some grades for the gym
        grade_response = client.post(
            "/api/grades",
            headers=other_headers,
            json={
                "gym_id": gym.id,
                "label": "Test Grade",
                "color_hex": "#FF0000",
                "relative_difficulty": 5,
                "order": 1
            }
        )
        grade_id = grade_response.json()["id"]
        
        # Create session with ascents
        session_response = client.post(
            "/api/sessions",
            headers=other_headers,
            json={"gym_id": gym.id}
        )
        session_id = session_response.json()["id"]
        
        # Add an ascent
        ascent_response = client.post(
            f"/api/sessions/{session_id}/ascents",
            headers=other_headers,
            json={"grade_id": grade_id, "status": "send"}
        )
        assert ascent_response.status_code == 201
        
        # Get profile
        response = client.get(
            f"/api/social/users/{other_user.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 1
        assert data["total_sends"] == 1

    def test_user_profile_includes_recent_sessions(self, client: TestClient, auth_headers, create_user, create_gym):
        """Test that profile includes recent sessions."""
        other_user = create_user(username="recent_user", email="recentuser@test.com", password="password123")
        login = client.post("/api/auth/login", json={"email": "recentuser@test.com", "password": "password123"})
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        
        gym = create_gym(name="Recent Gym", location="Recent Location")
        
        # Create a session
        client.post(
            "/api/sessions",
            headers=other_headers,
            json={"gym_id": gym.id, "title": "Test Session"}
        )
        
        # Get profile
        response = client.get(
            f"/api/social/users/{other_user.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["recent_sessions"]) == 1
        assert data["recent_sessions"][0]["title"] == "Test Session"
        assert data["recent_sessions"][0]["gym_name"] == "Recent Gym"


class TestFriendsProfilePictures:
    """Tests for profile pictures in friends endpoints."""

    def test_friends_list_includes_profile_pictures(self, client: TestClient, auth_headers, create_user, db):
        """Test that friends list includes profile pictures."""
        # Create friend with profile picture
        friend = create_user(username="pic_friend", email="picfriend@test.com", password="password123")
        friend.profile_picture = "/data/uploads/profiles/friend.png"
        db.commit()
        
        # Login as friend
        login = client.post("/api/auth/login", json={"email": "picfriend@test.com", "password": "password123"})
        friend_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        
        # Get my user ID
        me = client.get("/api/auth/me", headers=auth_headers)
        my_id = me.json()["id"]
        
        # Friend sends request
        client.post("/api/social/friends", headers=friend_headers, json={"friend_id": my_id})
        
        # I accept
        requests = client.get("/api/social/friends/requests", headers=auth_headers)
        request_id = requests.json()[0]["id"]
        client.post(f"/api/social/friends/requests/{request_id}/accept", headers=auth_headers)
        
        # Check friends list
        response = client.get("/api/social/friends", headers=auth_headers)
        assert response.status_code == 200
        friends = response.json()
        friend_data = next((f for f in friends if f["username"] == "pic_friend"), None)
        assert friend_data is not None
        assert friend_data["profile_picture"] == "/data/uploads/profiles/friend.png"

    def test_friend_requests_include_profile_pictures(self, client: TestClient, auth_headers, create_user, db):
        """Test that friend requests include profile pictures."""
        # Create user with profile picture
        sender = create_user(username="request_sender", email="requestsender@test.com", password="password123")
        sender.profile_picture = "/data/uploads/profiles/sender.png"
        db.commit()
        
        # Login as sender
        login = client.post("/api/auth/login", json={"email": "requestsender@test.com", "password": "password123"})
        sender_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        
        # Get my user ID
        me = client.get("/api/auth/me", headers=auth_headers)
        my_id = me.json()["id"]
        
        # Sender sends request
        client.post("/api/social/friends", headers=sender_headers, json={"friend_id": my_id})
        
        # Check requests list
        response = client.get("/api/social/friends/requests", headers=auth_headers)
        assert response.status_code == 200
        requests = response.json()
        assert len(requests) >= 1
        request_data = next((r for r in requests if r["user_username"] == "request_sender"), None)
        assert request_data is not None
        assert request_data["user_profile_picture"] == "/data/uploads/profiles/sender.png"

