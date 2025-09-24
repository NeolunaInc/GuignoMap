import shutil
import zipfile
from pathlib import Path
from datetime import datetime
import os

print("🔄 BACKUP COMPLET DU PROJET\n")

# 1. Préparer les chemins
now = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = Path("backup")
backup_dir.mkdir(exist_ok=True)
db_src = Path("guignomap/guigno_map.db")
db_dest = backup_dir / f"guigno_map_{now}.db"
zip_path = backup_dir / f"GuignoMap_Backup_{now}.zip"

# 2. Copier la base
print(f"Copie DB: {db_src} -> {db_dest}")
shutil.copy2(db_src, db_dest)

# 3. Copier les fichiers Excel
excel_files = list(Path("import").glob("*.xlsx"))
excel_dest_files = []
for f in excel_files:
    dest = backup_dir / f.name
    print(f"Copie Excel: {f} -> {dest}")
    shutil.copy2(f, dest)
    excel_dest_files.append(dest)

# 4. Zipper le tout
print(f"Création du zip: {zip_path}")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(db_dest, db_dest.name)
    for f in excel_dest_files:
        z.write(f, f.name)

# 5. Afficher la taille et le chemin
size_mb = os.path.getsize(zip_path) / (1024*1024)
print(f"\n✅ Backup créé: {zip_path}")
print(f"   Taille: {size_mb:.2f} MB")
