#!/bin/bash
# Complete setup and test script for IoT Smoke Detection Pipeline

echo "🚀 IoT Smoke Detection - Complete Test Setup"
echo "=============================================="

# Step 1: Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install pytest pytest-html pytest-cov pytest-timeout pytest-xdist requests kafka-python

# Step 2: Start Docker services
echo "🐳 Starting Docker services..."
docker-compose down  # Clean start
docker-compose up -d

# Step 3: Wait for services to be ready
echo "⏳ Waiting for services to initialize..."

# Wait for Kafka (usually takes 30-60 seconds)
echo "  📨 Waiting for Kafka..."
sleep 60

# Check Kafka health
echo "  🔍 Checking Kafka health..."
python -c "
try:
    from kafka import KafkaProducer
    producer = KafkaProducer(bootstrap_servers='localhost:9092', request_timeout_ms=5000)
    producer.close()
    print('  ✅ Kafka is ready')
except Exception as e:
    print(f'  ❌ Kafka not ready: {e}')
    print('  ⏳ Waiting additional 30 seconds...')
    import time; time.sleep(30)
"

# Wait for Flask API (ML model needs to be trained first)
echo "  🌐 Waiting for Flask API and ML model..."
sleep 120

# Check Flask API health
echo "  🔍 Checking Flask API health..."
for i in {1..10}; do
    if curl -s http://localhost:5000/health > /dev/null; then
        echo "  ✅ Flask API is ready"
        break
    else
        echo "  ⏳ Flask API not ready, waiting... ($i/10)"
        sleep 15
    fi
done

# Check Spark UI
echo "  ⚡ Checking Spark UI..."
for i in {1..5}; do
    if curl -s http://localhost:4040 > /dev/null; then
        echo "  ✅ Spark UI is ready"
        break
    else
        echo "  ⏳ Spark UI not ready, waiting... ($i/5)"
        sleep 10
    fi
done

# Step 4: Show service status
echo ""
echo "📊 Service Status Check:"
echo "========================"

# Check Docker containers
echo "🐳 Docker Containers:"
docker-compose ps

echo ""
echo "🔍 Service Health:"

# Kafka
python -c "
try:
    from kafka import KafkaProducer
    producer = KafkaProducer(bootstrap_servers='localhost:9092', request_timeout_ms=5000)
    producer.close()
    print('  Kafka: ✅ Ready')
except:
    print('  Kafka: ❌ Not Ready')
"

# Flask API
if curl -s http://localhost:5000/health > /dev/null; then
    echo "  Flask API: ✅ Ready"
else
    echo "  Flask API: ❌ Not Ready"
fi

# Spark UI
if curl -s http://localhost:4040 > /dev/null; then
    echo "  Spark UI: ✅ Ready"
else
    echo "  Spark UI: ❌ Not Ready"
fi

echo ""
echo "🧪 Running Tests:"
echo "=================="

# Step 5: Run tests progressively
echo "1️⃣ Running unit tests (no external dependencies)..."
python tests/run_streaming_tests.py --unit

echo ""
echo "2️⃣ Running quick smoke tests..."
python tests/run_streaming_tests.py --quick

echo ""
echo "3️⃣ Running integration tests..."
python tests/run_streaming_tests.py --integration

echo ""
echo "4️⃣ Running full test suite with reports..."
python tests/run_streaming_tests.py --all --html-report --coverage

echo ""
echo "🎉 Test execution complete!"
echo "📊 Check reports in tests/reports/ directory"
echo "📈 HTML Report: tests/reports/streaming_test_report.html"
echo "📊 Coverage Report: tests/reports/coverage/index.html"
