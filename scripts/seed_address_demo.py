# scripts/seed_address_demo.py
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import guignomap.database as db

def main():
    print("=== Demo d'assignation d'adresses ===")
    
    # Initialiser la DB
    db.init_db()
    
    # 1. Trouver une équipe cible (première non-ADMIN ou 'Equipe 1')
    try:
        teams = db.get_teams_list()  # [(id, name), ...]
        if not teams:
            print("❌ Aucune équipe trouvée. Créez d'abord des équipes.")
            return
        
        # Chercher une équipe non-ADMIN
        target_team = None
        for team_id, team_name in teams:
            if team_id != "ADMIN":
                target_team = (team_id, team_name)
                break
        
        # Fallback : chercher 'Equipe 1'
        if not target_team:
            for team_id, team_name in teams:
                if team_id == "Equipe 1" or team_name == "Equipe 1":
                    target_team = (team_id, team_name)
                    break
        
        if not target_team:
            # Prendre la première équipe disponible
            target_team = teams[0]
        
        team_id, team_name = target_team
        print(f"🎯 Équipe cible : {team_name} (ID: {team_id})")
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des équipes : {e}")
        return
    
    # 2. Récupérer 5 adresses non assignées
    try:
        unassigned_df = db.get_unassigned_addresses(limit=5)
        
        if unassigned_df.empty:
            print("✅ Aucune adresse non assignée trouvée (toutes sont déjà assignées)")
            return
        
        print(f"📍 {len(unassigned_df)} adresse(s) non assignée(s) trouvée(s) :")
        for _, row in unassigned_df.iterrows():
            sector_info = f" (secteur: {row['sector']})" if row['sector'] else ""
            print(f"  - ID:{row['id']} | {row['street_name']} {row['house_number']}{sector_info}")
        
        # Extraire les IDs
        address_ids = unassigned_df['id'].tolist()
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des adresses : {e}")
        return
    
    # 3. Assigner les adresses à l'équipe
    try:
        assigned_count = db.assign_addresses_to_team(address_ids, team_id)
        print(f"✅ {assigned_count} adresse(s) assignée(s) à l'équipe '{team_name}' (ID: {team_id})")
        
        # Invalider les caches
        try:
            db.invalidate_caches()
            print("🔄 Caches invalidés")
        except:
            pass
        
    except Exception as e:
        print(f"❌ Erreur lors de l'assignation : {e}")
        return
    
    # 4. Résumé final
    print("\n=== Résumé ===")
    try:
        # Compter les adresses assignées à cette équipe
        team_addresses = db.get_team_addresses(team_id, limit=1000)
        total_assigned = len(team_addresses)
        print(f"📊 L'équipe '{team_name}' a maintenant {total_assigned} adresse(s) assignée(s)")
        
        # Compter les adresses encore non assignées
        remaining_unassigned = db.get_unassigned_addresses(limit=1000)
        remaining_count = len(remaining_unassigned)
        print(f"📊 Il reste {remaining_count} adresse(s) non assignée(s) au total")
        
    except Exception as e:
        print(f"⚠️ Impossible de générer le résumé complet : {e}")
    
    print("✅ Demo terminée avec succès !")

if __name__ == "__main__":
    main()