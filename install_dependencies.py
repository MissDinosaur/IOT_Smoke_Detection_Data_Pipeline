#!/usr/bin/env python3
"""
IoT Smoke Detection Data Pipeline - Dependency Installation Script
Handles dependency conflicts and provides fallback options.
"""

import subprocess
import sys
import os
from typing import List, Dict, Optional

def run_command(cmd: List[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e.stderr}")
        return False

def install_core_dependencies() -> bool:
    """Install core dependencies without problematic packages."""
    core_packages = [
        "numpy>=1.24.3,<2.0",
        "pandas>=2.0.3,<3.0", 
        "scikit-learn>=1.3.2,<2.0",
        "scipy>=1.10.1,<2.0",
        "joblib>=1.3.2",
        "flask>=2.2.5,<2.3",
        "flask-cors>=3.0.10",
        "werkzeug>=2.0,<3.0",
        "gunicorn>=20.1.0",
        "requests>=2.31.0",
        "kafka-python>=2.0.2",
        "sqlalchemy>=1.4.48,<2.0",
        "psycopg2-binary>=2.9.7",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
        "prometheus-client>=0.17.1",
        "redis>=4.6.0",
        "schedule==1.2.0"
    ]
    
    print("📦 Installing core dependencies...")
    for package in core_packages:
        if not run_command([sys.executable, "-m", "pip", "install", package], f"Installing {package}"):
            print(f"⚠️  Failed to install {package}, continuing...")
    
    return True

def install_pyspark_with_compatibility() -> bool:
    """Install PySpark with correct py4j version."""
    print("🔥 Installing PySpark with compatible py4j...")
    
    # First install specific py4j version
    if not run_command([sys.executable, "-m", "pip", "install", "py4j==0.10.9.7"], "Installing py4j"):
        return False
    
    # Then install PySpark
    if not run_command([sys.executable, "-m", "pip", "install", "pyspark>=3.4.1,<3.6.0"], "Installing PySpark"):
        return False
    
    return True

def install_airflow_separately() -> bool:
    """Install Airflow in a way that avoids conflicts."""
    print("🌪️  Installing Airflow (this may take a while)...")
    
    # Set constraints for Airflow installation
    airflow_version = "2.10.3"
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    constraint_url = f"https://raw.githubusercontent.com/apache/airflow/constraints-{airflow_version}/constraints-{python_version}.txt"
    
    cmd = [
        sys.executable, "-m", "pip", "install", 
        f"apache-airflow=={airflow_version}",
        "--constraint", constraint_url
    ]
    
    return run_command(cmd, "Installing Apache Airflow with constraints")

def install_testing_dependencies() -> bool:
    """Install testing and development dependencies."""
    test_packages = [
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0", 
        "pytest-mock>=3.11.1",
        "black>=23.7.0",
        "flake8>=6.0.0",
        "mypy>=1.5.0"
    ]
    
    print("🧪 Installing testing dependencies...")
    for package in test_packages:
        run_command([sys.executable, "-m", "pip", "install", package], f"Installing {package}")
    
    return True

def main():
    """Main installation process."""
    print("🚀 IoT Smoke Detection Data Pipeline - Dependency Installation")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected")
    
    # Upgrade pip first
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], "Upgrading pip")
    
    # Install dependencies in order
    steps = [
        ("Core Dependencies", install_core_dependencies),
        ("PySpark with Compatibility", install_pyspark_with_compatibility),
        ("Testing Dependencies", install_testing_dependencies),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        try:
            step_func()
        except Exception as e:
            print(f"❌ Error in {step_name}: {e}")
            print("Continuing with next step...")
    
    # Optional Airflow installation
    print(f"\n{'='*20} Optional: Apache Airflow {'='*20}")
    install_airflow = input("Do you want to install Apache Airflow? (y/N): ").lower().strip()
    if install_airflow in ['y', 'yes']:
        install_airflow_separately()
    else:
        print("⏭️  Skipping Airflow installation")
    
    print("\n🎉 Installation process completed!")
    print("\n📋 Next steps:")
    print("1. Test the installation: python -c 'import pandas, flask, sklearn; print(\"✅ Core packages working\")'")
    print("2. Run tests: pytest tests/ (if you have tests)")
    print("3. Start your application")
    
    print("\n⚠️  If you encountered errors:")
    print("- Try using requirements_docker.txt for fixed versions")
    print("- Install Airflow in a separate virtual environment")
    print("- Check the Docker logs for system dependency issues")

if __name__ == "__main__":
    main()
