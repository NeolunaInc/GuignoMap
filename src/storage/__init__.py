"""
Adapter de stockage pour GuignoMap v5.0
Sélection automatique entre cloud S3 et local selon configuration
"""
import os
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from src.storage.cloud import (
        upload_osm_cache as cloud_upload_osm_cache,
        download_osm_cache as cloud_download_osm_cache,
        upload_backup_to_cloud as cloud_upload_backup,
        list_cloud_backups as cloud_list_backups,
        download_backup_from_cloud as cloud_download_backup
    )
    CLOUD_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Stockage cloud non disponible: {e}")
    CLOUD_AVAILABLE = False

from src.storage.local import (
    upload_osm_cache as local_upload_osm_cache,
    download_osm_cache as local_download_osm_cache,
    upload_backup_to_cloud as local_upload_backup,
    list_cloud_backups as local_list_backups,
    download_backup_from_cloud as local_download_backup
)


def is_cloud_storage_enabled() -> bool:
    """
    Détermine si le stockage cloud est activé
    Vérifie la présence des secrets S3 et la disponibilité des libs
    """
    if not CLOUD_AVAILABLE:
        return False
    
    try:
        from src.config import get_s3_config
        config = get_s3_config()
        
        # Vérifier que les clés essentielles sont présentes et non vides
        required_keys = ['bucket', 'access_key', 'secret_key']
        for key in required_keys:
            if not config.get(key) or config[key] in ['', 'xxx']:
                return False
        
        return True
    except Exception:
        return False


def get_storage_backend() -> str:
    """Retourne 'cloud' ou 'local' selon la configuration"""
    return 'cloud' if is_cloud_storage_enabled() else 'local'


# API unifiée pour le stockage
def upload_osm_cache(cache_data: Dict[Any, Any]) -> bool:
    """Upload du cache OSM (cloud ou local selon config)"""
    if is_cloud_storage_enabled():
        print("📡 Upload cache OSM vers S3...")
        return cloud_upload_osm_cache(cache_data)
    else:
        print("💾 Sauvegarde cache OSM en local...")
        return local_upload_osm_cache(cache_data)


def download_osm_cache() -> Optional[Dict[Any, Any]]:
    """Download du cache OSM (cloud ou local selon config)"""
    if is_cloud_storage_enabled():
        print("📡 Téléchargement cache OSM depuis S3...")
        return cloud_download_osm_cache()
    else:
        print("💾 Lecture cache OSM local...")
        return local_download_osm_cache()


def upload_backup(backup_path: Path) -> bool:
    """Upload d'un backup (cloud ou local selon config)"""
    if is_cloud_storage_enabled():
        print("📡 Upload backup vers S3...")
        return cloud_upload_backup(backup_path)
    else:
        print("💾 Copie backup en local...")
        return local_upload_backup(backup_path)


def list_backups() -> list:
    """Liste des backups disponibles (cloud ou local selon config)"""
    if is_cloud_storage_enabled():
        print("📡 Liste backups S3...")
        return cloud_list_backups()
    else:
        print("💾 Liste backups locaux...")
        return local_list_backups()


def download_backup(backup_key: str, local_path: Path) -> bool:
    """Download d'un backup (cloud ou local selon config)"""
    if is_cloud_storage_enabled():
        print("📡 Téléchargement backup depuis S3...")
        return cloud_download_backup(backup_key, local_path)
    else:
        print("💾 Copie backup depuis local...")
        return local_download_backup(backup_key, local_path)


def get_storage_info() -> Dict[str, Any]:
    """Informations sur le backend de stockage actuel"""
    backend = get_storage_backend()
    info = {
        'backend': backend,
        'cloud_available': CLOUD_AVAILABLE,
        'cloud_enabled': is_cloud_storage_enabled()
    }
    
    if backend == 'cloud':
        try:
            from src.config import get_s3_config
            config = get_s3_config()
            info.update({
                'bucket': config.get('bucket', ''),
                'region': config.get('region', ''),
                'cdn_enabled': bool(config.get('cdn_base_url', ''))
            })
        except:
            pass
    
    return info