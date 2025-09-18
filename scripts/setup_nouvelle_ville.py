#!/usr/bin/env python3
"""
Script de setup pour une nouvelle ville
Usage: python scripts/setup_nouvelle_ville.py "Nom De Ville"

Crée un clone de la base de données SQLite pour une nouvelle ville.
"""

import sys
import re
from pathlib import Path
import shutil


def slugify(text):
    """Convertit un nom de ville en slug utilisable comme nom de fichier"""
    # Convertir en minuscules
    text = text.lower()
    # Remplacer espaces et caractères spéciaux par des underscores
    text = re.sub(r'[^a-z0-9]+', '_', text)
    # Supprimer les underscores en début/fin
    text = text.strip('_')
    return text


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/setup_nouvelle_ville.py \"Nom De Ville\"")
        sys.exit(1)
    
    ville_nom = sys.argv[1].strip()
    if not ville_nom:
        print("Erreur: Le nom de ville ne peut pas être vide")
        sys.exit(1)
    
    # Créer le slug
    slug = slugify(ville_nom)
    if not slug:
        print(f"Erreur: Impossible de créer un slug valide pour '{ville_nom}'")
        sys.exit(1)
    
    # Chemins
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    source_db = project_root / "guignomap" / "guigno_map.db"
    data_dir = project_root / "data"
    target_db = data_dir / f"{slug}.db"
    
    # Vérifier que la DB source existe
    if not source_db.exists():
        print(f"Erreur: Base de données source introuvable: {source_db}")
        sys.exit(1)
    
    # Créer le dossier data/ s'il n'existe pas
    data_dir.mkdir(exist_ok=True)
    
    # Vérifier si le fichier cible existe déjà
    if target_db.exists():
        print(f"Attention: Le fichier {target_db} existe déjà et sera écrasé")
    
    try:
        # Copier la base de données
        shutil.copy2(source_db, target_db)
        print(f"✅ Base de données créée pour '{ville_nom}'")
        print(f"   Slug: {slug}")
        print(f"   Fichier: {target_db.absolute()}")
        
    except Exception as e:
        print(f"Erreur lors de la copie: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()