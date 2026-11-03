"""Composants Plotly réutilisables.

Les figures sont neutres : fond transparent et aucune couleur de texte en dur.
L'interface applique ensuite les couleurs du thème clair ou sombre. La seule
couleur imposée ici est l'accent configuré, plus une palette secondaire sobre.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import plotly.graph_objects as go
import plotly.io as pio

NEUTRAL = "#94A3B8"
SECONDARY = ("#6366F1", "#F59E0B", "#EC4899", "#10B981", "#8B5CF6", "#64748B")
FONT = "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"


def palette(accent: str) -> list[str]:
    return [accent, *SECONDARY]


def _layout(fig: go.Figure, **extra) -> go.Figure:
    layout = {
        "margin": {"l": 8, "r": 8, "t": 8, "b": 8},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": FONT, "size": 12},
        "hoverlabel": {"font": {"family": FONT}},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        "showlegend": False,
    }
    fig.update_layout(**{**layout, **extra})
    fig.update_xaxes(automargin=True, zeroline=False)
    fig.update_yaxes(automargin=True, zeroline=False)
    return fig


def to_json(fig: go.Figure) -> dict:
    """Dictionnaire 100 % JSON (types NumPy convertis), prêt pour l'API."""
    return json.loads(pio.to_json(fig, validate=False))


def line(x: Sequence, y: Sequence, accent: str, name: str = "", zero: bool = False) -> dict:
    """Courbe mensuelle. Sans `zero`, l'axe s'ajuste aux valeurs pour rendre
    lisibles des variations faibles (cas typique d'un effectif)."""
    values = list(y)
    fig = go.Figure(go.Scatter(
        x=list(x), y=values, name=name, mode="lines+markers",
        line={"color": accent, "width": 2.5, "shape": "spline", "smoothing": 0.6},
        marker={"size": 7, "color": accent, "line": {"width": 2, "color": "rgba(255,255,255,0.9)"}},
        fill="tozeroy" if zero else None, fillcolor=_alpha(accent, 0.10),
        hovertemplate="%{x|%b %Y}<br><b>%{y:,}</b><extra></extra>",
    ))
    yaxis: dict = {"rangemode": "tozero", "tickformat": ",d"}
    if not zero and values:
        low, high = min(values), max(values)
        pad = max((high - low) * 0.35, high * 0.02, 1)
        yaxis = {"range": [max(0, low - pad), high + pad], "tickformat": ",d"}
    return to_json(_layout(fig, yaxis=yaxis))


def bar_h(labels: Sequence, values: Sequence, accent: str, value_format: str = ",") -> dict:
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h", marker={"color": accent},
        text=list(values), texttemplate=f"%{{x:{value_format}}}", textposition="outside",
        cliponaxis=False, hovertemplate=f"%{{y}}<br><b>%{{x:{value_format}}}</b><extra></extra>",
    ))
    peak = max([float(v) for v in values] + [0])
    # Marge à droite pour que l'étiquette de la plus grande barre reste visible.
    fig.update_xaxes(range=[0, peak * 1.18 or 1], tickformat=",")
    fig.update_yaxes(autorange="reversed")
    return to_json(_layout(fig, bargap=0.35))



def donut(labels: Sequence, values: Sequence, accent: str) -> dict:
    fig = go.Figure(go.Pie(
        labels=list(labels), values=list(values), hole=0.62, sort=False,
        marker={"colors": palette(accent)[: len(labels)]},
        textinfo="percent",
        hovertemplate="%{label}<br><b>%{value:,}</b> · %{percent}<extra></extra>",
    ))
    return to_json(_layout(fig, showlegend=True,
                           legend={"orientation": "v", "x": 1, "y": 0.5}))






def _alpha(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"
