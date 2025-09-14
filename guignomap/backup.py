"""
Système de backup automatique pour GuignoMap
Sauvegarde la base de données et les caches
"""

import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
import json
import zipfile

class BackupManager:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backups = 7  # Garder 7 jours de backups
        
    def create_backup(self, reason="manual"):
        """Crée un backup complet avec timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}_{reason}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        try:
            # Backup de la base de données
            db_backup = backup_path / "guigno_map.db"
            shutil.copy2(self.db_path, db_backup)
            
            # Backup des caches OSM
            for cache_file in ["osm_cache.json", "osm_addresses.json"]:
                cache_path = self.db_path.parent / cache_file
                if cache_path.exists():
                    shutil.copy2(cache_path, backup_path / cache_file)
            
            # Créer un ZIP
            zip_path = self.backup_dir / f"{backup_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in backup_path.iterdir():
                    zipf.write(file, file.name)
            
            # Nettoyer le dossier temporaire
            shutil.rmtree(backup_path)
            
            # Nettoyer les vieux backups
            self._cleanup_old_backups()
            
            # Log le backup
            self._log_backup(timestamp, reason)
            
            print(f"✅ Backup créé : {zip_path.name}")
            return str(zip_path)
            
        except Exception as e:
            print(f"❌ Erreur backup : {e}")
            if backup_path.exists():
                shutil.rmtree(backup_path)
            return None
    
    def restore_backup(self, backup_file):
        """Restaure un backup spécifique"""
        backup_path = self.backup_dir / backup_file
        if not backup_path.exists():
            print(f"❌ Backup introuvable : {backup_file}")
            return False
            
        try:
            # Créer un backup de sécurité avant restauration
            self.create_backup("pre_restore")
            
            # Extraire le ZIP
            temp_dir = self.backup_dir / "temp_restore"
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Restaurer les fichiers
            for file in temp_dir.iterdir():
                target = self.db_path.parent / file.name
                shutil.copy2(file, target)
            
            # Nettoyer
            shutil.rmtree(temp_dir)
            
            print(f"✅ Backup restauré : {backup_file}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur restauration : {e}")
            return False
    
    def list_backups(self):
        """Liste tous les backups disponibles"""
        backups = []
        for file in self.backup_dir.glob("backup_*.zip"):
            stat = file.stat()
            backups.append({
                "name": file.name,
                "size": f"{stat.st_size / 1024 / 1024:.2f} MB",
                "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        return sorted(backups, key=lambda x: x["date"], reverse=True)
    
    def _cleanup_old_backups(self):
        """Supprime les backups de plus de 7 jours"""
        backups = sorted(self.backup_dir.glob("backup_*.zip"), key=lambda x: x.stat().st_mtime)
        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            oldest.unlink()
            print(f"🗑️ Ancien backup supprimé : {oldest.name}")
    
    def _log_backup(self, timestamp, reason):
        """Log les backups dans un fichier"""
        log_file = self.backup_dir / "backup_log.json"
        log = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                log = json.load(f)
        
        log.append({
            "timestamp": timestamp,
            "reason": reason,
            "date": datetime.now().isoformat()
        })
        
        # Garder seulement les 100 derniers logs
        log = log[-100:]
        
        with open(log_file, 'w') as f:
            json.dump(log, f, indent=2)

def auto_backup_before_critical(func):
    """Décorateur pour backup automatique avant opérations critiques"""
    def wrapper(*args, **kwargs):
        # Trouver la connexion DB dans les arguments
        conn = None
        for arg in args:
            if hasattr(arg, 'execute'):  # C'est une connexion SQLite
                conn = arg
                break
        
        if conn:
            try:
                # Créer un backup avant l'opération
                db_path = Path(__file__).parent / "guigno_map.db"
                backup_mgr = BackupManager(db_path)
                backup_mgr.create_backup(f"auto_{func.__name__}")
            except:
                pass  # Ne pas bloquer l'opération si le backup échoue
        
        return func(*args, **kwargs)
    return wrapper