"""
Configuration centralisée pour GuignoMap v5.0
Accès unifié aux variables d'environnement, secrets Streamlit et paramètres applicatifs
"""
import os
from dataclasses import dataclass
try:
    import streamlit as st
    _SECRETS = dict(st.secrets) if hasattr(st, "secrets") else {}
except Exception:
    _SECRETS = {}

def _get(key, default=None, section=None):
    """Récupère une valeur par priorité: env -> secrets -> défaut"""
    # Priorité 1: Variable d'environnement
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value
    
    # Priorité 2: Secrets Streamlit
    try:
        if section and section in _SECRETS:
            return _SECRETS[section].get(key, default)
        return _SECRETS.get(key, default)
    except (KeyError, AttributeError):
        return default


def _get_str(key, default="", section=None) -> str:
    """Récupère une valeur string avec garantie de type"""
    value = _get(key, default, section)
    return str(value) if value is not None else default


def _get_int(key, default=0, section=None) -> int:
    """Récupère une valeur int avec garantie de type"""
    value = _get(key, default, section)
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _get_bool(key, default=False, section=None) -> bool:
    """Récupère une valeur bool avec garantie de type"""
    value = _get(key, default, section)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value) if value is not None else default


@dataclass
class Settings:
    """Configuration unifiée de l'application"""
    # Authentification technique
    TECH_PIN: str = _get_str("TECH_PIN", "")
    
    # Base de données
    DB_URL: str = _get_str("url", "sqlite:///guigno_map.db", "database")
    DB_POOL_SIZE: int = _get_int("pool_size", 5, "database")
    DB_MAX_OVERFLOW: int = _get_int("max_overflow", 10, "database")
    
    # Stockage S3
    S3_BUCKET: str = _get_str("s3_bucket", "guignomap-dev", "storage")
    S3_REGION: str = _get_str("s3_region", "us-east-1", "storage")
    S3_ACCESS_KEY: str = _get_str("s3_access_key", "", "storage")
    S3_SECRET_KEY: str = _get_str("s3_secret_key", "", "storage")
    CDN_BASE_URL: str = _get_str("cdn_base_url", "", "storage")
    
    # Authentification
    ALLOW_BCRYPT_FALLBACK: bool = _get_bool("allow_bcrypt_fallback", True, "auth")
    MIN_PASSWORD_LENGTH: int = _get_int("min_password_length", 4, "auth")
    PASSWORD_SALT: str = _get_str("password_salt", "", "auth")
    
    # Environnement
    ENV: str = _get_str("ENV", "local")


# Instance globale des paramètres
settings = Settings()


# === FONCTIONS DE COMPATIBILITÉ LEGACY (à supprimer progressivement) ===

def get_database_url():
    """Récupère l'URL de la base de données depuis les secrets"""
    return settings.DB_URL


def get_database_pool_config():
    """Configuration du pool de connexions PostgreSQL"""
    return {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW
    }


def get_s3_config():
    """Configuration S3 pour le stockage cloud"""
    return {
        "bucket": settings.S3_BUCKET,
        "region": settings.S3_REGION,
        "access_key": settings.S3_ACCESS_KEY,
        "secret_key": settings.S3_SECRET_KEY
    }


def get_cdn_base_url():
    """URL de base CDN pour les assets (optionnel)"""
    return settings.CDN_BASE_URL


def get_auth_config():
    """Configuration de l'authentification"""
    return {
        "allow_bcrypt_fallback": settings.ALLOW_BCRYPT_FALLBACK,
        "min_password_length": settings.MIN_PASSWORD_LENGTH,
        "password_salt": settings.PASSWORD_SALT
    }


# Constantes pour accès direct (compatibilité)
ALLOW_BCRYPT_FALLBACK = settings.ALLOW_BCRYPT_FALLBACK