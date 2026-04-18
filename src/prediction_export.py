import json
from pathlib import Path

import pandas as pd

from src.config import DEFAULT_LEAGUES, LEAGUE_NAMES, PROCESSED_DATA_DIR, UPCOMING_PREDICTIONS_PATH
from src.fixtures import load_raw_data, prepare_fixtures
from src.model_runtime import GOAL_LINE_OVER_LABEL, GOAL_LINE_UNDER_LABEL, PRIMARY_GOAL_LINE, add_model_predictions, load_models
from src.prediction_rows import collect_last_completed_round_rows, collect_upcoming_feature_rows
from src.utils import ensure_project_directories


def format_prediction_payload(row: pd.Series, include_actual: bool = False) -> dict:
    """Prevede predikcni radek na JSON payload pro frontend."""
    payload = {
        "homeTeam": row["home_team_name"],
        "awayTeam": row["away_team_name"],
        "matchDate": row["utc_date"].strftime("%Y-%m-%d %H:%M UTC"),
        "round": row.get("round", ""),
        "status": row.get("status_short", ""),
        "predictedWinner": row["predicted_winner"],
        "winnerConfidence": round(float(row.get("winner_confidence", 0.0)), 4),
        "predictedHomeGoals": round(float(row.get("predicted_home_goals", 0.0)), 2),
        "predictedAwayGoals": round(float(row.get("predicted_away_goals", 0.0)), 2),
        "predictedTotalGoals": round(float(row["predicted_total_goals"]), 2),
        "predictedGoalLine": row["predicted_goal_line"],
        "goalLineConfidence": round(float(row.get("goal_line_confidence", 0.0)), 4),
    }

    if include_actual:
        actual_total_goals = int(row["actual_home_goals"]) + int(row["actual_away_goals"])
        actual_goal_line = GOAL_LINE_OVER_LABEL if actual_total_goals > PRIMARY_GOAL_LINE else GOAL_LINE_UNDER_LABEL
        payload.update(
            {
                "actualWinner": row["actual_winner"],
                "actualScore": f"{int(row['actual_home_goals'])}:{int(row['actual_away_goals'])}",
                "actualTotalGoals": actual_total_goals,
                "actualGoalLine": actual_goal_line,
                "winnerHit": row["predicted_winner"] == row["actual_winner"],
                "goalLineHit": row["predicted_goal_line"] == actual_goal_line,
            }
        )

    return payload


def build_league_sections(
    dataframe: pd.DataFrame,
    per_league: int,
    include_actual: bool = False,
) -> list[dict]:
    """Seskupi predikce podle lig do sekci pro frontend."""
    leagues = []

    for league_id in DEFAULT_LEAGUES:
        league_frame = dataframe[dataframe["league_id"] == league_id].copy()
        if league_frame.empty:
            continue

        selected_rows = league_frame if per_league == 0 else league_frame.head(per_league)
        predictions = [
            format_prediction_payload(row, include_actual=include_actual)
            for _, row in selected_rows.iterrows()
        ]
        leagues.append(
            {
                "code": league_id,
                "leagueName": LEAGUE_NAMES.get(league_id, str(league_id)),
                "predictions": predictions,
            }
        )

    return leagues


def select_next_rounds(dataframe: pd.DataFrame, rounds_ahead: int) -> pd.DataFrame:
    """Necha jen nejblizsi pocet kol pro kazdou ligu."""
    if dataframe.empty or rounds_ahead <= 0:
        return dataframe.copy()

    selected_frames = []
    for league_id in DEFAULT_LEAGUES:
        league_frame = dataframe[dataframe["league_id"] == league_id].sort_values(
            ["utc_date", "fixture_id"]
        )
        if league_frame.empty:
            continue

        selected_rounds = []
        for round_name in league_frame["round"].fillna("").astype(str):
            if round_name and round_name not in selected_rounds:
                selected_rounds.append(round_name)
            if len(selected_rounds) == rounds_ahead:
                break

        selected_frame = (
            league_frame[league_frame["round"].isin(selected_rounds)]
            if selected_rounds
            else league_frame.head(rounds_ahead)
        )
        selected_frames.append(selected_frame)

    if not selected_frames:
        return dataframe.iloc[0:0].copy()

    return pd.concat(selected_frames, ignore_index=True).sort_values(
        ["utc_date", "fixture_id"]
    ).reset_index(drop=True)


def generate_upcoming_predictions(per_league: int = 0, rounds_ahead: int = 2) -> dict:
    """Vygeneruje kompletni export budoucich zapasu a historicke kontroly."""
    raw_dataframe = load_raw_data()
    prepared_fixtures = prepare_fixtures(raw_dataframe)
    final_dataset_path = PROCESSED_DATA_DIR / "final_dataset.csv"
    final_dataset = pd.read_csv(final_dataset_path) if final_dataset_path.exists() else pd.DataFrame()
    if not final_dataset.empty:
        final_dataset["utc_date"] = pd.to_datetime(final_dataset["utc_date"], utc=True, errors="coerce")

    upcoming_features = collect_upcoming_feature_rows(prepared_fixtures)
    current_utc = pd.Timestamp.now(tz="UTC")
    upcoming_features = upcoming_features[upcoming_features["utc_date"] >= current_utc].copy()
    upcoming_features = select_next_rounds(upcoming_features, rounds_ahead=rounds_ahead)
    models = load_models()
    upcoming_features = add_model_predictions(
        upcoming_features.sort_values(["utc_date", "fixture_id"]),
        models=models,
    )
    history_features = add_model_predictions(
        collect_last_completed_round_rows(prepared_fixtures, final_dataset),
        models=models,
    )

    upcoming_leagues = build_league_sections(upcoming_features, per_league=per_league)
    history_leagues = build_league_sections(history_features, per_league=0, include_actual=True)
    return {
        "generated_at": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC"),
        "roundsAhead": rounds_ahead,
        "leagues": upcoming_leagues,
        "upcomingLeagues": upcoming_leagues,
        "historyLeagues": history_leagues,
    }


def export_upcoming_predictions_json(output_path: str | None, per_league: int, rounds_ahead: int = 2) -> Path:
    """Ulozi vygenerovane predikce do JSON souboru."""
    ensure_project_directories()
    predictions = generate_upcoming_predictions(per_league=per_league, rounds_ahead=rounds_ahead)
    path = Path(output_path) if output_path else UPCOMING_PREDICTIONS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(predictions, ensure_ascii=True, indent=2), encoding="utf-8")
    return path
