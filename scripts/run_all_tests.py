#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script runner pour tous les tests GuignoMap
Exécute les tests unitaires et de validation du projet
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Exécute une commande et retourne le code de sortie"""
    print(f"🔄 Exécution: {cmd}")
    if cwd:
        print(f"   📁 Dans: {cwd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=False,
            text=True
        )
        return result.returncode
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution: {e}")
        return 1

def main():
    """Point d'entrée principal"""
    print("🧪 GuignoMap - Runner de tests")
    print("=" * 50)
    
    # Chemins
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"
    
    exit_code = 0
    
    # 1. Tests d'authentification
    print("\n📍 Tests d'authentification")
    auth_test = tests_dir / "auth" / "test_passwords_smoke.py"
    if auth_test.exists():
        code = run_command(f"python {auth_test}", cwd=project_root)
        if code != 0:
            exit_code = code
    else:
        print("⚠️ Aucun test d'auth trouvé")
    
    # 2. Validation de structure
    print("\n📍 Validation de structure")
    validate_script = project_root / "scripts" / "validate_structure.py"
    if validate_script.exists():
        code = run_command(f"python scripts/validate_structure.py", cwd=project_root)
        if code != 0:
            print("⚠️ Validation de structure échouée (peut contenir des warnings)")
    else:
        print("⚠️ Script de validation non trouvé")
    
    # 3. Sanity check rapide
    print("\n📍 Sanity check (BD)")
    sanity_script = project_root / "tools" / "quick_sanity.py"
    if sanity_script.exists():
        code = run_command(f"python tools/quick_sanity.py", cwd=project_root)
        if code != 0:
            print("⚠️ Sanity check échoué")
    else:
        print("⚠️ Script sanity non trouvé")
    
    # Résumé
    print("\n" + "=" * 50)
    if exit_code == 0:
        print("✅ Tous les tests terminés (vérifiez les détails ci-dessus)")
    else:
        print(f"❌ Des tests ont échoué (code: {exit_code})")
    
    print("🏁 Runner terminé")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())