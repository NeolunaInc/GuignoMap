"""
Gestion des mots de passe avec Argon2 pour GuignoMap
Support de la migration depuis bcrypt et autres formats legacy
"""
import os
from typing import Tuple
from passlib.context import CryptContext

# Configuration passlib : Argon2 par défaut, bcrypt pour compatibilité legacy
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,        # 3 itérations
    argon2__parallelism=4,      # 4 threads
    bcrypt__rounds=12           # Pour compatibilité legacy
)


def _get_allow_bcrypt_fallback() -> bool:
    """Récupère la config ALLOW_BCRYPT_FALLBACK"""
    try:
        from src.config import ALLOW_BCRYPT_FALLBACK
        return ALLOW_BCRYPT_FALLBACK
    except ImportError:
        return True  # Par défaut autorisé pendant migration


def hash_password(password: str) -> str:
    """Hash un mot de passe avec Argon2"""
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> Tuple[bool, bool]:
    """
    Vérifie un mot de passe contre son hash
    Supporte la migration automatique bcrypt → Argon2 et autres formats legacy
    
    Returns:
        Tuple (verification_ok, needs_rehash)
    """
    try:
        # Vérifier d'abord avec passlib (supporte bcrypt et Argon2)
        try:
            # Vérifier si bcrypt est autorisé si c'est un hash bcrypt
            if hashed.startswith('$2') and not _get_allow_bcrypt_fallback():
                print("⚠️ Hash bcrypt détecté mais fallback désactivé")
                return False, False
                
            verification_ok = pwd_context.verify(password, hashed)
            if verification_ok:
                needs_rehash = pwd_context.needs_update(hashed)
                return True, needs_rehash
        except:
            pass  # Passlib ne reconnaît pas le format, essayer les formats legacy
        
        # Formats legacy qui nécessitent migration vers Argon2
        
        # 1) SHA-256 simple (64 hex chars)
        if len(hashed) == 64 and all(c in '0123456789abcdef' for c in hashed.lower()):
            import hashlib
            if hashed == hashlib.sha256(password.encode('utf-8')).hexdigest():
                return True, True  # Migration nécessaire
        
        # 2) MD5 (32 hex chars)
        if len(hashed) == 32 and all(c in '0123456789abcdef' for c in hashed.lower()):
            import hashlib
            if hashed == hashlib.md5(password.encode('utf-8')).hexdigest():
                return True, True  # Migration nécessaire
        
        # 3) PBKDF2 format Django
        if hashed.startswith('pbkdf2_sha256$'):
            try:
                parts = hashed.split('$')
                if len(parts) == 4:
                    _, iterations, salt, expected = parts
                    import hashlib
                    import base64
                    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iterations))
                    if base64.b64encode(actual).decode() == expected:
                        return True, True  # Migration nécessaire
            except:
                pass
        
        return False, False
            
    except Exception as e:
        print(f"Erreur vérification mot de passe: {e}")
        return False, False


def verify_password_with_context(password: str, stored_hash: str, stored_plain: str = "", stored_salt: str = "") -> Tuple[bool, bool]:
    """
    Vérifie un mot de passe avec support des formats legacy complexes
    """
    try:
        # 1) Vérifier d'abord les formats standards
        verification_ok, needs_rehash = verify_password(password, stored_hash)
        if verification_ok:
            return True, needs_rehash
        
        # 2) SHA-256 avec salt environnement
        if stored_hash and len(stored_hash) == 64:
            import hashlib
            salt_env = os.environ.get("GM_PWD_SALT", "")
            if salt_env and stored_hash == hashlib.sha256((salt_env + password).encode('utf-8')).hexdigest():
                return True, True  # Migration nécessaire
        
        # 3) SHA-256 avec salt stocké
        if stored_salt and stored_hash:
            import hashlib
            if stored_hash == hashlib.sha256((stored_salt + password).encode('utf-8')).hexdigest():
                return True, True  # Migration nécessaire
        
        # 4) Mot de passe en clair (legacy)
        if stored_plain and stored_plain == password:
            return True, True  # Migration nécessaire
        
        return False, False
        
    except Exception as e:
        print(f"Erreur vérification mot de passe avec contexte: {e}")
        return False, False


def detect_hash_algo(hashed: str) -> str:
    """Détecte l'algorithme utilisé pour un hash"""
    if not hashed:
        return "empty"
    
    if hashed.startswith('$argon2'):
        return "argon2"
    elif hashed.startswith('$2b$') or hashed.startswith('$2a$') or hashed.startswith('$2y$'):
        return "bcrypt"
    elif hashed.startswith('pbkdf2_sha256$'):
        return "pbkdf2_sha256"
    elif len(hashed) == 64 and all(c in '0123456789abcdef' for c in hashed.lower()):
        return "sha256"
    elif len(hashed) == 32 and all(c in '0123456789abcdef' for c in hashed.lower()):
        return "md5"
    else:
        return "unknown"