#!/usr/bin/env python3
"""
Script de migration automatique des types DataFrame vers List[Dict] dans app.py
Corrige les incompatibilités entre l'ancien db.py et le nouveau db_v5.py
"""

import re
from pathlib import Path

def fix_app_py():
    """Corrige automatiquement les incompatibilités de types dans app.py"""
    
    app_path = Path("guignomap/app.py")
    content = app_path.read_text(encoding='utf-8')
    
    # Corrections par regex
    corrections = [
        # 1. .empty sur listes -> len() == 0
        (r'if not (\w+)\.empty:', r'if \1:  # Liste non vide'),
        (r'if (\w+)\.empty:', r'if not \1:  # Liste vide'),
        
        # 2. .iterrows() -> enumerate() ou iteration directe
        (r'for _, (\w+) in (\w+)\.iterrows\(\):', r'for \1 in \2:'),
        (r'for (\w+), (\w+) in (\w+)\.iterrows\(\):', r'for \1, \2 in enumerate(\3):'),
        
        # 3. DataFrame['column'] -> list access pour unassigned
        (r"unassigned\['name'\]\.tolist\(\)", r"unassigned"),
        
        # 4. to_csv() sur listes -> DataFrame conversion
        (r'(\w+)\.to_csv\(([^)]+)\)', r'pd.DataFrame(\1).to_csv(\2)'),
        
        # 5. team_streets filtering (fonction get_team_streets retourne List[str])
        (r"team_streets\[team_streets\['status'\] == '(\w+)'\]", r"[s for s in team_streets if hasattr(s, 'status') and s.status == '\1']"),
        
        # 6. Accès par index sur dictionnaires (notes)
        (r"note\[(\d+)\]", r"list(note.values())[\1] if isinstance(note, dict) else note[\1]"),
    ]
    
    for pattern, replacement in corrections:
        content = re.sub(pattern, replacement, content)
    
    # Corrections manuelles spécifiques
    
    # Fix pour get_team_streets qui doit retourner les données complètes, pas juste les noms
    content = content.replace(
        'def get_team_streets(team_id: str) -> List[str]:',
        'def get_team_streets(team_id: str) -> List[Dict[str, Any]]:'
    )
    
    # Fix pour l'utilisation de team_streets dans l'interface équipe
    content = re.sub(
        r'if team_streets\.empty:',
        'if not team_streets:',
        content
    )
    
    content = re.sub(
        r'done_streets = len\(team_streets\[team_streets\[\'status\'\] == \'terminee\'\]\)',
        'done_streets = len([s for s in team_streets if isinstance(s, dict) and s.get("status") == "terminee"])',
        content
    )
    
    content = re.sub(
        r'in_progress = len\(team_streets\[team_streets\[\'status\'\] == \'en_cours\'\]\)',
        'in_progress = len([s for s in team_streets if isinstance(s, dict) and s.get("status") == "en_cours"])',
        content
    )
    
    # Fix pour l'iteration sur team_streets
    content = re.sub(
        r'for street in team_streets:',
        'for street in team_streets:\n            if isinstance(street, str):\n                street_name = street\n            else:\n                street_name = street.get("name", street)',
        content
    )
    
    # Fix pour les notes dans l'affichage
    content = re.sub(
        r'st\.markdown\(f"• \*\*#{note\[0\]}\*\* : {note\[1\]} _{note\[2\]}_"\)',
        'st.markdown(f"• **#{note.get(\'address_number\', \'?\')}** : {note.get(\'comment\', \'\')} _{note.get(\'created_at\', \'\')}_ ")',
        content
    )
    
    # Sauvegarder
    app_path.write_text(content, encoding='utf-8')
    print("✅ app.py corrigé automatiquement")

if __name__ == "__main__":
    fix_app_py()