import pandas as pd
import unicodedata
from pathlib import Path

def normalize_street_name(s: str) -> str:
    """Nettoie et standardise un nom de rue pour la comparaison."""
    if pd.isna(s): return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    
    # Normalisations pour le Québec
    replacements = {
        " CHEMIN ": " CH ", " BOULEVARD ": " BOUL ", " AVENUE ": " AV ",
        " RUE ": " RUE ", " MONTEE ": " MTEE ", " COTE ": " CTE ",
        "SAINT-": "ST-", " SAINTE-": " STE-",
    }
    
    s = f" {s} " # Ajoute des espaces pour un remplacement sûr
    for old, new in replacements.items():
        s = s.replace(old, new)
    
    return " ".join(s.split())

def run_offline_geocoding():
    """Exécute la jointure entre le fichier civique et les données OSM."""
    print("--- Début du géocodage offline ---")
    
    # --- 1. Charger notre fichier officiel (nocivique.xlsx) ---
    civic_path = Path("import/nocivique.xlsx")
    if not civic_path.exists():
        print(f"ERREUR: Le fichier {civic_path} est introuvable.")
        return

    df_civic = pd.read_excel(civic_path)
    print(f"Chargé: {len(df_civic)} adresses depuis {civic_path.name}")

    # Adapter aux noms de colonnes réels de nocivique.xlsx
    NUM_COL = "NoCiv"
    RUE_COL = "nomrue"

    # Créer une clé de jointure normalisée
    df_civic["join_key"] = df_civic[NUM_COL].astype(str).str.strip() + " " + df_civic[RUE_COL].astype(str).map(normalize_street_name)

    # --- 2. Charger le fichier exporté d'Overpass (OSM) ---
    osm_path = Path("import/osm_mascouche_adresses.csv")
    if not osm_path.exists():
        print(f"ERREUR: Le fichier {osm_path} est introuvable. Avez-vous complété la Mission 1 ?")
        return
        
    df_osm = pd.read_csv(osm_path)
    print(f"Chargé: {len(df_osm)} adresses depuis {osm_path.name}")

    # Renommer et créer la même clé de jointure normalisée
    df_osm.rename(columns={"addr:housenumber": "numero", "addr:street": "rue", "addr:postcode": "code_postal"}, inplace=True)
    df_osm["join_key"] = df_osm["numero"].astype(str).str.strip() + " " + df_osm["rue"].astype(str).map(normalize_street_name)
    
    # Garder seulement les colonnes utiles et dédoublonner
    df_osm_clean = df_osm[["join_key", "code_postal"]].dropna().drop_duplicates(subset="join_key")
    print(f"OSM: {len(df_osm_clean)} adresses uniques avec code postal.")

    # --- 3. Exécuter la jointure ---
    df_final = df_civic.merge(df_osm_clean, on="join_key", how="left")
    
    # --- 4. Sauvegarder les résultats ---
    output_matched_path = "import/nocivique_avec_cp.xlsx"
    output_unmatched_path = "import/nocivique_sans_cp.xlsx"

    df_final.to_excel(output_matched_path, index=False)
    df_final[df_final["code_postal"].isna()].to_excel(output_unmatched_path, index=False)
    
    matched_count = df_final["code_postal"].notna().sum()
    unmatched_count = df_final["code_postal"].isna().sum()

    print("\n--- ✅ Opération terminée ! ---")
    print(f"Résultat complet sauvegardé dans: {output_matched_path} ({matched_count} adresses enrichies)")
    print(f"Adresses sans correspondance sauvegardées dans: {output_unmatched_path} ({unmatched_count} adresses restantes)")

if __name__ == "__main__":
    run_offline_geocoding()
