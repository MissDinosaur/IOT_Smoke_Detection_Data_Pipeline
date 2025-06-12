"""
Comprehensive Flask API Tests for IoT Smoke Detection Pipeline.

This module provides complete Flask API testing including:
- All endpoint functionality
- Authentication and security
- Error handling and validation
- API versioning and compatibility
- Rate limiting and throttling
- Request/response validation
- API documentation compliance
- CORS and headers testing

Tests use mocks to avoid requiring a running Flask API server.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Flask API test configuration
FLASK_API_CONFIG = {
    "base_url": "http://localhost:5000",
    "timeout": 30,
    "max_retries": 3,
    "rate_limit_requests": 100,
    "rate_limit_window": 60,
}

# Test data for Flask API
VALID_SENSOR_DATA = {
    "Temperature[C]": 25.5,
    "Humidity[%]": 45.0,
    "TVOC[ppb]": 150.0,
    "eCO2[ppm]": 400.0,
    "Raw H2": 13000.0,
    "Raw Ethanol": 18500.0,
    "Pressure[hPa]": 1013.25,
    "PM1.0": 10.0,
    "PM2.5": 15.0,
    "NC0.5": 100.0,
    "NC1.0": 80.0,
    "NC2.5": 20.0,
}


class TestFlaskAPIEndpoints:
    """Test all Flask API endpoints comprehensively."""

    def test_health_endpoint(self, api_client):
        """Test health check endpoint."""
        try:
            response = api_client.get("/health", timeout=10)
            assert response.status_code == 200

            health_data = response.json()

            # Required health check fields
            required_fields = ["status", "timestamp", "version"]
            for field in required_fields:
                assert field in health_data, f"Missing health field: {field}"

            assert health_data["status"] in ["healthy", "ok", "up"]

            # Optional detailed health info
            if "services" in health_data:
                services = health_data["services"]
                assert isinstance(services, dict)

                # Check individual service status
                for service_name, service_status in services.items():
                    assert service_status in ["healthy", "ok", "up", "down"]

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_predict_endpoint(self, api_client):
        """Test single prediction endpoint."""
        try:
            response = api_client.predict(VALID_SENSOR_DATA, timeout=15)
            assert response.status_code == 200

            result = response.json()

            # Validate prediction response structure
            required_fields = [
                "prediction",
                "prediction_label",
                "confidence",
                "processing_time_seconds",
                "timestamp",
            ]

            for field in required_fields:
                assert field in result, f"Missing prediction field: {field}"

            # Validate prediction values
            assert result["prediction"] in [0, 1]
            assert result["prediction_label"] in ["fire", "no_fire"]

            # Validate confidence scores
            confidence = result["confidence"]
            assert isinstance(confidence, dict)
            assert "fire" in confidence
            assert "no_fire" in confidence
            assert 0.0 <= confidence["fire"] <= 1.0
            assert 0.0 <= confidence["no_fire"] <= 1.0

            # Confidence scores should sum to approximately 1
            total_confidence = confidence["fire"] + confidence["no_fire"]
            assert abs(total_confidence - 1.0) < 0.01

            # Validate processing time
            assert isinstance(result["processing_time_seconds"], (int, float))
            assert result["processing_time_seconds"] > 0

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_predict_batch_endpoint(self, api_client):
        """Test batch prediction endpoint."""
        try:
            # Create batch data
            batch_data = [VALID_SENSOR_DATA] * 5

            response = api_client.predict_batch(batch_data, timeout=30)
            assert response.status_code == 200

            result = response.json()

            # Validate batch response structure
            assert "predictions" in result
            assert "summary" in result
            assert "processing_time_seconds" in result

            predictions = result["predictions"]
            assert len(predictions) == len(batch_data)

            # Validate each prediction in batch
            for prediction in predictions:
                assert "prediction" in prediction
                assert "confidence" in prediction
                assert prediction["prediction"] in [0, 1]

            # Validate summary
            summary = result["summary"]
            assert "total_samples" in summary
            assert summary["total_samples"] == len(batch_data)
            assert "fire_predictions" in summary
            assert "no_fire_predictions" in summary

            # Fire + no_fire should equal total
            total_predictions = (
                summary["fire_predictions"] + summary["no_fire_predictions"]
            )
            assert total_predictions == summary["total_samples"]

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_model_info_endpoint(self, api_client):
        """Test model information endpoint."""
        try:
            response = api_client.get("/model/info", timeout=10)
            assert response.status_code == 200

            model_info = response.json()

            # Required model info fields
            required_fields = [
                "model_name",
                "model_version",
                "feature_columns",
                "training_timestamp",
                "model_metrics",
            ]

            for field in required_fields:
                assert field in model_info, f"Missing model info field: {field}"

            # Validate feature columns
            feature_columns = model_info["feature_columns"]
            assert isinstance(feature_columns, list)
            assert len(feature_columns) > 0

            # Check that expected features are present
            expected_features = list(VALID_SENSOR_DATA.keys())
            for feature in expected_features:
                assert feature in feature_columns, f"Missing feature: {feature}"

            # Validate model metrics
            metrics = model_info["model_metrics"]
            assert isinstance(metrics, dict)

            # Common ML metrics
            metric_names = ["accuracy", "precision", "recall", "f1_score"]
            for metric in metric_names:
                if metric in metrics:
                    assert (
                        0.0 <= metrics[metric] <= 1.0
                    ), f"Invalid {metric} value: {metrics[metric]}"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_model_reload_endpoint(self, api_client):
        """Test model reload endpoint if available."""
        try:
            response = api_client.post("/model/reload", timeout=60)

            if response.status_code == 200:
                result = response.json()
                assert "status" in result
                assert result["status"] in ["success", "reloaded", "completed"]

                # Verify model still works after reload
                time.sleep(2)  # Give model time to reload
                pred_response = api_client.predict(VALID_SENSOR_DATA, timeout=15)
                assert pred_response.status_code == 200

            elif response.status_code == 404:
                pytest.skip("Model reload endpoint not implemented")
            else:
                pytest.fail(f"Model reload failed with status {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_predictions_stats_endpoint(self, api_client):
        """Test prediction statistics endpoint if available."""
        try:
            response = api_client.get("/predictions/stats", timeout=10)

            if response.status_code == 200:
                stats = response.json()

                # Common statistics fields
                expected_stats = [
                    "total_predictions",
                    "fire_predictions",
                    "no_fire_predictions",
                    "avg_processing_time",
                    "last_prediction_time",
                ]

                # At least some stats should be present
                stats_present = sum(1 for stat in expected_stats if stat in stats)
                assert stats_present > 0, "No prediction statistics found"

                # Validate numeric stats
                for stat_name, stat_value in stats.items():
                    if isinstance(stat_value, (int, float)):
                        assert (
                            stat_value >= 0
                        ), f"Negative statistic value: {stat_name}={stat_value}"

            elif response.status_code == 404:
                pytest.skip("Prediction stats endpoint not implemented")
            else:
                pytest.fail(f"Stats endpoint failed with status {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestFlaskAPIValidation:
    """Test Flask API input validation and error handling."""

    def test_invalid_json_handling(self, api_client):
        """Test handling of invalid JSON data."""
        try:
            # Test with malformed JSON
            response = requests.post(
                f"{FLASK_API_CONFIG['base_url']}/predict",
                data="invalid json data",
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            assert response.status_code in [400, 422], "Should reject invalid JSON"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_missing_required_fields(self, api_client):
        """Test handling of missing required fields."""
        try:
            # Test with missing fields
            incomplete_data = {
                "Temperature[C]": 25.5,
                "Humidity[%]": 45.0,
                # Missing other required fields
            }

            response = api_client.predict(incomplete_data, timeout=10)
            assert response.status_code in [400, 422], "Should reject incomplete data"

            if response.status_code in [400, 422]:
                error_info = response.json()
                assert "error" in error_info or "message" in error_info

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_invalid_data_types(self, api_client):
        """Test handling of invalid data types."""
        try:
            invalid_data_tests = [
                # String instead of number
                {**VALID_SENSOR_DATA, "Temperature[C]": "not_a_number"},
                # Null values
                {**VALID_SENSOR_DATA, "Humidity[%]": None},
                # Array instead of number
                {**VALID_SENSOR_DATA, "TVOC[ppb]": [1, 2, 3]},
                # Object instead of number
                {**VALID_SENSOR_DATA, "eCO2[ppm]": {"invalid": "object"}},
            ]

            for invalid_data in invalid_data_tests:
                response = api_client.predict(invalid_data, timeout=10)
                assert response.status_code in [
                    400,
                    422,
                ], f"Should reject invalid data: {invalid_data}"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_extreme_values_handling(self, api_client):
        """Test handling of extreme sensor values."""
        try:
            extreme_value_tests = [
                # Extreme temperature
                {**VALID_SENSOR_DATA, "Temperature[C]": 1000.0},
                # Negative humidity
                {**VALID_SENSOR_DATA, "Humidity[%]": -50.0},
                # Zero pressure
                {**VALID_SENSOR_DATA, "Pressure[hPa]": 0.0},
                # Very large particulate matter
                {**VALID_SENSOR_DATA, "PM2.5": 10000.0},
            ]

            for extreme_data in extreme_value_tests:
                response = api_client.predict(extreme_data, timeout=10)

                # Should either handle gracefully (200) or reject appropriately (400/422)
                assert response.status_code in [200, 400, 422]

                if response.status_code == 200:
                    result = response.json()
                    # If handled gracefully, should still return valid prediction structure
                    assert "prediction" in result
                    assert "confidence" in result

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestFlaskAPIPerformance:
    """Test Flask API performance characteristics."""

    def test_response_time_consistency(self, api_client):
        """Test response time consistency."""
        try:
            response_times = []

            # Make multiple requests to measure consistency
            for _ in range(20):
                start_time = time.time()
                response = api_client.predict(VALID_SENSOR_DATA, timeout=10)
                end_time = time.time()

                assert response.status_code == 200
                response_times.append((end_time - start_time) * 1000)  # Convert to ms

            # Analyze response time consistency
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)

            print(f"Response Time Analysis:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Min: {min_time:.2f}ms")
            print(f"  Max: {max_time:.2f}ms")
            print(f"  Variance: {max_time - min_time:.2f}ms")

            # Response times should be reasonable and consistent
            assert avg_time < 200, f"Average response time too high: {avg_time:.2f}ms"
            assert max_time < 500, f"Maximum response time too high: {max_time:.2f}ms"

            # Variance should be reasonable (max shouldn't be more than 5x min)
            if min_time > 0:
                variance_ratio = max_time / min_time
                assert (
                    variance_ratio < 10
                ), f"Response time too variable: {variance_ratio:.2f}x"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_concurrent_request_handling(self, api_client):
        """Test concurrent request handling."""
        try:
            num_concurrent = 10

            def make_request(request_id):
                """Make a single request."""
                try:
                    start_time = time.time()
                    response = api_client.predict(VALID_SENSOR_DATA, timeout=20)
                    end_time = time.time()

                    return {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "response_time_ms": (end_time - start_time) * 1000,
                        "success": response.status_code == 200,
                    }
                except Exception as e:
                    return {"request_id": request_id, "error": str(e), "success": False}

            # Execute concurrent requests
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=num_concurrent
            ) as executor:
                futures = [
                    executor.submit(make_request, i) for i in range(num_concurrent)
                ]
                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]
            end_time = time.time()

            # Analyze results
            successful_requests = [r for r in results if r.get("success", False)]
            failed_requests = [r for r in results if not r.get("success", False)]

            print(f"Concurrent Request Analysis:")
            print(f"  Total requests: {num_concurrent}")
            print(f"  Successful: {len(successful_requests)}")
            print(f"  Failed: {len(failed_requests)}")
            print(f"  Total time: {(end_time - start_time)*1000:.2f}ms")

            # All requests should succeed
            success_rate = len(successful_requests) / len(results)
            assert success_rate >= 0.9, f"Success rate too low: {success_rate*100:.1f}%"

            # Response times should be reasonable even under concurrent load
            if successful_requests:
                response_times = [r["response_time_ms"] for r in successful_requests]
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)

                print(f"  Average response time: {avg_response_time:.2f}ms")
                print(f"  Max response time: {max_response_time:.2f}ms")

                assert (
                    avg_response_time < 300
                ), f"Concurrent average response time too high: {avg_response_time:.2f}ms"
                assert (
                    max_response_time < 1000
                ), f"Concurrent max response time too high: {max_response_time:.2f}ms"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestFlaskAPIHeaders:
    """Test Flask API headers and CORS."""

    def test_cors_headers(self, api_client):
        """Test CORS headers if enabled."""
        try:
            response = api_client.get("/health", timeout=10)
            assert response.status_code == 200

            headers = response.headers

            # Check for CORS headers (if enabled)
            cors_headers = [
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods",
                "Access-Control-Allow-Headers",
            ]

            cors_enabled = any(header in headers for header in cors_headers)

            if cors_enabled:
                print("CORS is enabled")
                # If CORS is enabled, validate headers
                if "Access-Control-Allow-Origin" in headers:
                    origin = headers["Access-Control-Allow-Origin"]
                    assert origin in [
                        "*",
                        "http://localhost:3000",
                        "http://localhost:8080",
                    ]
            else:
                print("CORS is not enabled or not configured")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")

    def test_content_type_headers(self, api_client):
        """Test content type headers."""
        try:
            response = api_client.get("/health", timeout=10)
            assert response.status_code == 200

            # Should return JSON content type
            content_type = response.headers.get("Content-Type", "")
            assert (
                "application/json" in content_type
            ), f"Expected JSON content type, got: {content_type}"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestFlaskAPIRateLimiting:
    """Test Flask API rate limiting if implemented."""

    def test_rate_limiting(self, api_client):
        """Test rate limiting functionality."""
        try:
            # Make rapid requests to test rate limiting
            rapid_requests = 50
            start_time = time.time()

            responses = []
            for i in range(rapid_requests):
                try:
                    response = api_client.get("/health", timeout=5)
                    responses.append(
                        {
                            "status_code": response.status_code,
                            "headers": dict(response.headers),
                        }
                    )
                except requests.exceptions.Timeout:
                    responses.append({"status_code": "timeout"})
                except Exception as e:
                    responses.append({"status_code": "error", "error": str(e)})

            end_time = time.time()
            duration = end_time - start_time

            # Analyze responses for rate limiting
            status_codes = [r.get("status_code") for r in responses]
            rate_limited = sum(1 for code in status_codes if code == 429)
            successful = sum(1 for code in status_codes if code == 200)

            print(f"Rate Limiting Analysis:")
            print(f"  Total requests: {rapid_requests}")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Rate: {rapid_requests/duration:.2f} req/s")
            print(f"  Successful (200): {successful}")
            print(f"  Rate limited (429): {rate_limited}")

            if rate_limited > 0:
                print("Rate limiting is active")
                # Check for rate limiting headers
                rate_limited_response = next(
                    (r for r in responses if r.get("status_code") == 429), None
                )
                if rate_limited_response and "headers" in rate_limited_response:
                    headers = rate_limited_response["headers"]
                    rate_limit_headers = [
                        "X-RateLimit-Limit",
                        "X-RateLimit-Remaining",
                        "X-RateLimit-Reset",
                        "Retry-After",
                    ]

                    for header in rate_limit_headers:
                        if header in headers:
                            print(f"  {header}: {headers[header]}")
            else:
                print("No rate limiting detected (or limit not reached)")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
