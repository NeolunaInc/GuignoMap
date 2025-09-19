"""
Test de performance SQLite - PHASE 3 optimisations
Vérifie que les optimisations PRAGMA, INDEX et cache améliorent les performances
"""
# Détection du runtime Streamlit
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    _RUNTIME = get_script_run_ctx() is not None
except Exception:
    _RUNTIME = False

import pytest
import time
import os
import tempfile
import sqlite3
from pathlib import Path
import sys

# Ajouter le path du projet
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import guignomap.database as db


class TestSQLitePerformance:
    """Tests de performance pour SQLite avec optimisations"""
    
    def setup_method(self):
        """Setup avant chaque test"""
        # Utiliser une DB temporaire pour les tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Backup de la DB originale
        self.original_db_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_db.name)
        
        # Reset la connexion thread-local
        if hasattr(db._local, 'conn'):
            if db._local.conn:
                db._local.conn.close()
            db._local.conn = None
        
        # Créer les tables et INDEX
        self.create_test_schema()
        db.create_performance_indexes()
    
    def teardown_method(self):
        """Cleanup après chaque test"""
        # Fermer la connexion
        if hasattr(db._local, 'conn') and db._local.conn:
            db._local.conn.close()
            db._local.conn = None
        
        # Restaurer la DB originale
        db.DB_PATH = self.original_db_path
        
        # Supprimer le fichier temporaire
        try:
            os.unlink(self.temp_db.name)
        except FileNotFoundError:
            pass
    
    def create_test_schema(self):
        """Crée le schéma de test"""
        with db.get_conn() as conn:
            # Table teams
            conn.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT 1
                )
            """)
            
            # Table streets
            conn.execute("""
                CREATE TABLE IF NOT EXISTS streets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    sector TEXT,
                    team TEXT,
                    status TEXT NOT NULL DEFAULT 'a_faire' 
                        CHECK (status IN ('a_faire', 'en_cours', 'terminee'))
                )
            """)
            
            # Table notes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    street_name TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    address_number TEXT,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (street_name) REFERENCES streets(name),
                    FOREIGN KEY (team_id) REFERENCES teams(id)
                )
            """)
            
            conn.commit()
    
    def test_pragma_optimizations(self):
        """Test que les PRAGMA optimisations sont actifs"""
        conn = db.get_conn()
        
        # Vérifier journal_mode=WAL
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal_mode.lower() == 'wal', f"Expected WAL, got {journal_mode}"
        
        # Vérifier cache_size
        cache_size = conn.execute("PRAGMA cache_size").fetchone()[0]
        assert cache_size == -64000, f"Expected -64000, got {cache_size}"
        
        # Vérifier mmap_size
        mmap_size = conn.execute("PRAGMA mmap_size").fetchone()[0]
        assert mmap_size == 268435456, f"Expected 268435456, got {mmap_size}"
        
        print("✅ PRAGMA optimisations actives")
    
    def test_indexes_created(self):
        """Test que les INDEX de performance sont créés"""
        conn = db.get_conn()
        
        # Lister tous les index personnalisés
        indexes = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
            ORDER BY name
        """).fetchall()
        
        index_names = [idx[0] for idx in indexes]
        
        # Vérifier les INDEX essentiels
        expected_indexes = [
            'idx_streets_team',
            'idx_streets_status',
            'idx_streets_name',
            'idx_notes_street_name',
            'idx_notes_team_id'
        ]
        
        for expected in expected_indexes:
            assert expected in index_names, f"INDEX manquant: {expected}"
        
        print(f"✅ {len(index_names)} INDEX créés: {index_names}")
    
    def test_bulk_insertions_performance(self):
        """Test performance des insertions en lot (≥100 insertions)"""
        conn = db.get_conn()
        
        # Créer quelques équipes de test
        teams = [('team1', 'Équipe 1'), ('team2', 'Équipe 2'), ('team3', 'Équipe 3')]
        for team_id, team_name in teams:
            conn.execute("""
                INSERT OR IGNORE INTO teams(id, name, password_hash) 
                VALUES (?, ?, 'test_hash')
            """, (team_id, team_name))
        
        # Test insertions de rues en lot
        start_time = time.time()
        
        streets_data = []
        for i in range(150):  # ≥100 insertions
            streets_data.append((
                f"Rue Test {i:03d}", 
                f"Secteur {i % 5}",
                f"team{(i % 3) + 1}",
                'a_faire'
            ))
        
        # Insertion par batch pour améliorer les performances
        conn.executemany("""
            INSERT INTO streets(name, sector, team, status) 
            VALUES (?, ?, ?, ?)
        """, streets_data)
        
        conn.commit()
        
        insert_time = time.time() - start_time
        
        # Vérifier le nombre d'enregistrements
        count = conn.execute("SELECT COUNT(*) FROM streets").fetchone()[0]
        assert count >= 150, f"Expected ≥150 streets, got {count}"
        
        # Performance doit être < 1 seconde pour 150 insertions
        assert insert_time < 1.0, f"Insertion trop lente: {insert_time:.3f}s"
        
        print(f"✅ {count} insertions en {insert_time*1000:.1f}ms")
    
    def test_bulk_reads_performance(self):
        """Test performance des lectures en lot (≥100 lectures)"""
        conn = db.get_conn()
        
        # Nettoyer d'abord les données existantes
        conn.execute("DELETE FROM streets")
        conn.commit()
        
        # Préparer les données fraîches
        self.test_bulk_insertions_performance()
        
        # Test lectures multiples avec différents filtres
        start_time = time.time()
        
        read_operations = 0
        
        # Lectures par équipe (50 opérations)
        for i in range(50):
            team_id = f"team{(i % 3) + 1}"
            streets = conn.execute("""
                SELECT s.name, s.sector, s.status 
                FROM streets s 
                WHERE s.team = ?
                ORDER BY s.name
            """, (team_id,)).fetchall()
            read_operations += 1
        
        # Lectures par secteur (30 opérations)
        for i in range(30):
            sector = f"Secteur {i % 5}"
            streets = conn.execute("""
                SELECT s.name, s.team, s.status 
                FROM streets s 
                WHERE s.sector = ?
                ORDER BY s.name
            """, (sector,)).fetchall()
            read_operations += 1
        
        # Lectures par statut (25 opérations)
        for i in range(25):
            streets = conn.execute("""
                SELECT s.name, s.sector, s.team
                FROM streets s 
                WHERE s.status = 'a_faire'
                ORDER BY s.name
                LIMIT 10
            """).fetchall()
            read_operations += 1
        
        read_time = time.time() - start_time
        
        assert read_operations >= 100, f"Expected ≥100 reads, got {read_operations}"
        
        # Performance: avec INDEX, doit être < 0.5 seconde pour 105 lectures
        assert read_time < 0.5, f"Lectures trop lentes: {read_time:.3f}s"
        
        print(f"✅ {read_operations} lectures en {read_time*1000:.1f}ms")
    
    @pytest.mark.skipif(not _RUNTIME, reason="Cache perf meaningful only in Streamlit runtime")
    def test_cache_performance(self):
        """Test que le cache améliore significativement les performances"""
        conn = db.get_conn()
        
        # Nettoyer d'abord les données existantes
        conn.execute("DELETE FROM streets")
        conn.commit()
        
        # Préparer les données fraîches
        self.test_bulk_insertions_performance()
        
        # Warm-up: 3 appels pour amorcer le cache/compilation SQLite
        for _ in range(3):
            db.extended_stats()
        
        # Mesure du premier appel avec cache
        start_time = time.time()
        db.extended_stats()
        time_first_cache = time.time() - start_time
        
        # Mesure de 5 cache hits consécutifs
        cache_hit_times = []
        for _ in range(5):
            start_time = time.time()
            db.extended_stats()
            cache_hit_times.append(time.time() - start_time)
        
        # Calculer la médiane des cache hits
        cache_hit_times.sort()
        median_hit = cache_hit_times[len(cache_hit_times) // 2]
        
        # Calculer le speedup
        speedup = time_first_cache / median_hit if median_hit > 0 else float('inf')
        
        # Seuil 10x car on est dans Streamlit runtime
        threshold = 10
        epsilon = 0.01
        
        # Vérifications avec messages d'erreur détaillés
        assert speedup >= threshold, (
            f"Cache pas assez efficace: speedup={speedup:.2f}x, "
            f"median_hit={median_hit*1000:.2f}ms, seuil={threshold}x"
        )
        assert median_hit < epsilon, (
            f"Cache hit médian trop lent: {median_hit*1000:.2f}ms (seuil {epsilon*1000:.0f}ms)"
        )
        
        print(f"✅ Cache efficace: {speedup:.2f}x plus rapide")
        print(f"   1er cache: {time_first_cache*1000:.1f}ms") 
        print(f"   Cache hit médian: {median_hit*1000:.2f}ms")
        print(f"   Seuil: {threshold}x")
    
    def test_vacuum_performance(self):
        """Test que vacuum_database() s'exécute rapidement"""
        conn = db.get_conn()
        
        # Nettoyer d'abord les données existantes
        conn.execute("DELETE FROM streets")
        conn.commit()
        
        # Préparer les données fraîches
        self.test_bulk_insertions_performance()
        
        # Test VACUUM
        start_time = time.time()
        db.vacuum_database()
        vacuum_time = time.time() - start_time
        
        # VACUUM doit être rapide sur une petite DB
        assert vacuum_time < 2.0, f"VACUUM trop lent: {vacuum_time:.3f}s"
        
        print(f"✅ VACUUM terminé en {vacuum_time*1000:.1f}ms")


if __name__ == "__main__":
    # Exécution directe pour tests rapides
    test = TestSQLitePerformance()
    
    print("🚀 Test de performance SQLite - PHASE 3")
    print("=" * 50)
    
    try:
        test.setup_method()
        
        test.test_pragma_optimizations()
        test.test_indexes_created()
        test.test_bulk_insertions_performance()
        test.test_bulk_reads_performance()
        test.test_cache_performance()
        test.test_vacuum_performance()
        
        print("=" * 50)
        print("✅ TOUS LES TESTS DE PERFORMANCE PASSÉS")
        
    finally:
        test.teardown_method()