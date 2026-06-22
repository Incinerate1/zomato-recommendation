import unittest
from fastapi.testclient import TestClient

# Adjust path to import backend modules correctly
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.main import app


class TestBackendAPI(unittest.TestCase):
    """Tests for Phase 4A: Standardized response schema, error handling, and meta endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    # ------------------------------------------------------------------
    # Response envelope helpers
    # ------------------------------------------------------------------

    def assert_success_envelope(self, response, expected_status=200):
        """Verify the response follows the standardized success envelope."""
        self.assertEqual(response.status_code, expected_status)
        body = response.json()
        self.assertTrue(body["success"], f"Expected success=True, got: {body}")
        self.assertIsNotNone(body["data"])
        self.assertIsNone(body["error"])
        return body["data"]

    def assert_error_envelope(self, response, expected_status):
        """Verify the response follows the standardized error envelope."""
        self.assertEqual(response.status_code, expected_status)
        body = response.json()
        self.assertFalse(body["success"], f"Expected success=False, got: {body}")
        self.assertIsNone(body["data"])
        self.assertIsNotNone(body["error"])
        return body["error"]

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def test_health_endpoint(self):
        """Test `/health` responds with a standardized success envelope."""
        response = self.client.get("/health")
        data = self.assert_success_envelope(response)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertGreater(data["unique_locations_count"], 0)

    # ------------------------------------------------------------------
    # Meta Endpoints
    # ------------------------------------------------------------------

    def test_meta_locations_returns_sorted_list(self):
        """Test `/api/meta/locations` returns a sorted, deduplicated list."""
        response = self.client.get("/api/meta/locations")
        data = self.assert_success_envelope(response)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        # Check that the list is sorted
        self.assertEqual(data, sorted(data))
        # Spot-check a known location
        self.assertIn("Banashankari", data)

    def test_meta_cuisines_returns_sorted_list(self):
        """Test `/api/meta/cuisines` returns a sorted, deduplicated list."""
        response = self.client.get("/api/meta/cuisines")
        data = self.assert_success_envelope(response)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        # Check that the list is sorted
        self.assertEqual(data, sorted(data))
        # Spot-check a known cuisine
        self.assertIn("Italian", [c for c in data])

    # ------------------------------------------------------------------
    # Search Endpoint
    # ------------------------------------------------------------------

    def test_search_endpoint_success(self):
        """Test `/api/restaurants/search` with valid location and filters."""
        response = self.client.get(
            "/api/restaurants/search?location=banashankari&cuisine=italian&budget=medium"
        )
        data = self.assert_success_envelope(response)
        self.assertIn("candidates", data)
        self.assertIsInstance(data["candidates"], list)

        for c in data["candidates"]:
            self.assertEqual(c["budget"], "medium")
            self.assertIn("italian", c["cuisines"].lower())

    def test_search_endpoint_missing_location(self):
        """Test `/api/restaurants/search` raises 422 when location param is missing."""
        response = self.client.get("/api/restaurants/search")
        self.assertEqual(response.status_code, 422)  # FastAPI validation error

    def test_search_endpoint_empty_location(self):
        """Test `/api/restaurants/search` returns 400 for blank location."""
        response = self.client.get("/api/restaurants/search?location= ")
        error = self.assert_error_envelope(response, 400)
        self.assertIn("Location", error)

    def test_search_endpoint_invalid_budget(self):
        """Test `/api/restaurants/search` rejects invalid budget values."""
        response = self.client.get(
            "/api/restaurants/search?location=banashankari&budget=ultra"
        )
        error = self.assert_error_envelope(response, 400)
        self.assertIn("Invalid budget", error)

    # ------------------------------------------------------------------
    # Recommend Endpoint
    # ------------------------------------------------------------------

    def test_recommend_endpoint_success(self):
        """Test POST `/api/restaurants/recommend` returns standardized envelope with recommendations."""
        payload = {
            "location": "Banashankari",
            "cuisine": "North Indian",
            "budget": "medium",
            "min_rating": 3.5,
            "extra_preferences": "rooftop seating, family friendly"
        }
        response = self.client.post("/api/restaurants/recommend", json=payload)
        data = self.assert_success_envelope(response)

        self.assertIn("recommendations", data)
        self.assertIn("query_info", data)
        self.assertIsInstance(data["recommendations"], list)
        self.assertLessEqual(len(data["recommendations"]), 3)

        for r in data["recommendations"]:
            self.assertIn("name", r)
            self.assertIn("ai_explanation", r)
            self.assertIn("rank", r)

    def test_recommend_endpoint_no_match(self):
        """Test `/api/restaurants/recommend` returns success=True with empty list and a message when no candidates match."""
        payload = {
            "location": "Banashankari",
            "cuisine": "NonExistentCuisineQuery",
            "budget": "high",
            "min_rating": 4.9
        }
        response = self.client.post("/api/restaurants/recommend", json=payload)
        data = self.assert_success_envelope(response)

        self.assertEqual(data["count"], 0)
        self.assertEqual(len(data["recommendations"]), 0)
        self.assertIn("No restaurants match", data["message"])

    def test_recommend_endpoint_empty_location(self):
        """Test `/api/restaurants/recommend` rejects empty location."""
        payload = {"location": "   "}
        response = self.client.post("/api/restaurants/recommend", json=payload)
        error = self.assert_error_envelope(response, 400)
        self.assertIn("Location", error)

    def test_recommend_endpoint_invalid_budget(self):
        """Test `/api/restaurants/recommend` rejects invalid budget."""
        payload = {
            "location": "Banashankari",
            "budget": "super-premium"
        }
        response = self.client.post("/api/restaurants/recommend", json=payload)
        error = self.assert_error_envelope(response, 400)
        self.assertIn("Invalid budget", error)

    # ------------------------------------------------------------------
    # CORS Headers
    # ------------------------------------------------------------------

    def test_cors_allowed_origin(self):
        """Test that CORS headers are present for allowed origin."""
        response = self.client.options(
            "/api/meta/locations",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        self.assertIn(
            response.headers.get("access-control-allow-origin", ""),
            ["http://localhost:3000", "*"]
        )


if __name__ == "__main__":
    unittest.main()
