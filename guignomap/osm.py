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

# Toutes les voies routières nommées de Mascouche
QUERY_STREETS_ALL = """
[out:json][timeout:180];
area["name"="Mascouche"]["boundary"="administrative"]->.a;
(
  way["highway"]["name"](area.a);
  way["highway"]["ref"](area.a);
);
out geom;
"""
# Note: On prend TOUT ce qui a highway+name OU highway+ref (pour autoroutes)

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
    Construit le cache des géométries pour TOUTES les voies de Mascouche
    """
    try:
        print("🔄 Récupération de TOUTES les voies de Mascouche...")
        api = overpy.Overpass()
        result = api.query(QUERY_STREETS_ALL)
        
        geo = {}
        stats = {"total": 0, "avec_geo": 0, "sans_geo": 0}
        
        ways = result.ways if hasattr(result, 'ways') else []
        print(f"📊 {len(ways)} voies trouvées dans OpenStreetMap")
        
        for way in ways:
            try:
                # Récupérer le nom ou ref (pour autoroutes)
                name = way.tags.get("name") if hasattr(way, 'tags') else None
                if not name:
                    # Pour les autoroutes sans nom, utiliser ref
                    ref = way.tags.get("ref") if hasattr(way, 'tags') else None
                    if ref:
                        name = f"Autoroute {ref}"
                    else:
                        continue
                
                stats["total"] += 1
                coords = []
                
                # Récupérer les coordonnées des nodes
                if hasattr(way, 'nodes'):
                    for node in way.nodes:
                        if hasattr(node, 'lat') and hasattr(node, 'lon'):
                            coords.append([float(node.lat), float(node.lon)])
                
                if len(coords) >= 2:
                    if name not in geo:
                        geo[name] = []
                    geo[name].append(coords)
                    stats["avec_geo"] += 1
                else:
                    stats["sans_geo"] += 1
                    print(f"⚠️ Pas de géométrie pour: {name}")
                    
            except Exception as e:
                print(f"Erreur traitement voie: {e}")
                continue
        
        print(f"✅ Statistiques: {stats['avec_geo']} voies avec géométrie, {stats['sans_geo']} sans")
        
        if geo:
            CACHE_FILE.write_text(json.dumps(geo, indent=2), encoding="utf-8")
            print(f"✅ Cache créé avec {len(geo)} voies de Mascouche")
            return geo
        else:
            raise RuntimeError("Aucune géométrie récupérée")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        # Fallback étendu avec plus de rues
        return get_fallback_geometry()

def get_fallback_geometry():
    """Fallback avec les principales voies de Mascouche"""
    return {
        "Autoroute 25": [[[45.70, -73.65], [45.78, -73.58]]],
        "Autoroute 640": [[[45.76, -73.70], [45.76, -73.55]]],
        "Montée Masson": [[[45.730, -73.620], [45.765, -73.580]]],
        "Chemin Sainte-Marie": [[[45.735, -73.615], [45.755, -73.595]]],
        "Boulevard de Mascouche": [[[45.740, -73.610], [45.752, -73.590]]],
        "Chemin des Anglais": [[[45.74, -73.65], [45.75, -73.64]]],
        "Chemin Gascon": [[[45.75, -73.62], [45.76, -73.60]]],
        "Chemin Pincourt": [[[45.72, -73.64], [45.73, -73.63]]],
        "Chemin Newton": [[[45.73, -73.58], [45.74, -73.57]]],
        "Chemin Saint-Henri": [[[45.71, -73.61], [45.72, -73.60]]],
        "Chemin Saint-Pierre": [[[45.74, -73.59], [45.75, -73.58]]],
        "Avenue de la Gare": [[[45.745, -73.601], [45.748, -73.598]]],
        "Rue Dupras": [[[45.745, -73.602], [45.748, -73.599]]],
        "Rue Saint-Pierre": [[[45.746, -73.604], [45.749, -73.600]]],
        "Rue de l'Église": [[[45.747, -73.601], [45.750, -73.599]]],
        "Avenue des Érables": [[[45.755, -73.605], [45.758, -73.600]]],
        "Rue des Pins": [[[45.756, -73.603], [45.759, -73.598]]],
        "Rue Brien": [[[45.738, -73.605], [45.741, -73.600]]],
        "Rue Bohémier": [[[45.742, -73.607], [45.745, -73.604]]]
    }

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