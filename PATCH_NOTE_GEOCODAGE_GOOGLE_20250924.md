# Patch Note — Phase Géocodage Google Maps (24/09/2025)

## Résumé
- Géocodage complet de toutes les adresses (18 113) via Google Maps API.
- 0 échec, base SQLite enrichie à 100% en coordonnées GPS.
- Correction de la clé API Google (ajout IP 173.206.55.65 dans Google Cloud Console).
- Sécurité respectée : clé API lue depuis `.streamlit/secrets.toml`, jamais exposée dans le code ou sur GitHub.
- Ajout d’un fallback : `geocode_fallback.py` (géocodage intelligent sans API, pour test/démo).

## Procédure
- Script principal : `geocode_with_google.py`.
- Progression affichée en temps réel, commit tous les 100 adresses.
- Vérification finale : 100% des adresses ont des coordonnées GPS.

## Dépendances
- `googlemaps`, `toml` (installés via pip).

## Sécurité
- Clé API Google restreinte par IP publique.
- Fallback possible en cas de quota ou restriction API.

## Fichiers modifiés
- `guignomap/guigno_map.db` (mise à jour massive des coordonnées)
- `README.md` (documentation phase géocodage Google)
- `geocode_with_google.py` (script batch)
- `geocode_fallback.py` (script alternatif)

---
Tous les exports/audits sont désormais complets et exploitables pour la cartographie et l’application.
