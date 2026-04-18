POINTS = {"WIN": 3, "DRAW": 1, "LOSS": 0}


def build_finished_match_updates(
    league_id: int,
    season: int,
    home_team_id: int,
    away_team_id: int,
    home_goals: int,
    away_goals: int,
    match_date,
) -> list[dict]:
    """Vytvori aktualizace historie pro oba tymy po odehranem zapase."""
    home_result, away_result = ("WIN", "LOSS") if home_goals > away_goals else ("LOSS", "WIN") if home_goals < away_goals else ("DRAW", "DRAW")
    return [
        {
            "league_id": league_id,
            "season": season,
            "team_id": team_id,
            "goals_scored": scored,
            "goals_conceded": conceded,
            "result": result,
            "context": context,
            "match_date": match_date,
        }
        for team_id, scored, conceded, result, context in (
            (home_team_id, home_goals, away_goals, home_result, "home"),
            (away_team_id, away_goals, home_goals, away_result, "away"),
        )
    ]


def apply_single_update(update: dict, last_five_history: dict, team_totals: dict) -> None:
    """Zapise jeden zapas do historie a souhrnnych statistik tymu."""
    team_id = update["team_id"]
    result = update["result"]
    goals_scored = update["goals_scored"]
    goals_conceded = update["goals_conceded"]
    points = POINTS[result]

    last_five_history[team_id].append(
        {
            "points": points,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "wins": 1 if result == "WIN" else 0,
            "draws": 1 if result == "DRAW" else 0,
            "losses": 1 if result == "LOSS" else 0,
        }
    )
    team_totals[team_id]["matches"] += 1
    team_totals[team_id]["goals_scored"] += goals_scored
    team_totals[team_id]["goals_conceded"] += goals_conceded
    team_totals[team_id]["points"] += points


def apply_pending_updates(
    pending_updates: list[dict],
    last_five_history: dict,
    team_totals: dict,
    last_match_dates: dict,
    home_last_five_history: dict,
    home_team_totals: dict,
    away_last_five_history: dict,
    away_team_totals: dict,
    season_tables: dict,
) -> None:
    """Aplikuje vsechny odlozene aktualizace po dokonceni casove skupiny."""
    for update in pending_updates:
        apply_single_update(update, last_five_history, team_totals)
        last_match_dates[update["team_id"]] = update["match_date"]

        if update["context"] == "home":
            apply_single_update(update, home_last_five_history, home_team_totals)
        else:
            apply_single_update(update, away_last_five_history, away_team_totals)

        season_row = season_tables[(update["league_id"], update["season"])][update["team_id"]]
        season_row["points"] += POINTS[update["result"]]
        season_row["goals_scored"] += update["goals_scored"]
        season_row["goals_conceded"] += update["goals_conceded"]
