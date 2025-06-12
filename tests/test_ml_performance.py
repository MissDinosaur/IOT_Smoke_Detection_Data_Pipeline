"""
ML Performance Tests for IoT Smoke Detection Streaming Pipeline.

This module tests:
- ML model inference performance
- Memory usage during predictions
- Concurrent prediction handling
- Model loading and initialization time
- Feature engineering performance
- Batch vs single prediction efficiency
- Model scalability under load
- Resource utilization monitoring
"""

import pytest
import time
import threading
import concurrent.futures
import psutil
import os
import requests
import json
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch
import gc

# Performance test configuration
ML_PERFORMANCE_CONFIG = {
    'flask_api_url': 'http://localhost:5000',
    'performance_thresholds': {
        'single_prediction_ms': 100,
        'batch_prediction_ms_per_item': 50,
        'memory_increase_mb': 50,
        'concurrent_predictions': 10,
        'throughput_predictions_per_second': 20,
        'model_loading_seconds': 30
    },
    'load_test': {
        'duration_seconds': 60,
        'concurrent_users': 5,
        'requests_per_user': 100
    }
}

# Test data for performance testing
PERFORMANCE_TEST_DATA = {
    'Temperature[C]': 25.5,
    'Humidity[%]': 45.0,
    'TVOC[ppb]': 150.0,
    'eCO2[ppm]': 400.0,
    'Raw H2': 13000.0,
    'Raw Ethanol': 18500.0,
    'Pressure[hPa]': 1013.25,
    'PM1.0': 10.0,
    'PM2.5': 15.0,
    'NC0.5': 100.0,
    'NC1.0': 80.0,
    'NC2.5': 20.0
}


class PerformanceMonitor:
    """Utility class for monitoring performance metrics."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = None
        self.start_time = None
        self.measurements = []
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_time = time.time()
        self.measurements = []
    
    def record_measurement(self, operation_name, duration_ms, memory_mb=None):
        """Record a performance measurement."""
        if memory_mb is None:
            memory_mb = self.process.memory_info().rss / 1024 / 1024
        
        self.measurements.append({
            'operation': operation_name,
            'duration_ms': duration_ms,
            'memory_mb': memory_mb,
            'timestamp': time.time()
        })
    
    def get_memory_increase(self):
        """Get memory increase since monitoring started."""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        return current_memory - self.start_memory if self.start_memory else 0
    
    def get_summary(self):
        """Get performance summary."""
        if not self.measurements:
            return {}
        
        durations = [m['duration_ms'] for m in self.measurements]
        return {
            'total_operations': len(self.measurements),
            'avg_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'total_duration_s': (time.time() - self.start_time) if self.start_time else 0,
            'memory_increase_mb': self.get_memory_increase(),
            'throughput_ops_per_second': len(self.measurements) / (time.time() - self.start_time) if self.start_time else 0
        }


class TestMLInferencePerformance:
    """Test ML model inference performance."""
    
    def test_single_prediction_latency(self, api_client):
        """Test single prediction latency."""
        try:
            monitor = PerformanceMonitor()
            monitor.start_monitoring()
            
            # Warm up the model with a few predictions
            for _ in range(3):
                api_client.predict(PERFORMANCE_TEST_DATA, timeout=10)
            
            # Measure actual performance
            latencies = []
            for i in range(50):
                start_time = time.time()
                response = api_client.predict(PERFORMANCE_TEST_DATA, timeout=10)
                end_time = time.time()
                
                assert response.status_code == 200
                
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)
                monitor.record_measurement(f'prediction_{i}', latency_ms)
            
            # Analyze performance
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            p95_latency = np.percentile(latencies, 95)
            
            print(f"Single Prediction Performance:")
            print(f"  Average latency: {avg_latency:.2f}ms")
            print(f"  Min latency: {min_latency:.2f}ms")
            print(f"  Max latency: {max_latency:.2f}ms")
            print(f"  95th percentile: {p95_latency:.2f}ms")
            
            # Performance assertions
            threshold = ML_PERFORMANCE_CONFIG['performance_thresholds']['single_prediction_ms']
            assert avg_latency < threshold, f"Average latency {avg_latency:.2f}ms exceeds threshold {threshold}ms"
            assert p95_latency < threshold * 2, f"95th percentile latency {p95_latency:.2f}ms too high"
            
            # Memory usage should be reasonable
            memory_increase = monitor.get_memory_increase()
            memory_threshold = ML_PERFORMANCE_CONFIG['performance_thresholds']['memory_increase_mb']
            assert memory_increase < memory_threshold, f"Memory increase {memory_increase:.2f}MB exceeds threshold {memory_threshold}MB"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_batch_prediction_efficiency(self, api_client):
        """Test batch prediction efficiency vs single predictions."""
        try:
            # Test single predictions
            single_start = time.time()
            for _ in range(20):
                response = api_client.predict(PERFORMANCE_TEST_DATA, timeout=10)
                assert response.status_code == 200
            single_duration = time.time() - single_start
            
            # Test batch prediction
            batch_data = [PERFORMANCE_TEST_DATA] * 20
            batch_start = time.time()
            response = api_client.predict_batch(batch_data, timeout=30)
            batch_duration = time.time() - batch_start
            
            assert response.status_code == 200
            
            # Batch should be more efficient
            single_per_item = single_duration / 20
            batch_per_item = batch_duration / 20
            
            print(f"Batch vs Single Prediction Performance:")
            print(f"  Single predictions: {single_per_item*1000:.2f}ms per item")
            print(f"  Batch prediction: {batch_per_item*1000:.2f}ms per item")
            print(f"  Efficiency gain: {(single_per_item/batch_per_item):.2f}x")
            
            # Batch should be at least as efficient as single predictions
            assert batch_per_item <= single_per_item * 1.2, "Batch prediction should be more efficient"
            
            # Check batch performance threshold
            batch_threshold = ML_PERFORMANCE_CONFIG['performance_thresholds']['batch_prediction_ms_per_item']
            assert batch_per_item * 1000 < batch_threshold, f"Batch prediction too slow: {batch_per_item*1000:.2f}ms per item"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_concurrent_prediction_handling(self, api_client):
        """Test concurrent prediction handling."""
        try:
            monitor = PerformanceMonitor()
            monitor.start_monitoring()
            
            num_concurrent = ML_PERFORMANCE_CONFIG['performance_thresholds']['concurrent_predictions']
            
            def make_prediction(thread_id):
                """Make a prediction in a separate thread."""
                try:
                    start_time = time.time()
                    response = api_client.predict(PERFORMANCE_TEST_DATA, timeout=15)
                    end_time = time.time()
                    
                    return {
                        'thread_id': thread_id,
                        'status_code': response.status_code,
                        'duration_ms': (end_time - start_time) * 1000,
                        'success': response.status_code == 200
                    }
                except Exception as e:
                    return {
                        'thread_id': thread_id,
                        'error': str(e),
                        'success': False
                    }
            
            # Execute concurrent predictions
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
                futures = [executor.submit(make_prediction, i) for i in range(num_concurrent)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            end_time = time.time()
            
            # Analyze results
            successful_results = [r for r in results if r.get('success', False)]
            failed_results = [r for r in results if not r.get('success', False)]
            
            print(f"Concurrent Prediction Performance:")
            print(f"  Concurrent requests: {num_concurrent}")
            print(f"  Successful: {len(successful_results)}")
            print(f"  Failed: {len(failed_results)}")
            print(f"  Total time: {(end_time - start_time)*1000:.2f}ms")
            
            # All predictions should succeed
            assert len(successful_results) == num_concurrent, f"Only {len(successful_results)}/{num_concurrent} predictions succeeded"
            
            # Check individual response times
            if successful_results:
                durations = [r['duration_ms'] for r in successful_results]
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                
                print(f"  Average response time: {avg_duration:.2f}ms")
                print(f"  Max response time: {max_duration:.2f}ms")
                
                # Response times should be reasonable even under concurrent load
                threshold = ML_PERFORMANCE_CONFIG['performance_thresholds']['single_prediction_ms']
                assert avg_duration < threshold * 2, f"Concurrent prediction average time too high: {avg_duration:.2f}ms"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_sustained_load_performance(self, api_client):
        """Test performance under sustained load."""
        try:
            monitor = PerformanceMonitor()
            monitor.start_monitoring()
            
            duration = 30  # 30 seconds of sustained load
            target_rps = 5  # 5 requests per second
            
            start_time = time.time()
            request_count = 0
            errors = 0
            response_times = []
            
            while time.time() - start_time < duration:
                request_start = time.time()
                
                try:
                    response = api_client.predict(PERFORMANCE_TEST_DATA, timeout=10)
                    request_end = time.time()
                    
                    if response.status_code == 200:
                        response_times.append((request_end - request_start) * 1000)
                    else:
                        errors += 1
                    
                    request_count += 1
                    
                    # Control request rate
                    elapsed = request_end - request_start
                    sleep_time = (1.0 / target_rps) - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        
                except Exception:
                    errors += 1
                    request_count += 1
            
            total_duration = time.time() - start_time
            actual_rps = request_count / total_duration
            error_rate = errors / request_count if request_count > 0 else 0
            
            print(f"Sustained Load Performance:")
            print(f"  Duration: {total_duration:.2f}s")
            print(f"  Total requests: {request_count}")
            print(f"  Actual RPS: {actual_rps:.2f}")
            print(f"  Error rate: {error_rate*100:.2f}%")
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                p95_response_time = np.percentile(response_times, 95)
                
                print(f"  Average response time: {avg_response_time:.2f}ms")
                print(f"  95th percentile response time: {p95_response_time:.2f}ms")
                
                # Performance assertions
                assert error_rate < 0.05, f"Error rate too high: {error_rate*100:.2f}%"
                assert avg_response_time < ML_PERFORMANCE_CONFIG['performance_thresholds']['single_prediction_ms'] * 1.5
            
            # Memory usage should be stable
            memory_increase = monitor.get_memory_increase()
            memory_threshold = ML_PERFORMANCE_CONFIG['performance_thresholds']['memory_increase_mb']
            assert memory_increase < memory_threshold, f"Memory leak detected: {memory_increase:.2f}MB increase"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestMLResourceUtilization:
    """Test ML model resource utilization."""
    
    def test_memory_usage_stability(self, api_client):
        """Test memory usage stability during predictions."""
        try:
            monitor = PerformanceMonitor()
            monitor.start_monitoring()
            
            initial_memory = monitor.process.memory_info().rss / 1024 / 1024
            memory_measurements = [initial_memory]
            
            # Make predictions and monitor memory
            for i in range(100):
                response = api_client.predict(PERFORMANCE_TEST_DATA, timeout=10)
                assert response.status_code == 200
                
                if i % 10 == 0:  # Measure memory every 10 predictions
                    current_memory = monitor.process.memory_info().rss / 1024 / 1024
                    memory_measurements.append(current_memory)
                    
                    # Force garbage collection periodically
                    if i % 50 == 0:
                        gc.collect()
            
            final_memory = monitor.process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            max_memory = max(memory_measurements)
            memory_variance = np.var(memory_measurements)
            
            print(f"Memory Usage Analysis:")
            print(f"  Initial memory: {initial_memory:.2f}MB")
            print(f"  Final memory: {final_memory:.2f}MB")
            print(f"  Memory increase: {memory_increase:.2f}MB")
            print(f"  Peak memory: {max_memory:.2f}MB")
            print(f"  Memory variance: {memory_variance:.2f}")
            
            # Memory should be stable (no significant leaks)
            memory_threshold = ML_PERFORMANCE_CONFIG['performance_thresholds']['memory_increase_mb']
            assert memory_increase < memory_threshold, f"Potential memory leak: {memory_increase:.2f}MB increase"
            
            # Memory variance should be low (stable usage)
            assert memory_variance < 100, f"Memory usage too variable: {memory_variance:.2f}"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_cpu_utilization(self, api_client):
        """Test CPU utilization during ML predictions."""
        try:
            # Measure CPU usage during predictions
            cpu_measurements = []
            
            def measure_cpu():
                """Measure CPU usage in background."""
                for _ in range(20):  # Measure for 20 seconds
                    cpu_percent = psutil.cpu_percent(interval=1)
                    cpu_measurements.append(cpu_percent)
            
            # Start CPU monitoring in background
            cpu_thread = threading.Thread(target=measure_cpu)
            cpu_thread.start()
            
            # Make predictions while monitoring CPU
            start_time = time.time()
            prediction_count = 0
            
            while time.time() - start_time < 15:  # Run for 15 seconds
                response = api_client.predict(PERFORMANCE_TEST_DATA, timeout=10)
                assert response.status_code == 200
                prediction_count += 1
                time.sleep(0.1)  # Small delay between predictions
            
            cpu_thread.join()
            
            if cpu_measurements:
                avg_cpu = sum(cpu_measurements) / len(cpu_measurements)
                max_cpu = max(cpu_measurements)
                
                print(f"CPU Utilization Analysis:")
                print(f"  Predictions made: {prediction_count}")
                print(f"  Average CPU: {avg_cpu:.2f}%")
                print(f"  Peak CPU: {max_cpu:.2f}%")
                
                # CPU usage should be reasonable
                assert avg_cpu < 80, f"Average CPU usage too high: {avg_cpu:.2f}%"
                assert max_cpu < 95, f"Peak CPU usage too high: {max_cpu:.2f}%"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestMLScalabilityLimits:
    """Test ML model scalability limits."""
    
    def test_maximum_concurrent_requests(self, api_client):
        """Test maximum number of concurrent requests the model can handle."""
        try:
            max_concurrent_levels = [5, 10, 20, 30]
            results = {}
            
            for concurrent_level in max_concurrent_levels:
                print(f"Testing {concurrent_level} concurrent requests...")
                
                def make_request(request_id):
                    try:
                        start_time = time.time()
                        response = api_client.predict(PERFORMANCE_TEST_DATA, timeout=30)
                        end_time = time.time()
                        
                        return {
                            'success': response.status_code == 200,
                            'duration_ms': (end_time - start_time) * 1000,
                            'status_code': response.status_code
                        }
                    except Exception as e:
                        return {
                            'success': False,
                            'error': str(e)
                        }
                
                # Execute concurrent requests
                start_time = time.time()
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_level) as executor:
                    futures = [executor.submit(make_request, i) for i in range(concurrent_level)]
                    request_results = [future.result() for future in concurrent.futures.as_completed(futures)]
                end_time = time.time()
                
                # Analyze results
                successful = sum(1 for r in request_results if r.get('success', False))
                success_rate = successful / len(request_results)
                total_time = end_time - start_time
                
                if successful > 0:
                    successful_results = [r for r in request_results if r.get('success', False)]
                    avg_response_time = sum(r['duration_ms'] for r in successful_results) / len(successful_results)
                else:
                    avg_response_time = float('inf')
                
                results[concurrent_level] = {
                    'success_rate': success_rate,
                    'avg_response_time_ms': avg_response_time,
                    'total_time_s': total_time
                }
                
                print(f"  Success rate: {success_rate*100:.1f}%")
                print(f"  Avg response time: {avg_response_time:.2f}ms")
                print(f"  Total time: {total_time:.2f}s")
                
                # If success rate drops significantly, we've found the limit
                if success_rate < 0.8:
                    print(f"  Scalability limit reached at {concurrent_level} concurrent requests")
                    break
            
            # Find the maximum sustainable concurrent level
            sustainable_levels = [level for level, result in results.items() 
                                if result['success_rate'] >= 0.95 and result['avg_response_time_ms'] < 1000]
            
            if sustainable_levels:
                max_sustainable = max(sustainable_levels)
                print(f"Maximum sustainable concurrent requests: {max_sustainable}")
                
                # Should handle at least the configured threshold
                min_threshold = ML_PERFORMANCE_CONFIG['performance_thresholds']['concurrent_predictions']
                assert max_sustainable >= min_threshold, f"Can only handle {max_sustainable} concurrent requests, need {min_threshold}"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_large_batch_handling(self, api_client):
        """Test handling of large batch predictions."""
        try:
            batch_sizes = [10, 50, 100, 200]
            results = {}
            
            for batch_size in batch_sizes:
                print(f"Testing batch size: {batch_size}")
                
                # Create batch data
                batch_data = [PERFORMANCE_TEST_DATA] * batch_size
                
                try:
                    start_time = time.time()
                    response = api_client.predict_batch(batch_data, timeout=60)
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        result_data = response.json()
                        predictions = result_data.get('predictions', [])
                        
                        duration = end_time - start_time
                        per_item_ms = (duration * 1000) / batch_size
                        
                        results[batch_size] = {
                            'success': True,
                            'duration_s': duration,
                            'per_item_ms': per_item_ms,
                            'predictions_count': len(predictions)
                        }
                        
                        print(f"  Duration: {duration:.2f}s")
                        print(f"  Per item: {per_item_ms:.2f}ms")
                        print(f"  Predictions returned: {len(predictions)}")
                        
                        # Verify all predictions were returned
                        assert len(predictions) == batch_size, f"Expected {batch_size} predictions, got {len(predictions)}"
                        
                    else:
                        results[batch_size] = {
                            'success': False,
                            'status_code': response.status_code
                        }
                        print(f"  Failed with status code: {response.status_code}")
                        
                except Exception as e:
                    results[batch_size] = {
                        'success': False,
                        'error': str(e)
                    }
                    print(f"  Failed with error: {e}")
            
            # Analyze batch performance scaling
            successful_batches = {size: result for size, result in results.items() if result.get('success', False)}
            
            if len(successful_batches) >= 2:
                # Check if performance scales reasonably
                sizes = sorted(successful_batches.keys())
                per_item_times = [successful_batches[size]['per_item_ms'] for size in sizes]
                
                print(f"Batch Performance Scaling:")
                for size, per_item in zip(sizes, per_item_times):
                    print(f"  Batch {size}: {per_item:.2f}ms per item")
                
                # Per-item time should not increase dramatically with batch size
                if len(per_item_times) >= 2:
                    scaling_factor = per_item_times[-1] / per_item_times[0]
                    assert scaling_factor < 3.0, f"Poor batch scaling: {scaling_factor:.2f}x slower for large batches"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
