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
ADDR_CACHE_FILE = Path(__file__).parent / "osm_addresses.json"

# Toutes les routes nommées "classiques" (SANS autoroutes)
QUERY_STREETS_ALL = """
[out:json][timeout:120];
area["name"="Mascouche"]["boundary"="administrative"]->.a;
(
  way["highway"~"^(primary|secondary|tertiary|unclassified|residential|living_street)$"]["name"](area.a);
  way["highway"~"^(primary_link|secondary_link|tertiary_link)$"]["name"](area.a);
);
out tags geom;
"""

# Requête pour les adresses
QUERY_ADDR_NODES = """
[out:json][timeout:120];
area["name"="Mascouche"]["boundary"="administrative"]->.a;
(
  node["addr:housenumber"]["addr:street"](area.a);
  way["addr:housenumber"]["addr:street"](area.a);
);
out tags;
"""

def generate_streets_csv(city="Mascouche"):
    """
    Génère un CSV avec les noms des rues principales de la ville
    Filtre automatiquement les rues privées et les petites ruelles
    """
    try:
        api = overpy.Overpass()
        result = api.query(QUERY_STREETS_ALL)
        
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
    Utilise la requête optimisée avec "out tags geom"
    """
    try:
        api = overpy.Overpass()
        result = api.query(QUERY_STREETS_ALL)
        
        geo = {}
        skip_keywords = ["privé", "private", "allée", "impasse", "accès", "service"]
        
        for way in result.ways:
            name = way.tags.get("name")
            if not name or any(skip in name.lower() for skip in skip_keywords):
                continue

            coords = []
            # 1) Priorité à la géométrie renvoyée par Overpass
            if hasattr(way, "geometry") and way.geometry:
                coords = [[float(p["lat"]), float(p["lon"])]
                          for p in way.geometry
                          if isinstance(p, dict) and "lat" in p and "lon" in p]
            # 2) Fallback si on a les nodes
            elif hasattr(way, "nodes") and way.nodes:
                for node in way.nodes:
                    try:
                        coords.append([float(node.lat), float(node.lon)])
                    except Exception:
                        pass

            if len(coords) >= 2:
                geo.setdefault(name, []).append(coords)

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

# ========================================
# NOUVELLES FONCTIONS POUR LES ADRESSES
# ========================================

def build_addresses_cache():
    """
    Construit le cache des adresses OSM pour Mascouche
    Récupère addr:housenumber + addr:street depuis OSM
    """
    try:
        api = overpy.Overpass()
        result = api.query(QUERY_ADDR_NODES)
        
        addresses = {}
        
        # Traiter les nodes avec adresses
        for node in result.nodes:
            house_number = node.tags.get("addr:housenumber")
            street_name = node.tags.get("addr:street")
            
            if house_number and street_name:
                if street_name not in addresses:
                    addresses[street_name] = []
                addresses[street_name].append({
                    "number": house_number,
                    "lat": float(node.lat),
                    "lon": float(node.lon),
                    "type": "node"
                })
        
        # Traiter les ways avec adresses
        for way in result.ways:
            house_number = way.tags.get("addr:housenumber")
            street_name = way.tags.get("addr:street")
            
            if house_number and street_name:
                # Calculer le centroïde approximatif du way
                if hasattr(way, 'nodes') and way.nodes:
                    try:
                        lats = [float(node.lat) for node in way.nodes]
                        lons = [float(node.lon) for node in way.nodes]
                        center_lat = sum(lats) / len(lats)
                        center_lon = sum(lons) / len(lons)
                        
                        if street_name not in addresses:
                            addresses[street_name] = []
                        addresses[street_name].append({
                            "number": house_number,
                            "lat": center_lat,
                            "lon": center_lon,
                            "type": "way"
                        })
                    except:
                        continue
        
        # Trier les adresses par numéro pour chaque rue
        for street_name in addresses:
            addresses[street_name].sort(key=lambda x: int(''.join(filter(str.isdigit, x["number"]))) if any(c.isdigit() for c in x["number"]) else 0)
        
        # Sauvegarder le cache
        ADDR_CACHE_FILE.write_text(json.dumps(addresses, indent=2), encoding="utf-8")
        total_addresses = sum(len(addrs) for addrs in addresses.values())
        print(f"✅ Cache adresses créé: {len(addresses)} rues, {total_addresses} adresses")
        return ADDR_CACHE_FILE
        
    except Exception as e:
        print(f"❌ Erreur construction cache adresses: {e}")
        # Créer un cache vide en cas d'erreur
        ADDR_CACHE_FILE.write_text(json.dumps({}), encoding="utf-8")
        return ADDR_CACHE_FILE

def load_addresses_cache():
    """
    Charge le cache d'adresses depuis le fichier JSON
    """
    if not ADDR_CACHE_FILE.exists():
        print("⚠️ Cache adresses non trouvé")
        return {}
    
    try:
        with open(ADDR_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            total_addresses = sum(len(addrs) for addrs in cache.values())
            print(f"✅ Cache adresses chargé: {len(cache)} rues, {total_addresses} adresses")
            return cache
    except Exception as e:
        print(f"❌ Erreur chargement cache adresses: {e}")
        return {}