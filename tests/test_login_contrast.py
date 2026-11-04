"""La page de connexion doit rester lisible : texte blanc sur l'accent assombri (WCAG AA)."""

import re
from pathlib import Path

import pytest

CSS = Path(__file__).resolve().parent.parent / "frontend" / "css" / "app.css"
LOGIN = Path(__file__).resolve().parent.parent / "frontend" / "login.html"


def _luminance(rgb):
    def chan(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hex(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _mix_with_black(accent, percent):
    return tuple(c * percent / 100 for c in _hex(accent))


def _accent_share():
    css = CSS.read_text(encoding="utf-8")
    pattern = (r"\.login-art \{[^}]*background: "
               r"color-mix\(in srgb, var\(--accent\) (\d+)%, #000\)")
    match = re.search(pattern, css)
    assert match, "le panneau de connexion doit assombrir l'accent avec color-mix(... #000)"
    return int(match.group(1))


ACCENTS = ["#0D9488", "#2563EB", "#DC2626", "#7C3AED", "#D97706", "#16A34A"]


@pytest.mark.parametrize("accent", ACCENTS)
def test_login_panel_text_is_readable(accent):
    background = _mix_with_black(accent, _accent_share())
    white = (255, 255, 255)
    # Le petit texte (copyright) est à 92 % d'opacité : on teste la couleur affichée.
    shown = tuple(0.92 * 255 + 0.08 * c for c in background)
    assert _ratio(white, background) >= 4.5
    assert _ratio(shown, background) >= 4.5


def test_login_year_label_keeps_high_opacity():
    html = LOGIN.read_text(encoding="utf-8")
    opacity = float(re.search(r'opacity: (\.\d+);" id="year"', html).group(1))
    assert opacity >= 0.9
