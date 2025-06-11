# 🔥 Flask API Backend - Frontend Developer Guide

## 📋 **Overview**

This guide provides complete documentation for frontend developers to integrate with our IoT Smoke Detection Flask API backend. The API provides real-time fire detection predictions using machine learning models.

## 🏗️ **API Architecture**

### **Backend Service**
- **Service**: Flask API Backend
- **URL**: `http://localhost:5000`
- **Technology**: Python Flask + scikit-learn
- **Model**: Pickle-based ML model loading
- **CORS**: Enabled for all origins

### **Key Features**
- ✅ **Real-time Predictions** - Single sensor reading analysis
- ✅ **Batch Processing** - Multiple readings at once
- ✅ **Data Validation** - Input validation and error handling
- ✅ **Health Monitoring** - System status and model info
- ✅ **Prometheus Metrics** - Performance monitoring
- ✅ **Sample Testing** - Built-in test scenarios

## 🔌 **API Endpoints**

### **🔥 Prediction Endpoints**

#### **1. Single Prediction**
```http
POST /predict
Content-Type: application/json

{
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
  "NC2.5": 20.0
}
```

**Response:**
```json
{
  "prediction": 0,
  "prediction_label": "no_fire",
  "confidence": {
    "no_fire": 0.85,
    "fire": 0.15
  },
  "processing_time_seconds": 0.023,
  "timestamp": "2024-01-15T10:30:00.123Z",
  "model_info": {
    "algorithm": "RandomForestClassifier",
    "version": "1.0"
  }
}
```

#### **2. Batch Predictions**
```http
POST /predict/batch
Content-Type: application/json

[
  {
    "Temperature[C]": 25.5,
    "Humidity[%]": 45.0,
    // ... other sensor fields
  },
  {
    "Temperature[C]": 85.0,
    "Humidity[%]": 20.0,
    // ... other sensor fields
  }
]
```

**Response:**
```json
{
  "predictions": [
    {
      "index": 0,
      "prediction": 0,
      "prediction_label": "no_fire",
      "confidence": {"no_fire": 0.85, "fire": 0.15}
    },
    {
      "index": 1,
      "prediction": 1,
      "prediction_label": "fire",
      "confidence": {"no_fire": 0.25, "fire": 0.75}
    }
  ],
  "summary": {
    "total_samples": 2,
    "successful_predictions": 2,
    "fire_detections": 1,
    "no_fire_detections": 1,
    "errors": 0
  },
  "processing_time_seconds": 0.045,
  "timestamp": "2024-01-15T10:30:00.123Z"
}
```

#### **3. Sample Data Test**
```http
GET /predict/sample
```

**Response:** Returns prediction using built-in normal sensor data

#### **4. Fire Scenario Test**
```http
GET /predict/fire-scenario
```

**Response:** Returns prediction using fire condition data (high temp, particles, etc.)

### **🔍 System Information Endpoints**

#### **5. Health Check**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.123Z",
  "model_loaded": true,
  "model_path": "ml/models/best_model.pkl",
  "uptime_seconds": 3600
}
```

#### **6. Model Information**
```http
GET /model/info
```

**Response:**
```json
{
  "model_type": "RandomForestClassifier",
  "algorithm": "RandomForestClassifier",
  "feature_count": 12,
  "training_timestamp": "2024-01-15T09:00:00.000Z",
  "version": "1.0",
  "loaded_at": "2024-01-15T10:00:00.123Z"
}
```

#### **7. Data Validation**
```http
POST /validate
Content-Type: application/json

{
  "Temperature[C]": 25.5,
  "Humidity[%]": 45.0
  // ... sensor data to validate
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

#### **8. Prometheus Metrics**
```http
GET /metrics
```

**Response:** Prometheus-formatted metrics for monitoring

### **🔧 Configuration & Management Endpoints**

#### **9. Sensor Schema**
```http
GET /sensors/schema
```

**Response:**
```json
{
  "required_fields": [
    "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
    "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
    "NC0.5", "NC1.0", "NC2.5"
  ],
  "field_types": {
    "Temperature[C]": {"type": "float", "unit": "Celsius", "range": [-40, 125]},
    "Humidity[%]": {"type": "float", "unit": "Percentage", "range": [0, 100]},
    // ... other field definitions
  },
  "validation_rules": {
    "all_fields_required": true,
    "numeric_values_only": true,
    "range_validation": true,
    "null_values_allowed": false
  }
}
```

#### **10. Model Reload**
```http
POST /model/reload
```

**Response:**
```json
{
  "status": "success",
  "message": "Model reloaded successfully",
  "model_info": {
    "model_type": "RandomForestClassifier",
    "algorithm": "RandomForestClassifier",
    "version": "1.0"
  },
  "timestamp": "2024-01-15T10:30:00.123Z"
}
```

#### **11. Prediction Statistics**
```http
GET /predictions/stats
```

**Response:**
```json
{
  "total_predictions": 1250,
  "fire_predictions": 125,
  "no_fire_predictions": 1125,
  "batch_predictions": 50,
  "average_confidence": 0.23,
  "average_processing_time": 0.045,
  "fire_detection_rate_percent": 10.0,
  "safe_detection_rate_percent": 90.0,
  "uptime_seconds": 7200,
  "last_reset": 1705312800.0,
  "timestamp": "2024-01-15T10:30:00.123Z"
}
```

#### **12. API Configuration**
```http
GET /config
```

**Response:**
```json
{
  "version": "1.0.0",
  "model_reload_interval": 3600,
  "max_batch_size": 1000,
  "supported_formats": ["json"],
  "cors_enabled": true,
  "metrics_enabled": true,
  "model_path": "ml/models/best_model.pkl",
  "model_loaded": true,
  "endpoints": [
    {"path": "/predict", "method": "POST", "description": "Single prediction"},
    {"path": "/predict/batch", "method": "POST", "description": "Batch predictions"},
    // ... all endpoint definitions
  ],
  "timestamp": "2024-01-15T10:30:00.123Z"
}
```

## 📊 **Sensor Data Schema**

### **Required Fields (All 12 fields must be provided)**

| Field | Type | Unit | Description | Example |
|-------|------|------|-------------|---------|
| `Temperature[C]` | float | Celsius | Ambient temperature | 25.5 |
| `Humidity[%]` | float | Percentage | Relative humidity | 45.0 |
| `TVOC[ppb]` | float | ppb | Total Volatile Organic Compounds | 150.0 |
| `eCO2[ppm]` | float | ppm | Equivalent CO2 | 400.0 |
| `Raw H2` | float | Raw value | Hydrogen sensor reading | 13000.0 |
| `Raw Ethanol` | float | Raw value | Ethanol sensor reading | 18500.0 |
| `Pressure[hPa]` | float | hPa | Atmospheric pressure | 1013.25 |
| `PM1.0` | float | μg/m³ | Particulate Matter 1.0 | 10.0 |
| `PM2.5` | float | μg/m³ | Particulate Matter 2.5 | 15.0 |
| `NC0.5` | float | #/cm³ | Number Concentration 0.5μm | 100.0 |
| `NC1.0` | float | #/cm³ | Number Concentration 1.0μm | 80.0 |
| `NC2.5` | float | #/cm³ | Number Concentration 2.5μm | 20.0 |

### **Validation Rules**
- ✅ All 12 fields are **required**
- ✅ All values must be **numeric** (int or float)
- ✅ Missing fields will return validation error
- ✅ Invalid data types will return error

## 💻 **JavaScript Integration**

### **API Client Class**
```javascript
class SmokeDetectionAPI {
  constructor(baseURL = 'http://localhost:5000') {
    this.baseURL = baseURL;
  }

  async predict(sensorData) {
    const response = await fetch(`${this.baseURL}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sensorData)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }

  async batchPredict(sensorDataArray) {
    const response = await fetch(`${this.baseURL}/predict/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sensorDataArray)
    });
    return await response.json();
  }

  async getHealth() {
    const response = await fetch(`${this.baseURL}/health`);
    return await response.json();
  }

  async getModelInfo() {
    const response = await fetch(`${this.baseURL}/model/info`);
    return await response.json();
  }

  async validateData(sensorData) {
    const response = await fetch(`${this.baseURL}/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sensorData)
    });
    return await response.json();
  }

  async testSample() {
    const response = await fetch(`${this.baseURL}/predict/sample`);
    return await response.json();
  }

  async testFireScenario() {
    const response = await fetch(`${this.baseURL}/predict/fire-scenario`);
    return await response.json();
  }

  async getSensorSchema() {
    const response = await fetch(`${this.baseURL}/sensors/schema`);
    return await response.json();
  }

  async reloadModel() {
    const response = await fetch(`${this.baseURL}/model/reload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return await response.json();
  }

  async getPredictionStats() {
    const response = await fetch(`${this.baseURL}/predictions/stats`);
    return await response.json();
  }

  async getConfig() {
    const response = await fetch(`${this.baseURL}/config`);
    return await response.json();
  }
}
```

### **Usage Example**
```javascript
const api = new SmokeDetectionAPI();

// Example sensor data
const sensorData = {
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
};

// Make prediction
try {
  const result = await api.predict(sensorData);
  console.log('Prediction:', result.prediction_label);
  console.log('Confidence:', result.confidence);
  console.log('Processing time:', result.processing_time_seconds);
} catch (error) {
  console.error('Prediction failed:', error);
}

// Check system health
const health = await api.getHealth();
console.log('System status:', health.status);
console.log('Model loaded:', health.model_loaded);
```

## ⚛️ **React Integration**

### **React Hook Example**
```jsx
import React, { useState, useEffect } from 'react';

const useSmokeDetection = () => {
  const [api] = useState(() => new SmokeDetectionAPI());
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);

  const predict = async (sensorData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.predict(sensorData);
      setPrediction(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const checkHealth = async () => {
    try {
      const health = await api.getHealth();
      setSystemHealth(health);
    } catch (err) {
      console.error('Health check failed:', err);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  return {
    prediction,
    loading,
    error,
    systemHealth,
    predict,
    checkHealth,
    api
  };
};
```

### **React Component Example**
```jsx
const SmokeDetectionDashboard = () => {
  const { prediction, loading, error, systemHealth, predict } = useSmokeDetection();

  const [sensorData, setSensorData] = useState({
    'Temperature[C]': 25.0,
    'Humidity[%]': 50.0,
    'TVOC[ppb]': 100.0,
    'eCO2[ppm]': 400.0,
    'Raw H2': 13000.0,
    'Raw Ethanol': 18500.0,
    'Pressure[hPa]': 1013.25,
    'PM1.0': 10.0,
    'PM2.5': 15.0,
    'NC0.5': 100.0,
    'NC1.0': 80.0,
    'NC2.5': 20.0
  });

  const handleInputChange = (field, value) => {
    setSensorData(prev => ({
      ...prev,
      [field]: parseFloat(value) || 0
    }));
  };

  const handlePredict = () => {
    predict(sensorData);
  };

  return (
    <div className="smoke-detection-dashboard">
      <h1>🔥 Smoke Detection Dashboard</h1>

      {/* System Status */}
      <div className="system-status">
        {systemHealth && (
          <div className={`status ${systemHealth.status}`}>
            <span>Status: {systemHealth.status}</span>
            <span>Model: {systemHealth.model_loaded ? '✅' : '❌'}</span>
          </div>
        )}
      </div>

      {/* Sensor Inputs */}
      <div className="sensor-inputs">
        {Object.entries(sensorData).map(([field, value]) => (
          <div key={field} className="input-group">
            <label>{field}</label>
            <input
              type="number"
              step="0.1"
              value={value}
              onChange={(e) => handleInputChange(field, e.target.value)}
            />
          </div>
        ))}
      </div>

      {/* Predict Button */}
      <button
        onClick={handlePredict}
        disabled={loading}
        className="predict-button"
      >
        {loading ? 'Analyzing...' : 'Analyze Fire Risk'}
      </button>

      {/* Results */}
      {error && (
        <div className="error">Error: {error}</div>
      )}

      {prediction && (
        <div className={`prediction ${prediction.prediction_label}`}>
          <h2>{prediction.prediction_label === 'fire' ? '🔥 FIRE DETECTED' : '✅ NO FIRE'}</h2>
          <div className="confidence">
            <div>Fire Risk: {(prediction.confidence.fire * 100).toFixed(1)}%</div>
            <div>Safe: {(prediction.confidence.no_fire * 100).toFixed(1)}%</div>
          </div>
          <div className="processing-time">
            Processing: {(prediction.processing_time_seconds * 1000).toFixed(1)}ms
          </div>
        </div>
      )}
    </div>
  );
};
```

## 🎨 **CSS Styling**

```css
.smoke-detection-dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.system-status {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.status {
  display: flex;
  gap: 20px;
  align-items: center;
}

.status.healthy { color: #28a745; }
.status.degraded { color: #ffc107; }

.sensor-inputs {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin: 20px 0;
}

.input-group {
  display: flex;
  flex-direction: column;
}

.input-group label {
  font-weight: 600;
  margin-bottom: 5px;
  color: #495057;
}

.input-group input {
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
}

.predict-button {
  background: #007bff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  margin: 20px 0;
}

.predict-button:hover {
  background: #0056b3;
}

.predict-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.prediction {
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
}

.prediction.fire {
  border-left: 4px solid #dc3545;
  background: #f8d7da;
}

.prediction.no_fire {
  border-left: 4px solid #28a745;
  background: #d4edda;
}

.prediction h2 {
  margin: 0 0 15px 0;
  font-size: 24px;
}

.prediction.fire h2 { color: #dc3545; }
.prediction.no_fire h2 { color: #28a745; }

.confidence {
  display: flex;
  gap: 20px;
  margin: 15px 0;
  font-size: 18px;
  font-weight: 600;
}

.processing-time {
  margin-top: 10px;
  color: #6c757d;
  font-size: 14px;
}

.error {
  color: #dc3545;
  background: #f8d7da;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #f5c6cb;
  margin: 10px 0;
}
```

## 🔧 **Error Handling**

### **API Error Types**
```javascript
// Handle different error scenarios
const handleAPIError = (error, response) => {
  if (!response.ok) {
    switch (response.status) {
      case 400:
        return 'Invalid sensor data provided';
      case 500:
        return 'Server error - model may not be loaded';
      case 404:
        return 'API endpoint not found';
      default:
        return `API error: ${response.status}`;
    }
  }
  return error.message;
};

// Enhanced API client with error handling
class RobustSmokeDetectionAPI extends SmokeDetectionAPI {
  async predict(sensorData) {
    try {
      const response = await fetch(`${this.baseURL}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sensorData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Prediction API error:', error);
      throw error;
    }
  }
}
```

## 🧪 **Testing the API**

### **Quick Test Commands**
```bash
# Test health endpoint
curl http://localhost:5000/health

# Test sample prediction
curl http://localhost:5000/predict/sample

# Test fire scenario
curl http://localhost:5000/predict/fire-scenario

# Test custom prediction
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
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
    "NC2.5": 20.0
  }'
```

## 📱 **Mobile Responsive Design**

```css
/* Mobile-first responsive design */
@media (max-width: 768px) {
  .smoke-detection-dashboard {
    padding: 10px;
  }

  .sensor-inputs {
    grid-template-columns: 1fr;
  }

  .confidence {
    flex-direction: column;
    gap: 10px;
  }
}

@media (max-width: 480px) {
  .prediction h2 {
    font-size: 20px;
  }

  .confidence {
    font-size: 16px;
  }
}
```

## 🚀 **Deployment & Environment**

### **Environment Configuration**
```javascript
// config.js
const config = {
  development: {
    API_BASE_URL: 'http://localhost:5000',
    POLLING_INTERVAL: 5000
  },
  production: {
    API_BASE_URL: 'https://your-domain.com/api',
    POLLING_INTERVAL: 10000
  }
};

export default config[process.env.NODE_ENV || 'development'];
```

### **Docker Integration**
The Flask API runs in a Docker container and is accessible at:
- **Development**: `http://localhost:5000`
- **Container Network**: `http://flask_api:5000` (for other containers)

## 📞 **Support & Resources**

- **API Health Check**: `GET http://localhost:5000/health`
- **Model Information**: `GET http://localhost:5000/model/info`
- **Metrics Endpoint**: `GET http://localhost:5000/metrics`
- **Sample Testing**: `GET http://localhost:5000/predict/sample`

## 🎯 **Quick Start Checklist**

1. ✅ **Start the system**: `docker-compose up --build`
2. ✅ **Check API health**: `curl http://localhost:5000/health`
3. ✅ **Test sample prediction**: `curl http://localhost:5000/predict/sample`
4. ✅ **Integrate API client** in your frontend
5. ✅ **Handle errors** gracefully
6. ✅ **Add real-time updates** with polling

**The Flask API backend is production-ready and provides comprehensive fire detection capabilities for frontend applications!** 🔥
```
