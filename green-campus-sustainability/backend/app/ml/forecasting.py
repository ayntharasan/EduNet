"""Simple energy consumption forecasting.

Uses Linear Regression with calendar features as a lightweight baseline.
Requires minimum 60 days of observations.

For each model:
- Documents input/output
- Uses chronological train/test split (no data leakage)
- Reports MAE vs naive baseline
- Explains limitations clearly
"""

from __future__ import annotations
import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MIN_OBSERVATIONS = 60
TEST_SPLIT_RATIO = 0.2  # Use last 20% of data for testing


def forecast_energy(
    df: pd.DataFrame,
    value_col: str = "consumption_kwh",
    date_col: str = "timestamp",
    forecast_days: int = 30,
) -> dict[str, Any]:
    """Forecast energy consumption using Linear Regression with calendar features.

    Input: Daily consumption DataFrame with date_col and value_col.
    Output: Forecast for next forecast_days days + model evaluation.

    Train/test split: Chronological (last 20% of data is test set).
    Evaluation metric: MAE (Mean Absolute Error) vs naive baseline.
    Naive baseline: Predicts the training set mean for all test days.

    Returns error message if insufficient data.
    """
    if df.empty or len(df) < MIN_OBSERVATIONS:
        return {
            "error": f"Insufficient data for forecasting. Minimum {MIN_OBSERVATIONS} daily observations required. "
                     f"Available: {len(df)}.",
            "forecast": [],
            "available_observations": len(df),
        }

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    daily = df.groupby(date_col)[value_col].sum().reset_index().sort_values(date_col)

    # Feature engineering
    daily["day_of_week"] = daily[date_col].dt.dayofweek  # 0=Mon
    daily["day_of_year"] = daily[date_col].dt.dayofyear
    daily["month"] = daily[date_col].dt.month
    daily["week_of_year"] = daily[date_col].dt.isocalendar().week.astype(int)
    daily["is_weekend"] = (daily["day_of_week"] >= 5).astype(int)

    features = ["day_of_week", "day_of_year", "month", "week_of_year", "is_weekend"]
    X = daily[features].values
    y = daily[value_col].values

    # Chronological train/test split
    split_idx = int(len(daily) * (1 - TEST_SPLIT_RATIO))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = LinearRegression()
    model.fit(X_train_s, y_train)

    y_pred = model.predict(X_test_s)
    mae = float(mean_absolute_error(y_test, y_pred))

    # Naive baseline: predict training mean
    naive_pred = np.full_like(y_test, y_train.mean())
    naive_mae = float(mean_absolute_error(y_test, naive_pred))

    # Generate forecast
    last_date = daily[date_col].max()
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days)
    future_df = pd.DataFrame({date_col: future_dates})
    future_df["day_of_week"] = future_df[date_col].dt.dayofweek
    future_df["day_of_year"] = future_df[date_col].dt.dayofyear
    future_df["month"] = future_df[date_col].dt.month
    future_df["week_of_year"] = future_df[date_col].dt.isocalendar().week.astype(int)
    future_df["is_weekend"] = (future_df["day_of_week"] >= 5).astype(int)

    X_future = scaler.transform(future_df[features].values)
    future_preds = model.predict(X_future)
    # Ensure non-negative forecasts
    future_preds = np.clip(future_preds, 0, None)

    forecast = [
        {"date": d.strftime("%Y-%m-%d"), "forecast_kwh": round(float(v), 2)}
        for d, v in zip(future_dates, future_preds)
    ]

    return {
        "model": "LinearRegression (calendar features)",
        "features": features,
        "train_samples": split_idx,
        "test_samples": len(y_test),
        "mae_kwh": round(mae, 2),
        "naive_mae_kwh": round(naive_mae, 2),
        "skill_score": round(1 - mae / naive_mae, 3) if naive_mae > 0 else None,
        "forecast_days": forecast_days,
        "forecast": forecast,
        "limitations": (
            "Simple linear model using calendar features only. "
            "Does not account for events, weather, building-specific patterns, or occupancy changes. "
            "Treat forecasts as rough estimates only."
        ),
    }
