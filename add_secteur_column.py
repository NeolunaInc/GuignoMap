import sqlite3
import os

# Chemin vers la base de données
DB_PATH = os.path.join("guignomap", "guigno_map.db")

def add_column():
    """Ajoute la colonne 'secteur' à la table 'streets' si elle n'existe pas."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print("Vérification de la table 'streets'...")
        cursor.execute("PRAGMA table_info(streets)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'secteur' not in columns:
            print("La colonne 'secteur' est manquante. Ajout en cours...")
            cursor.execute("ALTER TABLE streets ADD COLUMN secteur TEXT")
            conn.commit()
            print("✅ La colonne 'secteur' a été ajoutée avec succès à la table 'streets'.")
        else:
            print("👍 La colonne 'secteur' existe déjà. Aucune action nécessaire.")
    except sqlite3.Error as e:
        print(f"❌ Erreur de base de données : {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_column()
