#!/usr/bin/env python3
"""
Test runner for IoT Smoke Detection Streaming Tests.

This script provides convenient ways to run different types of streaming tests:
- Unit tests
- Integration tests
- Performance tests
- Kafka-specific tests
- API-specific tests
- Complete test suite

Usage:
    python tests/run_streaming_tests.py --help
    python tests/run_streaming_tests.py --unit
    python tests/run_streaming_tests.py --integration
    python tests/run_streaming_tests.py --kafka
    python tests/run_streaming_tests.py --performance
    python tests/run_streaming_tests.py --all
"""

import argparse
import subprocess
import sys
import os
import time
import requests
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_CONFIG = {
    "kafka_bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    "flask_api_url": os.getenv("FLASK_API_URL", "http://localhost:5000"),
    "spark_ui_url": os.getenv("SPARK_UI_URL", "http://localhost:4040"),
    "test_timeout": int(os.getenv("TEST_TIMEOUT", "300")),
}


def check_service_health(url, service_name, timeout=30):
    """Check if a service is healthy and ready for testing."""
    print(f"🔍 Checking {service_name} health at {url}...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {service_name} is healthy")
                return True
        except requests.exceptions.RequestException:
            pass

        print(f"⏳ Waiting for {service_name}...")
        time.sleep(2)

    print(f"❌ {service_name} is not available after {timeout}s")
    return False


def check_kafka_health():
    """Check Kafka health by attempting to create a producer."""
    print("🔍 Checking Kafka health...")
    try:
        from kafka import KafkaProducer

        producer = KafkaProducer(
            bootstrap_servers=TEST_CONFIG["kafka_bootstrap_servers"],
            request_timeout_ms=5000,
        )
        producer.close()
        print("✅ Kafka is healthy")
        return True
    except Exception as e:
        print(f"❌ Kafka is not available: {e}")
        return False


def run_pytest_command(args, test_markers=None, test_files=None):
    """Run pytest with specified arguments and markers."""
    cmd = ["python", "-m", "pytest"]

    # Add test files or default to tests directory
    if test_files:
        cmd.extend(test_files)
    else:
        cmd.append("tests/")

    # Add markers
    if test_markers:
        marker_expr = " and ".join(test_markers)
        cmd.extend(["-m", marker_expr])

    # Add common arguments
    cmd.extend(
        [
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            "--strict-markers",  # Strict marker checking
            "--disable-warnings",  # Disable warnings for cleaner output
            f'--timeout={TEST_CONFIG["test_timeout"]}',  # Test timeout
        ]
    )

    # Add additional arguments
    cmd.extend(args)

    print(f"🚀 Running command: {' '.join(cmd)}")
    return subprocess.run(cmd)


def run_unit_tests(args):
    """Run unit tests only."""
    print("🧪 Running unit tests...")
    test_files = [
        "tests/test_streaming.py::TestDataProcessingLogic",
        "tests/test_kafka_integration.py::TestKafkaConnection",
        "tests/test_spark_streaming.py::TestDataProcessingLogic",
    ]
    return run_pytest_command(args, test_markers=["unit"], test_files=test_files)


def run_integration_tests(args):
    """Run integration tests."""
    print("🔗 Running integration tests...")

    # Check service health first
    services_healthy = True

    if not check_kafka_health():
        print("⚠️  Kafka not available - some integration tests will be skipped")
        services_healthy = False

    if not check_service_health(f"{TEST_CONFIG['flask_api_url']}/health", "Flask API"):
        print("⚠️  Flask API not available - some integration tests will be skipped")
        services_healthy = False

    if not services_healthy:
        print("⚠️  Some services are not available. Tests will be skipped as needed.")

    test_files = [
        "tests/test_streaming.py::TestEndToEndStreaming",
        "tests/test_kafka_integration.py::TestKafkaReliability",
        "tests/test_spark_streaming.py::TestMLIntegration",
    ]
    return run_pytest_command(args, test_markers=["integration"], test_files=test_files)


def run_kafka_tests(args):
    """Run Kafka-specific tests."""
    print("� Running Kafka tests...")

    if not check_kafka_health():
        print("❌ Kafka is required for these tests but is not available")
        return subprocess.CompletedProcess(args=[], returncode=1)

    test_files = [
        "tests/test_kafka_integration.py",
        "tests/test_streaming.py::TestKafkaProducer",
        "tests/test_streaming.py::TestKafkaConsumer",
    ]
    return run_pytest_command(args, test_markers=["kafka"], test_files=test_files)


def run_api_tests(args):
    """Run API-specific tests."""
    print("🌐 Running API tests...")

    if not check_service_health(f"{TEST_CONFIG['flask_api_url']}/health", "Flask API"):
        print("❌ Flask API is required for these tests but is not available")
        return subprocess.CompletedProcess(args=[], returncode=1)

    test_files = [
        "tests/test_streaming.py::TestFlaskAPIIntegration",
        "tests/test_spark_streaming.py::TestMLIntegration",
    ]
    return run_pytest_command(args, test_markers=["api"], test_files=test_files)


def run_performance_tests(args):
    """Run performance tests."""
    print("⚡ Running performance tests...")

    # Check if services are available
    services_available = []
    if check_kafka_health():
        services_available.append("Kafka")
    if check_service_health(f"{TEST_CONFIG['flask_api_url']}/health", "Flask API"):
        services_available.append("Flask API")

    if not services_available:
        print("❌ No services available for performance testing")
        return subprocess.CompletedProcess(args=[], returncode=1)

    print(f"📊 Performance testing with: {', '.join(services_available)}")

    test_files = [
        "tests/test_streaming.py::TestKafkaProducer::test_producer_performance",
        "tests/test_streaming.py::TestEndToEndStreaming::test_streaming_performance",
        "tests/test_kafka_integration.py::TestKafkaPerformance",
        "tests/test_spark_streaming.py::TestStreamingPerformance",
    ]
    return run_pytest_command(args, test_markers=["performance"], test_files=test_files)


def run_spark_tests(args):
    """Run Spark-specific tests."""
    print("⚡ Running Spark tests...")

    if not check_service_health(TEST_CONFIG["spark_ui_url"], "Spark UI"):
        print("⚠️  Spark UI not available - some tests will be skipped")

    test_files = [
        "tests/test_spark_streaming.py",
    ]
    return run_pytest_command(args, test_markers=["spark"], test_files=test_files)


def run_ml_tests(args):
    """Run ML-specific tests."""
    print("🤖 Running ML tests...")

    if not check_service_health(f"{TEST_CONFIG['flask_api_url']}/health", "Flask API"):
        print("❌ Flask API is required for ML tests but is not available")
        return subprocess.CompletedProcess(args=[], returncode=1)

    # Check if ML model is available
    try:
        import requests

        response = requests.get(
            f"{TEST_CONFIG['flask_api_url']}/model/info", timeout=10
        )
        if response.status_code != 200:
            print("⚠️  ML model may not be fully loaded - some tests may fail")
    except:
        print("⚠️  Could not verify ML model status")

    test_files = [
        "tests/test_ml_streaming_integration.py",
    ]
    return run_pytest_command(args, test_markers=["ml"], test_files=test_files)


def run_ml_performance_tests(args):
    """Run ML performance tests."""
    print("🚀 Running ML performance tests...")

    if not check_service_health(f"{TEST_CONFIG['flask_api_url']}/health", "Flask API"):
        print("❌ Flask API is required for ML performance tests but is not available")
        return subprocess.CompletedProcess(args=[], returncode=1)

    print("📊 ML Performance testing - this may take several minutes...")

    test_files = [
        "tests/test_ml_performance.py",
    ]
    return run_pytest_command(
        args, test_markers=["performance", "ml"], test_files=test_files
    )


def run_flask_tests(args):
    """Run comprehensive Flask API tests."""
    print("🌐 Running comprehensive Flask API tests...")

    if not check_service_health(f"{TEST_CONFIG['flask_api_url']}/health", "Flask API"):
        print("❌ Flask API is required for Flask tests but is not available")
        return subprocess.CompletedProcess(args=[], returncode=1)

    print("🔍 Testing all Flask endpoints, validation, performance, and headers...")

    test_files = [
        "tests/test_flask_api_comprehensive.py",
    ]
    return run_pytest_command(
        args, test_markers=["api", "flask"], test_files=test_files
    )


def run_all_tests(args):
    """Run all streaming tests."""
    print("🎯 Running all streaming tests...")

    # Check service health
    print("🔍 Checking all services...")
    kafka_available = check_kafka_health()
    api_available = check_service_health(
        f"{TEST_CONFIG['flask_api_url']}/health", "Flask API"
    )
    spark_available = check_service_health(TEST_CONFIG["spark_ui_url"], "Spark UI")

    print(f"\n📊 Service Status:")
    print(f"  Kafka: {'✅' if kafka_available else '❌'}")
    print(f"  Flask API: {'✅' if api_available else '❌'}")
    print(f"  Spark UI: {'✅' if spark_available else '❌'}")
    print()

    test_files = [
        "tests/test_streaming.py",
        "tests/test_kafka_integration.py",
        "tests/test_spark_streaming.py",
        "tests/test_ml_streaming_integration.py",
        "tests/test_ml_performance.py",
        "tests/test_flask_api_comprehensive.py",
    ]
    return run_pytest_command(args, test_files=test_files)


def run_quick_tests(args):
    """Run quick smoke tests to verify basic functionality."""
    print("🚀 Running quick smoke tests...")

    test_files = [
        "tests/test_streaming.py::TestDataProcessingLogic::test_sensor_data_validation",
        "tests/test_streaming.py::TestDataProcessingLogic::test_data_transformation",
        "tests/test_kafka_integration.py::TestKafkaConnection::test_kafka_cluster_connection",
        "tests/test_spark_streaming.py::TestSparkStreamingSetup::test_spark_streaming_context",
    ]

    # Add quick test arguments
    quick_args = args + ["--maxfail=1", "--tb=line"]
    return run_pytest_command(quick_args, test_files=test_files)


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run IoT Smoke Detection Streaming Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_streaming_tests.py --unit
  python tests/run_streaming_tests.py --integration --verbose
  python tests/run_streaming_tests.py --kafka --performance
  python tests/run_streaming_tests.py --all --html-report
  python tests/run_streaming_tests.py --quick
        """,
    )

    # Test type selection
    test_group = parser.add_mutually_exclusive_group(required=True)
    test_group.add_argument("--unit", action="store_true", help="Run unit tests only")
    test_group.add_argument(
        "--integration", action="store_true", help="Run integration tests"
    )
    test_group.add_argument(
        "--kafka", action="store_true", help="Run Kafka-specific tests"
    )
    test_group.add_argument("--api", action="store_true", help="Run API-specific tests")
    test_group.add_argument(
        "--flask", action="store_true", help="Run comprehensive Flask API tests"
    )
    test_group.add_argument(
        "--spark", action="store_true", help="Run Spark-specific tests"
    )
    test_group.add_argument(
        "--performance", action="store_true", help="Run performance tests"
    )
    test_group.add_argument("--ml", action="store_true", help="Run ML-specific tests")
    test_group.add_argument(
        "--ml-performance", action="store_true", help="Run ML performance tests"
    )
    test_group.add_argument("--all", action="store_true", help="Run all tests")
    test_group.add_argument(
        "--quick", action="store_true", help="Run quick smoke tests"
    )

    # Output options
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")
    parser.add_argument(
        "--html-report", action="store_true", help="Generate HTML report"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")

    # Test filtering
    parser.add_argument("--keyword", "-k", help="Run tests matching keyword")
    parser.add_argument("--maxfail", type=int, help="Stop after N failures")

    args = parser.parse_args()

    # Build pytest arguments
    pytest_args = []

    if args.verbose:
        pytest_args.append("-vv")
    elif args.quiet:
        pytest_args.append("-q")

    if args.html_report:
        pytest_args.extend(
            ["--html=tests/reports/streaming_test_report.html", "--self-contained-html"]
        )

    if args.coverage:
        pytest_args.extend(
            [
                "--cov=data_processing",
                "--cov=app",
                "--cov-report=html:tests/reports/coverage",
            ]
        )

    if args.parallel:
        pytest_args.extend(["-n", "auto"])

    if args.keyword:
        pytest_args.extend(["-k", args.keyword])

    if args.maxfail:
        pytest_args.extend(["--maxfail", str(args.maxfail)])

    # Create reports directory
    reports_dir = Path("tests/reports")
    reports_dir.mkdir(exist_ok=True)

    # Run selected test suite
    print("🧪 IoT Smoke Detection - Streaming Test Runner")
    print("=" * 50)

    if args.unit:
        result = run_unit_tests(pytest_args)
    elif args.integration:
        result = run_integration_tests(pytest_args)
    elif args.kafka:
        result = run_kafka_tests(pytest_args)
    elif args.api:
        result = run_api_tests(pytest_args)
    elif args.flask:
        result = run_flask_tests(pytest_args)
    elif args.spark:
        result = run_spark_tests(pytest_args)
    elif args.performance:
        result = run_performance_tests(pytest_args)
    elif args.ml:
        result = run_ml_tests(pytest_args)
    elif args.ml_performance:
        result = run_ml_performance_tests(pytest_args)
    elif args.all:
        result = run_all_tests(pytest_args)
    elif args.quick:
        result = run_quick_tests(pytest_args)

    # Print results
    print("\n" + "=" * 50)
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        print(f"Exit code: {result.returncode}")

    if args.html_report:
        print(f"📊 HTML report: tests/reports/streaming_test_report.html")

    if args.coverage:
        print(f"📈 Coverage report: tests/reports/coverage/index.html")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
