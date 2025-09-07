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

# Toutes les voies routières nommées de Mascouche, sauf autoroutes
QUERY_STREETS_ALL = """
[out:json][timeout:180];
area["name"="Mascouche"]["boundary"="administrative"]->.a;
(
  /* garder toute route avec un nom, sauf autoroutes */
  way["highway"]["name"]["highway"!~"^motorway(_link)?$"](area.a);
  /* optionnel: si tu veux éviter les trottoirs/pistes, décommente la ligne suivante */
  /* way["highway"!~"^(footway|path|cycleway|steps|pedestrian)$"]["name"]["highway"!~"^motorway(_link)?$"](area.a); */
);
out tags geom;
"""

# Requête pour les adresses
QUERY_ADDR_NODES = """
[out:json][timeout:180];
area["name"="Mascouche"]["boundary"="administrative"]->.a;
(
  node["addr:housenumber"]["addr:street"](area.a);
  way["addr:housenumber"]["addr:street"](area.a);
);
out tags center;
"""

def generate_streets_csv(city="Mascouche"):
    """
    Génère un CSV avec les noms des rues principales de la ville
    Filtre automatiquement les rues privées et les petites ruelles
    """
    try:
        api = overpy.Overpass()
        result = api.query(QUERY_STREETS_ALL)
        
        streets = []
        for way in result.ways:
            name = way.tags.get("name")
            if not name:
                continue
            g = getattr(way, "geometry", None)
            # garder si on a une vraie géométrie (>= 2 points)
            if isinstance(g, list) and len(g) >= 2:
                streets.append(name)

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

        # Sécurise l'itération même si result.ways est None
        for way in (getattr(result, "ways", []) or []):
            name = None
            try:
                name = (way.tags or {}).get("name")
                if not name:
                    continue

                coords = []

                # 1) geometry -> liste de dicts {"lat":..,"lon":..}
                g = getattr(way, "geometry", None)
                if isinstance(g, list) and g:
                    for p in g:
                        if isinstance(p, dict):
                            lat = p.get("lat"); lon = p.get("lon")
                            if lat is not None and lon is not None:
                                coords.append([float(lat), float(lon)])
                else:
                    # 2) fallback nodes
                    nodes = getattr(way, "nodes", None) or []
                    for node in nodes:
                        if node and getattr(node, "lat", None) is not None and getattr(node, "lon", None) is not None:
                            coords.append([float(node.lat), float(node.lon)])

                if len(coords) >= 2:
                    geo.setdefault(name, []).append(coords)

            except Exception as e:
                # On skippe silencieusement la voie problématique, on continue
                print(f"⚠️ Skip way id={getattr(way,'id','?')} name={name!r}: {e}")
                continue

        # Si rien n'est trouvé, on lève explicitement pour déclencher le mécanisme de secours *sans* écraser un cache existant
        if not geo:
            raise RuntimeError("Overpass a renvoyé 0 géométries utilisables.")

        CACHE_FILE.write_text(json.dumps(geo, indent=2), encoding="utf-8")
        print(f"✅ Cache créé avec {len(geo)} rues géolocalisées")
        return geo

    except Exception as e:
        print(f"❌ Erreur construction cache: {e}")

        # Si un cache précédent existe, on le recharge (pas de fallback 10 qui écrase)
        if CACHE_FILE.exists():
            try:
                data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                print(f"⚠️ Échec refresh: cache précédent conservé ({len(data)} rues).")
                return data
            except Exception:
                pass

        # Ultime recours en mémoire (NE PAS écrire sur disque)
        fallback = {
            "Chemin Gascon": [[[45.75, -73.62], [45.76, -73.60]]],
            "Boulevard de Mascouche": [[[45.74, -73.61], [45.75, -73.59]]],
            "Montée Masson": [[[45.73, -73.63], [45.74, -73.62]]],
            "Chemin Sainte-Marie": [[[45.75, -73.64], [45.76, -73.63]]],
            "Rue Principale": [[[45.72, -73.61], [45.73, -73.60]]],
            "Chemin des Anglais": [[[45.74, -73.65], [45.75, -73.64]]],
            "Rue de l'Étang": [[[45.76, -73.62], [45.77, -73.61]]],
            "Boulevard Raymond": [[[45.73, -73.60], [45.74, -73.59]]],
            "Rue Sainte-Marie": [[[45.71, -73.62], [45.72, -73.61]]],
            "Rue Brien": [[[45.70, -73.63], [45.71, -73.62]]],
        }
        print("⚠️ Fallback temporaire en mémoire utilisé (aucune écriture disque).")
        return fallback

def load_geometry_cache():
    """
    Charge le cache de géométries depuis le fichier JSON
    Crée un cache de base si le fichier n'existe pas
    """
    if not CACHE_FILE.exists():
        print("⚠️ Cache non trouvé, construction en cours...")
        return build_geometry_cache()  # build_geometry_cache() gère déjà le fallback en mémoire
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            print(f"✅ Cache chargé: {len(cache)} rues")
            return cache
    except Exception as e:
        print(f"❌ Erreur chargement cache: {e}")
        # Ne pas écrire de fallback sur disque ! Utiliser build_geometry_cache() qui gère le fallback en mémoire
        return build_geometry_cache()

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
                    "number": str(house_number),  # Forcer en string
                    "lat": float(node.lat),
                    "lon": float(node.lon),
                    "type": "node"
                })
        
        # Traiter les ways avec adresses
        for way in result.ways:
            num = way.tags.get("addr:housenumber")
            street = way.tags.get("addr:street")
            if not num or not street:
                continue
            
            # Récupérer le centre du way
            lat = getattr(way, "center_lat", None)
            lon = getattr(way, "center_lon", None)
            
            # Fallback si center_lat/lon non disponibles
            if lat is None or lon is None:
                nodes = getattr(way, "nodes", []) or []
                if nodes:
                    try:
                        valid_lats = []
                        valid_lons = []
                        for n in nodes:
                            if hasattr(n, 'lat') and hasattr(n, 'lon'):
                                if n.lat is not None and n.lon is not None:
                                    valid_lats.append(float(n.lat))
                                    valid_lons.append(float(n.lon))
                        if valid_lats and valid_lons:
                            lat = sum(valid_lats) / len(valid_lats)
                            lon = sum(valid_lons) / len(valid_lons)
                    except Exception as e:
                        print(f"Erreur calcul centre pour way: {e}")
                        continue
            
            if lat is not None and lon is not None:
                addresses.setdefault(street, []).append({
                    "number": str(num),
                    "lat": float(lat),
                    "lon": float(lon),
                    "type": "way"
                })
        
        # Trier les adresses par numéro pour chaque rue
        for street_name in addresses:
            try:
                # Tri numérique intelligent
                addresses[street_name].sort(
                    key=lambda x: (
                        int(''.join(filter(str.isdigit, x["number"]))) 
                        if any(c.isdigit() for c in x["number"]) 
                        else float('inf')
                    )
                )
            except:
                # Si le tri échoue, garder l'ordre original
                pass
        
        # Sauvegarder le cache
        ADDR_CACHE_FILE.write_text(json.dumps(addresses, indent=2), encoding="utf-8")
        total_addresses = sum(len(addrs) for addrs in addresses.values())
        print(f"✅ Cache adresses créé: {len(addresses)} rues, {total_addresses} adresses")
        return addresses
        
    except Exception as e:
        print(f"❌ Erreur construction cache adresses: {e}")
        # Créer un cache vide en cas d'erreur
        ADDR_CACHE_FILE.write_text(json.dumps({}), encoding="utf-8")
        return {}

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