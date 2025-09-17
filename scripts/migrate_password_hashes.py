#!/usr/bin/env python3
"""
Script de migration manuelle des mots de passe vers Argon2
Migration batch de tous les hashes legacy vers Argon2

Usage:
    python scripts/migrate_password_hashes.py [--dry-run] [--team=TEAM_ID]
    
Options:
    --dry-run    : Simulation sans modifications
    --team=ID    : Migrer seulement l equipe specifiee
"""
import sys
import os
import argparse
import getpass
from pathlib import Path

# Ajout du chemin du projet pour les imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.operations import count_hash_algorithms, get_session
from src.auth.passwords import hash_password, detect_hash_algo
from sqlalchemy import text


def main():
    """Point d entree principal"""
    print("Migration des mots de passe vers Argon2")
    print("Script disponible mais necessite implementation complete")


if __name__ == "__main__":
    main()
