#!/usr/bin/env python3
"""
GuignoMap - Import d'adresses depuis Excel pour une ville
CLI réutilisable pour l'import autoritatif d'adresses
"""
import sys
import argparse
import logging
from pathlib import Path
import pandas as pd

# Ajouter le répertoire parent au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from guignomap.imports import detect_schema, prepare_dataframe, authoritative_swap
from guignomap.database import get_conn


def setup_logging(verbose: bool = False):
    """Configure le logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def import_city_addresses(city: str, file_path: Path, verbose: bool = False) -> bool:
    """
    Importe les adresses d'une ville depuis un fichier Excel
    
    Returns:
        bool: True si succès, False sinon
    """
    setup_logging(verbose)
    
    try:
        # 1. Lecture du fichier Excel
        logging.info(f"📁 Lecture de {file_path}")
        if not file_path.exists():
            logging.error(f"Fichier non trouvé: {file_path}")
            return False
        
        df = pd.read_excel(file_path)
        logging.info(f"📊 Fichier Excel: {len(df)} lignes, {len(df.columns)} colonnes")
        
        # 2. Détection automatique du schéma
        mapping = detect_schema(df, city)
        if 'street' not in mapping or 'number' not in mapping:
            logging.error("Impossible de détecter les colonnes rue/numéro obligatoires")
            logging.error(f"Colonnes disponibles: {list(df.columns)}")
            return False
        
        logging.info(f"🔍 Schéma détecté: {mapping}")
        
        # 3. Préparation des données
        logging.info("🔧 Préparation des données...")
        df_prepared = prepare_dataframe(df, mapping, city)
        logging.info(f"✅ Données préparées: {len(df_prepared)} adresses uniques")
        
        # 4. Import en base de données
        logging.info("💾 Import en base de données...")
        with get_conn() as conn:
            stats = authoritative_swap(conn, df_prepared)
        
        # 5. Rapport final
        logging.info("📈 RAPPORT D'IMPORT")
        logging.info(f"  • Total Excel original: {len(df):,}")
        logging.info(f"  • Adresses uniques: {len(df_prepared):,}")
        logging.info(f"  • Doublons ignorés: {len(df) - len(df_prepared):,}")
        logging.info(f"  • Total final en DB: {stats['total_imported']:,}")
        logging.info(f"  • Assignations préservées: {stats['preserved_assignments']:,}")
        
        if len(df) > 0:
            delta_pct = (len(df_prepared) / len(df)) * 100
            logging.info(f"  • Delta (%): {delta_pct:.1f}%")
        
        logging.info(f"✅ Import de {city} terminé avec succès!")
        
        # Forcer l'affichage des logs
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Confirmation finale
        print(f"\n✅ IMPORT TERMINÉ")
        print(f"   Total importé: {stats['total_imported']}")
        print(f"   Assignations préservées: {stats['preserved_assignments']}")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'import: {e}")
        if verbose:
            logging.exception("Détails de l'erreur:")
        return False


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Import d'adresses depuis Excel pour GuignoMap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s --city mascouche --file imports/mascouche_adresses.xlsx
  %(prog)s --city montreal --file data/mtl.xlsx --verbose
        """
    )
    
    parser.add_argument(
        '--city',
        required=True,
        help='Nom de la ville (utilisé pour les logs et la détection)'
    )
    
    parser.add_argument(
        '--file',
        required=True,
        type=Path,
        help='Chemin vers le fichier Excel à importer'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Affichage détaillé (debug)'
    )
    
    args = parser.parse_args()
    
    # Exécution de l'import
    success = import_city_addresses(args.city, args.file, args.verbose)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())