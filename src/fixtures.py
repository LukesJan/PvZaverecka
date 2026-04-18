from pathlib import Path

import pandas as pd

from src.config import DEFAULT_SEASONS, RAW_DATA_DIR

FIXTURE_NUMERIC_COLUMNS = "league_id season fixture_id timestamp elapsed home_team_id away_team_id home_goals away_goals".split()
BASE_REQUIRED_COLUMNS = "league_id league_name season fixture_id utc_date home_team_id home_team_name away_team_id away_team_name".split()


def list_raw_csv_files() -> list[Path]:
    """Najde raw CSV soubory pro aktualne povolene sezony."""
    return sorted(
        file_path
        for file_path in RAW_DATA_DIR.glob("*_fixtures.csv")
        if (parts := file_path.stem.split("_")) and len(parts) >= 3 and parts[1].isdigit() and int(parts[1]) in DEFAULT_SEASONS
    )


def load_raw_data() -> pd.DataFrame:
    """Nacte a spoji raw fixture CSV soubory do jednoho dataframe."""
    files = list_raw_csv_files()
    if not files:
        raise FileNotFoundError(
            "Ve slozce data/raw nebyly nalezeny zadne CSV soubory. Nejdriv spust crawler."
        )

    frames = []
    for file_path in files:
        try:
            frame = pd.read_csv(file_path)
            frames.append(frame)
            print(f"Nacten soubor {file_path.name} ({len(frame)} radku)")
        except Exception as error:
            print(f"Soubor {file_path.name} se nepodarilo nacist: {error}")

    if not frames:
        raise ValueError("Nepodarilo se nacist zadny platny raw CSV soubor.")

    combined = pd.concat(frames, ignore_index=True)
    combined["season"] = pd.to_numeric(combined.get("season"), errors="coerce")
    combined = combined[combined["season"].isin(DEFAULT_SEASONS)].copy()

    if combined.empty:
        raise ValueError("Po aplikaci filtru sezon nezustala zadna raw data.")

    return combined.reset_index(drop=True)


def prepare_fixtures(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Pripravi raw fixtures pro runtime predikce."""
    prepared = dataframe.copy()
    prepared["utc_date"] = pd.to_datetime(prepared["utc_date"], utc=True, errors="coerce")

    for column in FIXTURE_NUMERIC_COLUMNS:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")

    prepared = prepared.drop_duplicates(subset=["fixture_id"]).copy()
    prepared = prepared.dropna(subset=BASE_REQUIRED_COLUMNS + ["status_short"]).copy()

    integer_columns = ["league_id", "season", "fixture_id", "home_team_id", "away_team_id"]
    for column in integer_columns:
        prepared[column] = prepared[column].astype(int)

    return prepared.sort_values(["utc_date", "fixture_id"]).reset_index(drop=True)
