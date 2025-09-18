#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script administrateur pour afficher les statistiques des algorithmes de hash
Utilise count_hash_algorithms() de src.database.operations

Usage:
    python scripts/show_hash_stats.py
"""

import sys
import os

# Ajouter le répertoire parent au path pour importer src/
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def main():
    """Affiche les statistiques des algorithmes de hash"""
    try:
        from guignomap.database import count_hash_algorithms
        
        print("🔐 Statistiques des algorithmes de hash des équipes")
        print("=" * 55)
        
        stats = count_hash_algorithms()
        
        if not stats:
            print("❌ Aucune équipe avec mot de passe trouvée")
            return 1
        
        total = sum(v for k, v in stats.items() if k != "empty")
        total_with_empty = total + stats.get("empty", 0)
        
        print(f"📊 Total équipes actives: {total_with_empty}")
        print(f"🔑 Équipes avec mot de passe: {total}")
        print(f"🚫 Équipes sans mot de passe: {stats.get('empty', 0)}")
        print()
        
        if total > 0:
            print("📈 Répartition par algorithme:")
            print("-" * 30)
            
            for algo, count in sorted(stats.items()):
                if algo == "empty":
                    continue
                    
                if count > 0:
                    percent = (count / total) * 100
                    icon = "✅" if algo == "argon2" else "⚠️" if algo == "bcrypt" else "❌"
                    print(f"{icon} {algo:12} : {count:3d} ({percent:5.1f}%)")
            
            print()
            
            # Recommandations
            bcrypt_count = stats.get("bcrypt", 0)
            other_count = sum(v for k, v in stats.items() if k not in ["argon2", "bcrypt", "empty"])
            
            if bcrypt_count > 0:
                print(f"🔄 {bcrypt_count} équipes utilisent encore bcrypt (migration auto au login)")
            if other_count > 0:
                print(f"⚠️  {other_count} équipes utilisent des algorithmes legacy (nécessitent intervention)")
            if stats.get("argon2", 0) == total:
                print("🎉 Migration complète vers Argon2 !")
        
        return 0
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("Assurez-vous d'être dans le bon répertoire et que l'environnement Python est activé")
        return 1
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())