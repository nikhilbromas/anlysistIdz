"""
Restaurant ML models: sales forecasting, ingredient demand prediction.
Uses scikit-learn only.
"""
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


# ---------------------------------------------------------------------------
#  Model registry
# ---------------------------------------------------------------------------
MODEL_REGISTRY = {
    "Linear Regression":       LinearRegression,
    "Ridge Regression":        lambda: Ridge(alpha=1.0),
    "Random Forest":           lambda: RandomForestRegressor(n_estimators=100, random_state=42),
    "Gradient Boosting":       lambda: GradientBoostingRegressor(n_estimators=100, random_state=42),
}


def _make_model(name: str):
    """Instantiate a model from the registry."""
    entry = MODEL_REGISTRY[name]
    if callable(entry) and not isinstance(entry, type):
        return entry()
    return entry()


# ---------------------------------------------------------------------------
#  Train / evaluate
# ---------------------------------------------------------------------------
def train_model(X, y, model_name: str = "Random Forest", test_size: float = 0.2):
    """
    Train a model with train/test split. Returns (model, metrics_dict, y_test, y_pred).
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )
    model = _make_model(model_name)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = {
        "R2":   r2_score(y_test, y_pred),
        "MAE":  mean_absolute_error(y_test, y_pred),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
    }
    return model, metrics, y_test, y_pred


def predict(model, X):
    """Return predictions."""
    return model.predict(X)


def get_feature_importance(model, feature_names: list):
    """Return feature importance as dict (works for tree models; coef for linear)."""
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
    elif hasattr(model, "coef_"):
        imp = np.abs(model.coef_)
    else:
        return {}
    return dict(zip(feature_names, imp))
