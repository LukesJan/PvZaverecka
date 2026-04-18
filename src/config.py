from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

API_BASE_URL = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")
API_KEY = os.getenv("API_FOOTBALL_KEY", "")

REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
REQUEST_RETRIES = int(os.getenv("REQUEST_RETRIES", "3"))
REQUEST_SLEEP_SECONDS = float(os.getenv("REQUEST_SLEEP_SECONDS", "2"))

DEFAULT_LEAGUES = [39, 78, 61, 135, 140]
DEFAULT_SEASONS = [2020, 2021, 2022, 2023, 2024, 2025]

LEAGUE_NAMES = {
    39: "Premier League",
    78: "Bundesliga",
    61: "Ligue 1",
    135: "Serie A",
    140: "La Liga",
}

FINISHED_STATUS_SHORTS = {"FT"}
UPCOMING_STATUS_SHORTS = {"NS", "TBD", "PST"}

RAW_FIXTURE_COLUMNS = """
league_id league_name country_name season fixture_id utc_date timezone timestamp
status_long status_short elapsed round home_team_id home_team_name away_team_id
away_team_name home_goals away_goals winner venue_id venue_name referee
""".split()

SIDES = ("home", "away")
LEAGUE_FLAGS = {
    39: "is_premier_league",
    78: "is_bundesliga",
    61: "is_ligue_1",
    135: "is_serie_a",
    140: "is_la_liga",
}

TEAM_FEATURE_SUFFIXES = """
points_last_5 goals_scored_last_5 goals_conceded_last_5 wins_last_5 draws_last_5
losses_last_5 rest_days points_last_3 goals_scored_last_3 goals_conceded_last_3
wins_last_3 draws_last_3 losses_last_3 matches_played_before avg_points_before
avg_goals_scored_before avg_goals_conceded_before
""".split()

CONTEXT_FEATURE_SUFFIXES = """
points_last_5 points_last_3 goals_scored_last_3 goals_conceded_last_3
avg_goals_scored_before avg_goals_conceded_before
""".split()

DIFF_FEATURE_COLUMNS = """
diff_points_last_5 diff_points_last_3 diff_avg_points_before diff_goals_scored_last_5
diff_goals_conceded_last_5 diff_goal_diff_last_5 diff_goal_diff_last_3
diff_home_away_points_last_3 diff_home_away_goal_diff_last_3 diff_rest_days diff_wins_last_5
""".split()

GOAL_FEATURE_COLUMNS = [
    *[f"{side}_{suffix}" for suffix in TEAM_FEATURE_SUFFIXES for side in SIDES],
    *[f"{side}_{suffix}_{side}" for suffix in CONTEXT_FEATURE_SUFFIXES for side in SIDES],
    *[f"{side}_{suffix}" for suffix in ("goal_diff_last_5", "goal_diff_last_3") for side in SIDES],
    *DIFF_FEATURE_COLUMNS,
    *LEAGUE_FLAGS.values(),
]

WINNER_EXTRA_FEATURE_COLUMNS = """
home_season_points_before away_season_points_before home_season_goal_diff_before
away_season_goal_diff_before home_season_position_before away_season_position_before
diff_season_points_before diff_season_goal_diff_before diff_season_position_before
""".split()

WINNER_FEATURE_COLUMNS = GOAL_FEATURE_COLUMNS + WINNER_EXTRA_FEATURE_COLUMNS

UPCOMING_PREDICTIONS_PATH = PROCESSED_DATA_DIR / "upcoming_predictions.json"
