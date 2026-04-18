import argparse

from src.prediction_export import export_upcoming_predictions_json


def parse_args() -> argparse.Namespace:
    """Nacte argumenty pro export predikci do JSON souboru."""
    parser = argparse.ArgumentParser(
        description="Nacte modely a vygeneruje JSON s budoucimi predikcemi pro frontend."
    )
    parser.add_argument(
        "--export-upcoming-json",
        action="store_true",
        help="Zpetna kompatibilita: export probiha i bez tohoto flagu.",
    )
    parser.add_argument(
        "--per-league",
        type=int,
        default=0,
        help="Kolik budoucich zapasu na ligu vyexportovat do JSON. 0 znamena vsechny.",
    )
    parser.add_argument(
        "--rounds-ahead",
        type=int,
        default=2,
        help="Kolik nejblizsich kol na ligu vyexportovat. 0 znamena vsechna dostupna kola.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Volitelna vystupni cesta pro JSON s budoucimi predikcemi.",
    )
    return parser.parse_args()


def main() -> None:
    """Spusti export predikci pro frontend z prikazove radky."""
    args = parse_args()
    output_path = export_upcoming_predictions_json(
        output_path=args.output,
        per_league=args.per_league,
        rounds_ahead=args.rounds_ahead,
    )
    print(f"JSON s budoucimi predikcemi byl ulozen do {output_path.as_posix()}")


if __name__ == "__main__":
    main()
