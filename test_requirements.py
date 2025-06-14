#!/usr/bin/env python3
"""
Test script to verify that requirements can be installed successfully
"""

import subprocess
import sys
import tempfile
import os

def test_requirements_file(requirements_file):
    """Test if a requirements file can be installed successfully"""
    print(f"\n🧪 Testing {requirements_file}...")
    
    # Create a temporary virtual environment
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = os.path.join(temp_dir, "test_venv")
        
        try:
            # Create virtual environment
            print("  📦 Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", venv_path], 
                         check=True, capture_output=True)
            
            # Get pip path
            if sys.platform == "win32":
                pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
                python_path = os.path.join(venv_path, "Scripts", "python.exe")
            else:
                pip_path = os.path.join(venv_path, "bin", "pip")
                python_path = os.path.join(venv_path, "bin", "python")
            
            # Upgrade pip
            print("  ⬆️  Upgrading pip...")
            subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            # Install requirements
            print(f"  📥 Installing {requirements_file}...")
            result = subprocess.run([pip_path, "install", "-r", requirements_file], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"  ✅ {requirements_file} installed successfully!")
                return True
            else:
                print(f"  ❌ {requirements_file} failed to install:")
                print(f"     Error: {result.stderr[:500]}...")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  ⏰ {requirements_file} installation timed out")
            return False
        except Exception as e:
            print(f"  ❌ {requirements_file} test failed: {e}")
            return False

def test_core_imports():
    """Test that core packages can be imported"""
    print("\n🔍 Testing core package imports...")
    
    core_packages = [
        "numpy",
        "pandas", 
        "sklearn",
        "flask",
        "kafka",
        "sqlalchemy"
    ]
    
    success_count = 0
    for package in core_packages:
        try:
            __import__(package)
            print(f"  ✅ {package} imports successfully")
            success_count += 1
        except ImportError:
            print(f"  ❌ {package} failed to import")
    
    return success_count == len(core_packages)

def main():
    print("🚀 Requirements Testing Script")
    print("=" * 40)
    
    # Test different requirements files
    requirements_files = [
        "requirements_minimal.txt",
        "requirements_docker.txt", 
        "requirements_fixed.txt"
    ]
    
    results = {}
    
    for req_file in requirements_files:
        if os.path.exists(req_file):
            results[req_file] = test_requirements_file(req_file)
        else:
            print(f"⚠️  {req_file} not found, skipping...")
            results[req_file] = False
    
    # Summary
    print("\n📊 Test Results Summary:")
    print("=" * 40)
    
    for req_file, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {req_file}: {status}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if results.get("requirements_minimal.txt", False):
        print("  🎯 Use requirements_minimal.txt for Docker builds")
        print("  📝 Add specific packages as needed in Dockerfiles")
    elif results.get("requirements_docker.txt", False):
        print("  🎯 Use requirements_docker.txt for Docker builds")
    elif results.get("requirements_fixed.txt", False):
        print("  🎯 Use requirements_fixed.txt for local development")
    else:
        print("  ⚠️  All requirements files failed - check Python version compatibility")
        print("  💡 Try using Python 3.8-3.10 for better compatibility")
    
    print("\n🔧 Next Steps:")
    print("  1. Use the recommended requirements file")
    print("  2. Update Dockerfiles to use minimal requirements + specific packages")
    print("  3. Test with: docker-compose build [service_name]")

if __name__ == "__main__":
    main()
