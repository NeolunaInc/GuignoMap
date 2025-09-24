import sqlite3
import os

# Chemin vers la base de données
DB_PATH = os.path.join("guignomap", "guigno_map.db")

def add_column():
    """Ajoute la colonne 'team' à la table 'streets' si elle n'existe pas."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(streets)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'team' not in columns:
            print("La colonne 'team' est manquante. Ajout en cours...")
            cursor.execute("ALTER TABLE streets ADD COLUMN team TEXT")
            conn.commit()
            print("✅ La colonne 'team' a été ajoutée avec succès.")
        else:
            print("👍 La colonne 'team' existe déjà.")
    except sqlite3.Error as e:
        print(f"❌ Erreur de base de données : {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_column()
