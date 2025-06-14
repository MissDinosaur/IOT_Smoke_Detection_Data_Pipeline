#!/usr/bin/env python3
"""
Fix Model Compatibility Script
Regenerates the ML model with the current scikit-learn version to fix pickle compatibility issues.
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

def load_data():
    """Load the smoke detection dataset"""
    print("📊 Loading smoke detection dataset...")
    
    # Try different possible data file locations
    data_paths = [
        "data/smoke_detection_iot.csv",
        "data/cleaned_smoke_data.csv",
        "./smoke_detection_iot.csv",
        "./cleaned_smoke_data.csv"
    ]
    
    for path in data_paths:
        if os.path.exists(path):
            print(f"✅ Found data file: {path}")
            try:
                df = pd.read_csv(path)
                print(f"📈 Dataset shape: {df.shape}")
                print(f"📋 Columns: {list(df.columns)}")
                return df, path
            except Exception as e:
                print(f"❌ Error loading {path}: {e}")
                continue
    
    # If no data file found, create synthetic data
    print("⚠️  No data file found, creating synthetic dataset...")
    return create_synthetic_data()

def create_synthetic_data():
    """Create synthetic smoke detection data for testing"""
    np.random.seed(42)
    n_samples = 1000
    
    # Generate synthetic features
    temperature = np.random.normal(25, 10, n_samples)  # Temperature in Celsius
    humidity = np.random.normal(50, 20, n_samples)     # Humidity percentage
    smoke = np.random.exponential(0.1, n_samples)      # Smoke concentration
    
    # Create target based on logical rules
    fire_risk = (
        (temperature > 35) & (humidity < 30) & (smoke > 0.2) |
        (temperature > 40) & (smoke > 0.15) |
        (smoke > 0.3)
    ).astype(int)
    
    df = pd.DataFrame({
        'Temperature[C]': temperature,
        'Humidity[%]': humidity,
        'TVOC[ppb]': np.random.normal(100, 50, n_samples),
        'eCO2[ppm]': np.random.normal(400, 100, n_samples),
        'Raw H2': np.random.normal(13000, 1000, n_samples),
        'Raw Ethanol': np.random.normal(18000, 2000, n_samples),
        'Pressure[hPa]': np.random.normal(1013, 10, n_samples),
        'PM1.0': smoke * 10 + np.random.normal(0, 2, n_samples),
        'PM2.5': smoke * 15 + np.random.normal(0, 3, n_samples),
        'NC0.5': smoke * 100 + np.random.normal(0, 20, n_samples),
        'NC1.0': smoke * 80 + np.random.normal(0, 15, n_samples),
        'NC2.5': smoke * 60 + np.random.normal(0, 10, n_samples),
        'CNT': np.random.randint(0, 100, n_samples),
        'Fire Alarm': fire_risk
    })
    
    print(f"🔧 Created synthetic dataset with shape: {df.shape}")
    return df, "synthetic_data"

def prepare_features(df):
    """Prepare features for training"""
    print("🔧 Preparing features...")
    
    # Common feature names to look for
    feature_columns = []
    target_column = None
    
    # Look for target column
    target_candidates = ['Fire Alarm', 'fire_alarm', 'target', 'label', 'class']
    for col in target_candidates:
        if col in df.columns:
            target_column = col
            break
    
    if target_column is None:
        print("❌ No target column found. Looking for binary column...")
        # Find binary columns that could be the target
        for col in df.columns:
            if df[col].nunique() == 2 and df[col].dtype in ['int64', 'bool']:
                target_column = col
                print(f"🎯 Using {col} as target column")
                break
    
    if target_column is None:
        raise ValueError("Could not identify target column")
    
    # Use all numeric columns except target as features
    for col in df.columns:
        if col != target_column and df[col].dtype in ['int64', 'float64']:
            feature_columns.append(col)
    
    print(f"🎯 Target column: {target_column}")
    print(f"📊 Feature columns: {feature_columns}")
    
    X = df[feature_columns]
    y = df[target_column]
    
    # Handle missing values
    X = X.fillna(X.mean())
    
    return X, y, feature_columns

def train_model(X, y):
    """Train a new Random Forest model"""
    print("🤖 Training new Random Forest model...")
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train Random Forest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"✅ Model trained successfully!")
    print(f"📊 Accuracy: {accuracy:.4f}")
    print(f"📈 Feature importance (top 5):")
    
    feature_importance = list(zip(X.columns, model.feature_importances_))
    feature_importance.sort(key=lambda x: x[1], reverse=True)
    
    for feature, importance in feature_importance[:5]:
        print(f"   {feature}: {importance:.4f}")
    
    return model

def save_model(model, feature_columns):
    """Save the model in multiple formats"""
    print("💾 Saving model...")
    
    # Create models directory if it doesn't exist
    os.makedirs("models", exist_ok=True)
    
    # Save with joblib (recommended for scikit-learn)
    joblib_path = "models/smoke_detection_model.pkl"
    joblib.dump(model, joblib_path)
    print(f"✅ Model saved with joblib: {joblib_path}")
    
    # Save with pickle as backup
    pickle_path = "models/smoke_detection_model_pickle.pkl"
    with open(pickle_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"✅ Model saved with pickle: {pickle_path}")
    
    # Save feature names
    feature_path = "models/feature_columns.txt"
    with open(feature_path, 'w') as f:
        f.write('\n'.join(feature_columns))
    print(f"✅ Feature columns saved: {feature_path}")
    
    # Save model info
    info_path = "models/model_info.txt"
    with open(info_path, 'w') as f:
        f.write(f"Model Type: RandomForestClassifier\n")
        f.write(f"Scikit-learn Version: {__import__('sklearn').__version__}\n")
        f.write(f"Python Version: {sys.version}\n")
        f.write(f"Number of Features: {len(feature_columns)}\n")
        f.write(f"Features: {', '.join(feature_columns)}\n")
    print(f"✅ Model info saved: {info_path}")

def test_model_loading():
    """Test that the saved model can be loaded"""
    print("🧪 Testing model loading...")
    
    try:
        # Test joblib loading
        model = joblib.load("models/smoke_detection_model.pkl")
        print("✅ Model loads successfully with joblib")
        
        # Test prediction
        if hasattr(model, 'predict'):
            # Create dummy data for testing
            n_features = model.n_features_in_
            dummy_data = np.random.random((1, n_features))
            prediction = model.predict(dummy_data)
            print(f"✅ Model prediction test successful: {prediction}")
        
        return True
    except Exception as e:
        print(f"❌ Model loading test failed: {e}")
        return False

def main():
    """Main function"""
    print("🔧 Model Compatibility Fix Script")
    print("=" * 50)
    
    try:
        # Load data
        df, data_source = load_data()
        
        # Prepare features
        X, y, feature_columns = prepare_features(df)
        
        # Train model
        model = train_model(X, y)
        
        # Save model
        save_model(model, feature_columns)
        
        # Test loading
        if test_model_loading():
            print("\n🎉 Model compatibility fix completed successfully!")
            print("\n📋 Next steps:")
            print("1. Restart the Flask API container:")
            print("   docker-compose restart flask_api")
            print("2. Check the logs:")
            print("   docker-compose logs flask_api")
            print("3. Test the API:")
            print("   curl http://localhost:5000/health")
        else:
            print("\n❌ Model loading test failed. Please check the logs.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your data files and try again.")

if __name__ == "__main__":
    main()
