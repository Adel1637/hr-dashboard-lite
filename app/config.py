"""Configuration centralisée (édition Lite).

Toute valeur réglable (identité, couleur, sécurité, modules, chemins) est lue ici,
depuis les variables d'environnement ou un fichier `.env`. Aucun autre fichier
ne doit contenir de valeur en dur : l'interface et les graphiques lisent la
couleur d'accent via `settings.accent`.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

log = logging.getLogger("kit.config")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
LOCALES_DIR = BASE_DIR / "locales"

# Édition Lite : un seul module. Les autres sont présentés comme modules Pro.
MODULES = ("effectifs",)
PRO_MODULES = ("mouvements", "demographie", "formation")
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _load_dotenv(path: Path) -> None:
    """Charge un fichier .env minimal (CLE=valeur) sans écraser l'environnement."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        log.warning("%s invalide, valeur par défaut %s utilisée", name, default)
        return default


@dataclass(frozen=True)
class Settings:
    env: str
    app_name: str
    company: str
    accent: str
    logo: str
    default_lang: str
    pro_url: str
    show_pro_hints: bool
    jwt_secret: str
    jwt_expire_minutes: int
    admin_username: str
    admin_password: str
    cors_origins: tuple[str, ...]
    rate_limit_login: int
    rate_limit_upload: int
    data_dir: Path
    max_upload_mb: int
    cache_ttl_seconds: int
    languages: tuple[str, ...] = field(default=("fr", "en"))

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def public(self) -> dict:
        """Ce que l'interface a le droit de connaître (aucun secret)."""
        return {
            "app_name": self.app_name,
            "company": self.company,
            "accent": self.accent,
            "logo": self.logo,
            "default_lang": self.default_lang,
            "languages": list(self.languages),
            "edition": "lite",
            "pro_url": self.pro_url,
            "show_pro_hints": self.show_pro_hints,
        }


def build_settings() -> Settings:
    _load_dotenv(BASE_DIR / ".env")
    env = os.environ.get("APP_ENV", "development").lower()

    accent = os.environ.get("APP_ACCENT", "#0D9488")
    if not _HEX_COLOR.match(accent):
        log.warning("APP_ACCENT doit être une couleur #RRGGBB ; #0D9488 utilisé")
        accent = "#0D9488"

    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < 32:
        if env == "production":
            raise RuntimeError(
                "JWT_SECRET est absent ou trop court (32 caractères minimum) en production."
            )
        log.warning("JWT_SECRET absent : clé temporaire générée (sessions perdues au redémarrage)")
        secret = secrets.token_urlsafe(48)

    lang = os.environ.get("APP_DEFAULT_LANG", "fr")
    data_dir = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
    if not data_dir.is_absolute():
        data_dir = (BASE_DIR / data_dir).resolve()

    return Settings(
        env=env,
        app_name=os.environ.get("APP_NAME", "Dashboard RH"),
        company=os.environ.get("APP_COMPANY", ""),
        accent=accent.upper(),
        logo=os.environ.get("APP_LOGO", ""),
        default_lang=lang if lang in ("fr", "en") else "fr",
        pro_url=os.environ.get("PRO_URL", "").strip(),
        show_pro_hints=os.environ.get("SHOW_PRO_HINTS", "true").lower() in ("1", "true", "yes"),
        jwt_secret=secret,
        jwt_expire_minutes=_int("JWT_EXPIRE_MINUTES", 60),
        admin_username=os.environ.get("ADMIN_USERNAME", "admin"),
        admin_password=os.environ.get("ADMIN_PASSWORD", ""),
        cors_origins=tuple(_list(os.environ.get("CORS_ORIGINS", ""))),
        rate_limit_login=_int("RATE_LIMIT_LOGIN", 5),
        rate_limit_upload=_int("RATE_LIMIT_UPLOAD", 10),
        data_dir=data_dir,
        max_upload_mb=_int("MAX_UPLOAD_MB", 25),
        cache_ttl_seconds=_int("CACHE_TTL_SECONDS", 600),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Réglages chargés une seule fois par processus (immuables)."""
    return build_settings()
