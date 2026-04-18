from src.config import DATA_DIR, MODELS_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR


def ensure_project_directories() -> None:
    """Vytvori zakladni slozky projektu, pokud jeste neexistuji."""
    for path in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def get_winner_from_goals(home_goals: int, away_goals: int) -> str:
    """Vrati viteze podle poctu golu."""
    return "HOME" if home_goals > away_goals else "AWAY" if home_goals < away_goals else "DRAW"


def normalize_fixture_winner(
    home_winner: object,
    away_winner: object,
    home_goals: object,
    away_goals: object,
) -> str:
    """Prevede API-Football winner hodnoty na HOME / DRAW / AWAY."""
    if home_winner is True:
        return "HOME"
    if away_winner is True:
        return "AWAY"

    if home_goals is None or away_goals is None:
        return ""

    try:
        return get_winner_from_goals(int(home_goals), int(away_goals))
    except (TypeError, ValueError):
        return ""
