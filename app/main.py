"""Point d'entrée ASGI.

Développement :  uvicorn app.main:app --reload
Production   :  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from app.factory import __version__, create_app

app = create_app()

__all__ = ["__version__", "app"]
