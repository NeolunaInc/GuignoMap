#!/usr/bin/env python3
"""
Script de migration pour régénérer les clés addr_key selon la nouvelle logique
"""
import sqlite3
import logging
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guignomap.imports import build_addr_key

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_address_keys():
    """Régénère toutes les clés addr_key selon la nouvelle logique de normalisation"""
    
    db_path = "guignomap/guigno_map.db"
    
    logger.info(f"🔄 Migration des clés addr_key dans {db_path}")
    
    # Connexion à la DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Récupérer toutes les adresses
        cursor.execute("SELECT id, street_name, house_number, postal_code FROM addresses")
        addresses = cursor.fetchall()
        
        logger.info(f"📊 {len(addresses)} adresses à traiter")
        
        # 2. Régénérer les clés
        updated_count = 0
        
        for addr_id, street_name, house_number, postal_code in addresses:
            # Générer la nouvelle clé
            new_key = build_addr_key(street_name, house_number, postal_code)
            
            # Mettre à jour en DB
            cursor.execute(
                "UPDATE addresses SET addr_key = ? WHERE id = ?",
                (new_key, addr_id)
            )
            updated_count += 1
            
            if updated_count % 1000 == 0:
                logger.info(f"  Traité: {updated_count}/{len(addresses)}")
        
        # 3. Commit des changements
        conn.commit()
        logger.info(f"✅ Migration terminée: {updated_count} clés régénérées")
        
        # 4. Vérification des doublons
        cursor.execute("SELECT addr_key, COUNT(*) as count FROM addresses GROUP BY addr_key HAVING count > 1")
        duplicates = cursor.fetchall()
        
        if duplicates:
            logger.warning(f"⚠️  {len(duplicates)} clés dupliquées détectées après migration")
            for key, count in duplicates[:5]:  # Afficher les 5 premiers
                logger.warning(f"   {key}: {count} occurrences")
        else:
            logger.info("✅ Aucun doublon détecté")
            
        # 5. Statistiques finales
        cursor.execute("SELECT COUNT(*) FROM addresses")
        total_addresses = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT addr_key) FROM addresses")
        unique_keys = cursor.fetchone()[0]
        
        logger.info(f"📈 Statistiques finales:")
        logger.info(f"   Total adresses: {total_addresses}")
        logger.info(f"   Clés uniques: {unique_keys}")
        logger.info(f"   Ratio unicité: {unique_keys/total_addresses*100:.1f}%")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_address_keys()