"""
EC2 Idle Instance Detection using ML (Isolation Forest)
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from app.aws.resources import EC2ResourceCollector
from app.core.config import settings


class EC2IdleDetector:
    """
    Detect idle EC2 instances using Isolation Forest ML algorithm

    Criteria:
    - CPU < 5% for 7+ days
    - Minimal network activity
    - ML anomaly detection for pattern recognition
    """

    def __init__(self, resource_collector: EC2ResourceCollector):
        self.collector = resource_collector
        self.cpu_threshold = settings.EC2_IDLE_CPU_THRESHOLD
        self.idle_days = settings.EC2_IDLE_DAYS
        self.model = IsolationForest(
            contamination=settings.ISOLATION_FOREST_CONTAMINATION,
            random_state=42,
            n_estimators=100,
        )
        self.is_trained = False

    def _extract_features(self, metrics: List[Dict]) -> Optional[np.ndarray]:
        """
        Extract features from CloudWatch metrics

        Features:
        - Average CPU utilization
        - Max CPU utilization
        - Min CPU utilization
        - CPU variance
        - Network in average
        - Network out average
        - Number of data points
        """
        # if not metrics or len(metrics) < 24:  # Need at least 24 hours of data
        #     return None

        df = pd.DataFrame(metrics)

        # CPU features
        cpu_avg = df["Average"].mean() if "Average" in df.columns else 0
        cpu_max = df["Maximum"].max() if "Maximum" in df.columns else 0
        cpu_min = df["Minimum"].min() if "Minimum" in df.columns else 0
        cpu_std = df["Average"].std() if "Average" in df.columns else 0

        # Network features (if available)
        # Note: Network metrics would need separate API calls
        network_in = 0  # TODO: Fetch NetworkIn metrics
        network_out = 0  # TODO: Fetch NetworkOut metrics

        features = np.array(
            [
                [
                    cpu_avg,
                    cpu_max,
                    cpu_min,
                    cpu_std,
                    network_in,
                    network_out,
                    len(metrics),
                ]
            ]
        )

        return features

    def _train_model(self, feature_matrix: np.ndarray):
        """Train Isolation Forest model on historical data"""
        if len(feature_matrix) < 5:
            # Not enough data to train, use default model
            return

        self.model.fit(feature_matrix)
        self.is_trained = True

    def detect_idle_instances(
        self, instances: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Detect idle EC2 instances

        Args:
            instances: Optional list of instances (if None, fetches all)

        Returns:
            List of idle instance detections with confidence scores
        """
        if instances is None:
            instances = self.collector.get_all_instances()

        # Filter to only running instances
        running_instances = [inst for inst in instances if inst["state"] == "running"]

        detections = []
        all_features = []
        instance_features_map = {}

        # Collect metrics and extract features
        for instance in running_instances:
            instance_id = instance["instance_id"]

            # Get CPU metrics for the idle period
            cpu_metrics = self.collector.get_instance_metrics(
                instance_id, days=self.idle_days, metric_name="CPUUtilization"
            )

            if not cpu_metrics:
                continue

            # Extract features
            features = self._extract_features(cpu_metrics)
            if features is None:
                continue

            all_features.append(features[0])
            instance_features_map[instance_id] = {
                "instance": instance,
                "metrics": cpu_metrics,
                "features": features[0],
            }

        if not all_features:
            return []

        # Convert to numpy array
        feature_matrix = np.array(all_features)
        print(f"Feature matrix shape: {feature_matrix.shape}")
        print(f"Number of instances to analyze: {len(feature_matrix)}")

        # Determine detection mode based on data availability
        use_ml = len(feature_matrix) >= 5
        
        if use_ml:
            # ML-powered detection: Train model with sufficient data
            print("Using ML-powered detection (5+ instances)")
            self._train_model(feature_matrix)
            predictions = self.model.predict(feature_matrix)
            anomaly_scores = self.model.score_samples(feature_matrix)
        else:
            # Rule-based detection: Insufficient data for ML
            print(f"Using rule-based detection ({len(feature_matrix)} instances - need 5+ for ML)")
            predictions = None
            anomaly_scores = None

        # Process results
        for idx, (instance_id, data) in enumerate(instance_features_map.items()):
            instance = data["instance"]
            metrics = data["metrics"]
            features = data["features"]

            # Calculate average CPU
            avg_cpu = features[0]  # First feature is average CPU

            # Check basic threshold first
            if avg_cpu >= self.cpu_threshold:
                continue  # Not idle by threshold

            if use_ml:
                # ML-powered detection
                is_anomaly = predictions[idx] == -1
                confidence = 1.0 - (anomaly_scores[idx] + 1) / 2  # Normalize to 0-1
                
                # Only flag if both threshold and ML agree (or high confidence)
                if not (is_anomaly or confidence > 0.7):
                    continue
            else:
                # Rule-based detection: Use threshold only
                is_anomaly = False
                confidence = 0.8 if avg_cpu < self.cpu_threshold / 2 else 0.6  # Higher confidence for very low CPU
                
                # Already passed threshold check above, so flag it
            # Calculate estimated savings
            savings = self._estimate_savings(instance, avg_cpu)

            detections.append(
                {
                    "resource_type": "ec2_instance",
                    "resource_id": instance_id,
                    "resource_name": instance.get("tags", {}).get(
                        "Name", instance_id
                    ),
                    "region": instance["region"],
                    "instance_type": instance["instance_type"],
                    "state": instance["state"],
                    "avg_cpu_percent": round(avg_cpu, 2),
                    "days_idle": self.idle_days,
                    "confidence_score": round(confidence, 3),
                    "is_ml_detected": is_anomaly,
                    "detection_mode": "ml" if use_ml else "rule-based",
                    "estimated_monthly_savings_inr": savings,
                    "detected_at": datetime.utcnow().isoformat(),
                    "metadata": {
                        "launch_time": (
                            instance["launch_time"].isoformat()
                            if isinstance(instance["launch_time"], datetime)
                            else str(instance["launch_time"])
                        ),
                        "vpc_id": instance.get("vpc_id"),
                        "tags": instance.get("tags", {}),
                        "ml_enabled": use_ml,
                        "total_instances_analyzed": len(feature_matrix),
                    },
                }
            )

        return detections

    def _estimate_savings(self, instance: Dict, avg_cpu: float) -> float:
        """
        Estimate monthly savings in INR for stopping this instance

        This is a simplified calculation. In production, you'd:
        - Fetch actual pricing from AWS Pricing API
        - Consider reserved instances
        - Account for data transfer costs
        """
        instance_type = instance.get("instance_type", "t3.micro")

        # Rough pricing in INR (approximate, should use AWS Pricing API)
        # These are example values - actual pricing varies by region
        pricing_map = {
            "t3.micro": 0.5,  # ₹0.5/hour ≈ ₹360/month
            "t3.small": 1.0,
            "t3.medium": 2.0,
            "t3.large": 4.0,
            "m5.large": 8.0,
            "m5.xlarge": 16.0,
        }

        hourly_rate = pricing_map.get(instance_type, 2.0)  # Default ₹2/hour
        monthly_cost = hourly_rate * 24 * 30  # ₹/month

        # Savings = full cost if stopped (assuming no data transfer)
        return round(monthly_cost, 2)
