#!/usr/bin/env python3
"""
Script de validation de la prête pour la production
Tests d'encodage, charge simulée et robustesse de la base de données.

Usage: python scripts/validate_production_ready.py
"""

import sys
import time
from pathlib import Path

# Ajouter le répertoire racine au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from guignomap.database import get_conn


def test_encoding_and_special_characters():
    """Test l'encodage et les caractères spéciaux"""
    print("🔤 Test encodage et caractères spéciaux...")
    
    conn = get_conn()
    try:
        # Commencer une transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Créer une table temporaire pour le test d'encodage
        conn.execute("""
            CREATE TEMP TABLE test_encoding (
                id INTEGER PRIMARY KEY,
                street_name TEXT,
                comment TEXT
            )
        """)
        
        # Insérer temporairement un enregistrement avec accents
        test_data = {
            "street_name": "Érable",
            "comment": "Français: éèà ÉÈÀ ç ñ ü ß 中文 🎄"
        }
        
        conn.execute("""
            INSERT INTO test_encoding (street_name, comment)
            VALUES (?, ?)
        """, (test_data["street_name"], test_data["comment"]))
        
        # Vérifier round-trip
        cursor = conn.execute("""
            SELECT street_name, comment 
            FROM test_encoding 
            WHERE street_name = ?
        """, (test_data["street_name"],))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError("Enregistrement de test non trouvé")
        
        retrieved_street, retrieved_comment = row
        
        # Vérifier l'intégrité des données
        if retrieved_street != test_data["street_name"]:
            raise ValueError(f"Street name corrompu: {retrieved_street} != {test_data['street_name']}")
        if retrieved_comment != test_data["comment"]:
            raise ValueError(f"Comment corrompu: {retrieved_comment} != {test_data['comment']}")
        
        print("   ✅ Encodage UTF-8 et caractères spéciaux: OK")
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur encodage: {e}")
        return False
    finally:
        # ROLLBACK pour ne rien laisser
        conn.execute("ROLLBACK")


def test_simulated_load():
    """Test de charge simulée avec 1000+ rues"""
    print("⚡ Test charge simulée (1000+ rues)...")
    
    conn = get_conn()
    try:
        # Créer une table temporaire
        conn.execute("""
            CREATE TEMP TABLE temp_streets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sector TEXT,
                team TEXT,
                status TEXT DEFAULT 'a_faire'
            )
        """)
        
        # Copier les rues existantes avec suffixe unique
        start_time = time.time()
        conn.execute("""
            INSERT INTO temp_streets (name, sector, team, status)
            SELECT name || ' [SIM]', sector, team, status
            FROM streets
        """)
        
        # Ajouter des rues supplémentaires pour atteindre 1000+
        cursor = conn.execute("SELECT COUNT(*) FROM temp_streets")
        current_count = cursor.fetchone()[0]
        
        if current_count < 1000:
            needed = 1000 - current_count
            print(f"   📊 Ajout de {needed} rues supplémentaires...")
            
            for i in range(needed):
                conn.execute("""
                    INSERT INTO temp_streets (name, sector, team, status)
                    VALUES (?, ?, ?, ?)
                """, (f"Rue Test {i+1:04d} [SIM]", f"Secteur {(i % 10) + 1}", 
                      "ADMIN" if i % 5 == 0 else "", "a_faire"))
        
        load_time = time.time() - start_time
        
        # Vérifier le count total
        cursor = conn.execute("SELECT COUNT(*) FROM temp_streets")
        total_count = cursor.fetchone()[0]
        
        # Tests de performance sur requêtes filtrées
        start_time = time.time()
        
        # Test 1: Filter par status
        cursor = conn.execute("SELECT COUNT(*) FROM temp_streets WHERE status = 'a_faire'")
        status_count = cursor.fetchone()[0]
        
        # Test 2: Filter par team
        cursor = conn.execute("SELECT COUNT(*) FROM temp_streets WHERE team = 'ADMIN'")
        team_count = cursor.fetchone()[0]
        
        # Test 3: Filter par sector avec LIKE
        cursor = conn.execute("SELECT COUNT(*) FROM temp_streets WHERE sector LIKE 'Secteur%'")
        sector_count = cursor.fetchone()[0]
        
        # Test 4: Requête complexe avec ORDER BY
        cursor = conn.execute("""
            SELECT status, COUNT(*) as count 
            FROM temp_streets 
            GROUP BY status 
            ORDER BY count DESC
        """)
        status_stats = cursor.fetchall()
        
        query_time = time.time() - start_time
        
        print(f"   📊 Rues chargées: {total_count}")
        print(f"   ⏱️  Temps de chargement: {load_time:.3f}s")
        print(f"   ⏱️  Temps requêtes: {query_time:.3f}s")
        print(f"   🔍 Filtres - Status 'a_faire': {status_count}, Team 'ADMIN': {team_count}, Secteurs: {sector_count}")
        
        # Validation des performances
        if load_time > 5.0:
            print(f"   ⚠️  Chargement lent: {load_time:.3f}s > 5s")
        if query_time > 2.0:
            print(f"   ⚠️  Requêtes lentes: {query_time:.3f}s > 2s")
        
        if total_count >= 1000 and load_time <= 10.0 and query_time <= 5.0:
            print("   ✅ Test de charge: OK")
            return True
        else:
            print("   ❌ Test de charge: ÉCHEC")
            return False
            
    except Exception as e:
        print(f"   ❌ Erreur charge simulée: {e}")
        return False
    finally:
        # Nettoyer la table temporaire (elle sera automatiquement supprimée)
        try:
            conn.execute("DROP TABLE IF EXISTS temp_streets")
        except:
            pass  # Table temporaire déjà supprimée


def test_database_integrity():
    """Test l'intégrité de la base de données"""
    print("🔧 Test intégrité base de données...")
    
    conn = get_conn()
    try:
        # Vérifier les tables principales
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('streets', 'teams', 'notes')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['streets', 'teams', 'notes']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"   ❌ Tables manquantes: {missing_tables}")
            return False
        
        # Vérifier les contraintes
        cursor = conn.execute("SELECT COUNT(*) FROM streets")
        streets_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM teams")
        teams_count = cursor.fetchone()[0]
        
        if streets_count == 0:
            print("   ❌ Aucune rue dans la base")
            return False
        
        if teams_count == 0:
            print("   ❌ Aucune équipe dans la base")
            return False
        
        print(f"   📊 {streets_count} rues, {teams_count} équipes")
        print("   ✅ Intégrité base de données: OK")
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur intégrité: {e}")
        return False


def main():
    """Fonction principale de validation"""
    print("🚀 Validation Production Ready - GuignoMap")
    print("=" * 50)
    
    tests_results = []
    
    # Test 1: Encodage
    tests_results.append(test_encoding_and_special_characters())
    
    # Test 2: Charge simulée
    tests_results.append(test_simulated_load())
    
    # Test 3: Intégrité
    tests_results.append(test_database_integrity())
    
    # Résumé final
    print("\n" + "=" * 50)
    passed_tests = sum(tests_results)
    total_tests = len(tests_results)
    
    print(f"📋 Résultats: {passed_tests}/{total_tests} tests réussis")
    
    if all(tests_results):
        print("🎉 READY: PASS - Application prête pour la production!")
        sys.exit(0)
    else:
        print("❌ READY: FAIL - Problèmes détectés, correction requise")
        sys.exit(1)


if __name__ == "__main__":
    main()