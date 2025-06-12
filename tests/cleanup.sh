#!/bin/bash
# Script to clean up and organize the tests folder

echo "🧹 Cleaning up tests folder..."

# Create necessary directories if they don't exist
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/ml
mkdir -p tests/stream_processing
mkdir -p tests/api

# Move test files to appropriate directories
# Unit tests
find tests -name "test_*" -type f | grep -v "integration" | grep -v "stream_ingestion" | grep -v "ml" | xargs -I{} mv {} tests/unit/ 2>/dev/null

# Integration tests
find tests -name "*integration*" -type f | grep -v "stream_ingestion" | xargs -I{} mv {} tests/integration/ 2>/dev/null

# ML tests (already in the right place, just make sure we don't touch them)
# Stream processing tests (don't touch stream_ingestion folder)

# API tests
find tests -name "*api*" -type f | grep -v "stream_ingestion" | xargs -I{} mv {} tests/api/ 2>/dev/null

# Update conftest.py to work with new structure
cp tests/conftest.py tests/conftest.py.bak

# Delete unwanted files (but preserve important folders and files)
find tests -type f -not -path "*/stream_ingestion/*" -not -path "*/reports/*" \
  -not -name "conftest.py" -not -name "conftest.py.bak" \
  -not -path "*/unit/*" -not -path "*/integration/*" -not -path "*/ml/*" \
  -not -path "*/stream_processing/*" -not -path "*/api/*" \
  -not -name "cleanup.sh" -not -name "README.md" -not -name "__init__.py" \
  -not -name "requirements-test.txt" -not -name "requirements-essential.txt" \
  -delete

echo "✅ Tests folder cleanup complete!"
echo "📁 New structure:"
echo "  - tests/unit/: Unit tests"
echo "  - tests/integration/: Integration tests"
echo "  - tests/ml/: ML-related tests"
echo "  - tests/stream_processing/: Stream processing tests"
echo "  - tests/api/: API tests"
echo "  - tests/reports/: Test reports (preserved)"
echo "  - tests/stream_ingestion/: Stream ingestion tests (preserved)"
