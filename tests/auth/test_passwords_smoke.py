"""
Tests smoke pour le système d'authentification unifié Argon2
Tests basiques pour vérifier que le système de hachage et migration fonctionne
"""
import unittest
import sys
from pathlib import Path

# Ajout du chemin du projet pour les imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from guignomap.auth import (
    hash_password, 
    verify_password, 
    verify_password_with_context,
    detect_hash_algo
)


class TestPasswordsSmoke(unittest.TestCase):
    """Tests de base pour le système de mots de passe"""
    
    def setUp(self):
        """Données de test"""
        self.test_password = "TestPassword123"
        self.weak_password = "test"
        
        # Hashes de test pour différents algorithmes
        self.test_hashes = {
            # SHA-256 simple
            "sha256": "a5f8a84d6e2b8e86e4e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5",
            # MD5 (32 chars)
            "md5": "5d41402abc4b2a76b9719d911017c592",
            # Mot de passe en clair
            "plaintext": "TestPassword123"
        }
    
    def test_hash_password_creates_argon2(self):
        """Test que hash_password génère un hash Argon2"""
        hashed = hash_password(self.test_password)
        
        # Vérifier que c'est bien un hash Argon2
        self.assertTrue(hashed.startswith('$argon2'))
        self.assertEqual(detect_hash_algo(hashed), "argon2")
        
        # Le hash doit être différent à chaque fois
        hashed2 = hash_password(self.test_password)
        self.assertNotEqual(hashed, hashed2)
    
    def test_verify_password_argon2(self):
        """Test vérification avec hash Argon2"""
        hashed = hash_password(self.test_password)
        
        # Mot de passe correct
        verified, needs_rehash = verify_password(self.test_password, hashed)
        self.assertTrue(verified)
        self.assertFalse(needs_rehash)  # Pas de migration nécessaire pour Argon2
        
        # Mot de passe incorrect
        verified, needs_rehash = verify_password("wrong_password", hashed)
        self.assertFalse(verified)
        self.assertFalse(needs_rehash)
    
    def test_verify_password_legacy_sha256(self):
        """Test migration depuis SHA-256"""
        import hashlib
        test_password = "test123"
        sha256_hash = hashlib.sha256(test_password.encode('utf-8')).hexdigest()
        
        # Vérifier que la migration est détectée
        verified, needs_rehash = verify_password(test_password, sha256_hash)
        self.assertTrue(verified)
        self.assertTrue(needs_rehash)  # Migration nécessaire
        
        # Mot de passe incorrect
        verified, needs_rehash = verify_password("wrong", sha256_hash)
        self.assertFalse(verified)
        self.assertFalse(needs_rehash)
    
    def test_verify_password_legacy_md5(self):
        """Test migration depuis MD5"""
        import hashlib
        test_password = "test123"
        md5_hash = hashlib.md5(test_password.encode('utf-8')).hexdigest()
        
        # Vérifier que la migration est détectée
        verified, needs_rehash = verify_password(test_password, md5_hash)
        self.assertTrue(verified)
        self.assertTrue(needs_rehash)  # Migration nécessaire
    
    def test_verify_password_with_context_plaintext(self):
        """Test vérification avec mot de passe en clair (legacy)"""
        verified, needs_rehash = verify_password_with_context(
            self.test_password, "", self.test_password, ""
        )
        self.assertTrue(verified)
        self.assertTrue(needs_rehash)  # Migration nécessaire
    
    def test_verify_password_with_context_salt_env(self):
        """Test vérification avec salt environnement"""
        import os
        import hashlib
        
        # Simuler un salt environnement
        os.environ["GM_PWD_SALT"] = "test_salt"
        
        test_password = "test123"
        salted_hash = hashlib.sha256(("test_salt" + test_password).encode('utf-8')).hexdigest()
        
        verified, needs_rehash = verify_password_with_context(
            test_password, salted_hash, "", ""
        )
        self.assertTrue(verified)
        self.assertTrue(needs_rehash)  # Migration nécessaire
        
        # Nettoyer
        del os.environ["GM_PWD_SALT"]
    
    def test_verify_password_with_context_salt_stored(self):
        """Test vérification avec salt stocké"""
        import hashlib
        
        test_password = "test123"
        stored_salt = "stored_salt"
        salted_hash = hashlib.sha256((stored_salt + test_password).encode('utf-8')).hexdigest()
        
        verified, needs_rehash = verify_password_with_context(
            test_password, salted_hash, "", stored_salt
        )
        self.assertTrue(verified)
        self.assertTrue(needs_rehash)  # Migration nécessaire
    
    def test_detect_hash_algo(self):
        """Test détection d'algorithmes"""
        # Test Argon2
        argon2_hash = hash_password(self.test_password)
        self.assertEqual(detect_hash_algo(argon2_hash), "argon2")
        
        # Test SHA-256 (64 hex chars)
        import hashlib
        sha256_hash = hashlib.sha256(b"test").hexdigest()
        self.assertEqual(detect_hash_algo(sha256_hash), "sha256")
        
        # Test MD5 (32 hex chars)
        md5_hash = hashlib.md5(b"test").hexdigest()
        self.assertEqual(detect_hash_algo(md5_hash), "md5")
        
        # Test bcrypt
        self.assertEqual(detect_hash_algo("$2b$12$..."), "bcrypt")
        
        # Test PBKDF2
        self.assertEqual(detect_hash_algo("pbkdf2_sha256$..."), "pbkdf2_sha256")
        
        # Test empty
        self.assertEqual(detect_hash_algo(""), "empty")
        
        # Test unknown
        self.assertEqual(detect_hash_algo("random_string"), "unknown")
    
    def test_edge_cases(self):
        """Test cas limites"""
        # Mot de passe vide
        with self.assertRaises(Exception):
            hash_password("")
        
        # Hash vide
        verified, needs_rehash = verify_password("test", "")
        self.assertFalse(verified)
        self.assertFalse(needs_rehash)
        
        # Hash invalide
        verified, needs_rehash = verify_password("test", "invalid_hash")
        self.assertFalse(verified)
        self.assertFalse(needs_rehash)


if __name__ == '__main__':
    print("🧪 Tests smoke du système d'authentification Argon2")
    print("=" * 50)
    
    # Exécuter les tests
    unittest.main(verbosity=2)