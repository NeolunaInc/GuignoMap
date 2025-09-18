# scripts/enrich_addresses_from_osm.py
import json
import sqlite3
import unicodedata
import re
from pathlib import Path

DB_PATH = Path("guignomap/guigno_map.db")
OSM_ADDRESSES_PATH = Path("guignomap/osm_addresses.json")

def _normalize_text(s):
    """Normalise un texte pour créer une clé d'adresse unique (identique au script d'import)"""
    if s is None or s == "":
        return ""
    
    # Convertir en string et strip
    text = str(s).strip()
    
    # Enlever les accents (NFD normalization puis supprimer les diacritiques)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # Minuscules
    text = text.lower()
    
    # Compresser les espaces multiples
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def load_osm_addresses():
    """Charge et indexe les adresses OSM par addr_key"""
    if not OSM_ADDRESSES_PATH.exists():
        print(f"❌ Fichier OSM introuvable: {OSM_ADDRESSES_PATH}")
        return {}
    
    print(f"📖 Lecture du fichier OSM: {OSM_ADDRESSES_PATH}")
    
    with open(OSM_ADDRESSES_PATH, 'r', encoding='utf-8') as f:
        osm_data = json.load(f)
    
    # Indexer par addr_key
    osm_index = {}
    total_entries = 0
    
    for street_name, addresses in osm_data.items():
        for addr in addresses:
            house_number = str(addr.get("number", "")).strip()
            lat = addr.get("lat")
            lon = addr.get("lon") 
            osm_type = addr.get("type", "unknown")
            
            if house_number and lat is not None and lon is not None:
                # Créer la même addr_key qu'utilisée dans l'import
                # Pour OSM, nous n'avons que street_name et house_number, pas de postal_code
                addr_key = f"{_normalize_text(street_name)}|{_normalize_text(house_number)}|"
                
                # Si plusieurs entrées OSM pour la même addr_key, garder la première
                if addr_key not in osm_index:
                    osm_index[addr_key] = {
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "osm_type": osm_type,
                        "street_name": street_name,
                        "house_number": house_number
                    }
                
                total_entries += 1
    
    unique_keys = len(osm_index)
    print(f"📊 {total_entries} entrées OSM lues, {unique_keys} clés d'adresse uniques indexées")
    
    return osm_index

def enrich_addresses_from_osm():
    """Enrichit les adresses en base avec les données OSM par jointure sur addr_key"""
    print("=== Enrichissement des adresses depuis OSM ===")
    
    # 1. Charger et indexer les données OSM
    osm_index = load_osm_addresses()
    
    if not osm_index:
        print("❌ Aucune donnée OSM disponible pour l'enrichissement")
        return
    
    # 2. Vérifier la base de données
    if not DB_PATH.exists():
        print(f"❌ Base de données introuvable: {DB_PATH}")
        return
    
    with sqlite3.connect(DB_PATH) as conn:
        # Vérifier que la table addresses existe
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "addresses" not in tables:
            print("❌ Table 'addresses' introuvable dans la base")
            return
        
        # Vérifier les colonnes nécessaires
        columns = {row[1] for row in conn.execute("PRAGMA table_info(addresses)").fetchall()}
        required_cols = {"addr_key", "latitude", "longitude", "osm_type"}
        
        if not required_cols.issubset(columns):
            missing = required_cols - columns
            print(f"❌ Colonnes manquantes dans addresses: {missing}")
            return
        
        print("✅ Table addresses prête pour l'enrichissement")
        
        # 3. Compter les adresses totales et celles déjà géocodées
        total_addresses = conn.execute("SELECT COUNT(*) FROM addresses").fetchone()[0]
        already_geocoded = conn.execute("""
            SELECT COUNT(*) FROM addresses 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """).fetchone()[0]
        
        print(f"📊 {total_addresses} adresses en base, {already_geocoded} déjà géocodées")
        
        # 4. Enrichissement par jointure sur addr_key
        cursor = conn.cursor()
        updated_count = 0
        matched_count = 0
        
        # Récupérer toutes les adresses non géocodées
        non_geocoded = cursor.execute("""
            SELECT id, addr_key, street_name, house_number
            FROM addresses 
            WHERE latitude IS NULL OR longitude IS NULL
        """).fetchall()
        
        print(f"🔍 {len(non_geocoded)} adresse(s) à enrichir")
        
        # Debug: afficher quelques exemples de clés
        print("\n🔍 DEBUG - Stratégies de correspondance:")
        
        # Stratégie 1: correspondance exacte par addr_key
        exact_matches = 0
        for addr_id, addr_key, street_name, house_number in non_geocoded[:100]:  # Test sur 100 premiers
            if addr_key in osm_index:
                exact_matches += 1
        
        print(f"  Correspondances exactes (addr_key): {exact_matches}/{min(100, len(non_geocoded))}")
        
        # Stratégie 2: correspondance par nom de rue normalisé + numéro
        street_matches = 0
        for addr_id, addr_key, street_name, house_number in non_geocoded[:100]:
            # Nettoyer le street_name (supprimer les "nan" parasites)
            clean_street = street_name.replace("nan ", "").replace(" nan", "").strip()
            if clean_street:
                test_key = f"{_normalize_text(clean_street)}|{_normalize_text(house_number)}|"
                if test_key in osm_index:
                    street_matches += 1
        
        print(f"  Correspondances par rue nettoyée: {street_matches}/{min(100, len(non_geocoded))}")
        
        # Stratégie 3: correspondance partielle (même numéro, rue similaire)
        partial_matches = 0
        osm_streets = {}
        for addr_key, data in osm_index.items():
            normalized_street = _normalize_text(data["street_name"])
            house_num = _normalize_text(data["house_number"])
            key = f"{normalized_street}|{house_num}"
            osm_streets[key] = data
        
        for addr_id, addr_key, street_name, house_number in non_geocoded[:100]:
            clean_street = street_name.replace("nan ", "").replace(" nan", "").strip()
            if clean_street:
                search_key = f"{_normalize_text(clean_street)}|{_normalize_text(house_number)}"
                if search_key in osm_streets:
                    partial_matches += 1
        
        print(f"  Correspondances partielles: {partial_matches}/{min(100, len(non_geocoded))}")
        
        # Appliquer la meilleure stratégie trouvée
        print(f"\n🔧 Application de l'enrichissement...")
        
        for addr_id, addr_key, street_name, house_number in non_geocoded:
            osm_data = None
            
            # Stratégie 1: exacte
            if addr_key in osm_index:
                osm_data = osm_index[addr_key]
                matched_count += 1
            else:
                # Stratégie 2: rue nettoyée
                clean_street = street_name.replace("nan ", "").replace(" nan", "").strip()
                if clean_street:
                    test_key = f"{_normalize_text(clean_street)}|{_normalize_text(house_number)}|"
                    if test_key in osm_index:
                        osm_data = osm_index[test_key]
                        matched_count += 1
                    else:
                        # Stratégie 3: partielle
                        search_key = f"{_normalize_text(clean_street)}|{_normalize_text(house_number)}"
                        if search_key in osm_streets:
                            osm_data = osm_streets[search_key]
                            matched_count += 1
            
            if osm_data:
                try:
                    cursor.execute("""
                        UPDATE addresses 
                        SET latitude = ?, longitude = ?, osm_type = ?
                        WHERE id = ?
                    """, (
                        osm_data["latitude"],
                        osm_data["longitude"], 
                        osm_data["osm_type"],
                        addr_id
                    ))
                    
                    if cursor.rowcount > 0:
                        updated_count += 1
                    
                except Exception as e:
                    print(f"❌ Erreur mise à jour ID {addr_id}: {e}")
        
        conn.commit()
        
        # 5. Statistiques finales
        final_geocoded = conn.execute("""
            SELECT COUNT(*) FROM addresses 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """).fetchone()[0]
        
        newly_geocoded = final_geocoded - already_geocoded
        
        print(f"\n=== RÉSULTATS ===")
        print(f"📊 Correspondances trouvées: {matched_count}")
        print(f"📊 Mises à jour réussies: {updated_count}")
        print(f"📊 Nouvellement géocodées: {newly_geocoded}")
        print(f"📊 Total géocodé: {final_geocoded}/{total_addresses} ({final_geocoded/total_addresses*100:.1f}%)")
        
        if updated_count > 0:
            print("✅ Enrichissement terminé avec succès!")
        else:
            print("⚠️ Aucune mise à jour effectuée")
        
        # 6. Quelques exemples d'adresses enrichies
        if updated_count > 0:
            print(f"\n📍 Exemples d'adresses enrichies (5 premiers):")
            examples = cursor.execute("""
                SELECT street_name, house_number, latitude, longitude, osm_type
                FROM addresses 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY id DESC
                LIMIT 5
            """).fetchall()
            
            for street, number, lat, lon, osm_type in examples:
                print(f"  - {street} {number}: ({lat:.6f}, {lon:.6f}) [{osm_type}]")

if __name__ == "__main__":
    enrich_addresses_from_osm()