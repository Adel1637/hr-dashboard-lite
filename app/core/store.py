"""Stockage des jeux de données importés.

Chaque jeu est enregistré au format canonique (CSV UTF-8) dans DATA_DIR,
avec ses métadonnées et le mapping utilisé. Le numéro de `version` augmente
à chaque import : il sert de clé d'invalidation au cache des indicateurs.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.schemas import SCHEMAS


class DataStore:
    def __init__(self, data_dir: Path) -> None:
        self.dir = data_dir / "datasets"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._meta_path = self.dir / "meta.json"
        self._mappings_path = self.dir / "mappings.json"
        self._frames: dict[str, pd.DataFrame] = {}
        self._lock = threading.RLock()
        self.version = 0
        self._meta = self._read_json(self._meta_path)
        self._mappings = self._read_json(self._mappings_path)
        for key in SCHEMAS:
            self._load_from_disk(key)

    # -- persistance -------------------------------------------------
    @staticmethod
    def _read_json(path: Path) -> dict:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _csv_path(self, key: str) -> Path:
        return self.dir / f"{key}.csv"

    def _load_from_disk(self, key: str) -> None:
        path = self._csv_path(key)
        if not path.is_file():
            return
        frame = pd.read_csv(path, dtype=str, keep_default_na=True)
        for f in SCHEMAS[key].fields:
            if f.key not in frame.columns:
                frame[f.key] = pd.NA
            elif f.type == "date":
                frame[f.key] = pd.to_datetime(frame[f.key], format="%Y-%m-%d", errors="coerce")
            elif f.type == "number":
                frame[f.key] = pd.to_numeric(frame[f.key], errors="coerce")
        self._frames[key] = frame
        self.version += 1

    # -- API publique ------------------------------------------------
    def get(self, key: str) -> pd.DataFrame | None:
        with self._lock:
            return self._frames.get(key)

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def save(self, key: str, frame: pd.DataFrame, *, filename: str, user: str,
             mapping: dict, signature: str) -> None:
        with self._lock:
            out = frame.copy()
            for f in SCHEMAS[key].fields:
                if f.type == "date":
                    out[f.key] = out[f.key].dt.strftime("%Y-%m-%d")
            tmp = self._csv_path(key).with_suffix(".tmp")
            out.to_csv(tmp, index=False, encoding="utf-8")
            tmp.replace(self._csv_path(key))
            self._frames[key] = frame
            self._meta[key] = {
                "filename": filename,
                "rows": len(frame),
                "imported_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "imported_by": user,
            }
            self._mappings[signature] = {"dataset": key, "mapping": mapping}
            self._write_json(self._meta_path, self._meta)
            self._write_json(self._mappings_path, self._mappings)
            self.version += 1

    def saved_mapping(self, key: str, signature: str) -> dict | None:
        entry = self._mappings.get(signature)
        if entry and entry.get("dataset") == key:
            return entry["mapping"]
        return None

    def meta(self) -> dict:
        with self._lock:
            return {key: self._meta.get(key) if key in self._frames else None for key in SCHEMAS}
