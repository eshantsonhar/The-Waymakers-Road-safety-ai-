"""
Risk Prediction Engine
Computes road risk scores and generates accident blackspot heatmaps.
Uses scikit-learn Random Forest for 24-hour accident probability prediction.
"""
import numpy as np
import json
from typing import List, Dict, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import logging

logger = logging.getLogger(__name__)


class RiskPredictionEngine:
    """
    Predicts accident risk for road segments using ML and rule-based scoring.
    
    Risk Score Formula (0-100):
    - Historical accident frequency: 30%
    - Road surface condition (inverse): 15%
    - Rainfall intensity: 15%
    - Ambient lighting (inverse): 10%
    - Traffic density: 10%
    - Road curvature: 10%
    - Pothole density: 10%
    """

    BLACKSPOT_THRESHOLD = 70.0

    WEIGHTS = {
        "accident_frequency": 0.30,
        "surface_condition": 0.15,
        "rainfall": 0.15,
        "lighting": 0.10,
        "traffic_density": 0.10,
        "curvature": 0.10,
        "pothole_density": 0.10,
    }

    def __init__(self):
        self.model: Optional[RandomForestClassifier] = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_metrics = {}

    def compute_risk_score(
        self,
        accident_frequency_per_year: float,
        surface_condition: float,  # 0.0 bad to 1.0 perfect
        rainfall_intensity: float,  # 0.0 none to 1.0 heavy
        lighting_level: float,      # 0.0 dark to 1.0 bright
        traffic_density: float,     # 0.0 empty to 1.0 gridlock
        curvature_index: float,     # 0.0 straight to 1.0 very curved
        pothole_density: float,     # potholes per km (0-10+)
    ) -> tuple[float, float, dict]:
        """
        Compute risk score for a road segment.
        Returns (risk_score, prediction_confidence, contributing_factors).
        """
        # Normalize inputs to 0-1 risk contribution
        factors = {}

        # Higher accident frequency = higher risk
        factors["accident_frequency"] = min(1.0, accident_frequency_per_year / 20.0)

        # Worse surface = higher risk (inverse)
        factors["surface_condition"] = 1.0 - surface_condition

        # More rain = higher risk
        factors["rainfall"] = rainfall_intensity

        # Darker = higher risk (inverse)
        factors["lighting"] = 1.0 - lighting_level

        # More traffic = higher risk
        factors["traffic_density"] = traffic_density

        # More curved = higher risk
        factors["curvature"] = curvature_index

        # More potholes = higher risk
        factors["pothole_density"] = min(1.0, pothole_density / 10.0)

        # Weighted sum
        raw_score = sum(
            factors[k] * self.WEIGHTS[k]
            for k in self.WEIGHTS
        )

        risk_score = raw_score * 100.0

        # Compute confidence based on data completeness
        non_zero_factors = sum(1 for v in factors.values() if v > 0)
        confidence = min(1.0, non_zero_factors / len(factors))

        # If ML model is trained, blend with model prediction
        if self.is_trained:
            ml_score = self._predict_with_model(list(factors.values()))
            risk_score = 0.6 * risk_score + 0.4 * ml_score * 100.0
            confidence = min(1.0, confidence + 0.2)

        return round(risk_score, 1), round(confidence, 3), factors

    def _predict_with_model(self, features: list) -> float:
        """Get ML model prediction probability."""
        try:
            features_array = np.array(features).reshape(1, -1)
            features_scaled = self.scaler.transform(features_array)
            proba = self.model.predict_proba(features_scaled)[0]
            return proba[1] if len(proba) > 1 else proba[0]
        except Exception as e:
            logger.warning(f"ML prediction failed: {e}")
            return 0.5

    def train_model(self, training_data: List[Dict]) -> dict:
        """
        Train the Random Forest model on historical accident data.
        Returns model performance metrics.
        """
        if len(training_data) < 10:
            logger.warning("Insufficient training data, using rule-based scoring only")
            return {}

        X = []
        y = []

        for record in training_data:
            features = [
                min(1.0, record.get("accident_frequency_per_year", 0) / 20.0),
                1.0 - record.get("surface_condition", 0.7),
                record.get("rainfall_intensity", 0.0),
                1.0 - record.get("lighting_level", 0.8),
                record.get("traffic_density", 0.5),
                record.get("curvature_index", 0.1),
                min(1.0, record.get("pothole_density", 0.1) / 10.0),
            ]
            X.append(features)
            # Label: 1 if accident occurred, 0 otherwise
            y.append(1 if record.get("had_accident", False) else 0)

        X = np.array(X)
        y = np.array(y)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            random_state=42,
            class_weight="balanced",
        )
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        self.model_metrics = {
            "accuracy": round(accuracy_score(y_test, y_pred), 3),
            "precision": round(precision_score(y_test, y_pred, zero_division=0), 3),
            "recall": round(recall_score(y_test, y_pred, zero_division=0), 3),
            "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 3),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
        }

        self.is_trained = True
        logger.info(f"Risk model trained: {self.model_metrics}")
        return self.model_metrics

    def generate_heatmap_geojson(self, road_segments: list) -> dict:
        """
        Generate GeoJSON FeatureCollection for danger heatmap.
        Each feature is a road segment with risk_score property.
        """
        features = []

        for segment in road_segments:
            # Create LineString geometry
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [segment.start_longitude, segment.start_latitude],
                        [segment.end_longitude, segment.end_latitude],
                    ],
                },
                "properties": {
                    "id": segment.id,
                    "name": segment.name or "Unknown Road",
                    "district": segment.district,
                    "risk_score": segment.risk_score,
                    "is_blackspot": segment.is_blackspot,
                    "prediction_confidence": segment.prediction_confidence,
                    "accident_frequency": segment.accident_frequency_per_year,
                    "road_type": segment.road_type,
                    "risk_color": self._risk_to_color(segment.risk_score),
                    "risk_level": self._risk_to_level(segment.risk_score),
                    "contributing_factors": segment.risk_factors or {},
                },
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total_segments": len(features),
                "blackspots": sum(1 for s in road_segments if s.is_blackspot),
                "high_risk": sum(1 for s in road_segments if s.risk_score >= 50),
                "model_trained": self.is_trained,
                "model_metrics": self.model_metrics,
            },
        }

    def _risk_to_color(self, risk_score: float) -> str:
        """Convert risk score to hex color (green → yellow → red)."""
        if risk_score >= 80:
            return "#FF0000"  # Red
        elif risk_score >= 60:
            return "#FF6600"  # Orange
        elif risk_score >= 40:
            return "#FFAA00"  # Amber
        elif risk_score >= 20:
            return "#FFFF00"  # Yellow
        else:
            return "#00FF00"  # Green

    def _risk_to_level(self, risk_score: float) -> str:
        """Convert risk score to level label."""
        if risk_score >= 80:
            return "CRITICAL"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 40:
            return "MODERATE"
        elif risk_score >= 20:
            return "LOW"
        else:
            return "MINIMAL"


# Singleton instance
risk_engine = RiskPredictionEngine()
