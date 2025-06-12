# Complete setup and test script for IoT Smoke Detection Pipeline (PowerShell)

Write-Host "🚀 IoT Smoke Detection - Complete Test Setup" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

# Step 1: Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
pip install -r tests/requirements-essential.txt

# Step 2: Start Docker services
Write-Host "🐳 Starting Docker services..." -ForegroundColor Yellow
docker-compose down  # Clean start
docker-compose up -d

# Step 3: Wait for services to be ready
Write-Host "⏳ Waiting for services to initialize..." -ForegroundColor Yellow

# Wait for Kafka (usually takes 30-60 seconds)
Write-Host "  📨 Waiting for Kafka..." -ForegroundColor Cyan
Start-Sleep -Seconds 60

# Check Kafka health
Write-Host "  🔍 Checking Kafka health..." -ForegroundColor Cyan
try {
    python -c "
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers='localhost:9092', request_timeout_ms=5000)
producer.close()
print('  ✅ Kafka is ready')
"
} catch {
    Write-Host "  ❌ Kafka not ready, waiting additional 30 seconds..." -ForegroundColor Red
    Start-Sleep -Seconds 30
}

# Wait for Flask API (ML model needs to be trained first)
Write-Host "  🌐 Waiting for Flask API and ML model..." -ForegroundColor Cyan
Start-Sleep -Seconds 120

# Check Flask API health
Write-Host "  🔍 Checking Flask API health..." -ForegroundColor Cyan
for ($i = 1; $i -le 10; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ Flask API is ready" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "  ⏳ Flask API not ready, waiting... ($i/10)" -ForegroundColor Yellow
        Start-Sleep -Seconds 15
    }
}

# Check Spark UI
Write-Host "  ⚡ Checking Spark UI..." -ForegroundColor Cyan
for ($i = 1; $i -le 5; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:4040" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ Spark UI is ready" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "  ⏳ Spark UI not ready, waiting... ($i/5)" -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
}

# Step 4: Show service status
Write-Host ""
Write-Host "📊 Service Status Check:" -ForegroundColor Green
Write-Host "========================" -ForegroundColor Green

# Check Docker containers
Write-Host "🐳 Docker Containers:" -ForegroundColor Yellow
docker-compose ps

Write-Host ""
Write-Host "🔍 Service Health:" -ForegroundColor Yellow

# Kafka
try {
    python -c "
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers='localhost:9092', request_timeout_ms=5000)
producer.close()
print('  Kafka: ✅ Ready')
"
} catch {
    Write-Host "  Kafka: ❌ Not Ready" -ForegroundColor Red
}

# Flask API
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  Flask API: ✅ Ready" -ForegroundColor Green
} catch {
    Write-Host "  Flask API: ❌ Not Ready" -ForegroundColor Red
}

# Spark UI
try {
    $response = Invoke-WebRequest -Uri "http://localhost:4040" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  Spark UI: ✅ Ready" -ForegroundColor Green
} catch {
    Write-Host "  Spark UI: ❌ Not Ready" -ForegroundColor Red
}

Write-Host ""
Write-Host "🧪 Running Tests:" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green

# Step 5: Run tests progressively
Write-Host "1️⃣ Running unit tests (no external dependencies)..." -ForegroundColor Cyan
python tests/run_streaming_tests.py --unit

Write-Host ""
Write-Host "2️⃣ Running quick smoke tests..." -ForegroundColor Cyan
python tests/run_streaming_tests.py --quick

Write-Host ""
Write-Host "3️⃣ Running integration tests..." -ForegroundColor Cyan
python tests/run_streaming_tests.py --integration

Write-Host ""
Write-Host "4️⃣ Running full test suite with reports..." -ForegroundColor Cyan
python tests/run_streaming_tests.py --all --html-report --coverage

Write-Host ""
Write-Host "🎉 Test execution complete!" -ForegroundColor Green
Write-Host "📊 Check reports in tests/reports/ directory" -ForegroundColor Yellow
Write-Host "📈 HTML Report: tests/reports/streaming_test_report.html" -ForegroundColor Yellow
Write-Host "📊 Coverage Report: tests/reports/coverage/index.html" -ForegroundColor Yellow
