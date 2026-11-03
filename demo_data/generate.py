"""Génère des fichiers du personnel fictifs pour la démonstration.

Exemples :
    python demo_data/generate.py                 # 50, 1 000 et 20 000 salariés
    python demo_data/generate.py --size 3000     # un seul jeu
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.demo import generate_personnel, write_xlsx  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--size", type=int, action="append",
                        help="Effectif approximatif (répétable)")
    parser.add_argument("--end", type=date.fromisoformat, default=date.today(),
                        help="Date de fin de l'historique (AAAA-MM-JJ)")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for size in args.size or [50, 1000, 20000]:
        personnel = generate_personnel(size, end=args.end)
        path = args.out / f"personnel_demo_{size}.xlsx"
        write_xlsx(personnel, path, "Fichier du personnel — données fictives")
        print(f"{size:>6} salariés → {path.name} ({len(personnel)} lignes)")


if __name__ == "__main__":
    main()
