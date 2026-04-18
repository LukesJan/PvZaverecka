import joblib
import numpy as np
import pandas as pd

from src.config import (
    GOAL_FEATURE_COLUMNS,
    MODELS_DIR,
    WINNER_FEATURE_COLUMNS,
)

PRIMARY_GOAL_LINE = 2.5
GOAL_LINE_OVER_LABEL = f"Over {PRIMARY_GOAL_LINE:.1f}"
GOAL_LINE_UNDER_LABEL = f"Under {PRIMARY_GOAL_LINE:.1f}"
MODEL_FILES = (
    "winner_model.joblib",
    "home_goals_model.joblib",
    "away_goals_model.joblib",
    "goal_line_model.joblib",
)


def load_models() -> tuple[object, object, object, object]:
    """Nacte ulozene modely pro viteze a domaci/hostujici goly."""
    model_paths = [MODELS_DIR / file_name for file_name in MODEL_FILES]
    missing_paths = [path for path in model_paths if not path.exists()]
    if missing_paths:
        missing_text = ", ".join(path.name for path in missing_paths)
        raise FileNotFoundError(
            f"Chybi modely: {missing_text}. Nejdriv spust notebook notebooks/training.ipynb."
        )
    return tuple(joblib.load(path) for path in model_paths)


def numeric_features(dataframe: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Vrati modelove sloupce jako ciselny dataframe bez NaN."""
    return dataframe[columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)


def predict_winner_outcomes(
    winner_model: object,
    feature_data: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """Predikuje viteze zapasu a confidence pro winner model."""
    predicted_winners = winner_model.predict(feature_data)
    winner_probabilities = winner_model.predict_proba(feature_data)
    return np.asarray(predicted_winners), winner_probabilities.max(axis=1)


def ensure_feature_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Doplni chybejici modelove feature sloupce nulou."""
    prepared = dataframe.copy()
    for column_name in WINNER_FEATURE_COLUMNS:
        if column_name not in prepared.columns:
            prepared[column_name] = 0.0
    return prepared


def add_model_predictions(
    dataframe: pd.DataFrame,
    models: tuple[object, object, object, object] | None = None,
) -> pd.DataFrame:
    """Prida do dataframe predikce viteze, golu a Under/Over label."""
    if dataframe.empty:
        return dataframe.copy()

    prepared = ensure_feature_columns(dataframe)
    winner_model, home_goals_model, away_goals_model, goal_line_payload = models or load_models()
    goal_line_model = goal_line_payload.get("model") if isinstance(goal_line_payload, dict) else goal_line_payload
    goal_line_threshold = float(goal_line_payload.get("threshold", 0.5)) if isinstance(goal_line_payload, dict) else 0.5
    winner_feature_data = numeric_features(prepared, WINNER_FEATURE_COLUMNS)
    goal_feature_data = numeric_features(prepared, GOAL_FEATURE_COLUMNS)
    predicted_winners, winner_confidences = predict_winner_outcomes(winner_model, winner_feature_data)
    raw_home_goals = home_goals_model.predict(goal_feature_data)
    raw_away_goals = away_goals_model.predict(goal_feature_data)
    predicted_home_goals = np.round(np.maximum(raw_home_goals, 0.0), 2)
    predicted_away_goals = np.round(np.maximum(raw_away_goals, 0.0), 2)
    predicted_total_goals = np.round(np.maximum(raw_home_goals + raw_away_goals, 0.0), 2)
    goal_line_probabilities = goal_line_model.predict_proba(goal_feature_data)
    over_index = list(goal_line_model.classes_).index(1)
    over_probabilities = goal_line_probabilities[:, over_index]
    predicted_goal_line = over_probabilities >= goal_line_threshold

    result = prepared.copy()
    result["predicted_winner"] = predicted_winners
    result["winner_confidence"] = winner_confidences
    result["predicted_home_goals"] = predicted_home_goals
    result["predicted_away_goals"] = predicted_away_goals
    result["predicted_total_goals"] = predicted_total_goals
    result["predicted_goal_line"] = np.where(
        predicted_goal_line,
        GOAL_LINE_OVER_LABEL,
        GOAL_LINE_UNDER_LABEL,
    )
    result["goal_line_confidence"] = np.where(predicted_goal_line, over_probabilities, 1.0 - over_probabilities)
    return result
