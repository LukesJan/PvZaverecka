from collections import deque

import pandas as pd

from src.config import CONTEXT_FEATURE_SUFFIXES, DIFF_FEATURE_COLUMNS, LEAGUE_FLAGS, TEAM_FEATURE_SUFFIXES
from src.utils import get_winner_from_goals

SUMMARY_KEYS = ("points", "goals_scored", "goals_conceded", "wins", "draws", "losses")
DIFF_SOURCE_KEYS = {
    "diff_points_last_5": "points_last_5",
    "diff_points_last_3": "points_last_3",
    "diff_avg_points_before": "avg_points_before",
    "diff_goals_scored_last_5": "goals_scored_last_5",
    "diff_goals_conceded_last_5": "goals_conceded_last_5",
    "diff_goal_diff_last_5": "goal_diff_last_5",
    "diff_goal_diff_last_3": "goal_diff_last_3",
    "diff_home_away_points_last_3": "context_points_last_3",
    "diff_home_away_goal_diff_last_3": "context_goal_diff_last_3",
    "diff_rest_days": "rest_days",
    "diff_wins_last_5": "wins_last_5",
}


def summarize_recent(history: deque, matches: int) -> dict:
    """Secte formu tymu z poslednich vybranych zapasu."""
    history_list = list(history)[-matches:]
    return {key: sum(item[key] for item in history_list) for key in SUMMARY_KEYS}


def get_league_flag_features(league_id: int) -> dict:
    """Vytvori binarni priznaky pro konkretni ligu."""
    return {column: int(league_id == league) for league, column in LEAGUE_FLAGS.items()}


def safe_average(total: int, matches: int) -> float:
    """Vrati prumer a pri nulovem poctu zapasu bezpecne vrati nulu."""
    return total / matches if matches else 0.0


def get_rest_days(team_id: int, fixture_date: pd.Timestamp, last_match_dates: dict) -> float:
    """Spocte pocet dni od posledniho zapasu tymu."""
    last_match_date = last_match_dates.get(team_id)
    if last_match_date is None or pd.isna(last_match_date):
        return 7.0

    delta_days = (fixture_date - last_match_date).total_seconds() / 86400
    return round(max(0.0, min(delta_days, 21.0)), 2)


def build_table_positions(league_table: dict) -> dict:
    """Seradi tymy podle bodu a goloveho rozdilu do tabulkovych pozic."""
    ordered_table = sorted(
        league_table.items(),
        key=lambda item: (
            -item[1]["points"],
            -(item[1]["goals_scored"] - item[1]["goals_conceded"]),
            -item[1]["goals_scored"],
            item[0],
        ),
    )
    return {team_id: index + 1 for index, (team_id, _) in enumerate(ordered_table)}


def build_table_snapshot(
    league_id: int,
    season: int,
    team_id: int,
    season_tables: dict,
    season_positions: dict,
) -> dict:
    """Vrati stav tymu v tabulce pred aktualnim zapasem."""
    table_key = (league_id, season)
    league_table = season_tables[table_key]
    team_row = league_table[team_id]
    position = season_positions.get(table_key, {}).get(team_id, len(league_table) + 1)

    return {
        "season_points_before": team_row["points"],
        "season_goal_diff_before": team_row["goals_scored"] - team_row["goals_conceded"],
        "season_position_before": position,
    }


def build_team_snapshot(
    team_id: int,
    fixture_date: pd.Timestamp,
    last_five_history: dict,
    team_totals: dict,
    last_match_dates: dict,
    context_last_five_history: dict,
    context_team_totals: dict,
) -> dict:
    """Vrati predzapasovy snapshot formy, prumeru a odpocinku tymu."""
    totals = team_totals[team_id]
    recent = summarize_recent(last_five_history[team_id], matches=5)
    recent_last_3 = summarize_recent(last_five_history[team_id], matches=3)
    context_totals = context_team_totals[team_id]
    context_recent = summarize_recent(context_last_five_history[team_id], matches=5)
    context_recent_last_3 = summarize_recent(context_last_five_history[team_id], matches=3)
    matches = totals["matches"]
    context_matches = context_totals["matches"]
    snapshot = {"rest_days": get_rest_days(team_id, fixture_date, last_match_dates)}

    for recent_values, suffix in ((recent, "last_5"), (recent_last_3, "last_3")):
        snapshot.update({f"{key}_{suffix}": recent_values[key] for key in SUMMARY_KEYS})

    snapshot.update(
        {
        "matches_played_before": matches,
        "avg_points_before": safe_average(totals["points"], matches),
        "avg_goals_scored_before": safe_average(totals["goals_scored"], matches),
        "avg_goals_conceded_before": safe_average(totals["goals_conceded"], matches),
        "context_points_last_5": context_recent["points"],
        "context_points_last_3": context_recent_last_3["points"],
        "context_goals_scored_last_3": context_recent_last_3["goals_scored"],
        "context_goals_conceded_last_3": context_recent_last_3["goals_conceded"],
        "context_avg_goals_scored_before": safe_average(
            context_totals["goals_scored"], context_matches
        ),
        "context_avg_goals_conceded_before": safe_average(
            context_totals["goals_conceded"], context_matches
        ),
        "goal_diff_last_5": recent["goals_scored"] - recent["goals_conceded"],
        "goal_diff_last_3": recent_last_3["goals_scored"] - recent_last_3["goals_conceded"],
        "context_goal_diff_last_3": (
            context_recent_last_3["goals_scored"] - context_recent_last_3["goals_conceded"]
        ),
        }
    )
    return snapshot


def build_feature_values(
    home_snapshot: dict,
    away_snapshot: dict,
    home_table_snapshot: dict,
    away_table_snapshot: dict,
    league_id: int,
) -> dict:
    """Slozi modelove feature z predzapasovych snapshotu obou tymu."""
    snapshots = {"home": home_snapshot, "away": away_snapshot}
    table_snapshots = {"home": home_table_snapshot, "away": away_table_snapshot}
    return {
        **{f"{side}_{suffix}": snapshots[side][suffix] for suffix in TEAM_FEATURE_SUFFIXES for side in snapshots},
        **{f"{side}_{suffix}_{side}": snapshots[side][f"context_{suffix}"] for suffix in CONTEXT_FEATURE_SUFFIXES for side in snapshots},
        **{f"{side}_{suffix}": table_snapshots[side][suffix] for suffix in ("season_points_before", "season_goal_diff_before", "season_position_before") for side in snapshots},
        **{f"{side}_{suffix}": snapshots[side][suffix] for suffix in ("goal_diff_last_5", "goal_diff_last_3") for side in snapshots},
        **{column: snapshots["home"][DIFF_SOURCE_KEYS[column]] - snapshots["away"][DIFF_SOURCE_KEYS[column]] for column in DIFF_FEATURE_COLUMNS},
        "diff_season_points_before": home_table_snapshot["season_points_before"] - away_table_snapshot["season_points_before"],
        "diff_season_goal_diff_before": home_table_snapshot["season_goal_diff_before"] - away_table_snapshot["season_goal_diff_before"],
        "diff_season_position_before": away_table_snapshot["season_position_before"] - home_table_snapshot["season_position_before"],
        **get_league_flag_features(league_id),
    }


def build_feature_row(
    fixture: pd.Series,
    home_snapshot: dict,
    away_snapshot: dict,
    home_table_snapshot: dict,
    away_table_snapshot: dict,
) -> dict:
    """Vytvori jeden trenovaci radek vcetne targetu pro zapas."""
    home_goals = int(fixture["home_goals"])
    away_goals = int(fixture["away_goals"])
    league_id = int(fixture["league_id"])

    return {
        "league_id": league_id,
        "league_name": fixture["league_name"],
        "season": int(fixture["season"]),
        "utc_date": fixture["utc_date"],
        "fixture_id": int(fixture["fixture_id"]),
        "home_team_id": int(fixture["home_team_id"]),
        "home_team_name": fixture["home_team_name"],
        "away_team_id": int(fixture["away_team_id"]),
        "away_team_name": fixture["away_team_name"],
        "home_goals": home_goals,
        "away_goals": away_goals,
        "winner_target": get_winner_from_goals(home_goals, away_goals),
        "target_home_goals": home_goals,
        "target_away_goals": away_goals,
        **build_feature_values(
            home_snapshot,
            away_snapshot,
            home_table_snapshot,
            away_table_snapshot,
            league_id,
        ),
    }
