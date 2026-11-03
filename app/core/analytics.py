"""Point d'entrée du calcul : filtres + cache + module demandé."""

from __future__ import annotations

from app.config import MODULES, PRO_MODULES, Settings
from app.core.cache import TTLCache
from app.core.filters import Filters, apply_filters
from app.core.modules import REGISTRY, Context
from app.core.store import DataStore
from app.i18n import translator


class ModuleUnavailable(LookupError):
    pass


class Analytics:
    def __init__(self, store: DataStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self.cache = TTLCache(settings.cache_ttl_seconds)

    def available_modules(self) -> list[dict]:
        out = []
        for key in MODULES:
            module = REGISTRY[key]
            missing = [d for d in module.requires if not self.store.has(d)]
            out.append({"key": key, "ready": not missing, "missing": missing})
        if self.settings.show_pro_hints:
            out += [{"key": key, "ready": False, "missing": [], "pro": True} for key in PRO_MODULES]
        return out

    def run(self, key: str, filters: Filters, lang: str) -> dict:
        if key in PRO_MODULES:
            raise ModuleUnavailable(f"Le module {key} est disponible dans la version Pro.")
        if key not in REGISTRY:
            raise ModuleUnavailable(f"Module inconnu : {key}")
        module = REGISTRY[key]
        missing = [d for d in module.requires if not self.store.has(d)]
        if missing:
            raise ModuleUnavailable("Données manquantes : " + ", ".join(missing))

        cache_key = (key, filters, lang, self.store.version)

        def compute() -> dict:
            personnel = apply_filters(self.store.get("personnel"), filters)
            ctx = Context(personnel=personnel, filters=filters,
                          accent=self.settings.accent, t=translator(lang))
            result = module.compute(ctx)
            result["period"] = {"start": filters.period_start.date().isoformat(),
                                "end": filters.period_end.date().isoformat()}
            return result

        return self.cache.get_or_compute(cache_key, compute)

    def invalidate(self) -> None:
        self.cache.clear()
