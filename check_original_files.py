import pandas as pd
from pathlib import Path

print("📁 ANALYSE DES FICHIERS DISPONIBLES\n")

files_to_check = [
    "import/nocivique.xlsx",
    "import/nocivique_avec_cp.xlsx", 
    "import/nocivique_cp_complement.xlsx"
]

for file_path in files_to_check:
    if Path(file_path).exists():
        df = pd.read_excel(file_path, nrows=5)
        print(f"📄 {file_path}")
        print(f"   Colonnes: {list(df.columns)}")
        print(f"   Taille: {len(pd.read_excel(file_path))} lignes")
        print("   Échantillon:")
        for _, row in df.head(3).iterrows():
            # Afficher les valeurs importantes
            if 'NoCiv' in df.columns and 'nomrue' in df.columns:
                print(f"     {row['NoCiv']} {row['nomrue']}")
                if 'code_postal_trouve' in df.columns:
                    print(f"       -> CP: {row.get('code_postal_trouve', 'N/A')}")
        print()

# Recommandation
print("💡 RECOMMANDATION:")
print("Utiliser nocivique_cp_complement.xlsx car il contient les codes postaux!")
