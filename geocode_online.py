import pandas as pd
import time
from pathlib import Path
from geopy.geocoders import Nominatim

def run_online_geocoding():
    """
    Traite le fichier des adresses sans code postal en interrogeant Nominatim (1 req/sec).
    Sauvegarde les résultats progressivement pour éviter toute perte de données.
    """
    print("--- Début du géocodage en ligne (lent) ---")
    
    input_file = Path("import/nocivique_sans_cp.xlsx")
    output_file = Path("import/nocivique_cp_complement.xlsx")

    if not input_file.exists():
        print(f"ERREUR: Le fichier d'entrée '{input_file}' est introuvable.")
        return

    df = pd.read_excel(input_file)
    total_addresses = len(df)
    print(f"{total_addresses} adresses à traiter. Estimation du temps : {total_addresses / 3600:.2f} heures.")

    # Créer une nouvelle colonne pour les résultats
    if 'code_postal_trouve' not in df.columns:
        df['code_postal_trouve'] = None

    geolocator = Nominatim(user_agent="guignomap_mascouche_app_v2")

    for index, row in df.iterrows():
        # Si on a déjà un résultat pour cette ligne (reprise après une pause), on passe
        if pd.notna(row['code_postal_trouve']):
            continue

        full_address = f"{row['NoCiv']} {row['nomrue']}, Mascouche, QC, Canada"
        print(f"[{index + 1}/{total_addresses}] Recherche : {full_address}")

        try:
            location = geolocator.geocode(full_address, addressdetails=True, timeout=10)
            
            if location and 'postcode' in location.raw.get('address', {}):
                postcode = location.raw['address']['postcode']
                df.at[index, 'code_postal_trouve'] = postcode
                print(f"  -> TROUVÉ : {postcode}")
            else:
                df.at[index, 'code_postal_trouve'] = "NON TROUVÉ"
                print("  -> Non trouvé.")

        except Exception as e:
            df.at[index, 'code_postal_trouve'] = "ERREUR"
            print(f"  -> ERREUR : {e}")
        
        # Sauvegarde progressive toutes les 25 adresses
        if (index + 1) % 25 == 0:
            df.to_excel(output_file, index=False)
            print(f"*** Sauvegarde intermédiaire effectuée. ***")

        # Règle de Nominatim : 1 seconde de pause
        time.sleep(1)

    # Sauvegarde finale
    df.to_excel(output_file, index=False)
    print("--- ✅ Géocodage en ligne terminé ! ---")
    print(f"Les résultats sont dans le fichier : {output_file}")

if __name__ == "__main__":
    run_online_geocoding()
