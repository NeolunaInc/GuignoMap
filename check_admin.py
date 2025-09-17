#!/usr/bin/env python3
"""
Script temporaire pour vérifier le mot de passe admin
"""
import sqlite3
from pathlib import Path

# Chemin vers la base de données
db_path = Path("guignomap/guigno_map.db")

if not db_path.exists():
    print(f"❌ Base de données non trouvée: {db_path}")
    exit(1)

# Connexion à la base
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Vérifier la structure de la table teams
    cursor.execute("PRAGMA table_info(teams)")
    columns = cursor.fetchall()
    print("📋 Structure de la table teams:")
    for col in columns:
        print(f"   {col}")
    
    # Rechercher l'équipe admin
    cursor.execute("SELECT * FROM teams WHERE name = 'admin'")
    admin_team = cursor.fetchone()
    
    if admin_team:
        print(f"\n✅ Équipe admin trouvée:")
        print(f"   Données: {admin_team}")
    else:
        print("\n❌ Aucune équipe admin trouvée")
        
        # Lister toutes les équipes
        cursor.execute("SELECT * FROM teams LIMIT 5")
        teams = cursor.fetchall()
        print("\n📋 Premières équipes dans la base:")
        for team in teams:
            print(f"   {team}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Erreur: {e}")