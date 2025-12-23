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
