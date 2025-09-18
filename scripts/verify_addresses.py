#!/usr/bin/env python3
"""
GuignoMap - Vérification robuste des adresses importées
Compare Excel source vs DB et détecte les anomalies
"""
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

# Ajouter le répertoire parent au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from guignomap.imports import detect_schema, prepare_dataframe
from guignomap.database import get_conn


def setup_logging(verbose: bool = False):
    """Configure le logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def verify_addresses_robust(city: str, excel_file: Path, verbose: bool = False) -> bool:
    """
    Vérification robuste avec comparaison Excel vs DB
    
    Returns:
        bool: True si vérification OK, False si anomalies détectées
    """
    setup_logging(verbose)
    
    try:
        # 1. Rechargement et préparation Excel
        logging.info(f"🔄 Rechargement du fichier Excel: {excel_file}")
        if not excel_file.exists():
            logging.error(f"Fichier Excel introuvable: {excel_file}")
            return False
        
        df_excel = pd.read_excel(excel_file)
        logging.info(f"📊 Excel: {len(df_excel)} lignes, {len(df_excel.columns)} colonnes")
        
        # 2. Préparation des données Excel (même logique que l'import)
        mapping = detect_schema(df_excel, city)
        if 'street' not in mapping or 'number' not in mapping:
            logging.error("Impossible de détecter les colonnes rue/numéro")
            return False
        
        df_prepared = prepare_dataframe(df_excel, mapping, city)
        logging.info(f"✅ Excel préparé: {len(df_prepared)} adresses uniques")
        
        # 3. Lecture de la base de données
        logging.info("🔍 Analyse de la base de données...")
        with get_conn() as conn:
            cursor = conn.cursor()
            
            # Statistiques DB
            cursor.execute("SELECT COUNT(*) FROM addresses")
            db_total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT addr_key) FROM addresses")
            db_unique_keys = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM addresses WHERE assigned_to IS NOT NULL AND assigned_to != ''")
            db_assigned = cursor.fetchone()[0]
            
            logging.info(f"💾 DB: {db_total} adresses, {db_unique_keys} clés uniques, {db_assigned} assignées")
        
        # 4. Comparaisons et analyses
        anomalies = []
        verification_ok = True
        
        # Test 1: Comparaison des totaux
        excel_unique = len(df_prepared)
        doublons_excel = len(df_excel) - excel_unique
        delta_total = abs(db_total - excel_unique)
        
        logging.info("📈 ANALYSE COMPARATIVE")
        logging.info(f"  • Excel original: {len(df_excel):,}")
        logging.info(f"  • Excel unique: {excel_unique:,}")
        logging.info(f"  • Doublons Excel supprimés: {doublons_excel:,}")
        logging.info(f"  • DB total: {db_total:,}")
        logging.info(f"  • Delta (DB vs Excel unique): {delta_total:,}")
        
        if delta_total > 0:
            verification_ok = False
            anomalies.append({
                'type': 'DELTA_TOTAL',
                'description': f'DB ({db_total}) != Excel unique ({excel_unique})',
                'valeur_attendue': excel_unique,
                'valeur_reelle': db_total,
                'ecart': delta_total
            })
        
        # Test 2: Vérification unicité clés
        if db_unique_keys != db_total:
            verification_ok = False
            doublons_db = db_total - db_unique_keys
            anomalies.append({
                'type': 'DOUBLONS_DB',
                'description': f'Clés non uniques en DB: {doublons_db} doublons',
                'valeur_attendue': db_total,
                'valeur_reelle': db_unique_keys,
                'ecart': doublons_db
            })
            logging.warning(f"⚠️ Doublons en DB: {doublons_db}")
        
        # Test 3: Vérification cohérence des clés (échantillon)
        if db_total > 0:
            with get_conn() as conn:
                sample_db = pd.read_sql_query("""
                    SELECT street_name, house_number, postal_code, addr_key 
                    FROM addresses 
                    LIMIT 100
                """, conn)
                
                # Recalculer les clés et comparer
                from guignomap.imports import build_addr_key
                sample_db['addr_key_recalc'] = sample_db.apply(
                    lambda row: build_addr_key(row['street_name'], row['house_number'], row['postal_code']),
                    axis=1
                )
                
                key_mismatches = sample_db[sample_db['addr_key'] != sample_db['addr_key_recalc']]
                if len(key_mismatches) > 0:
                    verification_ok = False
                    anomalies.append({
                        'type': 'CLES_INCOHERENTES',
                        'description': f'Clés addr_key incohérentes: {len(key_mismatches)} sur 100 échantillonnées',
                        'valeur_attendue': 0,
                        'valeur_reelle': len(key_mismatches),
                        'ecart': len(key_mismatches)
                    })
                    logging.warning(f"⚠️ Clés incohérentes détectées: {len(key_mismatches)}")
        
        # 5. Export des anomalies si nécessaire
        if anomalies:
            exports_dir = Path("exports/maintenance")
            exports_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            anomalies_file = exports_dir / f"verify_anomalies_{city}_{timestamp}.csv"
            
            df_anomalies = pd.DataFrame(anomalies)
            df_anomalies.to_csv(anomalies_file, index=False, encoding='utf-8')
            
            logging.warning(f"📁 Anomalies exportées: {anomalies_file}")
        
        # 6. Rapport final
        if verification_ok:
            logging.info("✅ VÉRIFICATION RÉUSSIE - Aucune anomalie détectée")
            logging.info(f"  • Cohérence Excel ↔ DB: ✅")
            logging.info(f"  • Unicité clés DB: ✅") 
            logging.info(f"  • Intégrité addr_key: ✅")
        else:
            logging.error("❌ ANOMALIES DÉTECTÉES")
            for anomalie in anomalies:
                logging.error(f"  • {anomalie['type']}: {anomalie['description']}")
        
        return verification_ok
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la vérification: {e}")
        if verbose:
            logging.exception("Détails de l'erreur:")
        return False


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Vérification robuste des adresses GuignoMap",
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
        help='Nom de la ville'
    )
    
    parser.add_argument(
        '--file',
        required=True,
        type=Path,
        help='Chemin vers le fichier Excel source'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Affichage détaillé (debug)'
    )
    
    args = parser.parse_args()
    
    # Exécution de la vérification
    success = verify_addresses_robust(args.city, args.file, args.verbose)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())