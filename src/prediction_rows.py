from collections import defaultdict, deque

import numpy as np
import pandas as pd

from src.config import DEFAULT_LEAGUES, FINISHED_STATUS_SHORTS, UPCOMING_STATUS_SHORTS
from src.feature_snapshots import (
    build_feature_values,
    build_table_positions,
    build_table_snapshot,
    build_team_snapshot,
)
from src.feature_updates import apply_pending_updates, build_finished_match_updates


def new_history() -> defaultdict:
    """Vytvori historii poslednich peti zapasu."""
    return defaultdict(lambda: deque(maxlen=5))


def new_totals(include_matches: bool = True) -> defaultdict:
    """Vytvori souhrnne tymove statistiky."""
    base = {"goals_scored": 0, "goals_conceded": 0, "points": 0}
    if include_matches:
        base["matches"] = 0
    return defaultdict(lambda: base.copy())


def new_season_tables() -> defaultdict:
    """Vytvori ligove tabulky pro kazdou sezonu."""
    return defaultdict(lambda: new_totals(include_matches=False))


def collect_upcoming_feature_rows(fixtures: pd.DataFrame) -> pd.DataFrame:
    """Sestavi feature radky pro vsechny budouci zapasy."""
    last_five_history, home_last_five_history, away_last_five_history = [new_history() for _ in range(3)]
    team_totals, home_team_totals, away_team_totals = [new_totals() for _ in range(3)]
    last_match_dates = {}
    season_tables = new_season_tables()
    prediction_rows = []

    for _, same_time_fixtures in fixtures.groupby("utc_date", sort=True):
        pending_updates = []
        season_keys = same_time_fixtures[["league_id", "season"]].drop_duplicates()
        season_positions = {
            (int(row.league_id), int(row.season)): build_table_positions(
                season_tables[(int(row.league_id), int(row.season))]
            )
            for row in season_keys.itertuples(index=False)
        }

        for _, fixture in same_time_fixtures.iterrows():
            home_team_id = int(fixture["home_team_id"])
            away_team_id = int(fixture["away_team_id"])
            league_id = int(fixture["league_id"])
            season = int(fixture["season"])
            home_snapshot = build_team_snapshot(
                home_team_id,
                fixture["utc_date"],
                last_five_history,
                team_totals,
                last_match_dates,
                home_last_five_history,
                home_team_totals,
            )
            away_snapshot = build_team_snapshot(
                away_team_id,
                fixture["utc_date"],
                last_five_history,
                team_totals,
                last_match_dates,
                away_last_five_history,
                away_team_totals,
            )
            home_table_snapshot = build_table_snapshot(
                league_id, season, home_team_id, season_tables, season_positions
            )
            away_table_snapshot = build_table_snapshot(
                league_id, season, away_team_id, season_tables, season_positions
            )

            if fixture["status_short"] in UPCOMING_STATUS_SHORTS:
                prediction_rows.append(
                    {
                        "league_id": league_id,
                        "league_name": fixture["league_name"],
                        "season": int(fixture["season"]),
                        "utc_date": fixture["utc_date"],
                        "fixture_id": int(fixture["fixture_id"]),
                        "status_short": fixture["status_short"],
                        "round": fixture.get("round", ""),
                        "home_team_id": home_team_id,
                        "home_team_name": fixture["home_team_name"],
                        "away_team_id": away_team_id,
                        "away_team_name": fixture["away_team_name"],
                        **build_feature_values(
                            home_snapshot,
                            away_snapshot,
                            home_table_snapshot,
                            away_table_snapshot,
                            league_id,
                        ),
                    }
                )

            if fixture["status_short"] in FINISHED_STATUS_SHORTS and pd.notna(fixture["home_goals"]) and pd.notna(fixture["away_goals"]):
                pending_updates.extend(
                    build_finished_match_updates(
                        league_id=league_id,
                        season=season,
                        home_team_id=home_team_id,
                        away_team_id=away_team_id,
                        home_goals=int(fixture["home_goals"]),
                        away_goals=int(fixture["away_goals"]),
                        match_date=fixture["utc_date"],
                    )
                )

        apply_pending_updates(
            pending_updates,
            last_five_history,
            team_totals,
            last_match_dates,
            home_last_five_history,
            home_team_totals,
            away_last_five_history,
            away_team_totals,
            season_tables,
        )

    return pd.DataFrame(prediction_rows)


def collect_last_completed_round_rows(
    fixtures: pd.DataFrame,
    final_dataset: pd.DataFrame,
) -> pd.DataFrame:
    """Najde posledni dokoncene kolo a vrati jeho feature radky s realitou."""
    if final_dataset.empty:
        return pd.DataFrame()

    current_utc = pd.Timestamp.now(tz="UTC")
    history_rows = []

    for league_id in DEFAULT_LEAGUES:
        league_fixtures = fixtures[fixtures["league_id"] == league_id].copy()
        if league_fixtures.empty:
            continue

        latest_season = int(league_fixtures["season"].max())
        season_fixtures = league_fixtures[league_fixtures["season"] == latest_season].copy()
        completed_rounds = []

        for round_name, round_frame in season_fixtures.groupby("round", dropna=True):
            if round_name and round_frame["utc_date"].max() < current_utc and round_frame["status_short"].isin(FINISHED_STATUS_SHORTS).all():
                completed_rounds.append((round_frame["utc_date"].max(), round_name))

        if not completed_rounds:
            continue

        _, last_round = max(completed_rounds, key=lambda item: item[0])
        last_round_fixtures = season_fixtures[
            (season_fixtures["round"] == last_round)
            & (season_fixtures["status_short"].isin(FINISHED_STATUS_SHORTS))
        ].copy()
        if last_round_fixtures.empty:
            continue

        round_dataset = final_dataset.merge(
            last_round_fixtures[["fixture_id", "round", "status_short", "home_goals", "away_goals"]],
            on="fixture_id",
            how="inner",
            suffixes=("", "_raw"),
        )
        if round_dataset.empty:
            continue

        round_dataset["actual_home_goals"] = round_dataset["home_goals_raw"].astype(int)
        round_dataset["actual_away_goals"] = round_dataset["away_goals_raw"].astype(int)
        round_dataset["actual_winner"] = np.select(
            [
                round_dataset["actual_home_goals"] > round_dataset["actual_away_goals"],
                round_dataset["actual_home_goals"] < round_dataset["actual_away_goals"],
            ],
            ["HOME", "AWAY"],
            default="DRAW",
        )
        history_rows.append(round_dataset)

    if not history_rows:
        return pd.DataFrame()

    return pd.concat(history_rows, ignore_index=True).sort_values(
        ["utc_date", "fixture_id"]
    ).reset_index(drop=True)
