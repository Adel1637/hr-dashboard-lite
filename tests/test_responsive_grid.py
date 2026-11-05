"""Sur écran étroit, les grilles à une colonne doivent pouvoir rétrécir (minmax(0, 1fr)).

Avec « 1fr » seul, une table large (aperçu de l'import) élargit la carte et la page déborde :
les listes de correspondance des colonnes sont alors coupées sur téléphone.
"""

import re
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "frontend" / "css" / "app.css"


def test_narrow_screen_grids_can_shrink():
    css = CSS.read_text(encoding="utf-8")
    match = re.search(
        r"@media \(max-width: 1100px\) \{(?P<body>.*?)\n\}", css, flags=re.S)
    assert match, "bloc @media (max-width: 1100px) introuvable"
    rule = re.search(r"\.import-grid[^{]*\{([^}]*)\}", match.group("body"))
    assert rule, "règle .import-grid introuvable dans le bloc écrans étroits"
    assert "grid-template-columns: minmax(0, 1fr)" in rule.group(1)
