#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Correcteur de mojibake dans la base de données

Analyse et corrige les chaînes mojibakées dans la DB (labels, titres, settings).
ÉVITE les notes libres des bénévoles pour éviter les faux-positifs.

Usage:
    python scripts/fix_mojibake_db.py                    # DRY-RUN (affichage only)
    python scripts/fix_mojibake_db.py --apply            # Application des corrections
    python scripts/fix_mojibake_db.py --verbose          # Mode détaillé
"""

import sys
import os
import argparse
from typing import Dict, List, Tuple, Optional

# Ajouter le répertoire parent au path pour importer src/
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Mapping de correction des mojibakes les plus fréquents  
MOJIBAKE_FIXES = {
    # Caractères accentués français courants
    "Ã©": "é",
    "Ã¨": "è", 
    "Ã ": "à",
    "Ã´": "ô",
    "Ã»": "û",
    "Ã®": "î",
    "Ã§": "ç",
    "Ã¢": "â",
    "Ã¹": "ù",
    "Ã«": "ë",
    "Ã¯": "ï",
    "Ã¼": "ü",
    
    # Majuscules accentuées basiques
    "Ã‰": "É",
    "Ã€": "À", 
    "Ã‡": "Ç",
    
    # Espaces et caractères de contrôle
    "Â ": " ",   # espace insécable mojibakée
    "Â": "",     # caractère de contrôle isolé
}


def detect_mojibake(text: str) -> bool:
    """Détecte si une chaîne contient probablement du mojibake"""
    if not text:
        return False
    
    # Recherche des patterns dans notre mapping
    for pattern in MOJIBAKE_FIXES.keys():
        if pattern in text:
            return True
    
    # Recherche de patterns supplémentaires (caractères suspects en séquence)
    suspicious_patterns = ["Ã", "â€", "√", "Â", "Ë", "Ñ"]
    for pattern in suspicious_patterns:
        if pattern in text:
            return True
    
    return False


def fix_mojibake(text: str) -> Tuple[str, bool]:
    """
    Corrige le mojibake dans une chaîne
    
    Returns:
        (texte_corrigé, a_été_modifié)
    """
    if not text:
        return text, False
    
    original = text
    result = text
    
    # Appliquer les corrections du mapping
    for pattern, replacement in MOJIBAKE_FIXES.items():
        result = result.replace(pattern, replacement)
    
    return result, result != original


def get_correctable_text_fields() -> Dict[str, List[str]]:
    """
    Retourne les tables et champs texte que l'on peut corriger en toute sécurité
    
    ÉVITE les notes libres pour éviter les faux-positifs
    """
    return {
        "teams": ["name"],       # Nom d'équipe (safe à corriger)
        "streets": ["name"],     # Nom de rue (safe à corriger) 
        # "notes": [],           # ÉVITÉ: notes libres des bénévoles
        # "activity_log": [],    # ÉVITÉ: logs peuvent contenir des données brutes
    }


def scan_database_mojibake(verbose: bool = False) -> List[Tuple[str, str, int, str, str]]:
    """
    Scanne la DB pour détecter le mojibake
    
    Returns:
        List de (table, field, record_id, old_value, new_value)
    """
    try:
        from src.database.connection import get_session
        from sqlalchemy import text
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return []
    
    issues = []
    correctable_fields = get_correctable_text_fields()
    
    try:
        with get_session() as session:
            for table, fields in correctable_fields.items():
                if verbose:
                    print(f"🔍 Scan table: {table}")
                
                for field in fields:
                    if verbose:
                        print(f"  📋 Champ: {field}")
                    
                    # Requête pour récupérer les enregistrements
                    query = f"SELECT id, {field} FROM {table} WHERE {field} IS NOT NULL"
                    result = session.execute(text(query))
                    
                    for row in result:
                        record_id, value = row
                        
                        if detect_mojibake(value):
                            fixed_value, was_changed = fix_mojibake(value)
                            if was_changed:
                                issues.append((table, field, record_id, value, fixed_value))
                                if verbose:
                                    print(f"    🔧 ID {record_id}: '{value}' -> '{fixed_value}'")
    
    except Exception as e:
        print(f"❌ Erreur scan DB: {e}")
        return []
    
    return issues


def apply_fixes(issues: List[Tuple[str, str, int, str, str]], verbose: bool = False) -> int:
    """
    Applique les corrections dans la base de données
    
    Returns:
        Nombre de corrections appliquées
    """
    try:
        from src.database.connection import get_session
        from sqlalchemy import text
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return 0
    
    applied = 0
    
    try:
        with get_session() as session:
            for table, field, record_id, old_value, new_value in issues:
                if verbose:
                    print(f"🔧 Correction {table}.{field} ID {record_id}")
                    print(f"   Avant: {old_value}")
                    print(f"   Après: {new_value}")
                
                # Application de la correction
                query = f"UPDATE {table} SET {field} = :new_value WHERE id = :record_id"
                session.execute(text(query), {
                    "new_value": new_value,
                    "record_id": record_id
                })
                applied += 1
            
            session.commit()
            
    except Exception as e:
        print(f"❌ Erreur application corrections: {e}")
        return 0
    
    return applied


def print_issues_report(issues: List[Tuple[str, str, int, str, str]]):
    """Affiche un rapport des problèmes détectés"""
    if not issues:
        print("✅ Aucun mojibake détecté dans la DB !")
        return
    
    print(f"🔍 {len(issues)} problème(s) de mojibake détecté(s):\n")
    
    # Grouper par table
    by_table = {}
    for table, field, record_id, old_value, new_value in issues:
        if table not in by_table:
            by_table[table] = []
        by_table[table].append((field, record_id, old_value, new_value))
    
    for table, table_issues in by_table.items():
        print(f"📋 Table '{table}': {len(table_issues)} problème(s)")
        
        for field, record_id, old_value, new_value in table_issues:
            print(f"   🔧 {field} (ID {record_id}):")
            print(f"      Avant: {old_value}")
            print(f"      Après: {new_value}")
        print()


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Correcteur de mojibake dans la DB")
    parser.add_argument("--apply", action="store_true",
                       help="Applique les corrections (sinon DRY-RUN)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Affichage détaillé")
    
    args = parser.parse_args()
    
    print("🔍 Scanner de mojibake dans la base de données")
    print("⚠️  Note: évite les notes libres pour éviter les faux-positifs")
    
    if not args.apply:
        print("🔬 Mode DRY-RUN: aucune modification ne sera appliquée")
    
    print()
    
    # Scan
    print("🔍 Analyse de la base de données...")
    issues = scan_database_mojibake(args.verbose)
    
    # Rapport
    print_issues_report(issues)
    
    if issues and args.apply:
        print("🔧 Application des corrections...")
        applied = apply_fixes(issues, args.verbose)
        print(f"✅ {applied} correction(s) appliquée(s)")
    elif issues:
        print(f"💡 Utilisez --apply pour corriger {len(issues)} problème(s)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())