#!/usr/bin/env python3
"""
Comprehensive test runner for the IoT Smoke Detection Data Pipeline.

This script provides various testing options including:
- Unit tests for individual components
- Integration tests for end-to-end workflows
- Performance tests for stream processing
- ML model validation tests
- Coverage reporting
- Test result analysis

Usage:
    python tests/run_tests.py [options]

Examples:
    # Run all tests
    python tests/run_tests.py

    # Run only unit tests
    python tests/run_tests.py --unit

    # Run ML tests with coverage
    python tests/run_tests.py --ml --coverage

    # Run stream processing tests
    python tests/run_tests.py --stream

    # Run tests with detailed output
    python tests/run_tests.py --verbose

    # Run specific test file
    python tests/run_tests.py --file tests/ml/test_training.py
"""

import sys
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parents[1]
sys.path.append(str(project_root))


class TestRunner:
    """Comprehensive test runner for the smoke detection pipeline."""
    
    def __init__(self):
        self.project_root = Path(__file__).parents[1]
        self.tests_dir = self.project_root / "tests"
        self.results = {}
    
    def run_pytest(
        self,
        test_paths: List[str],
        markers: Optional[List[str]] = None,
        coverage: bool = False,
        verbose: bool = False,
        parallel: bool = False,
        output_file: Optional[str] = None
    ) -> int:
        """
        Run pytest with specified options.
        
        Args:
            test_paths: List of test paths to run
            markers: List of pytest markers to filter tests
            coverage: Whether to generate coverage report
            verbose: Whether to use verbose output
            parallel: Whether to run tests in parallel
            output_file: File to save test results
            
        Returns:
            Exit code from pytest
        """
        cmd = ["python", "-m", "pytest"]
        
        # Add test paths
        cmd.extend(test_paths)
        
        # Add markers
        if markers:
            marker_expr = " and ".join(markers)
            cmd.extend(["-m", marker_expr])
        
        # Add coverage options
        if coverage:
            cmd.extend([
                "--cov=data_processing",
                "--cov=ml",
                "--cov-report=html:tests/coverage_html",
                "--cov-report=term-missing",
                "--cov-report=xml:tests/coverage.xml"
            ])
        
        # Add verbosity
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        # Add parallel execution
        if parallel:
            cmd.extend(["-n", "auto"])
        
        # Add output options
        cmd.extend([
            "--tb=short",
            "--strict-markers",
            "--disable-warnings"
        ])
        
        # Add JUnit XML output
        if output_file:
            cmd.extend(["--junitxml", output_file])
        
        print(f"Running command: {' '.join(cmd)}")
        print("-" * 80)
        
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.project_root)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\nTest execution completed in {duration:.2f} seconds")
        
        return result.returncode
    
    def run_unit_tests(self, coverage: bool = False, verbose: bool = False) -> int:
        """Run unit tests only."""
        print("🧪 Running Unit Tests")
        print("=" * 50)
        
        return self.run_pytest(
            test_paths=[str(self.tests_dir)],
            markers=["unit"],
            coverage=coverage,
            verbose=verbose,
            output_file="tests/unit_test_results.xml"
        )
    
    def run_integration_tests(self, coverage: bool = False, verbose: bool = False) -> int:
        """Run integration tests only."""
        print("🔗 Running Integration Tests")
        print("=" * 50)
        
        return self.run_pytest(
            test_paths=[str(self.tests_dir)],
            markers=["integration"],
            coverage=coverage,
            verbose=verbose,
            output_file="tests/integration_test_results.xml"
        )
    
    def run_ml_tests(self, coverage: bool = False, verbose: bool = False) -> int:
        """Run ML-related tests."""
        print("🤖 Running ML Tests")
        print("=" * 50)
        
        return self.run_pytest(
            test_paths=[str(self.tests_dir / "ml")],
            markers=["ml"],
            coverage=coverage,
            verbose=verbose,
            output_file="tests/ml_test_results.xml"
        )
    
    def run_stream_tests(self, coverage: bool = False, verbose: bool = False) -> int:
        """Run stream processing tests."""
        print("🌊 Running Stream Processing Tests")
        print("=" * 50)
        
        return self.run_pytest(
            test_paths=[str(self.tests_dir / "stream_processing")],
            markers=["stream"],
            coverage=coverage,
            verbose=verbose,
            output_file="tests/stream_test_results.xml"
        )
    
    def run_all_tests(self, coverage: bool = False, verbose: bool = False, parallel: bool = False) -> int:
        """Run all tests."""
        print("🚀 Running All Tests")
        print("=" * 50)
        
        return self.run_pytest(
            test_paths=[str(self.tests_dir)],
            coverage=coverage,
            verbose=verbose,
            parallel=parallel,
            output_file="tests/all_test_results.xml"
        )
    
    def run_specific_file(self, file_path: str, coverage: bool = False, verbose: bool = False) -> int:
        """Run tests from a specific file."""
        print(f"📄 Running Tests from {file_path}")
        print("=" * 50)
        
        return self.run_pytest(
            test_paths=[file_path],
            coverage=coverage,
            verbose=verbose,
            output_file="tests/specific_test_results.xml"
        )
    
    def run_fast_tests(self, verbose: bool = False) -> int:
        """Run only fast tests (exclude slow tests)."""
        print("⚡ Running Fast Tests Only")
        print("=" * 50)
        
        return self.run_pytest(
            test_paths=[str(self.tests_dir)],
            markers=["not slow"],
            verbose=verbose,
            parallel=True,
            output_file="tests/fast_test_results.xml"
        )
    
    def generate_test_report(self) -> None:
        """Generate a comprehensive test report."""
        print("\n📊 Generating Test Report")
        print("=" * 50)
        
        report_file = self.tests_dir / "test_report.md"
        
        with open(report_file, 'w') as f:
            f.write("# Test Report\n\n")
            f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Test structure
            f.write("## Test Structure\n\n")
            f.write("```\n")
            f.write("tests/\n")
            f.write("├── stream_processing/\n")
            f.write("│   ├── test_error_handler.py\n")
            f.write("│   └── test_metrics_streaming.py\n")
            f.write("├── ml/\n")
            f.write("│   ├── test_training.py\n")
            f.write("│   └── test_inference.py\n")
            f.write("├── conftest.py\n")
            f.write("└── run_tests.py\n")
            f.write("```\n\n")
            
            # Test categories
            f.write("## Test Categories\n\n")
            f.write("- **Unit Tests**: Individual component testing\n")
            f.write("- **Integration Tests**: End-to-end workflow testing\n")
            f.write("- **ML Tests**: Machine learning pipeline testing\n")
            f.write("- **Stream Tests**: Stream processing testing\n\n")
            
            # Coverage information
            f.write("## Coverage\n\n")
            f.write("Coverage reports are generated in:\n")
            f.write("- HTML: `tests/coverage_html/index.html`\n")
            f.write("- XML: `tests/coverage.xml`\n\n")
            
            # Usage examples
            f.write("## Usage Examples\n\n")
            f.write("```bash\n")
            f.write("# Run all tests with coverage\n")
            f.write("python tests/run_tests.py --all --coverage\n\n")
            f.write("# Run only ML tests\n")
            f.write("python tests/run_tests.py --ml\n\n")
            f.write("# Run fast tests in parallel\n")
            f.write("python tests/run_tests.py --fast\n")
            f.write("```\n")
        
        print(f"Test report generated: {report_file}")
    
    def check_dependencies(self) -> bool:
        """Check if all test dependencies are available."""
        print("🔍 Checking Test Dependencies")
        print("=" * 50)
        
        required_packages = [
            "pytest",
            "pytest-cov",
            "pytest-xdist",
            "pandas",
            "numpy",
            "scikit-learn",
            "flask"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package}")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
            return False
        
        print("\n✅ All dependencies available")
        return True


def main():
    """Main function for test runner."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for IoT Smoke Detection Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test selection options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--all", action="store_true", help="Run all tests")
    test_group.add_argument("--unit", action="store_true", help="Run unit tests only")
    test_group.add_argument("--integration", action="store_true", help="Run integration tests only")
    test_group.add_argument("--ml", action="store_true", help="Run ML tests only")
    test_group.add_argument("--stream", action="store_true", help="Run stream processing tests only")
    test_group.add_argument("--fast", action="store_true", help="Run fast tests only (exclude slow)")
    test_group.add_argument("--file", type=str, help="Run tests from specific file")
    
    # Test execution options
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--parallel", "-p", action="store_true", help="Run tests in parallel")
    parser.add_argument("--check-deps", action="store_true", help="Check test dependencies")
    parser.add_argument("--report", action="store_true", help="Generate test report")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Check dependencies if requested
    if args.check_deps:
        if not runner.check_dependencies():
            sys.exit(1)
        return
    
    # Generate report if requested
    if args.report:
        runner.generate_test_report()
        return
    
    # Run tests based on selection
    exit_code = 0
    
    if args.unit:
        exit_code = runner.run_unit_tests(args.coverage, args.verbose)
    elif args.integration:
        exit_code = runner.run_integration_tests(args.coverage, args.verbose)
    elif args.ml:
        exit_code = runner.run_ml_tests(args.coverage, args.verbose)
    elif args.stream:
        exit_code = runner.run_stream_tests(args.coverage, args.verbose)
    elif args.fast:
        exit_code = runner.run_fast_tests(args.verbose)
    elif args.file:
        exit_code = runner.run_specific_file(args.file, args.coverage, args.verbose)
    else:
        # Default: run all tests
        exit_code = runner.run_all_tests(args.coverage, args.verbose, args.parallel)
    
    # Print summary
    print("\n" + "=" * 80)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    print(f"Exit code: {exit_code}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
