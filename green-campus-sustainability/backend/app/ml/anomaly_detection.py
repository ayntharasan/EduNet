"""Machine learning anomaly detection for energy and water consumption.

Uses Isolation Forest (scikit-learn) as the primary method.
Falls back to Z-score statistical method when insufficient data.

Minimum data requirement: 30 observations for Isolation Forest.
"""

from __future__ import annotations
import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MIN_SAMPLES_FOR_ML = 30
DEFAULT_CONTAMINATION = 0.05  # Expected fraction of anomalies


def detect_anomalies(
    df: pd.DataFrame,
    value_col: str,
    date_col: str,
    contamination: float = DEFAULT_CONTAMINATION,
    random_state: int = 42,
) -> dict[str, Any]:
    """Detect anomalies in time-series consumption data.

    Method selection:
    - >= 30 observations: Isolation Forest (ML-based)
    - < 30 observations: Z-score statistical method

    Args:
        df: DataFrame with at least date_col and value_col columns.
        value_col: Column name containing consumption values.
        date_col: Column name containing dates.
        contamination: Expected fraction of anomalies (Isolation Forest).
        random_state: Random seed for reproducibility.

    Returns:
        Dict containing anomaly flags, method used, evaluation notes, and flagged records.
    """
    if df.empty or value_col not in df.columns:
        return {"error": "Insufficient data for anomaly detection.", "method": None, "anomalies": []}

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    daily = df.groupby(date_col)[value_col].sum().reset_index()
    daily = daily.sort_values(date_col).reset_index(drop=True)

    n = len(daily)
    method = "isolation_forest" if n >= MIN_SAMPLES_FOR_ML else "z_score"

    logger.info(f"Anomaly detection: {n} samples, using {method} method.")

    if method == "isolation_forest":
        return _isolation_forest(daily, value_col, date_col, contamination, random_state)
    else:
        return _z_score(daily, value_col, date_col)


def _isolation_forest(
    daily: pd.DataFrame, value_col: str, date_col: str,
    contamination: float, random_state: int
) -> dict[str, Any]:
    """Apply Isolation Forest anomaly detection.

    Isolation Forest identifies anomalies by measuring how easily a point can
    be isolated from the rest using random partitioning. Anomalies are isolated
    with fewer partitions on average.

    Evaluation: No ground truth labels are available, so evaluation is limited
    to contamination rate and visual inspection.
    """
    features = daily[[value_col]].copy()
    # Add lag features to capture temporal context
    features["lag_1"] = daily[value_col].shift(1)
    features["rolling_7d"] = daily[value_col].rolling(7).mean()
    features = features.bfill().ffill()

    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=100,
    )
    preds = model.fit_predict(X)
    scores = model.score_samples(X)

    daily["is_anomaly"] = preds == -1
    daily["anomaly_score"] = scores  # Lower = more anomalous

    anomaly_records = daily[daily["is_anomaly"]][
        [date_col, value_col, "anomaly_score"]
    ].copy()
    anomaly_records[date_col] = anomaly_records[date_col].dt.strftime("%Y-%m-%d")
    anomaly_records = anomaly_records.rename(columns={value_col: "value", date_col: "date"})

    return {
        "method": "isolation_forest",
        "method_description": "Isolation Forest (scikit-learn). Identifies anomalies through random partitioning.",
        "n_samples": len(daily),
        "contamination": contamination,
        "n_anomalies": int(daily["is_anomaly"].sum()),
        "anomalies": anomaly_records.to_dict(orient="records"),
        "limitations": (
            "No ground truth labels. Contamination parameter is configurable. "
            "Results indicate candidates for review, not confirmed errors."
        ),
    }


def _z_score(daily: pd.DataFrame, value_col: str, date_col: str) -> dict[str, Any]:
    """Z-score statistical anomaly detection.

    Formula: z = (x - mean) / std
    Flags values with |z| > 2.5 (approximately top/bottom 1.2% of normal distribution).
    """
    mean = daily[value_col].mean()
    std = daily[value_col].std()

    if std == 0 or np.isnan(std):
        return {
            "method": "z_score",
            "n_samples": len(daily),
            "n_anomalies": 0,
            "anomalies": [],
            "limitations": "Standard deviation is zero — all values are identical.",
        }

    daily["z_score"] = (daily[value_col] - mean) / std
    daily["is_anomaly"] = daily["z_score"].abs() > 2.5
    anomaly_records = daily[daily["is_anomaly"]][[date_col, value_col, "z_score"]].copy()
    anomaly_records[date_col] = anomaly_records[date_col].dt.strftime("%Y-%m-%d")
    anomaly_records = anomaly_records.rename(columns={value_col: "value", date_col: "date"})

    return {
        "method": "z_score",
        "method_description": "Z-score (|z| > 2.5). Statistical method for small samples.",
        "n_samples": len(daily),
        "n_anomalies": int(daily["is_anomaly"].sum()),
        "anomalies": anomaly_records.to_dict(orient="records"),
        "limitations": (
            f"Only {len(daily)} samples — fewer than the 30 required for Isolation Forest. "
            "Z-score assumes normally distributed data."
        ),
    }
