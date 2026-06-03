"""
Unit tests for PC4 Feedback Service TTS functionality
"""
import pytest
import sys
import os

# Add src/feedback-service to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src/feedback-service'))

try:
    from feedback import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
except ImportError:
    pytest.skip("Feedback service dependencies not installed", allow_module_level=True)


class TestTTSEngine:
    """Test TTS engine functionality"""
    
    def test_speak_basic(self):
        """Test basic speak functionality"""
        response = client.post(
            "/speak",
            json={"message": "Test message", "priority": "normal"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Test message"
        assert "queued" in data
    
    def test_speak_with_priority(self):
        """Test speak with different priorities"""
        priorities = ["low", "normal", "high", "emergency"]
        for priority in priorities:
            response = client.post(
                "/speak",
                json={"message": "Test", "priority": priority}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["priority"] == priority
    
    def test_speak_empty_message(self):
        """Test speak with empty message"""
        response = client.post(
            "/speak",
            json={"message": "", "priority": "normal"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_speak_long_message(self):
        """Test speak with very long message"""
        long_message = "Test " * 200  # 1000 characters
        response = client.post(
            "/speak",
            json={"message": long_message, "priority": "normal"}
        )
        # Should either accept it or reject it
        assert response.status_code in [200, 400]
    
    def test_speak_invalid_priority(self):
        """Test speak with invalid priority"""
        response = client.post(
            "/speak",
            json={"message": "Test", "priority": "invalid"}
        )
        # Should handle invalid priority gracefully
        assert response.status_code in [200, 400]
    
    def test_speak_missing_message(self):
        """Test speak without message field"""
        response = client.post(
            "/speak",
            json={"priority": "normal"}
        )
        assert response.status_code in [400, 422]


class TestAnnouncements:
    """Test announcement functionality"""
    
    def test_announce_takeoff(self):
        """Test takeoff announcement"""
        response = client.post(
            "/announce",
            json={"event": "takeoff", "details": "Ready for flight"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "announced"
        assert data["event"] == "takeoff"
    
    def test_announce_landing(self):
        """Test landing announcement"""
        response = client.post(
            "/announce",
            json={"event": "landing"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["event"] == "landing"
    
    def test_announce_emergency(self):
        """Test emergency announcement"""
        response = client.post(
            "/announce",
            json={"event": "emergency"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["event"] == "emergency"
        assert data["priority"] == "emergency"
    
    def test_announce_invalid_event(self):
        """Test announcement with invalid event"""
        response = client.post(
            "/announce",
            json={"event": "invalid_event"}
        )
        assert response.status_code in [400, 422]
    
    def test_announce_without_event(self):
        """Test announcement without event field"""
        response = client.post(
            "/announce",
            json={"details": "Some details"}
        )
        assert response.status_code in [400, 422]


class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Test basic health check"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
    
    def test_health_check_fields(self):
        """Test health check has required fields"""
        response = client.get("/health")
        data = response.json()
        required_fields = ["status", "service", "timestamp"]
        for field in required_fields:
            assert field in data


class TestStats:
    """Test statistics endpoint"""
    
    def test_get_stats(self):
        """Test getting service statistics"""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "queue_stats" in data
    
    def test_stats_fields(self):
        """Test stats has required fields"""
        response = client.get("/stats")
        data = response.json()
        required_fields = ["service", "queue_stats"]
        for field in required_fields:
            assert field in data


class TestAudioDevices:
    """Test audio device management"""
    
    def test_list_audio_devices(self):
        """Test listing audio devices"""
        response = client.get("/audio-devices")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert isinstance(data["devices"], list)


class TestConcurrency:
    """Test concurrent requests"""
    
    def test_concurrent_speak_requests(self):
        """Test handling multiple concurrent speak requests"""
        import threading
        results = []
        
        def make_request():
            response = client.post(
                "/speak",
                json={"message": "Concurrent test", "priority": "normal"}
            )
            results.append(response.status_code)
        
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All requests should complete
        assert len(results) == 5
        # At least some should succeed
        assert any(code == 200 for code in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
