"""
Food Price Prediction Model based on Weather Conditions
Prediksi Harga Pangan berdasarkan Kondisi Cuaca

Model ini memprediksi apakah harga pangan akan NAIK atau TURUN
berdasarkan kondisi cuaca (suhu, hujan, kelembapan, dll)
"""

import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FoodPricePredictionModel:
    """
    Model ML untuk prediksi perubahan harga pangan berdasarkan cuaca
    
    Target Prediksi:
    - NAIK: Harga akan naik (perubahan > 2%)
    - TURUN: Harga akan turun (perubahan < -2%)
    - STABIL: Harga relatif stabil (-2% <= perubahan <= 2%)
    """
    
    def __init__(self, model_path='models/saved/food_price_predictor.pkl'):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = [
            'suhu_mean',
            'curah_hujan_mm',
            'kelembapan',
            'kecepatan_angin',
            'tekanan_udara',
            'awan_persen',
            'suhu_max',
            'suhu_min',
            'curah_hujan_lag_1d',  # Hujan 1 hari lalu
            'curah_hujan_lag_3d',  # Hujan 3 hari lalu
            'curah_hujan_lag_7d'   # Hujan 7 hari lalu (weekly)
        ]
        self.target_classes = ['TURUN', 'STABIL', 'NAIK']
        
    def prepare_features(self, weather_data, historical_rain=None):
        """
        Prepare features dari data cuaca
        
        Args:
            weather_data: Dict dengan keys:
                - suhu_mean, suhu_max, suhu_min
                - curah_hujan_mm
                - kelembapan, kecepatan_angin, tekanan_udara, awan_persen
            historical_rain: Dict dengan rainfall history untuk lag features
                - 'lag_1d': curah hujan 1 hari lalu
                - 'lag_3d': curah hujan 3 hari lalu
                - 'lag_7d': curah hujan 7 hari lalu
        
        Returns:
            np.array: Feature vector
        """
        # Default lag values jika tidak ada historical data
        if historical_rain is None:
            historical_rain = {'lag_1d': 0, 'lag_3d': 0, 'lag_7d': 0}
        
        features = [
            weather_data.get('suhu_mean', 25),
            weather_data.get('curah_hujan_mm', 0),
            weather_data.get('kelembapan', 80),
            weather_data.get('kecepatan_angin', 10),
            weather_data.get('tekanan_udara', 1010),
            weather_data.get('awan_persen', 50),
            weather_data.get('suhu_max', 30),
            weather_data.get('suhu_min', 20),
            historical_rain.get('lag_1d', 0),
            historical_rain.get('lag_3d', 0),
            historical_rain.get('lag_7d', 0)
        ]
        
        return np.array(features).reshape(1, -1)
    
    def train_from_csv(self, weather_csv_path, price_csv_path):
        """
        Train model dari data CSV cuaca dan harga
        
        Args:
            weather_csv_path: Path ke file cuaca CSV
            price_csv_path: Path ke file harga pangan CSV
        """
        logger.info(f"Loading data from {weather_csv_path} and {price_csv_path}")
        
        # Load data
        weather_df = pd.read_csv(weather_csv_path)
        price_df = pd.read_csv(price_csv_path)
        
        # Prepare data
        training_data = self._prepare_training_data(weather_df, price_df)
        
        if len(training_data) == 0:
            raise ValueError("No training data available after merging weather and price data")
        
        logger.info(f"Prepared {len(training_data)} training samples")
        
        # Train model
        self.train(training_data)
        
        return self
    
    def _prepare_training_data(self, weather_df, price_df):
        """
        Merge dan prepare training data dari weather dan price dataframe
        """
        # Convert tanggal to datetime
        weather_df['tanggal'] = pd.to_datetime(weather_df['tanggal'])
        price_df['tanggal'] = pd.to_datetime(price_df['tanggal'])
        
        # Create lag features untuk curah hujan
        weather_df = weather_df.sort_values('tanggal')
        weather_df['curah_hujan_lag_1d'] = weather_df.groupby('kab_kota')['curah_hujan_mm'].shift(1).fillna(0)
        weather_df['curah_hujan_lag_3d'] = weather_df.groupby('kab_kota')['curah_hujan_mm'].shift(3).fillna(0)
        weather_df['curah_hujan_lag_7d'] = weather_df.groupby('kab_kota')['curah_hujan_mm'].shift(7).fillna(0)
        
        # Aggregate price by date and location (average all commodities)
        price_agg = price_df.groupby(['tanggal', 'kab_kota']).agg({
            'persen_perubahan': 'mean'
        }).reset_index()
        
        # Merge weather and price data
        merged = pd.merge(
            weather_df,
            price_agg,
            on=['tanggal', 'kab_kota'],
            how='inner'
        )
        
        # Create target variable: NAIK, TURUN, STABIL
        def categorize_price_change(persen):
            if persen > 2:
                return 2  # NAIK
            elif persen < -2:
                return 0  # TURUN
            else:
                return 1  # STABIL
        
        merged['target'] = merged['persen_perubahan'].apply(categorize_price_change)
        
        # Prepare training data
        training_data = []
        for _, row in merged.iterrows():
            training_data.append({
                'features': {
                    'suhu_mean': row['suhu_mean'],
                    'curah_hujan_mm': row['curah_hujan_mm'],
                    'kelembapan': row['kelembapan'],
                    'kecepatan_angin': row['kecepatan_angin'],
                    'tekanan_udara': row['tekanan_udara'],
                    'awan_persen': row['awan_persen'],
                    'suhu_max': row['suhu_max'],
                    'suhu_min': row['suhu_min'],
                    'curah_hujan_lag_1d': row['curah_hujan_lag_1d'],
                    'curah_hujan_lag_3d': row['curah_hujan_lag_3d'],
                    'curah_hujan_lag_7d': row['curah_hujan_lag_7d']
                },
                'target': row['target']
            })
        
        return training_data
    
    def train(self, training_data):
        """
        Train model dengan data historis
        
        Args:
            training_data: List of dict dengan keys:
                - 'features': dict dengan weather features
                - 'target': 0 (TURUN), 1 (STABIL), 2 (NAIK)
        """
        logger.info("Starting model training...")
        
        # Prepare X and y
        X = []
        y = []
        
        for sample in training_data:
            features = sample['features']
            feature_vector = [
                features['suhu_mean'],
                features['curah_hujan_mm'],
                features['kelembapan'],
                features['kecepatan_angin'],
                features['tekanan_udara'],
                features['awan_persen'],
                features['suhu_max'],
                features['suhu_min'],
                features['curah_hujan_lag_1d'],
                features['curah_hujan_lag_3d'],
                features['curah_hujan_lag_7d']
            ]
            X.append(feature_vector)
            y.append(sample['target'])
        
        X = np.array(X)
        y = np.array(y)
        
        logger.info(f"Training data shape: X={X.shape}, y={y.shape}")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train Gradient Boosting Classifier (better for this use case)
        self.model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        logger.info(f"Training accuracy: {train_score:.3f}")
        logger.info(f"Test accuracy: {test_score:.3f}")
        
        # Classification report
        y_pred = self.model.predict(X_test)
        logger.info("\nClassification Report:")
        logger.info(f"\n{classification_report(y_test, y_pred, target_names=self.target_classes)}")
        
        # Feature importance
        importances = self.model.feature_importances_
        feature_importance = sorted(zip(self.feature_names, importances), key=lambda x: x[1], reverse=True)
        logger.info("\nTop 5 Most Important Features:")
        for feat, imp in feature_importance[:5]:
            logger.info(f"  {feat}: {imp:.4f}")
        
        # Save model
        self.save_model()
        
        return self
    
    def predict(self, weather_data, historical_rain=None):
        """
        Prediksi perubahan harga pangan berdasarkan data cuaca
        
        Args:
            weather_data: Dict dengan weather features
            historical_rain: Dict dengan rainfall history
        
        Returns:
            dict: {
                'prediction': 'NAIK' | 'TURUN' | 'STABIL',
                'prediction_code': 0 | 1 | 2,
                'confidence': float (0-1),
                'probabilities': {
                    'TURUN': float,
                    'STABIL': float,
                    'NAIK': float
                },
                'recommendation': str,
                'timestamp': str
            }
        """
        if not self.is_trained:
            logger.warning("Model not trained, loading from file...")
            self.load_model()
        
        # Prepare features
        features = self.prepare_features(weather_data, historical_rain)
        
        # Scale
        features_scaled = self.scaler.transform(features)
        
        # Predict
        prediction_code = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]
        
        prediction = self.target_classes[prediction_code]
        confidence = float(probabilities[prediction_code])
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            prediction, 
            confidence, 
            weather_data
        )
        
        result = {
            'prediction': prediction,
            'prediction_code': int(prediction_code),
            'confidence': confidence,
            'probabilities': {
                'TURUN': float(probabilities[0]),
                'STABIL': float(probabilities[1]),
                'NAIK': float(probabilities[2])
            },
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat(),
            'weather_summary': self._weather_summary(weather_data)
        }
        
        logger.info(f"Prediction: {result}")
        return result
    
    def _generate_recommendation(self, prediction, confidence, weather_data):
        """Generate actionable recommendation"""
        recommendations = {
            'NAIK': [
                f"⚠️ PREDIKSI HARGA NAIK (Confidence: {confidence:.1%})",
                "Rekomendasi:",
                "- Konsumen: Pertimbangkan untuk membeli kebutuhan pangan lebih awal",
                "- Petani: Waktu yang baik untuk menjual hasil panen",
                "- Distributor: Antisipasi peningkatan permintaan"
            ],
            'TURUN': [
                f"📉 PREDIKSI HARGA TURUN (Confidence: {confidence:.1%})",
                "Rekomendasi:",
                "- Konsumen: Tunggu beberapa hari untuk harga lebih baik",
                "- Petani: Pertimbangkan untuk menyimpan atau mengolah hasil panen",
                "- Distributor: Kurangi stok untuk menghindari kerugian"
            ],
            'STABIL': [
                f"📊 PREDIKSI HARGA STABIL (Confidence: {confidence:.1%})",
                "Rekomendasi:",
                "- Harga relatif tidak berubah signifikan",
                "- Kondisi normal, tidak ada tindakan khusus diperlukan",
                "- Lakukan pembelian sesuai kebutuhan rutin"
            ]
        }
        
        rec_lines = recommendations[prediction].copy()
        
        # Add weather context
        rain = weather_data.get('curah_hujan_mm', 0)
        if rain > 50:
            rec_lines.append(f"⚠️ Curah hujan tinggi ({rain:.1f} mm) - Potensi gangguan distribusi")
        elif rain > 20:
            rec_lines.append(f"🌧️ Curah hujan sedang ({rain:.1f} mm) - Monitor kondisi jalan")
        
        return "\n".join(rec_lines)
    
    def _weather_summary(self, weather_data):
        """Create weather summary string"""
        return (
            f"Suhu: {weather_data.get('suhu_mean', 'N/A')}°C, "
            f"Hujan: {weather_data.get('curah_hujan_mm', 'N/A')} mm, "
            f"Kelembapan: {weather_data.get('kelembapan', 'N/A')}%"
        )
    
    def save_model(self):
        """Save model to disk"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained,
            'feature_names': self.feature_names,
            'target_classes': self.target_classes,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load model from disk"""
        if not os.path.exists(self.model_path):
            logger.error(f"Model file not found: {self.model_path}")
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.is_trained = model_data['is_trained']
        self.feature_names = model_data['feature_names']
        self.target_classes = model_data['target_classes']
        
        logger.info(f"Model loaded from {self.model_path}")
        return self


# Training script
def train_model_from_data():
    """
    Script untuk training model dari data CSV yang ada
    """
    logger.info("Starting food price prediction model training...")
    
    # Path ke data
    weather_csv = 'data/processed/cuaca/cuaca_openmeteo_minggu_01_20260101_20260107.csv'
    price_csv = 'data/processed/harga/harga_jawa_jan_mei_2026.csv'
    
    # Check if files exist
    if not os.path.exists(weather_csv):
        logger.error(f"Weather data not found: {weather_csv}")
        logger.info("Using synthetic training data instead...")
        return train_synthetic_model()
    
    if not os.path.exists(price_csv):
        logger.error(f"Price data not found: {price_csv}")
        logger.info("Using synthetic training data instead...")
        return train_synthetic_model()
    
    # Train model
    predictor = FoodPricePredictionModel()
    predictor.train_from_csv(weather_csv, price_csv)
    
    logger.info("Model training completed!")
    return predictor


def train_synthetic_model():
    """
    Train model dengan synthetic data untuk demo/testing
    """
    logger.info("Generating synthetic training data...")
    
    np.random.seed(42)
    training_data = []
    
    # Scenario 1: Hujan tinggi -> Harga NAIK (distribusi terganggu)
    for _ in range(150):
        training_data.append({
            'features': {
                'suhu_mean': np.random.normal(25, 2),
                'curah_hujan_mm': np.random.normal(80, 20),  # Hujan tinggi
                'kelembapan': np.random.normal(90, 5),
                'kecepatan_angin': np.random.normal(15, 5),
                'tekanan_udara': np.random.normal(1008, 3),
                'awan_persen': np.random.normal(85, 10),
                'suhu_max': np.random.normal(30, 3),
                'suhu_min': np.random.normal(22, 2),
                'curah_hujan_lag_1d': np.random.normal(70, 15),
                'curah_hujan_lag_3d': np.random.normal(60, 15),
                'curah_hujan_lag_7d': np.random.normal(50, 15)
            },
            'target': 2  # NAIK
        })
    
    # Scenario 2: Cuaca ideal -> Harga STABIL
    for _ in range(200):
        training_data.append({
            'features': {
                'suhu_mean': np.random.normal(27, 2),
                'curah_hujan_mm': np.random.normal(10, 5),  # Hujan ringan
                'kelembapan': np.random.normal(75, 5),
                'kecepatan_angin': np.random.normal(10, 3),
                'tekanan_udara': np.random.normal(1012, 2),
                'awan_persen': np.random.normal(50, 15),
                'suhu_max': np.random.normal(32, 2),
                'suhu_min': np.random.normal(23, 2),
                'curah_hujan_lag_1d': np.random.normal(10, 5),
                'curah_hujan_lag_3d': np.random.normal(8, 5),
                'curah_hujan_lag_7d': np.random.normal(12, 5)
            },
            'target': 1  # STABIL
        })
    
    # Scenario 3: Kering panjang -> Harga TURUN (panen melimpah)
    for _ in range(150):
        training_data.append({
            'features': {
                'suhu_mean': np.random.normal(28, 2),
                'curah_hujan_mm': np.random.normal(0, 2),  # Tidak hujan
                'kelembapan': np.random.normal(65, 5),
                'kecepatan_angin': np.random.normal(8, 3),
                'tekanan_udara': np.random.normal(1014, 2),
                'awan_persen': np.random.normal(30, 15),
                'suhu_max': np.random.normal(33, 2),
                'suhu_min': np.random.normal(24, 2),
                'curah_hujan_lag_1d': np.random.normal(0, 2),
                'curah_hujan_lag_3d': np.random.normal(0, 2),
                'curah_hujan_lag_7d': np.random.normal(2, 3)
            },
            'target': 0  # TURUN
        })
    
    # Train model
    predictor = FoodPricePredictionModel()
    predictor.train(training_data)
    
    logger.info("Synthetic model training completed!")
    return predictor


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Train model
    model = train_model_from_data()
    
    # Test predictions
    print("\n" + "="*60)
    print("TESTING PREDICTIONS")
    print("="*60)
    
    # Test 1: Heavy rain
    test_weather_1 = {
        'suhu_mean': 25,
        'curah_hujan_mm': 85,
        'kelembapan': 92,
        'kecepatan_angin': 18,
        'tekanan_udara': 1008,
        'awan_persen': 95,
        'suhu_max': 28,
        'suhu_min': 23
    }
    historical_rain_1 = {'lag_1d': 75, 'lag_3d': 60, 'lag_7d': 50}
    
    print("\n📍 Test Case 1: Cuaca Hujan Lebat")
    result = model.predict(test_weather_1, historical_rain_1)
    print(f"\n{result['recommendation']}")
    
    # Test 2: Ideal weather
    test_weather_2 = {
        'suhu_mean': 27,
        'curah_hujan_mm': 8,
        'kelembapan': 75,
        'kecepatan_angin': 10,
        'tekanan_udara': 1012,
        'awan_persen': 45,
        'suhu_max': 31,
        'suhu_min': 24
    }
    historical_rain_2 = {'lag_1d': 5, 'lag_3d': 10, 'lag_7d': 12}
    
    print("\n📍 Test Case 2: Cuaca Ideal")
    result = model.predict(test_weather_2, historical_rain_2)
    print(f"\n{result['recommendation']}")
