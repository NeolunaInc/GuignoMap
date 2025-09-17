"""
Configuration centralisée pour GuignoMap v5.0
Accès aux secrets Streamlit et paramètres applicatifs
"""
import streamlit as st
import os


def get_database_url():
    """Récupère l'URL de la base de données depuis les secrets"""
    try:
        return st.secrets["database"]["url"]
    except (KeyError, AttributeError):
        # Fallback pour développement local ou tests
        return os.getenv("DATABASE_URL", "sqlite:///guigno_map.db")


def get_database_pool_config():
    """Configuration du pool de connexions PostgreSQL"""
    try:
        return {
            "pool_size": st.secrets["database"].get("pool_size", 5),
            "max_overflow": st.secrets["database"].get("max_overflow", 10)
        }
    except (KeyError, AttributeError):
        return {"pool_size": 5, "max_overflow": 10}


def get_s3_config():
    """Configuration S3 pour le stockage cloud"""
    try:
        return {
            "bucket": st.secrets["storage"]["s3_bucket"],
            "region": st.secrets["storage"]["s3_region"],
            "access_key": st.secrets["storage"]["s3_access_key"],
            "secret_key": st.secrets["storage"]["s3_secret_key"]
        }
    except (KeyError, AttributeError):
        return {
            "bucket": os.getenv("S3_BUCKET", "guignomap-dev"),
            "region": os.getenv("S3_REGION", "us-east-1"),
            "access_key": os.getenv("S3_ACCESS_KEY", ""),
            "secret_key": os.getenv("S3_SECRET_KEY", "")
        }


def get_cdn_base_url():
    """URL de base CDN pour les assets (optionnel)"""
    try:
        return st.secrets["storage"].get("cdn_base_url", "")
    except (KeyError, AttributeError):
        return os.getenv("CDN_BASE_URL", "")


# =============================================================================
# CONFIGURATION AUTHENTIFICATION
# =============================================================================

def get_auth_config():
    """Configuration de l'authentification"""
    try:
        return {
            "allow_bcrypt_fallback": st.secrets["auth"].get("allow_bcrypt_fallback", True),
            "min_password_length": st.secrets["auth"].get("min_password_length", 4),
            "password_salt": st.secrets["auth"].get("password_salt", "")
        }
    except (KeyError, AttributeError):
        return {
            "allow_bcrypt_fallback": True,  # Permettre bcrypt pendant migration
            "min_password_length": 4,
            "password_salt": os.getenv("GM_PWD_SALT", "")
        }


# Constantes pour accès direct
ALLOW_BCRYPT_FALLBACK = get_auth_config()["allow_bcrypt_fallback"]