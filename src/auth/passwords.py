"""
Gestion des mots de passe avec Argon2 pour GuignoMap v5.0
Migration compatible depuis bcrypt + politique UI inchangée (min 4 + confirmation)
"""
from passlib.context import CryptContext
from typing import Tuple
import bcrypt


# Configuration passlib avec Argon2 comme algorithme principal
# Garde bcrypt pour la compatibilité ascendante (lecture uniquement)
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",  # Marque bcrypt comme obsolète
    argon2__rounds=2,   # Paramètres Argon2 pour performance/sécurité équilibrée
    argon2__memory_cost=65536,  # 64 MB
    argon2__parallelism=1,
    argon2__hash_len=32
)


def hash_password(password: str) -> str:
    """
    Hash un mot de passe avec Argon2
    
    Args:
        password: Mot de passe en texte clair
        
    Returns:
        Hash Argon2 du mot de passe
    """
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> Tuple[bool, bool]:
    """
    Vérifie un mot de passe contre son hash
    Supporte la migration automatique bcrypt → Argon2
    
    Args:
        password: Mot de passe en texte clair
        hashed: Hash stocké (bcrypt ou Argon2)
        
    Returns:
        Tuple (verification_ok, needs_rehash)
        - verification_ok: True si le mot de passe est correct
        - needs_rehash: True si le hash doit être mis à jour (migration paresseuse)
    """
    try:
        # Vérification avec passlib (supporte bcrypt et Argon2)
        verification_ok = pwd_context.verify(password, hashed)
        
        if verification_ok:
            # Vérifier si une mise à jour du hash est nécessaire
            needs_rehash = pwd_context.needs_update(hashed)
            return True, needs_rehash
        else:
            return False, False
            
    except Exception as e:
        print(f"Erreur vérification mot de passe: {e}")
        return False, False


def is_bcrypt_hash(hashed: str) -> bool:
    """
    Détermine si un hash est au format bcrypt
    
    Args:
        hashed: Hash à vérifier
        
    Returns:
        True si c'est un hash bcrypt
    """
    return hashed.startswith('$2b$') or hashed.startswith('$2a$') or hashed.startswith('$2y$')


def is_argon2_hash(hashed: str) -> bool:
    """
    Détermine si un hash est au format Argon2
    
    Args:
        hashed: Hash à vérifier
        
    Returns:
        True si c'est un hash Argon2
    """
    return hashed.startswith('$argon2')


def migrate_password_if_needed(password: str, old_hash: str) -> Tuple[bool, str]:
    """
    Migration paresseuse d'un mot de passe bcrypt vers Argon2
    Appelé lors d'une connexion réussie
    
    Args:
        password: Mot de passe en texte clair (fourni lors de la connexion)
        old_hash: Hash actuel stocké
        
    Returns:
        Tuple (migrated, new_hash)
        - migrated: True si une migration a eu lieu
        - new_hash: Nouveau hash Argon2 (ou old_hash si pas de migration)
    """
    verification_ok, needs_rehash = verify_password(password, old_hash)
    
    if verification_ok and needs_rehash:
        # Migration nécessaire : re-hasher avec Argon2
        new_hash = hash_password(password)
        print(f"🔄 Migration hash bcrypt → Argon2")
        return True, new_hash
    
    return False, old_hash


def validate_password_policy(password: str) -> Tuple[bool, str]:
    """
    Validation de la politique de mot de passe
    IMPORTANT: Garder la politique UI v4.1 (min 4 caractères + confirmation)
    
    Args:
        password: Mot de passe à valider
        
    Returns:
        Tuple (valid, error_message)
    """
    if not password:
        return False, "Le mot de passe est requis"
    
    if len(password) < 4:
        return False, "Le mot de passe doit contenir au moins 4 caractères"
    
    # Note: La confirmation est gérée côté UI, pas ici
    return True, ""


def get_password_hash_info(hashed: str) -> dict:
    """
    Informations sur un hash de mot de passe
    Utile pour diagnostics et migration
    
    Args:
        hashed: Hash à analyser
        
    Returns:
        Dictionnaire avec les informations du hash
    """
    info = {
        'algorithm': 'unknown',
        'needs_update': False,
        'is_bcrypt': is_bcrypt_hash(hashed),
        'is_argon2': is_argon2_hash(hashed)
    }
    
    try:
        if is_bcrypt_hash(hashed):
            info['algorithm'] = 'bcrypt'
            info['needs_update'] = True  # Tous les bcrypt doivent migrer
        elif is_argon2_hash(hashed):
            info['algorithm'] = 'argon2'
            info['needs_update'] = pwd_context.needs_update(hashed)
        
        # Informations supplémentaires via passlib
        hash_info = pwd_context.identify(hashed)
        if hash_info:
            info['passlib_scheme'] = hash_info
            
    except Exception as e:
        info['error'] = str(e)
    
    return info


# Fonctions de compatibilité avec l'ancien système bcrypt
def legacy_verify_bcrypt(password: str, bcrypt_hash: str) -> bool:
    """
    Vérification directe bcrypt pour rétrocompatibilité
    Utilisé uniquement si passlib échoue
    
    Args:
        password: Mot de passe en texte clair
        bcrypt_hash: Hash bcrypt à vérifier
        
    Returns:
        True si le mot de passe correspond
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), bcrypt_hash.encode('utf-8'))
    except Exception as e:
        print(f"Erreur vérification bcrypt legacy: {e}")
        return False


def create_test_hashes(password: str = "test123") -> dict:
    """
    Utilitaire pour créer des hashes de test
    Aide au développement et aux tests
    
    Args:
        password: Mot de passe de test
        
    Returns:
        Dictionnaire avec les différents hashes
    """
    return {
        'password': password,
        'argon2': hash_password(password),
        'bcrypt_legacy': bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    }