#!/usr/bin/env python3
"""
Simple model regeneration script to fix scikit-learn version compatibility
"""

import os
import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

def main():
    print('🔧 Regenerating model with current scikit-learn version...')
    print(f'🔬 Current scikit-learn version: {__import__("sklearn").__version__}')
    print(f'🐍 Python version: {sys.version}')

    # Create synthetic smoke detection data
    np.random.seed(42)
    n_samples = 1000

    # Generate realistic sensor data
    temperature = np.random.normal(25, 10, n_samples)  # Temperature in Celsius
    humidity = np.random.normal(50, 20, n_samples)     # Humidity percentage  
    smoke = np.random.exponential(0.1, n_samples)      # Smoke concentration
    tvoc = np.random.normal(100, 50, n_samples)        # TVOC in ppb
    eco2 = np.random.normal(400, 100, n_samples)       # eCO2 in ppm
    pressure = np.random.normal(1013, 10, n_samples)   # Pressure in hPa

    # Create fire alarm target based on realistic conditions
    fire_risk = (
        (temperature > 35) & (humidity < 30) & (smoke > 0.2) |  # Hot, dry, smoky
        (temperature > 40) & (smoke > 0.15) |                   # Very hot and smoky
        (smoke > 0.3) |                                          # Very smoky
        (tvoc > 200) & (smoke > 0.1)                           # High TVOC and some smoke
    ).astype(int)

    # Create DataFrame
    df = pd.DataFrame({
        'Temperature': temperature,
        'Humidity': humidity, 
        'Smoke': smoke,
        'TVOC': tvoc,
        'eCO2': eco2,
        'Pressure': pressure,
        'Fire_Alarm': fire_risk
    })

    print(f'📊 Generated dataset with {len(df)} samples')
    print(f'🎯 Fire alarm rate: {fire_risk.mean():.2%}')

    # Prepare features and target
    feature_columns = ['Temperature', 'Humidity', 'Smoke', 'TVOC', 'eCO2', 'Pressure']
    X = df[feature_columns]
    y = df['Fire_Alarm']

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f'📈 Training set: {len(X_train)} samples')
    print(f'🧪 Test set: {len(X_test)} samples')

    # Train Random Forest model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )

    print('🤖 Training Random Forest model...')
    model.fit(X_train, y_train)

    # Evaluate model
    train_accuracy = model.score(X_train, y_train)
    test_accuracy = model.score(X_test, y_test)

    print(f'📊 Training accuracy: {train_accuracy:.4f}')
    print(f'📊 Test accuracy: {test_accuracy:.4f}')

    # Show feature importance
    feature_importance = list(zip(feature_columns, model.feature_importances_))
    feature_importance.sort(key=lambda x: x[1], reverse=True)
    
    print('📈 Feature importance:')
    for feature, importance in feature_importance:
        print(f'   {feature}: {importance:.4f}')

    # Create models directory
    models_dir = '/app/models'
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
        print(f'📁 Created directory: {models_dir}')

    # Save model in the format expected by the Flask API
    model_path = os.path.join(models_dir, 'smoke_detection_model.pkl')

    # Create model package dictionary
    model_package = {
        'model': model,
        'feature_columns': feature_columns,
        'target_column': 'Fire_Alarm',
        'scaler': None,  # No scaler used in this simple model
        'training_timestamp': pd.Timestamp.now().isoformat(),
        'model_name': 'smoke_detection_rf',
        'algorithm': 'RandomForestClassifier',
        'version': '1.0.0',
        'sklearn_version': __import__('sklearn').__version__
    }

    # Save with joblib
    joblib.dump(model_package, model_path)
    print(f'💾 Model package saved to: {model_path}')

    # Save feature names for reference
    feature_path = os.path.join(models_dir, 'feature_columns.txt')
    with open(feature_path, 'w') as f:
        f.write('\n'.join(feature_columns))
    print(f'📝 Feature columns saved to: {feature_path}')

    # Test model loading
    print('🧪 Testing model loading...')
    try:
        # Load the model package
        loaded_package = joblib.load(model_path)
        loaded_model = loaded_package['model']
        loaded_features = loaded_package['feature_columns']

        print(f'✅ Model package loads successfully!')
        print(f'📦 Package keys: {list(loaded_package.keys())}')
        print(f'🏷️  Feature columns: {loaded_features}')

        # Test prediction with dummy data
        dummy_data = np.array([[25.0, 50.0, 0.1, 100.0, 400.0, 1013.0]])
        prediction = loaded_model.predict(dummy_data)
        probability = loaded_model.predict_proba(dummy_data)

        print(f'🔮 Test prediction: {prediction[0]}')
        print(f'📊 Test probability: {probability[0]}')

        return True

    except Exception as e:
        print(f'❌ Error testing model: {e}')
        return False

if __name__ == '__main__':
    try:
        success = main()
        if success:
            print('\n🎉 Model regeneration completed successfully!')
            print('✅ The model is now compatible with the current scikit-learn version')
        else:
            print('\n❌ Model regeneration failed')
            sys.exit(1)
    except Exception as e:
        print(f'\n❌ Error during model regeneration: {e}')
        sys.exit(1)
