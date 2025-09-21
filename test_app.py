#!/usr/bin/env python3
import sys
import guignomap.database as db
def main():
    try:
        db.init_db(); print("✓ DB initialisée")
        print("✓ Stats:", db.extended_stats()); return 0
    except Exception as e:
        print("✗ Erreur:", e); return 1
if __name__ == "__main__": raise SystemExit(main())