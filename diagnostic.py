
import sqlite3
from pathlib import Path
import pandas as pd
from datetime import datetime

DB_PATH = Path("guignomap/guigno_map.db")
IMPORT_DIR = Path("import")
REPORT_PATH = Path(f"etat_actuel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

import streamlit as st
import sys
import sqlite3
from pathlib import Path

st.set_page_config(page_title="Diagnostic GuignoMap", page_icon="🔧", layout="wide")

st.title("🔧 Diagnostic GuignoMap")

# Test 1: Python et Streamlit
st.header("1. Environnement")
st.info(f"Python: {sys.version}")
st.info(f"Streamlit: {st.__version__}")

# Test 2: Structure des fichiers
st.header("2. Fichiers critiques")
files_to_check = [
    "guignomap/app.py",
    "guignomap/db.py",
    "guignomap/assets/styles.css",
    "guignomap/guigno_map.db"
]

for file in files_to_check:
    path = Path(file)
    if path.exists():
        size = path.stat().st_size
        st.success(f"✅ {file} ({size} octets)")
    else:
        st.error(f"❌ {file} MANQUANT!")

# Test 3: Base de données
st.header("3. Base de données")
try:
    conn = sqlite3.connect("guignomap/guigno_map.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    
    if tables:
        st.success(f"✅ {len(tables)} tables trouvées: {', '.join(tables)}")
        
        # Compter les enregistrements
        for table in ['streets', 'teams', 'addresses']:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                st.info(f"   • {table}: {count} enregistrements")
    else:
        st.warning("⚠️ Base de données vide!")
        
except Exception as e:
    st.error(f"❌ Erreur DB: {e}")

# Test 4: Import des modules
st.header("4. Modules GuignoMap")
try:
    from guignomap import db
    st.success("✅ Module db importé")
    
    # Vérifier les fonctions critiques
    if hasattr(db, 'init_db'):
        st.success("✅ Fonction init_db trouvée")
    else:
        st.error("❌ Fonction init_db MANQUANTE!")
        
except ImportError as e:
    st.error(f"❌ Impossible d'importer db: {e}")

        report.append(f"  Prêtes pour géocodage (CP sans GPS): {ready_for_geocoding}")
st.success("🎯 Diagnostic terminé. Corrige les erreurs ❌ avant de lancer l'app principale.")
        
        # 4. STATISTIQUES TEAMS
        report.append("\n👥 ÉQUIPES (table teams):")
        cursor.execute("SELECT COUNT(*) FROM teams")
        total_teams = cursor.fetchone()[0]
        report.append(f"  Total: {total_teams}")
        
        cursor.execute("SELECT id, name FROM teams LIMIT 5")
        teams = cursor.fetchall()
        for team_id, team_name in teams:
            report.append(f"  - {team_id}: {team_name}")
        
        # 5. FICHIERS EXCEL
        report.append("\n📁 FICHIERS EXCEL DISPONIBLES:")
        excel_files = list(IMPORT_DIR.glob("*.xlsx"))
        for f in excel_files:
            size_mb = f.stat().st_size / (1024*1024)
            report.append(f"  - {f.name} ({size_mb:.1f} MB)")
        
        # Vérifier nocivique_cp_complement.xlsx
        cp_file = IMPORT_DIR / "nocivique_cp_complement.xlsx"
        if cp_file.exists():
            try:
                df = pd.read_excel(cp_file, nrows=5)
                report.append(f"\n✅ nocivique_cp_complement.xlsx trouvé!")
                report.append(f"  Colonnes: {list(df.columns)}")
            except Exception as e:
                report.append(f"  ⚠️ Erreur lecture: {e}")
        else:
            report.append(f"\n⚠️ nocivique_cp_complement.xlsx MANQUANT!")
        
        # 6. ACTIONS RECOMMANDÉES
        report.append("\n🎯 ACTIONS RECOMMANDÉES:")
        if with_cp < total_addr * 0.8:
            report.append(f"  1. Importer les codes postaux ({total_addr - with_cp} manquants)")
        if with_gps < total_addr * 0.5:
            report.append(f"  2. Géocoder les adresses ({total_addr - with_gps} sans GPS)")
        if ready_for_geocoding > 0:
            report.append(f"  3. {ready_for_geocoding} adresses prêtes pour géocodage GPS")
        
        conn.close()
        
    except Exception as e:
        report.append(f"\n❌ ERREUR DB: {str(e)}")
    
    # Sauvegarder rapport
    report_text = "\n".join(report)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    
    # Afficher aussi dans console
    print(report_text)
    print(f"\n📄 Rapport sauvegardé: {REPORT_PATH}")
    
    return report

if __name__ == "__main__":
    diagnostic_complet()
