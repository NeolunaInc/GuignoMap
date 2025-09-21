#!/usr/bin/env python3
"""
Script de correction fine pour les types de retour dans app.py
"""

import re
from pathlib import Path

def fix_specific_issues():
    """Corrige les problèmes spécifiques identifiés"""
    
    app_path = Path("guignomap/app.py")
    content = app_path.read_text(encoding='utf-8')
    
    # 1. Revert les corrections sur DataFrames (list_streets retourne bien un DataFrame)
    content = re.sub(
        r'if df_all:  # Liste non vide',
        'if not df_all.empty:',
        content
    )
    
    content = re.sub(
        r'if not df_team:  # Liste vide',
        'if df_team.empty:',
        content
    )
    
    # 2. Fix team_streets access patterns
    content = re.sub(
        r'done_streets = len\(\[s for s in team_streets if hasattr\(s, \'status\'\) and s\.status == \'terminee\'\]\)',
        'done_streets = len([s for s in team_streets if s.get("status") == "terminee"])',
        content
    )
    
    content = re.sub(
        r'in_progress = len\(\[s for s in team_streets if hasattr\(s, \'status\'\) and s\.status == \'en_cours\'\]\)',
        'in_progress = len([s for s in team_streets if s.get("status") == "en_cours"])',
        content
    )
    
    # 3. Fix row access in iterrows (certains endroits ont encore des DataFrames)
    content = re.sub(
        r"for row in df_team:\s*street = row\['name'\]\s*status = row\['status'\]\s*notes_count = row\.get\('notes', 0\)",
        """for _, row in df_team.iterrows():
            street = row['name']
            status = row['status'] 
            notes_count = row.get('notes', 0)""",
        content, flags=re.MULTILINE
    )
    
    app_path.write_text(content, encoding='utf-8')
    print("✅ Corrections spécifiques appliquées")

if __name__ == "__main__":
    fix_specific_issues()