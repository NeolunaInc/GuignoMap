"""Backup helpers for GuignoMap (Windows-friendly, silent by default)."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Callable, Any, Optional
import os, shutil, logging

# --- Logging (désactivé par défaut) -------------------------------------------------
_LOG = logging.getLogger("guignomap.backup")
if os.getenv("GUIGNOMAP_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)
else:
    _LOG.addHandler(logging.NullHandler())

# --- Chemins par défaut --------------------------------------------------------------
DEFAULT_DB  = Path("guignomap/guigno_map.db")
DEFAULT_DIR = Path("backup")

class BackupManager:
    def __init__(self, db_path: Path = DEFAULT_DB, backup_dir: Path = DEFAULT_DIR, prefix: str = "db"):
        self.db_path   = Path(db_path)
        self.backup_dir= Path(backup_dir)
        self.prefix    = prefix
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_db(self, tag: Optional[str]=None) -> Optional[Path]:
        """Copie la DB si elle existe. Retourne le chemin du backup (ou None)."""
        if not self.db_path.exists():
            _LOG.debug("no DB file yet: %s", self.db_path)
            return None
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{self.prefix}_{ts}{'_'+tag if tag else ''}.db"
        dest = self.backup_dir / name
        shutil.copy2(self.db_path, dest)
        _LOG.debug("backup created: %s", dest)
        return dest

    def autorotate(self, keep: int = 10) -> None:
        """Garde seulement les N derniers backups."""
        files = sorted(self.backup_dir.glob(f"{self.prefix}_*.db"))
        for f in files[:-keep]:
            try:
                f.unlink()
                _LOG.debug("backup pruned: %s", f)
            except Exception:
                pass

    def create_backup(self, tag=None):
        """Alias pour backup_db() - compatibilité avec l'ancien code."""
        return self.backup_db(tag=tag)

    def list_backups(self):
        """Liste tous les backups triés par date décroissante."""
        pats = f"{self.prefix}_*.db"
        return sorted(self.backup_dir.glob(pats), key=lambda p: p.stat().st_mtime, reverse=True)

_manager: Optional[BackupManager] = None
def get_backup_manager() -> BackupManager:
    global _manager
    if _manager is None:
        _manager = BackupManager()
    return _manager

def auto_backup_before_critical(func: Callable[..., Any] | None = None, *, tag: Optional[str]=None, rotate_keep: int=10):
    """Décorateur: fait un backup avant d'exécuter la fonction (si DB présente)."""
    def _decorator(f: Callable[..., Any]):
        def _wrapped(*args, **kwargs):
            try:
                mgr = get_backup_manager()
                mgr.backup_db(tag=tag)
                mgr.autorotate(keep=rotate_keep)
            except Exception:
                # on ne bloque pas l'opération si le backup échoue
                _LOG.debug("backup step failed (ignored)", exc_info=True)
            return f(*args, **kwargs)
        return _wrapped
    return _decorator if func is None else _decorator(func)

# --- Wrappers silencieux (délèguent à db.* si dispo, sinon no-op) -------------------
def _call_db(name: str, *args, **kwargs):
    """Appelle guigno_map.db.<name> si présent; sinon no-op (retourne None)."""
    try:
        from guignomap import db  # import tardif pour éviter les cycles
    except Exception:
        _LOG.debug("db not importable yet; skipping %s", name)
        return None
    fn = getattr(db, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    _LOG.debug("db.%s not found; skipping", name)
    return None

@auto_backup_before_critical(tag="auto_import_streets")
def auto_import_streets(*args, **kwargs):
    return _call_db("auto_import_streets", *args, **kwargs)

@auto_backup_before_critical(tag="delete_team")
def delete_team(*args, **kwargs):
    return _call_db("delete_team", *args, **kwargs)

# Fonctions wrapper supprimées pour éviter la confusion Pylance
# Les fonctions db ont déjà le décorateur auto_backup_before_critical
