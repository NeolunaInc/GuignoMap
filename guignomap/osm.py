"""
Module OSM pour Guigno-Map
Gère l'import et le cache des données OpenStreetMap pour Mascouche
"""

import io
import json
from pathlib import Path
import pandas as pd
import overpy

# Configuration
CACHE_FILE = Path(__file__).parent / "osm_cache.json"

# Requête OSM optimisée - récupère SEULEMENT les rues principales
QUERY_STREETS_FILTERED = """
[out:json][timeout:60];
area["name"="Mascouche"]["boundary"="administrative"]->.a;
(
  way["highway"~"^(primary|secondary|tertiary|residential)$"]["name"](area.a);
);
out tags geom;
"""

def generate_streets_csv(city="Mascouche"):
    """
    Génère un CSV avec les noms des rues principales de la ville
    Filtre automatiquement les rues privées et les petites ruelles
    """
    try:
        api = overpy.Overpass()
        result = api.query(QUERY_STREETS_FILTERED)
        
        # Filtrer les rues indésirables
        skip_keywords = ["privé", "private", "allée", "impasse", "accès", "service"]
        streets = []
        
        for way in result.ways:
            name = way.tags.get("name")
            if name and not any(skip in name.lower() for skip in skip_keywords):
                # Ignorer les rues trop petites (moins de 3 nœuds)
                if hasattr(way, 'nodes') and len(way.nodes) >= 3:
                    streets.append(name)
        
        # Éliminer les doublons et trier
        streets = sorted(set(streets))
        
        # Assigner automatiquement des secteurs basés sur les patterns de noms
        sectors = []
        for street in streets:
            if any(word in street.lower() for word in ["montée", "chemin", "boulevard"]):
                sectors.append("Principal")
            elif any(word in street.lower() for word in ["avenue", "place", "croissant"]):
                sectors.append("Résidentiel")
            elif "rue" in street.lower():
                sectors.append("Centre")
            else:
                sectors.append("")
        
        df = pd.DataFrame({
            "name": streets,
            "sector": sectors,
            "team": [""] * len(streets)
        })
        
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        print(f"✅ CSV généré avec {len(streets)} rues principales")
        return buf.getvalue().encode("utf-8")
        
    except Exception as e:
        print(f"❌ Erreur OSM: {e}")
        # Retourner des données de test en cas d'erreur
        return create_fallback_csv()

def build_geometry_cache():
    """
    Construit le cache des géométries pour affichage sur la carte
    Utilise la même requête filtrée pour cohérence
    """
    try:
        api = overpy.Overpass()
        result = api.query(QUERY_STREETS_FILTERED)
        
        geo = {}
        skip_keywords = ["privé", "private", "allée", "impasse", "accès", "service"]
        
        for way in result.ways:
            name = way.tags.get("name")
            
            # Appliquer le même filtre que pour le CSV
            if not name or any(skip in name.lower() for skip in skip_keywords):
                continue
            
            # Récupérer les coordonnées
            coords = []
            if hasattr(way, 'nodes'):
                for node in way.nodes:
                    try:
                        coords.append([float(node.lat), float(node.lon)])
                    except:
                        continue
            
            # Ajouter seulement si on a au moins 2 points
            if len(coords) >= 2:
                if name not in geo:
                    geo[name] = []
                geo[name].append(coords)
        
        # Sauvegarder le cache
        CACHE_FILE.write_text(json.dumps(geo, indent=2), encoding="utf-8")
        print(f"✅ Cache créé avec {len(geo)} rues géolocalisées")
        return CACHE_FILE
        
    except Exception as e:
        print(f"❌ Erreur construction cache: {e}")
        # Créer un cache de fallback
        create_fallback_cache()
        return CACHE_FILE

def load_geometry_cache():
    """
    Charge le cache de géométries depuis le fichier JSON
    Crée un cache de base si le fichier n'existe pas
    """
    if not CACHE_FILE.exists():
        print("⚠️ Cache non trouvé, construction en cours...")
        build_geometry_cache()
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            print(f"✅ Cache chargé: {len(cache)} rues")
            return cache
    except Exception as e:
        print(f"❌ Erreur chargement cache: {e}")
        create_fallback_cache()
        return json.loads(CACHE_FILE.read_text(encoding='utf-8'))

def create_fallback_csv():
    """
    Crée un CSV de fallback avec quelques rues principales de Mascouche
    Utilisé si l'API OSM est indisponible
    """
    fallback_streets = [
        ("Montée Masson", "Principal"),
        ("Chemin Sainte-Marie", "Principal"),
        ("Boulevard de Mascouche", "Principal"),
        ("Chemin des Anglais", "Principal"),
        ("Rue Dupras", "Centre"),
        ("Rue Saint-Pierre", "Centre"),
        ("Rue de l'Église", "Centre"),
        ("Avenue des Érables", "Résidentiel"),
        ("Rue des Pins", "Résidentiel"),
        ("Avenue Garden", "Résidentiel"),
    ]
    
    df = pd.DataFrame(fallback_streets, columns=["name", "sector"])
    df["team"] = ""
    
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    print("⚠️ Mode fallback: 10 rues de test")
    return buf.getvalue().encode("utf-8")

def create_fallback_cache():
    """
    Crée un cache minimal pour tests
    """
    fallback_geo = {
        "Montée Masson": [[[45.730, -73.620], [45.750, -73.600], [45.765, -73.580]]],
        "Chemin Sainte-Marie": [[[45.735, -73.615], [45.748, -73.602], [45.755, -73.595]]],
        "Boulevard de Mascouche": [[[45.740, -73.610], [45.747, -73.600], [45.752, -73.590]]],
        "Rue Dupras": [[[45.745, -73.602], [45.748, -73.599]]],
        "Rue Saint-Pierre": [[[45.746, -73.604], [45.749, -73.600]]],
        "Rue de l'Église": [[[45.747, -73.601], [45.750, -73.599]]],
        "Avenue des Érables": [[[45.755, -73.605], [45.758, -73.600]]],
        "Rue des Pins": [[[45.756, -73.603], [45.759, -73.598]]],
        "Avenue Garden": [[[45.753, -73.606], [45.756, -73.601]]],
        "Rue Gravel": [[[45.738, -73.605], [45.741, -73.600]]]
    }
    
    CACHE_FILE.write_text(json.dumps(fallback_geo, indent=2), encoding="utf-8")
    print("⚠️ Cache fallback créé avec 10 rues")

# Fonction utilitaire pour tests
def test_osm_connection():
    """
    Teste la connexion à l'API Overpass
    """
    try:
        api = overpy.Overpass()
        # Requête minimale pour tester
        result = api.query('[out:json];node(45.7475,-73.6005,45.7476,-73.6004);out;')
        print("✅ Connexion OSM OK")
        return True
    except:
        print("❌ Connexion OSM échouée")
        return False