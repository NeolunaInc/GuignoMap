"""
Stockage local pour GuignoMap v5.0  
Fallback avec API identique à cloud.py
"""
import json
import shutil
import os
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime


class LocalStorageClient:
    """Client stockage local avec API identique au client S3"""
    
    def __init__(self, base_path: Optional[Path] = None):
        # Répertoire de base pour le stockage local
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "storage_local"
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Sous-répertoires
        self.backups_dir = self.base_path / "backups"
        self.backups_dir.mkdir(exist_ok=True)
    
    def upload_json_file(self, key: str, data: Dict[Any, Any], metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Sauvegarde d'un fichier JSON en local
        """
        try:
            file_path = self.base_path / key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder les données JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder les métadonnées si fournies
            if metadata:
                metadata_path = file_path.with_suffix('.metadata.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON sauvé localement: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde JSON local {key}: {e}")
            return False
    
    def download_json_file(self, key: str) -> Optional[Dict[Any, Any]]:
        """
        Lecture d'un fichier JSON local
        """
        try:
            file_path = self.base_path / key
            
            if not file_path.exists():
                print(f"ℹ️ Fichier JSON local non trouvé: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ JSON lu localement: {file_path}")
            return data
            
        except Exception as e:
            print(f"❌ Erreur lecture JSON local {key}: {e}")
            return None
    
    def upload_backup(self, backup_file_path: Path, s3_key: Optional[str] = None) -> bool:
        """
        Copie d'un fichier backup vers le répertoire local
        """
        try:
            if not backup_file_path.exists():
                print(f"❌ Fichier backup non trouvé: {backup_file_path}")
                return False
            
            # Générer le nom de destination si non fourni
            if not s3_key:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_name = f"{backup_file_path.stem}_{timestamp}{backup_file_path.suffix}"
            else:
                # Extraire le nom du fichier de la clé S3
                dest_name = Path(s3_key).name
            
            dest_path = self.backups_dir / dest_name
            
            # Copier le fichier
            shutil.copy2(backup_file_path, dest_path)
            
            # Créer un fichier de métadonnées
            metadata = {
                'original_filename': backup_file_path.name,
                'original_path': str(backup_file_path),
                'upload_timestamp': datetime.utcnow().isoformat(),
                'size': backup_file_path.stat().st_size
            }
            
            metadata_path = dest_path.with_suffix(dest_path.suffix + '.metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Backup copié localement: {dest_path}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur copie backup local: {e}")
            return False
    
    def download_backup(self, s3_key: str, local_path: Path) -> bool:
        """
        Copie d'un backup depuis le stockage local
        """
        try:
            # Trouver le fichier source
            source_name = Path(s3_key).name
            source_path = self.backups_dir / source_name
            
            if not source_path.exists():
                print(f"❌ Backup local non trouvé: {source_path}")
                return False
            
            # Créer le répertoire de destination
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copier le fichier
            shutil.copy2(source_path, local_path)
            
            print(f"✅ Backup copié depuis local: {source_path} → {local_path}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur copie backup depuis local {s3_key}: {e}")
            return False
    
    def list_backups(self, prefix: str = "backups/") -> list:
        """
        Liste des backups disponibles en local
        """
        try:
            backups = []
            
            # Lister tous les fichiers (sauf métadonnées)
            for backup_file in self.backups_dir.glob("*"):
                if backup_file.is_file() and not backup_file.name.endswith('.metadata.json'):
                    # Lire les métadonnées si disponibles
                    metadata_path = backup_file.with_suffix(backup_file.suffix + '.metadata.json')
                    metadata = {}
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                        except:
                            pass
                    
                    stat = backup_file.stat()
                    backups.append({
                        'key': f"backups/{backup_file.name}",
                        'size': stat.st_size,
                        'last_modified': datetime.fromtimestamp(stat.st_mtime),
                        'filename': backup_file.name,
                        'metadata': metadata
                    })
            
            # Trier par date de modification (plus récent en premier)
            backups.sort(key=lambda x: x['last_modified'], reverse=True)
            return backups
            
        except Exception as e:
            print(f"❌ Erreur liste backups locaux: {e}")
            return []
    
    def delete_file(self, key: str) -> bool:
        """
        Suppression d'un fichier local
        """
        try:
            file_path = self.base_path / key
            
            if file_path.exists():
                file_path.unlink()
                
                # Supprimer les métadonnées si elles existent
                metadata_path = file_path.with_suffix('.metadata.json')
                if metadata_path.exists():
                    metadata_path.unlink()
                
                print(f"✅ Fichier supprimé localement: {file_path}")
                return True
            else:
                print(f"ℹ️ Fichier local non trouvé: {file_path}")
                return False
            
        except Exception as e:
            print(f"❌ Erreur suppression fichier local {key}: {e}")
            return False
    
    def file_exists(self, key: str) -> bool:
        """
        Vérifier si un fichier existe en local
        """
        file_path = self.base_path / key
        return file_path.exists()
    
    def get_public_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Générer un chemin local pour un fichier (pas d'URL publique)
        """
        file_path = self.base_path / key
        if file_path.exists():
            return f"file://{file_path.absolute()}"
        return None


# Instance globale pour le stockage local
_local_client = None

def get_local_client() -> LocalStorageClient:
    """Factory pour client de stockage local"""
    global _local_client
    if _local_client is None:
        _local_client = LocalStorageClient()
    return _local_client


# API simplifiée pour les fonctions métier (identique à cloud.py)
def upload_osm_cache(cache_data: Dict[Any, Any]) -> bool:
    """Upload du cache OSM en local"""
    client = get_local_client()
    return client.upload_json_file(
        "osm_cache.json", 
        cache_data,
        metadata={
            'type': 'osm_cache',
            'updated_at': datetime.utcnow().isoformat()
        }
    )


def download_osm_cache() -> Optional[Dict[Any, Any]]:
    """Download du cache OSM depuis local"""
    client = get_local_client()
    return client.download_json_file("osm_cache.json")


def upload_backup_to_cloud(backup_path: Path) -> bool:
    """Upload d'un backup en local"""
    client = get_local_client()
    return client.upload_backup(backup_path)


def list_cloud_backups() -> list:
    """Liste des backups locaux disponibles"""
    client = get_local_client()
    return client.list_backups()


def download_backup_from_cloud(s3_key: str, local_path: Path) -> bool:
    """Download d'un backup depuis local"""
    client = get_local_client()
    return client.download_backup(s3_key, local_path)