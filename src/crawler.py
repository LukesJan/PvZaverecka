import argparse
import time

import pandas as pd
import requests

from src.config import (
    API_BASE_URL,
    API_KEY,
    DEFAULT_LEAGUES,
    DEFAULT_SEASONS,
    RAW_DATA_DIR,
    RAW_FIXTURE_COLUMNS,
    REQUEST_RETRIES,
    REQUEST_SLEEP_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
)
from src.utils import ensure_project_directories, normalize_fixture_winner


def parse_args() -> argparse.Namespace:
    """Nacte argumenty pro stazeni fixtures z API-Football."""
    parser = argparse.ArgumentParser(
        description="Stahne fixtures z API-Football a ulozi je do CSV."
    )
    parser.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        default=DEFAULT_SEASONS,
        help="Sezony, ktere se maji stahnout.",
    )
    parser.add_argument(
        "--leagues",
        nargs="+",
        type=int,
        default=DEFAULT_LEAGUES,
        help="League ID, ktere se maji stahnout.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Pokud je nastaveno, prepise existujici CSV soubory.",
    )
    return parser.parse_args()

def get_fixtures(session: requests.Session, league_id: int, season: int) -> list[dict]:
    """Stahne fixtures z API-Football pro jednu ligu a sezonu."""
    url = f"{API_BASE_URL.rstrip('/')}/fixtures"
    last_error = None

    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            response = session.get(
                url,
                params={"league": league_id, "season": season},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json().get("response", [])
        except requests.RequestException as error:
            last_error = error
            if attempt == REQUEST_RETRIES:
                break
            time.sleep(REQUEST_SLEEP_SECONDS * attempt)

    raise RuntimeError(f"API request failed for league {league_id} season {season}") from last_error


def flatten_fixture(fixture_data: dict) -> dict:
    """Prevede jednu API-Football fixture odpoved na plochy CSV radek."""
    fixture = fixture_data.get("fixture", {}) or {}
    league = fixture_data.get("league", {}) or {}
    teams = fixture_data.get("teams", {}) or {}
    goals = fixture_data.get("goals", {}) or {}

    home_team = teams.get("home", {}) or {}
    away_team = teams.get("away", {}) or {}
    status = fixture.get("status", {}) or {}
    venue = fixture.get("venue", {}) or {}

    return {
        "league_id": league.get("id"),
        "league_name": league.get("name"),
        "country_name": league.get("country"),
        "season": league.get("season"),
        "fixture_id": fixture.get("id"),
        "utc_date": fixture.get("date"),
        "timezone": fixture.get("timezone"),
        "timestamp": fixture.get("timestamp"),
        "status_long": status.get("long"),
        "status_short": status.get("short"),
        "elapsed": status.get("elapsed"),
        "round": league.get("round"),
        "home_team_id": home_team.get("id"),
        "home_team_name": home_team.get("name"),
        "away_team_id": away_team.get("id"),
        "away_team_name": away_team.get("name"),
        "home_goals": goals.get("home"),
        "away_goals": goals.get("away"),
        "winner": normalize_fixture_winner(
            home_winner=home_team.get("winner"),
            away_winner=away_team.get("winner"),
            home_goals=goals.get("home"),
            away_goals=goals.get("away"),
        ),
        "venue_id": venue.get("id"),
        "venue_name": venue.get("name"),
        "referee": fixture.get("referee"),
    }


def crawl_fixtures(
    seasons: list[int],
    leagues: list[int],
    overwrite: bool = False,
) -> None:
    """Stahne a ulozi fixtures pro vybrane ligy a sezony."""
    ensure_project_directories()
    if not API_KEY:
        raise ValueError("Chybi API_FOOTBALL_KEY v .env souboru.")

    session = requests.Session()
    session.headers.update({"x-apisports-key": API_KEY})

    for league_id in leagues:
        for season in seasons:
            output_path = RAW_DATA_DIR / f"{league_id}_{season}_fixtures.csv"

            if output_path.exists() and not overwrite:
                print(f"Preskakuji league {league_id} season {season}, soubor uz existuje.")
                continue

            try:
                fixtures = get_fixtures(session=session, league_id=league_id, season=season)
                rows = [flatten_fixture(fixture_data) for fixture_data in fixtures]
                dataframe = pd.DataFrame(rows, columns=RAW_FIXTURE_COLUMNS)
                dataframe.to_csv(output_path, index=False)
                print(f"Ulozeno {len(dataframe)} fixtures do {output_path.as_posix()}")
            except Exception as error:
                print(f"Chyba pri stahovani league {league_id} season {season}: {error}")


def main() -> None:
    """Spusti crawler z prikazove radky."""
    args = parse_args()
    crawl_fixtures(
        seasons=args.seasons,
        leagues=args.leagues,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
