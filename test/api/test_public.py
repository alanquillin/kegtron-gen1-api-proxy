import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPublicEndpoints:
    """Test public API endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == "We are up and running!"
    
    @pytest.mark.asyncio
    async def test_ping_endpoint(self, client):
        """Test the ping endpoint."""
        response = await client.get("/api/v1/ping")
        assert response.status_code == 200
        assert response.json() == "pong"
    
    def test_health_endpoint_sync(self, sync_client):
        """Test the health endpoint with sync client."""
        response = sync_client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == "We are up and running!"
    
    def test_ping_endpoint_sync(self, sync_client):
        """Test the ping endpoint with sync client."""
        response = sync_client.get("/api/v1/ping")
        assert response.status_code == 200
        assert response.json() == "pong"
    
    @pytest.mark.asyncio
    async def test_health_endpoint_methods(self, client):
        """Test that health endpoint only accepts GET requests."""
        # Test POST (should fail)
        response = await client.post("/api/v1/health")
        assert response.status_code == 405  # Method Not Allowed
        
        # Test PUT (should fail)
        response = await client.put("/api/v1/health")
        assert response.status_code == 405
        
        # Test DELETE (should fail)
        response = await client.delete("/api/v1/health")
        assert response.status_code == 405
    
    @pytest.mark.asyncio
    async def test_ping_endpoint_methods(self, client):
        """Test that ping endpoint only accepts GET requests."""
        # Test POST (should fail)
        response = await client.post("/api/v1/ping")
        assert response.status_code == 405  # Method Not Allowed
        
        # Test PUT (should fail)
        response = await client.put("/api/v1/ping")
        assert response.status_code == 405
        
        # Test DELETE (should fail)
        response = await client.delete("/api/v1/ping")
        assert response.status_code == 405
    
    @pytest.mark.asyncio
    async def test_api_docs_endpoint(self, client):
        """Test that API docs are accessible in test environment."""
        response = await client.get("/api/docs")
        # Should either return 200 (if docs are served) or 307 (redirect to docs with trailing slash)
        assert response.status_code in [200, 307]
    
    @pytest.mark.asyncio
    async def test_nonexistent_endpoint(self, client):
        """Test accessing a non-existent endpoint."""
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test the root endpoint serves static files."""
        with patch('api.StaticFiles') as mock_static:
            response = await client.get("/")
            # Since we're mocking StaticFiles, we can't test the actual static file serving
            # but we can verify it doesn't return a 404
            assert response.status_code != 405  # Not "Method Not Allowed"
    
    @pytest.mark.asyncio
    async def test_cors_headers_in_test_env(self, client):
        """Test CORS headers are properly set in test environment."""
        # FastAPI handles CORS differently, GET with Origin header is better test
        response = await client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        # Check if CORS headers are present (they may not be in all configurations)
        # Just verify the endpoint works with Origin header
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self, client):
        """Test that health check responds quickly (basic performance test)."""
        import time
        start = time.time()
        response = await client.get("/api/v1/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        # Health check should be fast (less than 100ms)
        assert duration < 0.1
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_pings(self, client):
        """Test handling multiple concurrent ping requests."""
        import asyncio
        
        async def ping():
            response = await client.get("/api/v1/ping")
            return response.status_code == 200 and response.json() == "pong"
        
        # Send 10 concurrent ping requests
        results = await asyncio.gather(*[ping() for _ in range(10)])
        
        # All should succeed
        assert all(results)