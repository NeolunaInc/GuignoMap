
import sqlite3
from pathlib import Path
import pandas as pd
from datetime import datetime

DB_PATH = Path("guignomap/guigno_map.db")
IMPORT_DIR = Path("import")
REPORT_PATH = Path(f"etat_actuel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

def diagnostic_complet():
    report = []
    report.append("="*60)
    report.append(f"DIAGNOSTIC GUIGNOMAP - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*60)
    
    # Vérifier existence DB
    if not DB_PATH.exists():
        report.append(f"❌ ERREUR: Base de données introuvable: {DB_PATH}")
        return report
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # 1. TABLES EXISTANTES
        report.append("\n📊 TABLES DANS LA BASE:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            report.append(f"  ✓ {table[0]}")
        
        # 2. STATISTIQUES STREETS
        report.append("\n🛤️ RUES (table streets):")
        cursor.execute("SELECT COUNT(*) FROM streets")
        total_streets = cursor.fetchone()[0]
        report.append(f"  Total: {total_streets}")
        
        cursor.execute("SELECT status, COUNT(*) FROM streets GROUP BY status")
        for status, count in cursor.fetchall():
            report.append(f"  - {status}: {count}")
        
        cursor.execute("SELECT COUNT(DISTINCT team) FROM streets WHERE team IS NOT NULL AND team != ''")
        teams_assigned = cursor.fetchone()[0]
        report.append(f"  Équipes assignées: {teams_assigned}")
        
        # 3. STATISTIQUES ADDRESSES
        report.append("\n📍 ADRESSES (table addresses):")
        cursor.execute("SELECT COUNT(*) FROM addresses")
        total_addr = cursor.fetchone()[0]
        report.append(f"  Total: {total_addr}")
        
        # Avec code postal
        cursor.execute("SELECT COUNT(*) FROM addresses WHERE postal_code IS NOT NULL AND postal_code != ''")
        with_cp = cursor.fetchone()[0]
        report.append(f"  Avec code postal: {with_cp} ({with_cp*100/total_addr:.1f}%)")
        
        # Avec GPS
        cursor.execute("SELECT COUNT(*) FROM addresses WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
        with_gps = cursor.fetchone()[0]
        report.append(f"  Avec GPS: {with_gps} ({with_gps*100/total_addr:.1f}%)")
        
        # Sans GPS mais avec CP (candidats au géocodage)
        cursor.execute("""
            SELECT COUNT(*) FROM addresses 
            WHERE postal_code IS NOT NULL AND postal_code != ''
            AND (latitude IS NULL OR longitude IS NULL)
        """)
        ready_for_geocoding = cursor.fetchone()[0]
        report.append(f"  Prêtes pour géocodage (CP sans GPS): {ready_for_geocoding}")
        
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
