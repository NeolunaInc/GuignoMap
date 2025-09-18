"""
Stockage cloud S3 pour GuignoMap v5.0
Client boto3 pour osm_cache.json et backups
"""
import boto3
import json
import io
import os
import streamlit as st
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
from datetime import datetime
from src.config import get_s3_config, get_cdn_base_url


class S3StorageClient:
    """Client S3 pour gérer osm_cache.json et backups"""
    
    def __init__(self):
        self.config = get_s3_config()
        self.cdn_base_url = get_cdn_base_url()
        self._client = None
    
    @property
    def client(self):
        """Client S3 avec lazy loading et cache Streamlit"""
        if self._client is None:
            try:
                self._client = boto3.client(
                    's3',
                    region_name=self.config['region'],
                    aws_access_key_id=self.config['access_key'],
                    aws_secret_access_key=self.config['secret_key']
                )
            except Exception as e:
                print(f"Erreur initialisation client S3: {e}")
                raise
        return self._client
    
    def upload_json_file(self, key: str, data: Dict[Any, Any], metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Upload d'un fichier JSON vers S3
        """
        try:
            json_content = json.dumps(data, ensure_ascii=False, indent=2)
            json_bytes = json_content.encode('utf-8')
            
            extra_args: Dict[str, Any] = {
                'ContentType': 'application/json',
                'ContentEncoding': 'utf-8'
            }
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.client.put_object(
                Bucket=self.config['bucket'],
                Key=key,
                Body=json_bytes,
                **extra_args
            )
            
            print(f"✅ JSON uploadé vers S3: {key}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur upload JSON S3 {key}: {e}")
            return False
    
    def download_json_file(self, key: str) -> Optional[Dict[Any, Any]]:
        """
        Download d'un fichier JSON depuis S3
        """
        try:
            response = self.client.get_object(
                Bucket=self.config['bucket'],
                Key=key
            )
            
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            
            print(f"✅ JSON téléchargé depuis S3: {key}")
            return data
            
        except self.client.exceptions.NoSuchKey:
            print(f"ℹ️ Fichier JSON S3 non trouvé: {key}")
            return None
        except Exception as e:
            print(f"❌ Erreur download JSON S3 {key}: {e}")
            return None
    
    def upload_backup(self, backup_file_path: Path, s3_key: Optional[str] = None) -> bool:
        """
        Upload d'un fichier backup vers S3
        """
        try:
            if not backup_file_path.exists():
                print(f"❌ Fichier backup non trouvé: {backup_file_path}")
                return False
            
            # Générer la clé S3 si non fournie
            if not s3_key:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                s3_key = f"backups/{backup_file_path.stem}_{timestamp}{backup_file_path.suffix}"
            
            # Upload avec streaming pour gros fichiers
            with open(backup_file_path, 'rb') as f:
                self.client.upload_fileobj(
                    f,
                    self.config['bucket'],
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'application/zip',
                        'Metadata': {
                            'original_filename': backup_file_path.name,
                            'upload_timestamp': datetime.utcnow().isoformat()
                        }
                    }
                )
            
            print(f"✅ Backup uploadé vers S3: {s3_key}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur upload backup S3: {e}")
            return False
    
    def download_backup(self, s3_key: str, local_path: Path) -> bool:
        """
        Download d'un backup depuis S3
        """
        try:
            # Créer le répertoire parent si nécessaire
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download avec streaming
            with open(local_path, 'wb') as f:
                self.client.download_fileobj(
                    self.config['bucket'],
                    s3_key,
                    f
                )
            
            print(f"✅ Backup téléchargé depuis S3: {s3_key} → {local_path}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur download backup S3 {s3_key}: {e}")
            return False
    
    def list_backups(self, prefix: str = "backups/") -> list:
        """
        Liste des backups disponibles sur S3
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.config['bucket'],
                Prefix=prefix
            )
            
            backups = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    backups.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'filename': Path(obj['Key']).name
                    })
                
                # Trier par date de modification (plus récent en premier)
                backups.sort(key=lambda x: x['last_modified'], reverse=True)
            
            return backups
            
        except Exception as e:
            print(f"❌ Erreur liste backups S3: {e}")
            return []
    
    def delete_file(self, key: str) -> bool:
        """
        Suppression d'un fichier sur S3
        """
        try:
            self.client.delete_object(
                Bucket=self.config['bucket'],
                Key=key
            )
            print(f"✅ Fichier supprimé de S3: {key}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur suppression S3 {key}: {e}")
            return False
    
    def file_exists(self, key: str) -> bool:
        """
        Vérifier si un fichier existe sur S3
        """
        try:
            self.client.head_object(
                Bucket=self.config['bucket'],
                Key=key
            )
            return True
        except self.client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            print(f"❌ Erreur vérification existence S3 {key}: {e}")
            return False
    
    def get_public_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Générer URL publique signée pour un fichier S3
        """
        try:
            # Si CDN configuré, utiliser l'URL CDN
            if self.cdn_base_url:
                return f"{self.cdn_base_url.rstrip('/')}/{key}"
            
            # Sinon, générer URL signée S3
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.config['bucket'], 'Key': key},
                ExpiresIn=expires_in
            )
            return url
            
        except Exception as e:
            print(f"❌ Erreur génération URL publique S3 {key}: {e}")
            return None


# Instance globale pour cache Streamlit
@st.cache_resource
def get_s3_client() -> S3StorageClient:
    """Factory avec cache Streamlit pour client S3"""
    return S3StorageClient()


# API simplifiée pour les fonctions métier
def upload_osm_cache(cache_data: Dict[Any, Any]) -> bool:
    """Upload du cache OSM vers S3"""
    client = get_s3_client()
    return client.upload_json_file(
        "osm_cache.json", 
        cache_data,
        metadata={
            'type': 'osm_cache',
            'updated_at': datetime.utcnow().isoformat()
        }
    )


def download_osm_cache() -> Optional[Dict[Any, Any]]:
    """Download du cache OSM depuis S3"""
    client = get_s3_client()
    return client.download_json_file("osm_cache.json")


def upload_backup_to_cloud(backup_path: Path) -> bool:
    """Upload d'un backup vers S3"""
    client = get_s3_client()
    return client.upload_backup(backup_path)


def list_cloud_backups() -> list:
    """Liste des backups cloud disponibles"""
    client = get_s3_client()
    return client.list_backups()


def download_backup_from_cloud(s3_key: str, local_path: Path) -> bool:
    """Download d'un backup depuis S3"""
    client = get_s3_client()
    return client.download_backup(s3_key, local_path)