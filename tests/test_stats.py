"""
Tests for stats endpoints.
"""
import pytest


class TestStats:
    """Tests for /api/stats endpoints."""
    
    def test_get_stats_empty(self, client, auth_headers):
        """Test getting stats with no data."""
        response = client.get("/api/stats/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 0
        assert data["total_ascents"] == 0
        assert data["max_grade_ever"] is None
    
    def test_get_stats_with_data(self, client, auth_headers, test_session, test_ascents):
        """Test getting stats with sessions and ascents."""
        response = client.get("/api/stats/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_sessions"] == 1
        assert data["total_ascents"] == 3  # Excludes PROJECT status
        assert data["total_sends"] == 3  # 1 flash + 2 sends
        assert data["total_flashes"] == 1
        assert data["sessions_this_week"] == 1
        assert data["ascents_this_week"] == 4  # Includes all ascents this week
        
        # Grade distribution
        assert len(data["grade_distribution"]) > 0
        
        # Weekly progress (last 8 weeks)
        assert len(data["weekly_progress"]) == 8
    
    def test_get_max_grade(self, client, auth_headers, test_session, test_ascents, test_grades):
        """Test that max grade is calculated correctly."""
        response = client.get("/api/stats/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Max sent should be "Azul" (difficulty 4) since "Rojo" (difficulty 6) was only a project
        assert data["max_grade_ever"] == "Azul"
        assert data["max_relative_difficulty"] == 4
    
    def test_get_summary(self, client, auth_headers, test_session, test_ascents):
        """Test getting quick summary."""
        response = client.get("/api/stats/summary", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sessions_this_week"] == 1
        assert data["ascents_this_week"] == 4
        assert data["sends_this_week"] == 3
        assert data["flashes_this_week"] == 1
        assert "message" in data  # Motivational message
    
    def test_stats_unauthorized(self, client):
        """Test stats access without auth."""
        response = client.get("/api/stats/me")
        
        assert response.status_code == 401
    
    def test_friends_leaderboard(self, client, auth_headers):
        """Test friends leaderboard endpoint."""
        response = client.get("/api/stats/friends-leaderboard", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "gyms" in data
        assert isinstance(data["gyms"], list)
    
    def test_friends_leaderboard_period_total(self, client, auth_headers):
        """Test friends leaderboard with total period."""
        response = client.get("/api/stats/friends-leaderboard?period=total", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "gyms" in data
    
    def test_friends_leaderboard_period_year(self, client, auth_headers):
        """Test friends leaderboard with year period filter."""
        response = client.get("/api/stats/friends-leaderboard?period=year", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "gyms" in data
    
    def test_yearly_stats(self, client, auth_headers):
        """Test yearly stats endpoint."""
        response = client.get("/api/stats/yearly", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "total_ascents" in data
        assert "monthly_stats" in data
