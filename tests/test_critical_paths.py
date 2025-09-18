"""
Tests critiques pour les chemins de production GuignoMap
Ces tests vérifient les fonctionnalités essentielles en production.
"""

import os
import sys
import pytest
from pathlib import Path

# Ajouter le répertoire racine au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import guignomap.database as db


class TestCriticalPaths:
    """Tests des chemins critiques de l'application"""
    
    def test_login_admin(self):
        """Test de connexion administrateur"""
        result = db.authenticate_team("ADMIN", "RELAIS2025")
        assert result["success"] is True, "Échec de l'authentification ADMIN"
        assert result["team_id"] == "ADMIN", "ID d'équipe incorrect"
    
    def test_create_team(self):
        """Test de création d'équipe"""
        conn = db.get_conn()
        
        # Nom d'équipe de test unique
        test_team_id = "TEST_P5_001"
        test_team_name = "Équipe Test Phase 5"
        
        # Nettoyer d'abord au cas où
        conn.execute("DELETE FROM teams WHERE id = ?", (test_team_id,))
        conn.commit()
        
        # Créer l'équipe de test
        password_hash = db.hash_password("test123")
        conn.execute("""
            INSERT OR IGNORE INTO teams (id, name, password_hash)
            VALUES (?, ?, ?)
        """, (test_team_id, test_team_name, password_hash))
        conn.commit()
        
        # Vérifier qu'elle apparaît dans la liste
        teams_df = db.list_teams()
        team_ids = teams_df['id'].tolist() if not teams_df.empty else []
        
        assert test_team_id in team_ids, f"Équipe {test_team_id} non trouvée dans list_teams()"
        
        # Nettoyer après le test
        conn.execute("DELETE FROM teams WHERE id = ?", (test_team_id,))
        conn.commit()
    
    def test_assign_streets(self):
        """Test d'assignation de rue"""
        conn = db.get_conn()
        
        # Trouver une rue en statut "a_faire"
        cursor = conn.execute("""
            SELECT id, name, team, status 
            FROM streets 
            WHERE status = 'a_faire' 
            LIMIT 1
        """)
        row = cursor.fetchone()
        
        if not row:
            pytest.skip("Aucune rue 'a_faire' disponible pour le test")
        
        street_id, street_name, original_team, original_status = row
        
        try:
            # Assigner la rue à ADMIN en statut "en_cours"
            db.update_street_status(street_id, "en_cours", "ADMIN")
            
            # Vérifier la mise à jour
            cursor = conn.execute("""
                SELECT team, status 
                FROM streets 
                WHERE id = ?
            """, (street_id,))
            updated_row = cursor.fetchone()
            
            assert updated_row is not None, f"Rue {street_id} introuvable après mise à jour"
            updated_team, updated_status = updated_row
            
            assert updated_team == "ADMIN", f"Équipe incorrecte: {updated_team} != ADMIN"
            assert updated_status == "en_cours", f"Statut incorrect: {updated_status} != en_cours"
            
        finally:
            # Restaurer l'état initial
            db.update_street_status(street_id, original_status, original_team)
    
    def test_export_excel(self):
        """Test d'export Excel (si fonction disponible)"""
        try:
            from guignomap.reports import export_assignments_to_excel
        except ImportError:
            pytest.skip("export_assignments_to_excel function missing")
        
        # Fichier de test
        test_export_file = Path("exports/test_export.xlsx")
        test_export_file.parent.mkdir(exist_ok=True)
        
        # Supprimer le fichier s'il existe déjà
        if test_export_file.exists():
            test_export_file.unlink()
        
        try:
            # Exporter
            export_assignments_to_excel(str(test_export_file))
            
            # Vérifier que le fichier existe et n'est pas vide
            assert test_export_file.exists(), "Fichier d'export non créé"
            assert test_export_file.stat().st_size > 0, "Fichier d'export vide"
            
        finally:
            # Nettoyer
            if test_export_file.exists():
                test_export_file.unlink()


if __name__ == "__main__":
    # Permettre l'exécution directe du fichier
    pytest.main([__file__, "-v"])