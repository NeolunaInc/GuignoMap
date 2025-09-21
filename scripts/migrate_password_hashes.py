"""
Script de migration des hashes de mots de passe bcrypt → Argon2
Migration paresseuse : les anciens hashes bcrypt sont migrés lors de la prochaine connexion
"""
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from src.auth.passwords import get_password_hash_info, is_bcrypt_hash, is_argon2_hash


def get_sqlite_connection():
    """Connexion à la base SQLite existante"""
    sqlite_path = Path(__file__).parent.parent / "guignomap" / "guigno_map.db"
    if not sqlite_path.exists():
        print(f"❌ Base SQLite non trouvée: {sqlite_path}")
        return None
    
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    return conn


def analyze_password_hashes():
    """
    Analyse des hashes de mots de passe dans la base
    Identifie les équipes avec des hashes bcrypt qui nécessitent une migration
    """
    conn = get_sqlite_connection()
    if not conn:
        return
    
    try:
        print("🔍 Analyse des hashes de mots de passe...")
        print("=" * 50)
        
        # Récupérer toutes les équipes
        cursor = conn.execute("SELECT id, name, password_hash, created_at FROM teams ORDER BY id")
        teams = cursor.fetchall()
        
        if not teams:
            print("ℹ️ Aucune équipe trouvée dans la base")
            return
        
        bcrypt_count = 0
        argon2_count = 0
        unknown_count = 0
        
        print(f"{'Équipe':<15} {'Algorithme':<10} {'Statut':<20} {'Créé le'}")
        print("-" * 65)
        
        for team in teams:
            team_id = team['id']
            name = team['name']
            hash_value = team['password_hash']
            created_at = team['created_at']
            
            # Analyser le hash
            hash_info = get_password_hash_info(hash_value)
            algorithm = hash_info['algorithm']
            needs_update = hash_info['needs_update']
            
            if algorithm == 'bcrypt':
                bcrypt_count += 1
                status = "🔄 À migrer"
            elif algorithm == 'argon2':
                argon2_count += 1
                status = "✅ Moderne" if not needs_update else "🔄 À mettre à jour"
            else:
                unknown_count += 1
                status = "❓ Inconnu"
            
            print(f"{team_id:<15} {algorithm:<10} {status:<20} {created_at or 'N/A'}")
        
        print("-" * 65)
        print(f"\n📊 Résumé de l'analyse:")
        print(f"   • Hashes bcrypt (à migrer) : {bcrypt_count}")
        print(f"   • Hashes Argon2 (modernes) : {argon2_count}")
        print(f"   • Hashes inconnus          : {unknown_count}")
        print(f"   • Total équipes            : {len(teams)}")
        
        if bcrypt_count > 0:
            print(f"\n💡 Migration nécessaire:")
            print(f"   Les {bcrypt_count} équipe(s) avec bcrypt seront automatiquement")
            print(f"   migrées vers Argon2 lors de leur prochaine connexion réussie.")
            print(f"   Aucune action manuelle n'est requise.")
        else:
            print(f"\n🎉 Toutes les équipes utilisent déjà Argon2 !")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
    finally:
        conn.close()


def generate_migration_report():
    """
    Génère un rapport détaillé de migration
    """
    conn = get_sqlite_connection()
    if not conn:
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(__file__).parent.parent / f"password_migration_report_{timestamp}.txt"
    
    try:
        with open(report_path, 'w', encoding='utf-8') as report:
            report.write(f"Rapport de migration des mots de passe - {datetime.now()}\n")
            report.write("=" * 70 + "\n\n")
            
            # Récupérer toutes les équipes
            cursor = conn.execute("SELECT id, name, password_hash, created_at FROM teams ORDER BY id")
            teams = cursor.fetchall()
            
            teams_to_migrate = []
            
            for team in teams:
                team_id = team['id']
                name = team['name']
                hash_value = team['password_hash']
                created_at = team['created_at']
                
                hash_info = get_password_hash_info(hash_value)
                
                report.write(f"Équipe: {team_id} ({name})\n")
                report.write(f"  Créée: {created_at or 'Date inconnue'}\n")
                report.write(f"  Algorithme: {hash_info['algorithm']}\n")
                report.write(f"  Nécessite mise à jour: {hash_info['needs_update']}\n")
                
                if 'passlib_scheme' in hash_info:
                    report.write(f"  Schéma passlib: {hash_info['passlib_scheme']}\n")
                
                if hash_info['algorithm'] == 'bcrypt':
                    teams_to_migrate.append(team_id)
                    report.write(f"  🔄 MIGRATION REQUISE lors de la prochaine connexion\n")
                elif hash_info['algorithm'] == 'argon2':
                    report.write(f"  ✅ Hash moderne\n")
                else:
                    report.write(f"  ⚠️ Hash de type inconnu\n")
                
                report.write("\n")
            
            report.write(f"RÉSUMÉ DE MIGRATION\n")
            report.write("=" * 30 + "\n")
            report.write(f"Équipes à migrer: {len(teams_to_migrate)}\n")
            if teams_to_migrate:
                report.write(f"IDs concernés: {', '.join(teams_to_migrate)}\n")
            report.write(f"Total équipes: {len(teams)}\n\n")
            
            report.write("PROCÉDURE DE MIGRATION\n")
            report.write("=" * 30 + "\n")
            report.write("1. La migration est automatique et transparente\n")
            report.write("2. Elle se déclenche lors de la prochaine connexion réussie\n")
            report.write("3. L'ancien hash bcrypt est remplacé par un nouveau hash Argon2\n")
            report.write("4. Le mot de passe de l'utilisateur reste inchangé\n")
            report.write("5. Aucune action manuelle n'est requise\n\n")
            
            report.write("POLITIQUE DE MOT DE PASSE\n")
            report.write("=" * 30 + "\n")
            report.write("• Minimum 4 caractères (politique UI v4.1 conservée)\n")
            report.write("• Confirmation requise lors de la création (UI)\n")
            report.write("• Algorithme Argon2 pour nouveaux comptes\n")
            report.write("• Compatibilité bcrypt maintenue\n")
        
        print(f"📄 Rapport généré: {report_path}")
        
    except Exception as e:
        print(f"❌ Erreur génération rapport: {e}")
    finally:
        conn.close()


def test_migration_functions():
    """
    Test des fonctions de migration avec des données d'exemple
    """
    print("🧪 Test des fonctions de migration...")
    
    try:
        from src.auth.passwords import create_test_hashes, verify_password, migrate_password_if_needed
        
        # Créer des hashes de test
        test_password = "test123"
        hashes = create_test_hashes(test_password)
        
        print(f"\n🔑 Mot de passe de test: {test_password}")
        print(f"Hash Argon2: {hashes['argon2'][:50]}...")
        print(f"Hash bcrypt: {hashes['bcrypt_legacy'][:50]}...")
        
        # Tester la vérification
        print(f"\n✅ Tests de vérification:")
        
        # Test Argon2
        ok, needs_rehash = verify_password(test_password, hashes['argon2'])
        print(f"Argon2: OK={ok}, Rehash={needs_rehash}")
        
        # Test bcrypt
        ok, needs_rehash = verify_password(test_password, hashes['bcrypt_legacy'])
        print(f"bcrypt: OK={ok}, Rehash={needs_rehash}")
        
        # Test migration
        print(f"\n🔄 Test de migration:")
        migrated, new_hash = migrate_password_if_needed(test_password, hashes['bcrypt_legacy'])
        print(f"Migration effectuée: {migrated}")
        if migrated:
            print(f"Nouveau hash: {new_hash[:50]}...")
        
        print(f"✅ Tests terminés avec succès")
        
    except Exception as e:
        print(f"❌ Erreur durant les tests: {e}")


def main():
    """Point d'entrée principal du script"""
    print("🔐 Script de migration des mots de passe GuignoMap v5.0")
    print("bcrypt → Argon2 avec migration paresseuse")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "analyze":
            analyze_password_hashes()
        elif command == "report":
            generate_migration_report()
        elif command == "test":
            test_migration_functions()
        else:
            print(f"❌ Commande inconnue: {command}")
            print_usage()
    else:
        # Par défaut, faire l'analyse
        analyze_password_hashes()


def print_usage():
    """Affiche l'aide d'utilisation"""
    print("\nUtilisation:")
    print("  python scripts/migrate_password_hashes.py [commande]")
    print("\nCommandes disponibles:")
    print("  analyze  - Analyser les hashes actuels (défaut)")
    print("  report   - Générer un rapport détaillé")
    print("  test     - Tester les fonctions de migration")
    print("\nExemples:")
    print("  python scripts/migrate_password_hashes.py analyze")
    print("  python scripts/migrate_password_hashes.py report")


if __name__ == "__main__":
    main()