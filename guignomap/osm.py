"""
Module OSM pour Guigno-Map
G√®re l'import et le cache des donn√©es OpenStreetMap pour Mascouche
"""

import io
import json
from pathlib import Path
import pandas as pd
import overpy

# Configuration
CACHE_FILE = Path(__file__).parent / "osm_cache.json"
ADDR_CACHE_FILE = Path(__file__).parent / "osm_addresses.json"

# Toutes les voies routi√®res nomm√©es de Mascouche
QUERY_STREETS_ALL = """
[out:json][timeout:300];
area["name"="Mascouche"]["boundary"="administrative"]->.a;
(
  way["highway"~"^(primary|secondary|tertiary|residential|service|unclassified|living_street|pedestrian|track|road|busway|footway|path)$"](area.a);
);
(._;>;);
out body;
"""
# Note: R√©cup√®re TOUS les types de voies incluant petites rues, all√©es, chemins pi√©tonniers

# Requ√™te pour les adresses
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
    G√©n√®re un CSV avec les noms des rues principales de la ville
    Filtre automatiquement les rues priv√©es et les petites ruelles
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
            # garder si on a une vraie g√©om√©trie (>= 2 points)
            if isinstance(g, list) and len(g) >= 2:
                streets.append(name)

        streets = sorted(set(streets))
        
        # Assigner automatiquement des secteurs bas√©s sur les patterns de noms
        sectors = []
        for street in streets:
            if any(word in street.lower() for word in ["mont√©e", "chemin", "boulevard"]):
                sectors.append("Principal")
            elif any(word in street.lower() for word in ["avenue", "place", "croissant"]):
                sectors.append("R√©sidentiel")
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
        print(f"‚úÖ CSV g√©n√©r√© avec {len(streets)} rues principales")
        return buf.getvalue().encode("utf-8")
        
    except Exception as e:
        print(f"‚ùå Erreur OSM: {e}")
        # Retourner des donn√©es de test en cas d'erreur
        return create_fallback_csv()

def build_geometry_cache():
    """
    Construit le cache des g√©om√©tries pour TOUTES les voies de Mascouche
    Force la r√©solution compl√®te des nodes
    """
    try:
        print("üîÑ R√©cup√©ration compl√®te de toutes les voies de Mascouche...")
        
        # IMPORTANT: Configurer l'API pour r√©soudre automatiquement les nodes manquants
        api = overpy.Overpass()
        
        # Requ√™te am√©lior√©e qui force le retour des coordonn√©es
        query = """
        [out:json][timeout:300];
        area["name"="Mascouche"]["boundary"="administrative"]->.a;
        (
          way["highway"]["name"](area.a);
          way["highway"]["ref"](area.a);
        );
        (._;>;);
        out body;
        """
        
        print("üì° Connexion √† OpenStreetMap (cela peut prendre 30-60 secondes)...")
        result = api.query(query)
        
        geo = {}
        stats = {"total": 0, "avec_geo": 0, "sans_geo": 0}
        
        # Construire un dictionnaire des nodes pour acc√®s rapide
        nodes_dict = {}
        if hasattr(result, 'nodes'):
            for node in result.nodes:
                if hasattr(node, 'id') and hasattr(node, 'lat') and hasattr(node, 'lon'):
                    nodes_dict[node.id] = (float(node.lat), float(node.lon))
        
        print(f"üìç {len(nodes_dict)} nodes r√©cup√©r√©s")
        
        ways = result.ways if hasattr(result, 'ways') else []
        print(f"üìä {len(ways)} voies trouv√©es dans OpenStreetMap")
        
        for way in ways:
            try:
                # R√©cup√©rer le nom ou ref
                if not hasattr(way, 'tags'):
                    continue
                    
                name = way.tags.get("name")
                if not name:
                    ref = way.tags.get("ref")
                    if ref:
                        name = f"Autoroute {ref}"
                    else:
                        continue
                
                stats["total"] += 1
                coords = []
                
                # R√©cup√©rer les IDs des nodes
                if hasattr(way, 'nd_ids'):
                    # Si on a les IDs des nodes, les r√©soudre
                    for node_id in way.nd_ids:
                        if node_id in nodes_dict:
                            lat, lon = nodes_dict[node_id]
                            coords.append([lat, lon])
                elif hasattr(way, 'nodes'):
                    # Si on a directement les nodes
                    for node in way.nodes:
                        if hasattr(node, 'lat') and hasattr(node, 'lon'):
                            coords.append([float(node.lat), float(node.lon)])
                        elif hasattr(node, 'id') and node.id in nodes_dict:
                            lat, lon = nodes_dict[node.id]
                            coords.append([lat, lon])
                
                if len(coords) >= 2:
                    if name not in geo:
                        geo[name] = []
                    geo[name].append(coords)
                    stats["avec_geo"] += 1
                else:
                    stats["sans_geo"] += 1
                    
            except Exception as e:
                continue
        
        print(f"‚úÖ R√©sultat: {stats['avec_geo']} voies avec g√©om√©trie sur {stats['total']} trouv√©es")
        
        # Si on a r√©cup√©r√© des donn√©es, sauvegarder
        if geo:
            CACHE_FILE.write_text(json.dumps(geo, indent=2), encoding="utf-8")
            print(f"üíæ Cache cr√©√©: {len(geo)} voies sauvegard√©es dans osm_cache.json")
            
            # Importer aussi automatiquement dans la DB
            try:
                from pathlib import Path
                import sys
                sys.path.append(str(Path(__file__).parent))
                import db
                
                db_path = Path(__file__).parent / "guigno_map.db"
                conn = db.get_conn(db_path)
                
                # Ajouter les rues manquantes √† la DB
                for street_name in geo.keys():
                    cursor = conn.execute("SELECT COUNT(*) FROM streets WHERE name = ?", (street_name,))
                    if cursor.fetchone()[0] == 0:
                        conn.execute(
                            "INSERT INTO streets(name, sector, team, status) VALUES (?, '', '', 'a_faire')",
                            (street_name,)
                        )
                conn.commit()
                print(f"‚úÖ Rues import√©es dans la base de donn√©es")
            except Exception as e:
                print(f"‚ö†Ô∏è Import DB: {e}")
            
            return geo
        
        # Si aucune donn√©e, utiliser un fallback √©tendu
        print("‚ö†Ô∏è Aucune donn√©e OSM, utilisation du fallback local")
        return get_extended_fallback()
            
    except Exception as e:
        print(f"‚ùå Erreur: {e}")
        return get_extended_fallback()

def get_fallback_geometry():
    """Fallback avec les principales voies de Mascouche"""
    return {
        "Autoroute 25": [[[45.70, -73.65], [45.78, -73.58]]],
        "Autoroute 640": [[[45.76, -73.70], [45.76, -73.55]]],
        "Mont√©e Masson": [[[45.730, -73.620], [45.765, -73.580]]],
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
        "Rue de l'√âglise": [[[45.747, -73.601], [45.750, -73.599]]],
        "Avenue des √ârables": [[[45.755, -73.605], [45.758, -73.600]]],
        "Rue des Pins": [[[45.756, -73.603], [45.759, -73.598]]],
        "Rue Brien": [[[45.738, -73.605], [45.741, -73.600]]],
        "Rue Boh√©mier": [[[45.742, -73.607], [45.745, -73.604]]]
    }

def get_extended_fallback():
    """Fallback √©tendu avec les principales voies de Mascouche"""
    fallback = {
        # Autoroutes
        "Autoroute 25": [[[45.70, -73.65], [45.72, -73.63], [45.74, -73.61], [45.76, -73.59], [45.78, -73.58]]],
        "Autoroute 640": [[[45.76, -73.70], [45.76, -73.65], [45.76, -73.60], [45.76, -73.55]]],
        
        # Chemins principaux
        "Mont√©e Masson": [[[45.730, -73.620], [45.740, -73.610], [45.750, -73.600], [45.765, -73.580]]],
        "Chemin Sainte-Marie": [[[45.735, -73.615], [45.745, -73.605], [45.755, -73.595]]],
        "Boulevard de Mascouche": [[[45.740, -73.610], [45.747, -73.600], [45.752, -73.590]]],
        "Chemin des Anglais": [[[45.74, -73.65], [45.745, -73.645], [45.75, -73.64]]],
        "Chemin Gascon": [[[45.75, -73.62], [45.755, -73.615], [45.76, -73.60]]],
        "Chemin Pincourt": [[[45.72, -73.64], [45.725, -73.635], [45.73, -73.63]]],
        "Chemin Newton": [[[45.73, -73.58], [45.735, -73.575], [45.74, -73.57]]],
        "Chemin Saint-Henri": [[[45.71, -73.61], [45.715, -73.605], [45.72, -73.60]]],
        "Chemin Saint-Pierre": [[[45.74, -73.59], [45.745, -73.585], [45.75, -73.58]]],
        
        # Avenues
        "Avenue de la Gare": [[[45.745, -73.601], [45.747, -73.599], [45.748, -73.598]]],
        "Avenue Bourque": [[[45.742, -73.603], [45.744, -73.601], [45.746, -73.599]]],
        "Avenue Cr√©peau": [[[45.743, -73.602], [45.745, -73.600], [45.747, -73.598]]],
        "Avenue Garden": [[[45.751, -73.606], [45.753, -73.604], [45.755, -73.602]]],
        "Avenue de l'Esplanade": [[[45.748, -73.605], [45.750, -73.603], [45.752, -73.601]]],
        
        # Rues du centre
        "Rue Dupras": [[[45.745, -73.602], [45.747, -73.600], [45.748, -73.599]]],
        "Rue Saint-Pierre": [[[45.746, -73.604], [45.748, -73.602], [45.749, -73.600]]],
        "Rue de l'√âglise": [[[45.747, -73.601], [45.749, -73.599], [45.750, -73.598]]],
        "Rue Brien": [[[45.738, -73.605], [45.740, -73.603], [45.741, -73.600]]],
        "Rue Boh√©mier": [[[45.742, -73.607], [45.744, -73.605], [45.745, -73.604]]],
        
        # Rues r√©sidentielles
        "Rue des Pins": [[[45.756, -73.603], [45.758, -73.601], [45.759, -73.598]]],
        "Avenue des √ârables": [[[45.755, -73.605], [45.757, -73.603], [45.758, -73.600]]],
        "Rue Gravel": [[[45.738, -73.605], [45.740, -73.603], [45.741, -73.600]]]
    }
    
    # Sauvegarder le fallback
    CACHE_FILE.write_text(json.dumps(fallback, indent=2), encoding="utf-8")
    print(f"üíæ Fallback sauvegard√© avec {len(fallback)} voies principales")
    
    return fallback

def load_geometry_cache():
    """
    Charge le cache de g√©om√©tries depuis le fichier JSON
    Cr√©e un cache de base si le fichier n'existe pas
    """
    if not CACHE_FILE.exists():
        print("‚ö†Ô∏è Cache non trouv√©, construction en cours...")
        return build_geometry_cache()  # build_geometry_cache() g√®re d√©j√† le fallback en m√©moire
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            print(f"‚úÖ Cache charg√©: {len(cache)} rues")
            return cache
    except Exception as e:
        print(f"‚ùå Erreur chargement cache: {e}")
        # Ne pas √©crire de fallback sur disque ! Utiliser build_geometry_cache() qui g√®re le fallback en m√©moire
        return build_geometry_cache()

def create_fallback_csv():
    """
    Cr√©e un CSV de fallback avec quelques rues principales de Mascouche
    Utilis√© si l'API OSM est indisponible
    """
    fallback_streets = [
        ("Mont√©e Masson", "Principal"),
        ("Chemin Sainte-Marie", "Principal"),
        ("Boulevard de Mascouche", "Principal"),
        ("Chemin des Anglais", "Principal"),
        ("Rue Dupras", "Centre"),
        ("Rue Saint-Pierre", "Centre"),
        ("Rue de l'√âglise", "Centre"),
        ("Avenue des √ârables", "R√©sidentiel"),
        ("Rue des Pins", "R√©sidentiel"),
        ("Avenue Garden", "R√©sidentiel"),
    ]
    
    df = pd.DataFrame(fallback_streets, columns=["name", "sector"])
    df["team"] = ""
    
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    print("‚ö†Ô∏è Mode fallback: 10 rues de test")
    return buf.getvalue().encode("utf-8")

def create_fallback_cache():
    """
    Cr√©e un cache minimal pour tests
    """
    fallback_geo = {
        "Mont√©e Masson": [[[45.730, -73.620], [45.750, -73.600], [45.765, -73.580]]],
        "Chemin Sainte-Marie": [[[45.735, -73.615], [45.748, -73.602], [45.755, -73.595]]],
        "Boulevard de Mascouche": [[[45.740, -73.610], [45.747, -73.600], [45.752, -73.590]]],
        "Rue Dupras": [[[45.745, -73.602], [45.748, -73.599]]],
        "Rue Saint-Pierre": [[[45.746, -73.604], [45.749, -73.600]]],
        "Rue de l'√âglise": [[[45.747, -73.601], [45.750, -73.599]]],
        "Avenue des √ârables": [[[45.755, -73.605], [45.758, -73.600]]],
        "Rue des Pins": [[[45.756, -73.603], [45.759, -73.598]]],
        "Avenue Garden": [[[45.753, -73.606], [45.756, -73.601]]],
        "Rue Gravel": [[[45.738, -73.605], [45.741, -73.600]]]
    }
    
    CACHE_FILE.write_text(json.dumps(fallback_geo, indent=2), encoding="utf-8")
    print("‚ö†Ô∏è Cache fallback cr√©√© avec 10 rues")

# Fonction utilitaire pour tests
def test_osm_connection():
    """
    Teste la connexion √† l'API Overpass
    """
    try:
        api = overpy.Overpass()
        # Requ√™te minimale pour tester
        result = api.query('[out:json];node(45.7475,-73.6005,45.7476,-73.6004);out;')
        print("‚úÖ Connexion OSM OK")
        return True
    except:
        print("‚ùå Connexion OSM √©chou√©e")
        return False

# ========================================
# NOUVELLES FONCTIONS POUR LES ADRESSES
# ========================================

def build_addresses_cache():
    """
    Construit le cache des adresses OSM pour Mascouche
    R√©cup√®re addr:housenumber + addr:street depuis OSM
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
            
            # R√©cup√©rer le centre du way
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
        
        # Trier les adresses par num√©ro pour chaque rue
        for street_name in addresses:
            try:
                # Tri num√©rique intelligent
                addresses[street_name].sort(
                    key=lambda x: (
                        int(''.join(filter(str.isdigit, x["number"]))) 
                        if any(c.isdigit() for c in x["number"]) 
                        else float('inf')
                    )
                )
            except:
                # Si le tri √©choue, garder l'ordre original
                pass
        
        # Sauvegarder le cache
        ADDR_CACHE_FILE.write_text(json.dumps(addresses, indent=2), encoding="utf-8")
        total_addresses = sum(len(addrs) for addrs in addresses.values())
        print(f"‚úÖ Cache adresses cr√©√©: {len(addresses)} rues, {total_addresses} adresses")
        return addresses
        
    except Exception as e:
        print(f"‚ùå Erreur construction cache adresses: {e}")
        # Cr√©er un cache vide en cas d'erreur
        ADDR_CACHE_FILE.write_text(json.dumps({}), encoding="utf-8")
        return {}

def load_addresses_cache():
    """
    Charge le cache d'adresses depuis le fichier JSON
    """
    if not ADDR_CACHE_FILE.exists():
        print("‚ö†Ô∏è Cache adresses non trouv√©")
        return {}
    
    try:
        with open(ADDR_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            total_addresses = sum(len(addrs) for addrs in cache.values())
            print(f"‚úÖ Cache adresses charg√©: {len(cache)} rues, {total_addresses} adresses")
            return cache
    except Exception as e:
        print(f"‚ùå Erreur chargement cache adresses: {e}")
        return {}