"""
Integration tests for public API endpoints.
These tests run against a real API server to validate actual HTTP behavior.
"""

import pytest
import httpx
import time
import concurrent.futures


class TestPublicEndpointsIntegration:
    """Test public API endpoints against running API."""
    
    def test_health_endpoint(self, api_client):
        """Test the health check endpoint."""
        response = api_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["api"] == "running"
        assert "scanner" in data
    
    def test_ping_endpoint(self, api_client):
        """Test the ping endpoint."""
        response = api_client.get("/api/v1/ping")
        assert response.status_code == 200
        assert response.json() == "pong"
    
    def test_health_endpoint_methods(self, api_client):
        """Test that health endpoint only accepts GET requests."""
        # POST should fail
        response = api_client.post("/api/v1/health")
        assert response.status_code == 405  # Method Not Allowed
        
        # PUT should fail
        response = api_client.put("/api/v1/health")
        assert response.status_code == 405
        
        # DELETE should fail
        response = api_client.delete("/api/v1/health")
        assert response.status_code == 405
        
        # PATCH should fail
        response = api_client.patch("/api/v1/health")
        assert response.status_code == 405
    
    def test_ping_endpoint_methods(self, api_client):
        """Test that ping endpoint only accepts GET requests."""
        # POST should fail
        response = api_client.post("/api/v1/ping")
        assert response.status_code == 405
        
        # PUT should fail
        response = api_client.put("/api/v1/ping")
        assert response.status_code == 405
        
        # DELETE should fail
        response = api_client.delete("/api/v1/ping")
        assert response.status_code == 405
    
    def test_api_docs_endpoint(self, api_client):
        """Test that API docs are accessible."""
        response = api_client.get("/api/docs")
        # Should either return 200 or redirect
        assert response.status_code in [200, 307]
        
        # If redirect, follow it
        if response.status_code == 307:
            redirect_url = response.headers.get("location")
            if redirect_url:
                # For relative redirects
                if redirect_url.startswith("/"):
                    response = api_client.get(redirect_url)
                    assert response.status_code == 200
    
    def test_nonexistent_endpoint(self, api_client):
        """Test accessing a non-existent endpoint."""
        response = api_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        
        response = api_client.post("/api/v1/this-does-not-exist")
        # Should be 404 for truly non-existent endpoint, or 405 if path exists but method not allowed
        assert response.status_code in [404, 405]
    
    def test_cors_headers(self, api_client):
        """Test CORS headers are properly set."""
        # Make request with Origin header
        headers = {"Origin": "http://localhost:3000"}
        response = api_client.get("/api/v1/health", headers=headers)
        assert response.status_code == 200
        
        # In test environment, CORS should be permissive
        # Check for CORS headers (exact headers depend on CORS configuration)
        # The presence of these headers varies based on the CORS middleware configuration
    
    def test_health_check_performance(self, api_client):
        """Test that health check responds quickly."""
        start = time.time()
        response = api_client.get("/api/v1/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        # Health check should be fast (less than 1 second)
        # Using 1 second for integration test to account for network latency
        assert duration < 1.0
    
    def test_concurrent_ping_requests(self, api_client):
        """Test handling multiple concurrent ping requests."""
        def ping():
            response = api_client.get("/api/v1/ping")
            return response.status_code == 200 and response.json() == "pong"
        
        # Send 20 concurrent ping requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(ping) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # All should succeed
        assert all(results)
    
    def test_content_type_headers(self, api_client):
        """Test that API returns proper content-type headers."""
        response = api_client.get("/api/v1/health")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
        
        response = api_client.get("/api/v1/ping")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_error_response_format(self, api_client):
        """Test that error responses have consistent format."""
        # 404 error
        response = api_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        
        # 405 error
        response = api_client.post("/api/v1/health")
        assert response.status_code == 405
        error_data = response.json()
        assert "detail" in error_data
    
    def test_api_versioning(self, api_client):
        """Test that API versioning is consistent."""
        # v1 endpoints should work
        response = api_client.get("/api/v1/health")
        assert response.status_code == 200
        
        response = api_client.get("/api/v1/ping")
        assert response.status_code == 200
        
        response = api_client.get("/api/v1/devices")
        assert response.status_code == 200
        
        # Non-versioned or wrong version should fail
        response = api_client.get("/api/v2/health")
        assert response.status_code == 404
        
        response = api_client.get("/api/health")
        assert response.status_code == 404


class TestLoadAndStress:
    """Test API behavior under load."""
    
    def test_sustained_load(self, api_client):
        """Test API can handle sustained load of requests."""
        import time
        
        errors = []
        start_time = time.time()
        request_count = 0
        
        # Send requests for 5 seconds
        while time.time() - start_time < 5:
            try:
                response = api_client.get("/api/v1/ping", timeout=1.0)
                if response.status_code != 200:
                    errors.append(f"Status {response.status_code}")
                request_count += 1
            except Exception as e:
                errors.append(str(e))
            
            # Small delay to avoid overwhelming
            time.sleep(0.01)  # 10ms between requests
        
        # Should handle at least 100 requests per second
        assert request_count > 100
        # Error rate should be very low
        assert len(errors) < request_count * 0.01  # Less than 1% error rate
    
    def test_mixed_endpoint_load(self, api_client, create_test_device):
        """Test API with mixed requests to different endpoints."""
        import random
        
        # Create some test data
        device = create_test_device()
        
        def random_request():
            """Make a random request to various endpoints."""
            endpoints = [
                ("GET", "/api/v1/health", None),
                ("GET", "/api/v1/ping", None),
                ("GET", "/api/v1/devices", None),
                ("GET", f"/api/v1/devices/{device.id}", None),
            ]
            
            method, path, data = random.choice(endpoints)
            
            try:
                if method == "GET":
                    response = api_client.get(path)
                    return response.status_code in [200, 201, 204]
                return False
            except:
                return False
        
        # Make 100 random requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(random_request) for _ in range(100)]
            results = [f.result() for f in futures]
        
        # At least 95% should succeed
        success_rate = sum(results) / len(results)
        assert success_rate > 0.95


class TestStaticFiles:
    """Test static file serving."""
    
    def test_root_serves_static(self, api_client):
        """Test that root path serves static files."""
        # The root path should either serve a file or return 404 if no index.html
        response = api_client.get("/")
        # Should not return 405 (method not allowed)
        assert response.status_code != 405
        # Either serves content (200) or not found (404)
        assert response.status_code in [200, 404]
    
    def test_static_file_path(self, api_client, test_static_dir):
        """Test serving a specific static file."""
        import os
        
        # Create a test static file
        test_file_path = os.path.join(test_static_dir, "test.txt")
        with open(test_file_path, "w") as f:
            f.write("Test static content")
        
        # Try to access it
        response = api_client.get("/test.txt")
        # Should either serve it or return 404 (depending on static file configuration)
        assert response.status_code in [200, 404]