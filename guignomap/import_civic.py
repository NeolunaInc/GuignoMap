import pandas as pd
from pathlib import Path
import time
from geopy.geocoders import Nominatim
def enrich_addresses_with_geocoding(conn):
    """Parcourt les adresses de la DB pour les enrichir avec code postal et GPS via Nominatim."""
    print("\nDébut de l'enrichissement par géocodage (peut prendre plusieurs heures)...")
    
    geolocator = Nominatim(user_agent="guignomap_mascouche_app")
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, house_number, street_name FROM addresses WHERE code_postal IS NULL")
    addresses_to_process = cursor.fetchall()
    
    total_addresses = len(addresses_to_process)
    print(f"{total_addresses} adresses à traiter.")
    
    for index, addr in enumerate(addresses_to_process):
        address_id, house_number, street_name = addr
        full_address = f"{house_number} {street_name}, Mascouche, QC, Canada"
        
        print(f"Traitement {index + 1}/{total_addresses} : {full_address}")
        
        try:
            location = geolocator.geocode(full_address, addressdetails=True)
            
            if location:
                lat = location.latitude
                lon = location.longitude
                postcode = location.raw.get('address', {}).get('postcode', '')
                
                cursor.execute(
                    "UPDATE addresses SET latitude = ?, longitude = ?, code_postal = ? WHERE id = ?",
                    (lat, lon, postcode, address_id)
                )
                conn.commit()
                print(f"  -> Trouvé ! CP: {postcode}")
            else:
                print("  -> Adresse non trouvée.")

        except Exception as e:
            print(f"  -> Erreur lors du géocodage : {e}")

        # Règle d'or de Nominatim : 1 requête par seconde !
        time.sleep(1)

    print("✅ Enrichissement par géocodage terminé.")
import sys

def analyze_civic_file():
    """Analyse le fichier nocivique.xlsx et retourne un rapport."""
    report = []
    file_path = Path("import/nocivique.xlsx")
    
    report.append("=== ANALYSE DU FICHIER OFFICIEL NOCIVIQUE.XLSX ===")
    
    if not file_path.exists():
        error_msg = f"ERREUR CRITIQUE: Le fichier {file_path.resolve()} est introuvable !"
        print(error_msg, file=sys.stderr)
        report.append(error_msg)
        return "\n".join(report)
    
    try:
        df = pd.read_excel(file_path)
        report.append(f"Fichier lu avec succès.")
        report.append(f"Nombre total d'adresses: {len(df)}")
        report.append(f"Colonnes détectées: {list(df.columns)}")
        report.append("\n=== Types de données des colonnes ===")
        report.append(str(df.dtypes))
        report.append("\n=== ÉCHANTILLON (5 premières lignes) ===")
        report.append(str(df.head(5)))
        
        # Validation des colonnes clés attendues
        key_columns = ['rue', 'numero', 'code_postal', 'lat', 'lon']
        missing = [col for col in key_columns if col not in df.columns]
        if missing:
            report.append(f"\nATTENTION: Des colonnes clés semblent manquantes: {missing}. Il faudra adapter le script d'import.")
        else:
            report.append("\nINFO: Les colonnes clés attendues ('rue', 'numero', 'code_postal', 'lat', 'lon') semblent présentes.")

    except Exception as e:
        error_msg = f"ERREUR lors de la lecture du fichier Excel : {e}"
        print(error_msg, file=sys.stderr)
        report.append(error_msg)

    return "\n".join(report)

if __name__ == '__main__':
    analysis_report = analyze_civic_file()
    # Sauvegarder le rapport dans les logs
    log_dir = Path("guignomap/logs")
    log_dir.mkdir(exist_ok=True)
    report_file = log_dir / "civic_analysis_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(analysis_report)
    print(f"\nRapport d'analyse sauvegardé dans : {report_file}")


import pandas as pd
from pathlib import Path

def import_to_database(conn):
    """Importe le contenu de nocivique.xlsx dans la DB (v2, sans secteur prédéfini)."""
    print("Début de l'importation des données officielles (stratégie sans secteur)...")
    file_path = Path("import/nocivique.xlsx")
    
    if not file_path.exists():
        print(f"ERREUR: Fichier {file_path} introuvable. Import annulé.")
        return 0, 0
    
    df = pd.read_excel(file_path)

    # Noms des colonnes réelles du fichier Excel
    COL_RUE = 'nomrue'
    COL_NUMERO = 'NoCiv'
    
    if not all(col in df.columns for col in [COL_RUE, COL_NUMERO]):
        print(f"ERREUR: Les colonnes requises ('{COL_RUE}', '{COL_NUMERO}') sont introuvables. Import annulé.")
        return 0, 0

    print("Nettoyage des anciennes données (notes, addresses, streets)...")
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM addresses")
    conn.execute("DELETE FROM streets")
    conn.commit()

    # 1. Importer les rues uniques sans secteur
    rues_uniques = df[COL_RUE].dropna().unique()
    print(f"Détection de {len(rues_uniques)} rues uniques.")
    
    rues_importees = 0
    for rue in rues_uniques:
        # Le secteur est laissé NULL (None) pour être défini plus tard par le gestionnaire.
        conn.execute(
            "INSERT OR IGNORE INTO streets (name, sector_id, status) VALUES (?, NULL, 'a_faire')",
            (rue,)
        )
        rues_importees += 1
    conn.commit()
    print(f"{rues_importees} rues insérées sans secteur.")

    # 2. Importer toutes les adresses civiques
    adresses_importees = 0
    for _, row in df.iterrows():
        # S'assurer que le numéro civique n'est pas vide/NaN
        if pd.notna(row[COL_NUMERO]):
            conn.execute(
                "INSERT INTO addresses (street_name, house_number, osm_type) VALUES (?, ?, 'official')",
                (row[COL_RUE], str(row[COL_NUMERO]))
            )
            adresses_importees += 1
    conn.commit()
    print(f"{adresses_importees} adresses insérées.")
    
    total_db = conn.execute("SELECT COUNT(*) FROM addresses").fetchone()[0]
    print(f"Vérification: {total_db} adresses sont maintenant dans la base de données.")
    print("✅ Importation terminée avec succès.")
    enrich_addresses_with_geocoding(conn)
    return rues_importees, adresses_importees