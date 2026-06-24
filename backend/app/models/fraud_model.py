"""
BOU Sentinel - AI Fraud Detection Engine
Uses scikit-learn Isolation Forest for anomaly detection on financial transactions.
"""
import os
import pickle
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("bou-sentinel.fraud_model")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "fraud_model.pkl")


class FraudDetectionModel:
    """
    Isolation Forest-based anomaly detector for financial transactions.
    Trains on normal transaction patterns and assigns risk scores.
    """

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model: Optional[IsolationForest] = None
        self.feature_columns = [
            "amount",
            "transaction_type_encoded",
            "hour_of_day",
            "day_of_week",
            "is_international",
            "amount_velocity",
            "is_high_value",
        ]
        self.is_loaded = False

    def _extract_features(self, transaction: Dict[str, Any]) -> pd.DataFrame:
        """
        Extract numerical features from a raw transaction dict for model scoring.
        """
        # Transaction type encoding
        tx_type_map = {
            "transfer": 0,
            "deposit": 1,
            "withdrawal": 2,
            "payment": 3,
            "internal_transfer": 4,
        }
        tx_type_encoded = tx_type_map.get(transaction.get("transaction_type", "transfer"), 0)

        # Temporal features
        from datetime import datetime
        timestamp_str = transaction.get("timestamp")
        if timestamp_str:
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.utcnow()
        else:
            ts = datetime.utcnow()
        hour_of_day = ts.hour
        day_of_week = ts.weekday()

        # Amount-based features
        amount = float(transaction.get("amount", 0))
        is_high_value = 1 if amount > 10000000 else 0  # UGX 10M threshold

        # Location-based features
        location = transaction.get("location", "Unknown")
        is_international = 1 if location and location.lower() not in [
            "kampala", "entebbe", "jinja", "mbarara", "gulu", "mbale",
            "unknown", "uganda"
        ] else 0

        # Build feature vector
        features = {
            "amount": np.log1p(amount),  # log transform for skewed distribution
            "transaction_type_encoded": tx_type_encoded,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "is_international": is_international,
            "amount_velocity": 0.0,  # Will be computed with historical context
            "is_high_value": is_high_value,
        }

        return pd.DataFrame([features])[self.feature_columns]

    def train(self, transactions: pd.DataFrame) -> "FraudDetectionModel":
        """
        Train the Isolation Forest model on historical transaction data.

        Args:
            transactions: DataFrame with columns matching feature_columns
        """
        logger.info(f"Training Isolation Forest model on {len(transactions)} transactions...")

        # Ensure we have the right features
        X = transactions[self.feature_columns].values if all(
            col in transactions.columns for col in self.feature_columns
        ) else transactions.values

        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=200,
            max_samples="auto",
            bootstrap=False,
            n_jobs=-1,
            verbose=0,
        )
        self.model.fit(X)
        self.is_loaded = True
        logger.info("✅ Model training complete")
        return self

    def score(self, transaction: Dict[str, Any]) -> Tuple[float, bool, Optional[str]]:
        """
        Score a single transaction. Returns (risk_score, is_fraud, reason).

        Args:
            transaction: Raw transaction dictionary

        Returns:
            Tuple of (risk_score: 0.0-1.0, is_fraud: bool, reason: str or None)
        """
        if not self.is_loaded or self.model is None:
            logger.warning("Model not loaded. Attempting to load from disk...")
            self.load()

        if not self.is_loaded or self.model is None:
            logger.error("No trained model available. Using heuristic fallback.")
            return self._heuristic_score(transaction)

        try:
            features_df = self._extract_features(transaction)
            X = features_df.values

            # Decision function: lower = more anomalous
            decision_score = self.model.decision_function(X)[0]

            # Convert to risk score (0.0 to 1.0)
            # decision_function ranges from ~-0.5 (anomalous) to ~0.5 (normal)
            # We normalize: 1.0 = high risk, 0.0 = low risk
            risk_score = float(1.0 - (decision_score + 0.5))

            # Clamp to [0, 1]
            risk_score = max(0.0, min(1.0, risk_score))

            # Classification
            is_fraud = risk_score > 0.75
            reason = None
            if is_fraud:
                amount = float(transaction.get("amount", 0))
                tx_type = transaction.get("transaction_type", "")
                location = transaction.get("location", "")
                reasons = []
                if amount > 10000000:
                    reasons.append(f"High-value transaction: UGX {amount:,.0f}")
                if location and location.lower() not in ["kampala", "entebbe", "jinja", "uganda"]:
                    reasons.append(f"International location: {location}")
                if tx_type == "withdrawal" and amount > 5000000:
                    reasons.append("Large withdrawal amount")
                reason = "; ".join(reasons) if reasons else "Anomalous pattern detected by AI"

            return risk_score, is_fraud, reason

        except Exception as e:
            logger.error(f"Model scoring failed: {e}")
            return self._heuristic_score(transaction)

    def _heuristic_score(self, transaction: Dict[str, Any]) -> Tuple[float, bool, Optional[str]]:
        """
        Fallback heuristic scoring when model is unavailable.
        Based on banking domain rules.
        """
        amount = float(transaction.get("amount", 0))
        tx_type = transaction.get("transaction_type", "")
        location = transaction.get("location", "Unknown")

        risk_score = 0.0
        reasons = []

        # Rule 1: High-value transactions
        if amount > 20000000:  # UGX 20M
            risk_score += 0.4
            reasons.append(f"High-value: UGX {amount:,.0f}")
        elif amount > 10000000:
            risk_score += 0.2

        # Rule 2: Large withdrawals
        if tx_type == "withdrawal" and amount > 5000000:
            risk_score += 0.3
            reasons.append("Large withdrawal")

        # Rule 3: International transactions
        if location and location.lower() not in [
            "kampala", "entebbe", "jinja", "mbarara", "gulu", "mbale", "uganda", "unknown"
        ]:
            risk_score += 0.3
            reasons.append(f"International: {location}")

        # Rule 4: Suspicious hours (midnight to 5 AM)
        from datetime import datetime
        hour = datetime.utcnow().hour
        if hour < 5:
            risk_score += 0.15
            reasons.append(f"Off-hours: {hour}:00")

        # Clamp
        risk_score = min(1.0, risk_score)
        is_fraud = risk_score > 0.6
        reason = "; ".join(reasons) if reasons else (None if not is_fraud else "Suspicious pattern detected")

        return risk_score, is_fraud, reason

    def save(self, path: str = MODEL_PATH) -> str:
        """Save the trained model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info(f"Model saved to {path}")
        return path

    def load(self, path: str = MODEL_PATH) -> bool:
        """Load a trained model from disk."""
        if not os.path.exists(path):
            logger.warning(f"No model found at {path}. Train or use heuristic.")
            return False
        try:
            with open(path, "rb") as f:
                self.model = pickle.load(f)
            self.is_loaded = True
            logger.info(f"✅ Model loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def generate_training_data(self, n_samples: int = 10000) -> pd.DataFrame:
        """
        Generate synthetic training data for bootstrapping the model.
        Creates realistic Ugandan transaction patterns.
        """
        np.random.seed(self.random_state)
        data = []

        for _ in range(n_samples):
            # Generate realistic amounts (UGX)
            # Normal transactions: 50k to 5M
            # Some outliers for fraud simulation
            is_anomaly = np.random.random() < self.contamination

            if is_anomaly:
                amount = np.random.exponential(5000000) + 5000000  # 5M-50M+
                tx_type = np.random.choice(["transfer", "withdrawal"], p=[0.4, 0.6])
                hour = np.random.randint(0, 6)  # Off-hours
                location = np.random.choice(["Lagos", "Nairobi", "London", "Dubai"])
            else:
                amount = np.random.lognormal(mean=12.5, sigma=1.5)  # ~270k median
                tx_type = np.random.choice(
                    ["transfer", "deposit", "withdrawal", "payment"],
                    p=[0.4, 0.25, 0.2, 0.15]
                )
                hour = np.random.randint(6, 22)  # Business hours
                location = np.random.choice(["Kampala", "Entebbe", "Jinja", "Mbarara", "Gulu"])

            tx_type_map = {"transfer": 0, "deposit": 1, "withdrawal": 2, "payment": 3}
            is_international = 1 if location.lower() not in [
                "kampala", "entebbe", "jinja", "mbarara", "gulu", "mbale", "uganda"
            ] else 0

            row = {
                "amount": np.log1p(amount),
                "transaction_type_encoded": tx_type_map.get(tx_type, 0),
                "hour_of_day": hour,
                "day_of_week": np.random.randint(0, 7),
                "is_international": is_international,
                "amount_velocity": np.random.exponential(2.0),
                "is_high_value": 1 if amount > 10000000 else 0,
            }
            data.append(row)

        df = pd.DataFrame(data)
        logger.info(f"Generated {n_samples} synthetic training samples ("
                     f"{int(self.contamination * n_samples)} anomalies)")
        return df


# Singleton instance
_model_instance: Optional[FraudDetectionModel] = None


def get_model() -> FraudDetectionModel:
    """Get or initialize the singleton fraud detection model."""
    global _model_instance
    if _model_instance is None:
        _model_instance = FraudDetectionModel()
        # Try to load pre-trained model, otherwise bootstrap with synthetic data
        if not _model_instance.load():
            logger.info("No pre-trained model found. Bootstrapping with synthetic data...")
            training_data = _model_instance.generate_training_data(n_samples=5000)
            _model_instance.train(training_data)
            _model_instance.save()
    return _model_instance