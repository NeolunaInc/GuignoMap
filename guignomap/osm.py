import io, json
from pathlib import Path
import pandas as pd
import overpy

# --- CSV des rues ---
QUERY_STREETS = """
[out:json][timeout:50];
area["name"="Mascouche"]["boundary"="administrative"]["admin_level"="8"]->.a;
( way["highway"]["name"](area.a); );
out tags; >; out skel qt;
"""

def generate_streets_csv(city="Mascouche"):
    """Génère un CSV avec les noms de rues de la ville"""
    try:
        api = overpy.Overpass()
        res = api.query(QUERY_STREETS)
        names = sorted({w.tags.get("name") for w in res.ways if "name" in w.tags})
        df = pd.DataFrame({"name": names, "sector": "", "team": ""})
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")
    except Exception as e:
        print(f"Erreur lors de la génération du CSV: {e}")
        # Retourner un CSV vide en cas d'erreur
        df = pd.DataFrame({"name": [], "sector": [], "team": []})
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")

# --- Cache géométrie ---
CACHE = Path(__file__).with_name("osm_cache.json")

QUERY_GEOM = """
[out:json][timeout:120];
area["name"="Mascouche"]["boundary"="administrative"]["admin_level"="8"]->.a;
( way["highway"]["name"](area.a); );
out tags geom;
"""

def build_geometry_cache():
    """Construit/écrase osm_cache.json avec les géométries des rues"""
    try:
        api = overpy.Overpass()
        res = api.query(QUERY_GEOM)
        
        geo = {}
        for w in res.ways:
            name = w.tags.get("name")
            if not name:
                continue
            
            # Récupérer les coordonnées des nœuds
            coords = []
            try:
                # Méthode 1 : via get_nodes() si disponible
                nodes = w.get_nodes(resolve_missing=True)
                coords = [[float(node.lat), float(node.lon)] for node in nodes]
            except:
                try:
                    # Méthode 2 : via les nœuds directs
                    for node_id in w.nd:
                        node = res.get_node(node_id)
                        if node:
                            coords.append([float(node.lat), float(node.lon)])
                except:
                    # Méthode 3 : si les données sont déjà dans w.nodes
                    if hasattr(w, 'nodes'):
                        coords = [[float(n.lat), float(n.lon)] for n in w.nodes]
            
            if coords:
                geo.setdefault(name, []).append(coords)
        
        # Sauvegarder le cache
        CACHE.write_text(json.dumps(geo), encoding="utf-8")
        print(f"Cache créé avec {len(geo)} rues")
        return CACHE
        
    except Exception as e:
        print(f"Erreur lors de la construction du cache: {e}")
        # Créer un cache vide en cas d'erreur
        CACHE.write_text(json.dumps({}), encoding="utf-8")
        return CACHE

def load_geometry_cache():
    """Charge le cache de géométries depuis le fichier JSON"""
    if not CACHE.exists():
        print("Cache non trouvé, création d'un cache vide")
        # Créer un cache avec quelques rues de test si le cache n'existe pas
        test_data = {
            "Rue de l'Église": [[[45.75, -73.60], [45.751, -73.601], [45.752, -73.602]]],
            "Boulevard Sainte-Marie": [[[45.745, -73.595], [45.746, -73.596], [45.747, -73.597]]],
            "Rue Principale": [[[45.740, -73.590], [45.741, -73.591], [45.742, -73.592]]]
        }
        CACHE.write_text(json.dumps(test_data), encoding="utf-8")
        return test_data
    
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Erreur lors du chargement du cache: {e}")
        return {}

# --- Fonction utilitaire pour récupérer des données de test ---
def create_test_streets_csv():
    """Crée un CSV de test avec quelques rues de Mascouche"""
    streets = [
        "Rue de l'Église",
        "Boulevard Sainte-Marie", 
        "Rue Principale",
        "Avenue des Érables",
        "Chemin Sainte-Marie",
        "Montée Masson",
        "Rue Dupras",
        "Rue Saint-Pierre",
        "Rue Bohémier",
        "Boulevard de Mascouche",
        "Rue Chartrand",
        "Rue Garden",
        "Rue Lamoureux",
        "Rue Morin",
        "Rue Napoléon",
        "Avenue de la Gare",
        "Rue des Pins",
        "Rue des Cèdres",
        "Rue Forget",
        "Rue Gravel"
    ]
    
    df = pd.DataFrame({
        "name": streets,
        "sector": ["Centre"] * 10 + ["Nord"] * 5 + ["Sud"] * 5,
        "team": [""] * 20
    })
    
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")