import pandas as pd
from pathlib import Path

excel_file = Path("import/nocivique_cp_complement.xlsx")
df = pd.read_excel(excel_file)

print(f"Total lignes: {len(df)}")
print(f"Colonnes: {list(df.columns)}")

# Analyser la colonne code_postal_trouve
if 'code_postal_trouve' in df.columns:
    valides = df[df['code_postal_trouve'].notna() & \
                 (df['code_postal_trouve'] != 'NON TROUVÉ') & \
                 (df['code_postal_trouve'] != 'ERREUR')]
    print(f"\nCodes postaux valides trouvés: {len(valides)}")
    print(f"Codes postaux non trouvés: {len(df) - len(valides)}")
    
    # Afficher 10 exemples
    print("\nExemples de codes postaux trouvés:")
    for _, row in valides.head(10).iterrows():
        print(f"  {row['NoCiv']} {row['nomrue']}: {row['code_postal_trouve']}")

# Sauvegarder les stats
with open("postal_codes_stats.txt", "w", encoding="utf-8") as f:
    f.write(f"Codes postaux valides: {len(valides)}/{len(df)}\n")
    f.write(f"Taux de réussite: {len(valides)*100/len(df):.1f}%\n")
