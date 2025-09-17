"""
Guigno-Map - Application de gestion de collecte de denr√©es
Le Relais de Mascouche
Version 3.0 - Production
"""

# pyright: reportCallIssue=false

import sys
from pathlib import Path
import time
from datetime import datetime
import pandas as pd
import streamlit as st

# Ajout du répertoire parent au path pour importer src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# --- Compat Streamlit: retirer `width=` et mapper vers `use_container_width` si pertinent ---
try:
    _orig_button = st.button
    def _button_compat(label, **kwargs):
        w = str(kwargs.pop("width", "")).lower() if "width" in kwargs else ""
        if w in {"stretch","full","100%","true"}:
            kwargs["use_container_width"] = True
        return _orig_button(label, **kwargs)
    st.button = _button_compat

    _orig_dl = st.download_button
    def _download_button_compat(*args, **kwargs):
        # retirer toute trace de `width` pour √©viter l'erreur de signature
        kwargs.pop("width", None)
        return _orig_dl(*args, **kwargs)
    st.download_button = _download_button_compat

    _orig_form_submit = st.form_submit_button
    def _form_submit_button_compat(label, **kwargs):
        # supprimer 'width' pour √©viter l'erreur de signature
        kwargs.pop("width", None)
        return _orig_form_submit(label, **kwargs)
    st.form_submit_button = _form_submit_button_compat
except Exception:
    pass

# Configuration Streamlit (doit √™tre la premi√®re commande Streamlit)
st.set_page_config(
    page_title="Guigno-Map | Relais de Mascouche",
    page_icon="üéÅ",
    layout="wide",
    initial_sidebar_state="expanded"
)

import folium
from streamlit_folium import st_folium

# Import des modules locaux
from src.database import operations as db
from guignomap.validators import validate_and_clean_input
from guignomap.osm import build_geometry_cache, load_geometry_cache, build_addresses_cache, load_addresses_cache, CACHE_FILE
from src.utils.adapters import to_dataframe

# --- Utilitaire de compatibilit√© pandas Styler ---
from typing import Callable, Any

def style_map_compat(df: pd.DataFrame, fn: Callable[[Any], str], subset: Any = None):
    """Applique un style cellule-√†-cellule en utilisant Styler.map si disponible,
    sinon fallback dynamique vers applymap sans exposer l'attribut (OK pour Pylance).
    
    Args:
        df: DataFrame √† styliser
        fn: Fonction qui prend une valeur cellule et retourne une string CSS
        subset: Colonnes √† cibler (ex: ['status'] ou None pour toutes)
    """
    styler = df.style
    if hasattr(styler, "map"):
        # Pandas 2.4+ : utilise la nouvelle API map()
        return styler.map(fn, subset=subset)
    # Pandas < 2.4 : fallback vers applymap (sans r√©f√©rence statique)
    return getattr(styler, "applymap")(fn, subset=subset)

# --- Mapping des statuts pour l'affichage ---
STATUS_TO_LABEL = {"a_faire": "√Ä faire", "en_cours": "En cours", "terminee": "Termin√©e"}
LABEL_TO_STATUS = {v: k for k, v in STATUS_TO_LABEL.items()}

ASSETS = Path(__file__).parent / "assets"

# Initialisation session
if "auth" not in st.session_state:
    st.session_state.auth = None

# ============================================
# COMPOSANTS UI
# ============================================

def inject_css():
    """Charge le CSS depuis le fichier externe"""
    css_file = ASSETS / "styles.css"
    if css_file.exists():
        css = css_file.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def render_header():
    """Header moderne avec logo Guignol√©e et design festif"""
    
    # Container principal avec fond festif
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #c41e3a 0%, #165b33 100%);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    ">
        <!-- Flocons de neige anim√©s en CSS -->
        <div style="position: absolute; width: 100%; height: 100%; opacity: 0.1;">
            <span style="position: absolute; top: 10%; left: 10%; font-size: 2rem;">‚ùÑÔ∏è</span>
            <span style="position: absolute; top: 20%; left: 80%; font-size: 1.5rem;">‚ùÑÔ∏è</span>
            <span style="position: absolute; top: 60%; left: 30%; font-size: 1.8rem;">‚ùÑÔ∏è</span>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 5, 2])
    
    with col1:
        # Logo Guignol√©e
        if (ASSETS / "guignolee.png").exists():
            st.image(str(ASSETS / "guignolee.png"), width=150)
    
    with col2:
        st.markdown("""
        <div style="text-align: center;">
            <h1 style="
                color: white;
                font-family: 'Manrope', sans-serif;
                font-size: 2.5rem;
                margin: 0;
                text-shadow: 3px 3px 6px rgba(0,0,0,0.5);
                letter-spacing: 2px;
            ">üéÖ GUIGNOL√âE 2025 üéÅ</h1>
            <p style="
                color: #FFD700;
                font-size: 1.2rem;
                margin: 0.5rem 0 0 0;
                font-weight: 600;
            ">Le Relais de Mascouche - 1er d√©cembre</p>
            <p style="
                color: rgba(255,255,255,0.9);
                font-size: 1rem;
                margin-top: 0.5rem;
            ">Syst√®me de gestion de collecte</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Stats en temps r√©el
        stats = db.extended_stats()
        # Normalisation anti-KeyError (valeurs par d√©faut)
        stats = stats or {}
        total = int(stats.get('total') or stats.get('count') or 0)
        done = int(stats.get('done') or stats.get('completed') or 0)
        # R√©injecte pour la suite de l'UI si d'autres blocs lisent ces cl√©s
        stats['total'] = total
        stats['done'] = done
        progress = (done / total * 100) if total > 0 else 0
        
        st.markdown(f"""
        <div style="
            background: rgba(255,255,255,0.2);
            border-radius: 15px;
            padding: 1rem;
            text-align: center;
        ">
            <div style="color: #FFD700; font-size: 2rem; font-weight: bold;">
                {progress:.0f}%
            </div>
            <div style="color: white; font-size: 0.9rem;">
                Compl√©t√©
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_login_card(role="benevole"):
    """Carte de connexion moderne avec design festif"""
    
    # Container de connexion stylis√©
    st.markdown("""
    <div style="
        max-width: 400px;
        margin: 3rem auto;
        background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
        backdrop-filter: blur(10px);
        border: 2px solid rgba(255,215,0,0.3);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    ">
    """, unsafe_allow_html=True)
    
    # Ic√¥ne et titre
    if role == "superviseur" or role == "gestionnaire":
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 3rem;">üëî</div>
            <h2 style="color: #FFD700; margin: 1rem 0;">Espace Gestionnaire</h2>
            <p style="color: #cbd5e1;">G√©rez la collecte et les √©quipes</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_gestionnaire", clear_on_submit=False):
            password = st.text_input(
                "üîê Mot de passe",
                type="password",
                placeholder="Entrez le mot de passe gestionnaire"
            )
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                submit = st.form_submit_button(
                    "üöÄ Connexion",
                    width="stretch"
                )
            
            if submit:
                if db.verify_team("ADMIN", password):
                    st.session_state.auth = {"role": "supervisor", "team_id": "ADMIN"}
                    st.success("‚úÖ Bienvenue dans l'espace gestionnaire!")
                    st.snow()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("‚ùå Mot de passe incorrect")
    
    else:  # B√©n√©vole
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 3rem;">üéÖ</div>
            <h2 style="color: #FFD700; margin: 1rem 0;">Espace B√©n√©vole</h2>
            <p style="color: #cbd5e1;">Acc√©dez √† vos rues assign√©es</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_benevole", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                team_id = st.text_input(
                    "üë• Identifiant d'√©quipe",
                    placeholder="Ex: EQ001"
                )
            
            with col2:
                password = st.text_input(
                    "üîê Mot de passe",
                    type="password",
                    placeholder="Mot de passe √©quipe"
                )
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                submit = st.form_submit_button(
                    "üéÑ Connexion",
                    width="stretch"
                )
            
            if submit:
                if db.verify_team(team_id, password):
                    st.session_state.auth = {"role": "volunteer", "team_id": team_id}
                    st.success(f"‚úÖ Bienvenue √©quipe {team_id}!")
                    st.snow()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("‚ùå Identifiants incorrects")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Aide en bas
    st.markdown("""
    <div style="text-align: center; margin-top: 2rem; color: #8b92a4;">
        <small>
        Besoin d'aide? Contactez votre gestionnaire<br>
        üìû 450-474-4133
        </small>
    </div>
    """, unsafe_allow_html=True)

def render_metrics(stats):
    """Affiche les m√©triques principales"""
    progress = (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Rues", stats['total'])
    
    with col2:
        st.metric("Rues Termin√©es", stats['done'])
    
    with col3:
        st.metric("En Cours", stats.get('partial', 0))
    
    with col4:
        st.metric("Progression", f"{progress:.1f}%")

def render_dashboard_gestionnaire(geo):
    """Dashboard moderne pour gestionnaires avec KPIs visuels"""
    
    # KPIs principaux en cartes color√©es
    stats = db.extended_stats()
    progress = (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    st.markdown("### üìä Tableau de bord en temps r√©el")
    
    # Ligne de KPIs avec ic√¥nes festives
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #22c55e, #16a34a);
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(34,197,94,0.3);
        ">
            <div style="font-size: 2.5rem;">üèòÔ∏è</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{stats['total']}</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">Total Rues</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(59,130,246,0.3);
        ">
            <div style="font-size: 2.5rem;">‚úÖ</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{stats['done']}</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">Termin√©es</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #f59e0b, #d97706);
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(245,158,11,0.3);
        ">
            <div style="font-size: 2.5rem;">üö∂</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{stats.get('partial', 0)}</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">En cours</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Nombre d'√©quipes actives
        teams_count = len(db.teams())
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(139,92,246,0.3);
        ">
            <div style="font-size: 2.5rem;">üë•</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{teams_count}</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">√âquipes</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #c41e3a, #165b33);
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(196,30,58,0.3);
        ">
            <div style="font-size: 2.5rem;">üéØ</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{progress:.0f}%</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">Progression</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Barre de progression visuelle
    st.markdown("### üéÑ Progression globale")
    st.progress(progress / 100)
    
    # Graphique par secteur (si disponible)
    st.markdown("### üìà Performance par √©quipe")
    try:
        teams_stats = db.stats_by_team()
        if teams_stats:  # Liste non vide
            # Convertir en DataFrame pour plotly
            import pandas as pd
            teams_df = pd.DataFrame(teams_stats)
            
            # Calculer le pourcentage de progression
            teams_df['progress'] = ((teams_df['completed'] / teams_df['total_streets']) * 100).fillna(0)
            
            # Graphique en barres color√©es
            import plotly.express as px
            fig = px.bar(
                teams_df, 
                x='id', 
                y='progress',
                color='progress',
                color_continuous_scale=['#ef4444', '#f59e0b', '#22c55e'],
                labels={'team': '√âquipe', 'progress': 'Progression (%)'},
                title="Performance des √©quipes"
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune statistique d'√©quipe disponible")
    except Exception as e:
        st.warning("Graphiques non disponibles (module plotly manquant)")
        # Fallback vers un tableau simple
        try:
            teams_stats = db.stats_by_team()
            if teams_stats:  # Liste non vide
                st.dataframe(to_dataframe(teams_stats), use_container_width=True)
        except:
            st.info("Aucune statistique d'√©quipe disponible")

def add_persistent_legend(m):
    """Ajoute une l√©gende persistante pour les 4 √©tats des rues via contr√¥le HTML"""
    legend_html = """
    <div id='gm-legend' class='leaflet-control-layers leaflet-control' 
         style='position: absolute; bottom: 10px; right: 10px; z-index: 1000;
                background: white; border: 2px solid rgba(0,0,0,0.2); 
                border-radius: 5px; padding: 10px; box-shadow: 0 1px 5px rgba(0,0,0,0.2);
                font-family: "Helvetica Neue", Arial, Helvetica, sans-serif; 
                font-size: 12px; line-height: 18px; color: #333;'>
        <strong style='margin-bottom: 8px; display: block;'>L√©gende</strong>
        <div style='margin: 4px 0; display: flex; align-items: center;'>
            <span style='width: 20px; height: 0; border-top: 3px solid #28a745; 
                         display: inline-block; margin-right: 8px;'></span>
            <span>Termin√©e</span>
        </div>
        <div style='margin: 4px 0; display: flex; align-items: center;'>
            <span style='width: 20px; height: 0; border-top: 3px solid #f1c40f; 
                         display: inline-block; margin-right: 8px;'></span>
            <span>En cours</span>
        </div>
        <div style='margin: 4px 0; display: flex; align-items: center;'>
            <span style='width: 20px; height: 0; border-top: 3px solid #ff4d4f; 
                         display: inline-block; margin-right: 8px;'></span>
            <span>Assign√©e (√† faire)</span>
        </div>
        <div style='margin: 4px 0; display: flex; align-items: center;'>
            <span style='width: 20px; height: 0; border-top: 3px dashed #ff4d4f; 
                         display: inline-block; margin-right: 8px;'></span>
            <span>Non assign√©e</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

def create_map(df, geo):
    """Cr√©e la carte Folium centr√©e sur Mascouche avec toutes les rues"""
    # 1) Coercition s√ªre en DataFrame
    if not isinstance(df, pd.DataFrame):
        try:
            df = pd.DataFrame(df)
        except Exception:
            df = pd.DataFrame([])
    
    # Limites de Mascouche
    bounds = {
        "north": 45.78,
        "south": 45.70,
        "east": -73.55,
        "west": -73.70
    }
    center = [(bounds["north"] + bounds["south"]) / 2, 
              (bounds["east"] + bounds["west"]) / 2]
    
    # Cr√©er la carte
    m = folium.Map(
        location=center,
        zoom_start=13,  # Zoom optimis√© pour voir toute la ville
        tiles="https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
        attr='¬© OpenStreetMap France',
        control_scale=True,
        max_bounds=True,
        min_zoom=11,
        max_zoom=18,
        prefer_canvas=True,
        zoom_control=True,
        scrollWheelZoom=True
    )
    
    # Ajouter plusieurs couches de fond
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png',
        attr='¬© OpenStreetMap France',
        name='OSM France (D√©taill√©)',
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
        attr='¬© CARTO',
        name='CARTO Voyager',
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attr='¬© Esri',
        name='Esri WorldStreetMap',
        overlay=False,
        control=True
    ).add_to(m)

    # Ajouter le contr√¥le des couches
    folium.LayerControl().add_to(m)
    
    # D√©finir les limites de la carte sur Mascouche
    m.fit_bounds([[bounds["south"], bounds["west"]], 
                  [bounds["north"], bounds["east"]]])
    
    if not geo:
        st.warning("Aucune donn√©e g√©om√©trique disponible")
        return m
    
    # Construire le lookup des infos DB
    street_info = {}
    if not df.empty:  # DataFrame non vide
        for idx, row in df.iterrows():
            name = str(row.get('name', '')) if pd.notna(row.get('name', '')) else ''
            status = row.get('status', 'a_faire')
            status = status if pd.notna(status) else 'a_faire'
            team = row.get('team', '')
            team = team if pd.notna(team) else ''
            notes = str(row.get('notes', '0')) if pd.notna(row.get('notes', '0')) else '0'
            
            street_info[name] = {
                'status': status,
                'team': str(team).strip() if team else '',
                'notes': notes
            }
    
    # Couleurs par statut
    status_colors = {
        'terminee': '#22c55e',  # Vert
        'en_cours': '#f59e0b',  # Orange
        'a_faire': '#ef4444'    # Rouge
    }
    
    # Compteurs pour stats
    stats = {"total": 0, "assigned": 0, "unassigned": 0}
    
    # Ajouter TOUTES les rues de la g√©om√©trie
    for name, paths in geo.items():
        stats["total"] += 1
        
        # Info depuis DB ou d√©faut (rouge pointill√©)
        info = street_info.get(name, {
            'status': 'a_faire',
            'team': '',
            'notes': '0'
        })
        
        status = info['status']
        team = info['team']
        notes = info['notes']
        
        # Style: TOUJOURS pointill√© si pas d'√©quipe
        has_team = bool(team)
        color = status_colors.get(status, '#ef4444')  # Rouge par d√©faut
        opacity = 0.9 if has_team else 0.7
        dash = None if has_team else '8,12'  # Pointill√©s si non assign√©
        weight = 7 if has_team else 5
        
        if has_team:
            stats["assigned"] += 1
        else:
            stats["unassigned"] += 1
        
        # Tooltip informatif
        tooltip_html = f"""
        <div style='font-family: sans-serif'>
            <strong style='font-size: 14px'>{name}</strong><br>
            <span style='color: {color}'>‚óè Statut: {status.replace('_', ' ').title()}</span><br>
            <span>üìã √âquipe: {team if team else '‚ö†Ô∏è NON ASSIGN√âE'}</span><br>
            <span>üìù Notes: {notes}</span>
        </div>
        """
        
        # Ajouter chaque segment de la rue
        for path in paths:
            if path and len(path) >= 2:
                folium.PolyLine(
                    path,
                    color=color,
                    weight=weight,
                    opacity=opacity,
                    dash_array=dash,
                    tooltip=folium.Tooltip(tooltip_html, sticky=True)
                ).add_to(m)
    
    # Ajouter un marqueur au centre-ville
    folium.Marker(
        [45.7475, -73.6005],
        popup="Centre-ville de Mascouche",
        tooltip="Centre-ville",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Ajouter la l√©gende persistante
    add_persistent_legend(m)
    
    return m


# ============================================
# UTILITAIRES EXPORT
# ============================================

def export_excel_professionnel(conn):
    """Export Excel avec mise en forme professionnelle"""
    try:
        from reports import ReportGenerator
        generator = ReportGenerator()
        return generator.generate_excel()
    except ImportError:
        # Fallback si les d√©pendances ne sont pas install√©es
        return db.export_to_csv()


# ============================================
# FONCTIONNALIT√âS AVANC√âES
# ============================================

def detect_mobile():
    """D√©tecte si l'utilisateur est sur mobile"""
    try:
        # R√©cup√©rer les param√®tres de l'URL pour forcer le mode mobile
        query_params = st.experimental_get_query_params()
        if 'mobile' in query_params:
            return True
        
        # Mobile-first approach pour l'instant
        return True
    except:
        return False

def show_notification(message, type="success"):
    """Affiche une notification stylis√©e"""
    icons = {
        "success": "‚úÖ",
        "error": "‚ùå",
        "warning": "‚ö†Ô∏è",
        "info": "‚ÑπÔ∏è"
    }
    colors = {
        "success": "#22c55e",
        "error": "#ef4444", 
        "warning": "#f59e0b",
        "info": "#3b82f6"
    }
    
    st.markdown(f"""
    <div style="
        position: fixed;
        top: 20px;
        right: 20px;
        background: {colors[type]};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
    ">
        <strong>{icons[type]} {message}</strong>
    </div>
    <style>
    @keyframes slideIn {{
        from {{ transform: translateX(100%); opacity: 0; }}
        to {{ transform: translateX(0); opacity: 1; }}
    }}
    </style>
    """, unsafe_allow_html=True)

def show_team_badges(team_id):
    """Affiche les badges de r√©ussite de l'√©quipe"""
    try:
        df = db.list_streets(team=team_id)
        done = len(df[df['status'] == 'terminee'])
        total = len(df)
        
        badges = []
        if done >= 1:
            badges.append("üèÜ Premi√®re rue!")
        if done >= total * 0.25:
            badges.append("ü•â 25% compl√©t√©")
        if done >= total * 0.5:
            badges.append("ü•à 50% compl√©t√©")
        if done >= total * 0.75:
            badges.append("ü•á 75% compl√©t√©")
        if done == total:
            badges.append("üåü CHAMPION!")
        
        if badges:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #FFD700, #FFA500);
                padding: 1rem;
                border-radius: 10px;
                text-align: center;
                margin: 1rem 0;
            ">
                <strong>Vos badges:</strong><br>
                <div style="font-size: 2rem; margin-top: 0.5rem;">
                    {' '.join(badges)}
                </div>
            </div>
            """, unsafe_allow_html=True)
    except:
        pass

def generate_sms_list(conn):
    """G√©n√®re une liste de t√©l√©phones pour SMS de groupe"""
    try:
        # Cette fonction n√©cessiterait une table de t√©l√©phones
        # Pour l'instant, retourne un exemple
        return "# Liste des t√©l√©phones b√©n√©voles\n# 450-XXX-XXXX\n# 438-XXX-XXXX"
    except:
        return "Liste non disponible"

def page_export_gestionnaire(conn):
    """Section export avec formats multiples"""
    
    st.markdown("### üìä Centre d'export des donn√©es")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; border: 2px dashed #ccc; border-radius: 10px;">
            <h4>ÔøΩ Rapport PDF</h4>
            <p><small>Format professionnel pour pr√©sentation</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            from reports import ReportGenerator
            generator = ReportGenerator()
            pdf_data = generator.generate_pdf()
            st.download_button(
                "üì• T√©l√©charger PDF",
                pdf_data,
                "rapport_guignolee_2025.pdf",
                "application/pdf",
                width="stretch"
            )
        except ImportError:
            st.button("PDF (Installer reportlab)", disabled=True, width="stretch")
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; border: 2px dashed #ccc; border-radius: 10px;">
            <h4>üìä Excel d√©taill√©</h4>
            <p><small>Avec graphiques et mise en forme</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            excel_data = export_excel_professionnel(conn)
            st.download_button(
                "üì• T√©l√©charger Excel",
                excel_data,
                "guignolee_2025.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )
        except:
            st.button("Excel (Non disponible)", disabled=True, width="stretch")
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; border: 2px dashed #ccc; border-radius: 10px;">
            <h4>üì± Liste SMS</h4>
            <p><small>T√©l√©phones des b√©n√©voles</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        sms_list = generate_sms_list(conn)
        st.download_button(
            "üì• Liste t√©l√©phones",
            sms_list,
            "telephones_benevoles.txt",
            "text/plain",
            width="stretch"
        )


# ============================================
# PAGES
# ============================================

def page_accueil(conn, geo):
    """Page d'accueil"""
    st.markdown("### üéÅ Bienvenue sur Guigno-Map!")
    st.info("S√©lectionnez votre mode dans le menu de gauche pour commencer.")
    
    st.markdown("---")
    st.markdown("#### üìä Aper√ßu de la collecte")
    
    stats = db.extended_stats()
    render_metrics(stats)
    
    df_all = db.list_streets()
    if not df_all.empty:  # Liste non vide
        m = create_map(df_all, geo)
        st_folium(m, height=800, width=None, returned_objects=[])

def page_accueil_v2(geo):
    """Page d'accueil festive avec compte √† rebours"""
    
    # Compte √† rebours jusqu'au 1er d√©cembre
    from datetime import datetime, timedelta
    target = datetime(2025, 12, 1, 8, 0, 0)
    now = datetime.now()
    diff = target - now
    
    if diff.days > 0:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #c41e3a, #165b33);
            padding: 2rem;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        ">
            <h2 style="color: #FFD700; margin: 0;">‚è∞ Compte √† rebours Guignol√©e</h2>
            <div style="font-size: 3rem; color: white; margin: 1rem 0;">
                {diff.days} jours {diff.seconds//3600} heures
            </div>
            <p style="color: rgba(255,255,255,0.9);">avant le grand jour!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #FFD700, #FFA500);
            padding: 2rem;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        ">
            <h2 style="color: #c41e3a; margin: 0;">üéâ C'EST AUJOURD'HUI!</h2>
            <div style="font-size: 2rem; color: #165b33; margin: 1rem 0;">
                Bonne Guignol√©e 2025!
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Hero section festif
    st.markdown("""
    <div style="
        text-align: center;
        padding: 3rem 1rem;
        background: linear-gradient(135deg, rgba(196,30,58,0.1), rgba(22,91,51,0.1));
        border-radius: 20px;
        margin-bottom: 2rem;
    ">
        <h1 style="font-size: 3rem; margin: 0;">üéÑ Bienvenue sur Guigno-Map üéÑ</h1>
        <p style="font-size: 1.3rem; color: #666; margin: 1rem 0;">
            Votre plateforme digitale pour la Guignol√©e 2025
        </p>
        <p style="color: #888;">
            G√©rez efficacement votre collecte de denr√©es avec une interface moderne
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats visuelles am√©lior√©es
    stats = db.extended_stats()
    progress = (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    st.markdown("### üìä √âtat de la collecte en temps r√©el")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 2rem;
            background: linear-gradient(135deg, #22c55e, #16a34a);
            border-radius: 15px;
            color: white;
            box-shadow: 0 4px 15px rgba(34,197,94,0.3);
        ">
            <div style="font-size: 3rem;">üèòÔ∏è</div>
            <div style="font-size: 2.5rem; font-weight: bold;">{stats['total']}</div>
            <div>Total Rues</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 2rem;
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            border-radius: 15px;
            color: white;
            box-shadow: 0 4px 15px rgba(59,130,246,0.3);
        ">
            <div style="font-size: 3rem;">‚úÖ</div>
            <div style="font-size: 2.5rem; font-weight: bold;">{stats['done']}</div>
            <div>Compl√©t√©es</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 2rem;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            border-radius: 15px;
            color: white;
            box-shadow: 0 4px 15px rgba(245,158,11,0.3);
        ">
            <div style="font-size: 3rem;">üö∂</div>
            <div style="font-size: 2.5rem; font-weight: bold;">{stats.get('partial', 0)}</div>
            <div>En Cours</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 2rem;
            background: linear-gradient(135deg, #c41e3a, #165b33);
            border-radius: 15px;
            color: white;
            box-shadow: 0 4px 15px rgba(196,30,58,0.3);
        ">
            <div style="font-size: 3rem;">üéØ</div>
            <div style="font-size: 2.5rem; font-weight: bold;">{progress:.0f}%</div>
            <div>Progression</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Barre de progression globale
    st.markdown("### üéÑ Progression globale de la collecte")
    st.progress(progress / 100)
    
    # Carte festive
    st.markdown("### üó∫Ô∏è Vue d'ensemble de Mascouche")
    df_all = db.list_streets()
    if not df_all.empty:  # Liste non vide
        m = create_map(df_all, geo)
        st_folium(m, height=750, width=None, returned_objects=[])
    
    # CSS pour r√©duire l'espace apr√®s la carte
    st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] > div:has(iframe) {
        margin-bottom: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Call to action
    st.markdown("""
    <div style="
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, rgba(255,215,0,0.1), rgba(255,215,0,0.05));
        border: 2px solid rgba(255,215,0,0.3);
        border-radius: 15px;
        margin-top: 1rem;
    ">
        <h3>üéÖ Pr√™t √† participer ?</h3>
        <p>Choisissez votre r√¥le dans le menu de gauche pour commencer</p>
        <p style="font-size: 0.9rem; color: #666;">
            B√©n√©voles : Acc√©dez √† vos rues assign√©es<br>
            Gestionnaires : Supervisez toute la collecte
        </p>
    </div>
    """, unsafe_allow_html=True)

def page_benevole(geo):
    """Interface b√©n√©vole moderne avec vue limit√©e"""
    
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        render_login_card("benevole")
        return
    
    team_id = st.session_state.auth["team_id"]
    
    # Header d'√©quipe personnalis√©
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #165b33, #c41e3a);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
    ">
        <h2 style="color: white; margin: 0;">üéÖ √âquipe {team_id}</h2>
        <p style="color: #FFD700; margin: 0.5rem 0 0 0;">Bonne collecte!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats de l'√©quipe
    df_team = db.list_streets(team=team_id)
    if df_team.empty:  # Liste vide
        st.warning("Aucune rue assign√©e. Contactez votre superviseur.")
        return
    
    done = len(df_team[df_team['status'] == 'terminee'])
    total = len(df_team)
    progress = (done / total * 100) if total > 0 else 0
    
    # Mini dashboard √©quipe
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("üìç Vos rues", total)
    with col2:
        st.metric("‚úÖ Compl√©t√©es", done)
    with col3:
        st.metric("üéØ Progression", f"{progress:.0f}%")
    
    # Syst√®me de badges
    show_team_badges(team_id)
    
    # Barre de progression
    st.progress(progress / 100)
    
    # Tabs modernis√©s
    tab1, tab2, tab3 = st.tabs(["üó∫Ô∏è Ma carte", "üìù Collecte", "üìä Historique"])
    
    with tab1:
        # CARTE LIMIT√âE AUX RUES DE L'√âQUIPE
        st.markdown("### Vos rues assign√©es")
        
        # Cr√©er une carte avec SEULEMENT les rues de l'√©quipe
        m = folium.Map(
            location=[45.7475, -73.6005],
            zoom_start=14,
            tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
            attr='¬© CARTO'
        )
        
        # Filtrer geo pour n'afficher QUE les rues de l'√©quipe
        team_streets = df_team['name'].tolist()
        
        for street_name in team_streets:
            if street_name in geo:
                status = df_team[df_team['name'] == street_name]['status'].iloc[0]
                
                # Couleurs selon statut
                colors = {
                    'terminee': '#22c55e',
                    'en_cours': '#f59e0b',
                    'a_faire': '#ef4444'
                }
                color = colors.get(status, '#ef4444')
                
                # Ajouter les segments de cette rue
                for path in geo[street_name]:
                    if path and len(path) >= 2:
                        folium.PolyLine(
                            path,
                            color=color,
                            weight=8,  # Plus √©pais pour mobile
                            opacity=0.9,
                            tooltip=f"{street_name} - {status.replace('_', ' ').title()}"
                        ).add_to(m)
        
        # Centrer sur les rues de l'√©quipe
        if team_streets and team_streets[0] in geo:
            first_street = geo[team_streets[0]][0]
            if first_street:
                m.location = first_street[0]
        
        st_folium(m, height=650, width=None, returned_objects=[])
    
    with tab2:
        st.markdown("### üìã Checklist de collecte")
        
        # Liste interactive des rues
        for _, row in df_team.iterrows():
            name = str(row.get('name', '')) if pd.notna(row.get('name', '')) else ''
            status = row.get('status', 'a_faire')
            status = status if pd.notna(status) else 'a_faire'
            notes = str(row.get('notes', '0')) if pd.notna(row.get('notes', '0')) else '0'
            
            # Carte de rue stylis√©e
            status_emoji = {'terminee': '‚úÖ', 'en_cours': 'üö∂', 'a_faire': '‚≠ï'}
            status_color = {'terminee': '#22c55e', 'en_cours': '#f59e0b', 'a_faire': '#ef4444'}
            
            with st.expander(f"{status_emoji.get(status, '‚≠ï')} **{name}** ({notes} notes)"):
                
                # Changement rapide de statut
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("‚≠ï √Ä faire", key=f"todo_{name}", width="stretch"):
                        db.set_status(name, 'a_faire')
                        st.rerun()
                with col2:
                    if st.button("üö∂ En cours", key=f"progress_{name}", width="stretch"):
                        db.set_status(name, 'en_cours')
                        st.rerun()
                with col3:
                    if st.button("‚úÖ Termin√©e", key=f"done_{name}", width="stretch"):
                        db.set_status(name, 'terminee')
                        st.rerun()
                
                st.markdown("---")
                
                # Ajout de note rapide
                st.markdown("**Ajouter une note:**")
                with st.form(f"note_{name}", clear_on_submit=True):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        num = st.text_input("N¬∞", placeholder="123")
                    with col2:
                        note = st.text_input("Note", placeholder="Personne absente")
                    
                    if st.form_submit_button("‚ûï Ajouter"):
                        if num and note:
                            db.add_note_for_address(name, team_id, num, note)
                            st.success("Note ajout√©e!")
                            st.rerun()
                
                # Notes existantes
                notes_list = db.get_street_addresses_with_notes(name)
                if notes_list:  # Liste non vide
                    st.markdown("**Notes existantes:**")
                    for n in notes_list:
                        st.markdown(f"‚Ä¢ **{n['address_number']}** : {n['comment']}")

                # ===== üìç Adresses de la rue (nouveau) =====
                with st.expander("üìç Adresses de la rue", expanded=False):
                    if st.button("Afficher les adresses", key=f"show_addr_{name}"):
                        try:
                            addrs = db.get_addresses_by_street(name)
                        except Exception:
                            addrs = []
                        if addrs:
                            import pandas as pd
                            df_addr = pd.DataFrame(addrs)
                            st.dataframe(df_addr.head(300), use_container_width=True)
                            # Ajout note rapide li√©e √† un num√©ro
                            colA, colB = st.columns([1,3])
                            with colA:
                                sel_num = st.selectbox(
                                    "Num√©ro",
                                    options=[a["house_number"] for a in addrs][:300],
                                    key=f"addr_sel_{name}",
                                )
                            with colB:
                                txt_note = st.text_input(
                                    "Note", key=f"addr_note_{name}", placeholder="Ex.: Absent / Don / Refus‚Ä¶"
                                )
                            if st.button("‚ûï Ajouter note", key=f"addr_add_{name}"):
                                ok = False
                                # team_id d√©j√† dispo dans la fonction (variable plus haut)
                                try:
                                    ok = bool(db.add_note_for_address(name, team_id, sel_num, txt_note))
                                except Exception:
                                    try:
                                        ok = bool(db.add_street_note(name, team_id, sel_num, txt_note))
                                    except Exception:
                                        ok = False
                                if ok:
                                    st.success(f"Note ajout√©e pour {name} #{sel_num}")
                                    st.rerun()
                                else:
                                    st.error("√âchec de l'ajout de note")
                        else:
                            st.info("Aucune adresse trouv√©e pour cette rue")
    
    with tab3:
        st.markdown("### üìä Votre historique")
        try:
            notes = db.get_team_notes(team_id)
            if notes:  # Liste non vide
                st.dataframe(to_dataframe(notes), use_container_width=True)
            else:
                st.info("Aucune note encore")
        except:
            st.info("Historique non disponible")

def page_benevole_v2(geo):
    """Interface b√©n√©vole moderne v4.1 avec vue 'Mes rues'"""
    
    # V√©rifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        # Afficher la page de connexion b√©n√©vole
        return page_benevole(geo)
    
    # Interface b√©n√©vole connect√© avec tabs
    st.header("üéÖ Espace B√©n√©vole")
    team_id = st.session_state.auth.get("team", "√âquipe inconnue")
    st.markdown(f"**√âquipe:** {team_id}")
    
    # Tabs pour b√©n√©voles
    tabs = st.tabs([
        "üèòÔ∏è Mes rues",
        "üó∫Ô∏è Carte de terrain", 
        "üìù Journal d'activit√©"
    ])
    
    with tabs[0]:
        # Nouvelle vue "Mes rues" v4.1
        page_benevole_mes_rues()
    
    with tabs[1]:
        # Carte traditionnelle (r√©utilise l'ancienne interface)
        page_benevole(geo)
    
    with tabs[2]:
        # Journal d'activit√© de l'√©quipe
        st.markdown("### üìù Journal d'activit√© de votre √©quipe")
        try:
            # Afficher les activit√©s r√©centes de l'√©quipe
            from src.database.operations import recent_activity
            activities = recent_activity(20)
            
            if activities:
                team_activities = [a for a in activities if a.get('team_id') == team_id]
                for activity in team_activities:
                    action = activity.get('action', '')
                    details = activity.get('details', '')
                    created_at = activity.get('created_at', '')
                    st.markdown(f"**{created_at}** - {action}: {details}")
            else:
                st.info("Aucune activit√© enregistr√©e pour votre √©quipe")
                
        except Exception as e:
            st.info("Journal d'activit√© temporairement indisponible")
            st.caption(f"Erreur: {e}")

def page_gestionnaire_v2(geo):
    """Interface gestionnaire moderne (ancien superviseur)"""
    st.header("üëî Tableau de Bord Gestionnaire")
    
    # V√©rifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "supervisor":
        render_login_card("gestionnaire")
        return
    
    # Dashboard moderne
    render_dashboard_gestionnaire(geo)
    
    # Tabs
    tabs = st.tabs([
        "üìä Vue d'ensemble",
        "üë• √âquipes",
        "üó∫Ô∏è Assignation",
        "üì• Export",
        "üõ† Tech"
    ])
    
    with tabs[0]:
        # Carte g√©n√©rale
        st.markdown("### Carte g√©n√©rale")
        df_all = db.list_streets()
        if not df_all.empty:  # Liste non vide
            m = create_map(df_all, geo)
            st_folium(m, height=800, width=None, returned_objects=[])
        
        # Activit√© r√©cente
        st.markdown("### Activit√© r√©cente")
        try:
            recent = db.recent_activity(limit=10)
            if recent:  # Liste non vide
                st.dataframe(to_dataframe(recent), use_container_width=True)
            else:
                st.info("Aucune activit√© r√©cente")
        except:
            st.info("Historique d'activit√© non disponible")
    
    with tabs[1]:
        # Gestion des √©quipes
        st.subheader("üë• Gestion des √©quipes", anchor=False)
        
        # === Formulaire de cr√©ation d'√©quipe (robuste) ===
        with st.expander("‚ûï Cr√©er une nouvelle √©quipe", expanded=False):
            with st.form("create_team_form", clear_on_submit=True):
                team_id_in = st.text_input(
                    "Identifiant d'√©quipe", 
                    key="new_team_id", 
                    placeholder="Ex: EQUIPE1",
                    help="Lettres et chiffres uniquement, max 20 caract√®res"
                )
                team_name_in = st.text_input(
                    "Nom d'√©quipe", 
                    key="new_team_name", 
                    placeholder="Ex: √âquipe Centre",
                    help="Nom descriptif de l'√©quipe"
                )
                
                # Toggle pour afficher/masquer les mots de passe
                show_pw = st.checkbox("Afficher les mots de passe", value=False)
                pw_type = "default" if show_pw else "password"
                
                pwd_in = st.text_input(
                    "Mot de passe", 
                    type=pw_type, 
                    key="new_team_pwd", 
                    placeholder="Minimum 4 caract√®res",
                    help="Tout caract√®re accept√©, min 4 / max 128"
                )
                pwd_conf = st.text_input(
                    "Confirmer le mot de passe", 
                    type=pw_type, 
                    key="new_team_pwd_conf", 
                    placeholder="Retapez le mot de passe",
                    help="Doit correspondre au mot de passe ci-dessus"
                )
                
                submitted = st.form_submit_button("‚úÖ Cr√©er l'√©quipe", width="stretch")

            if submitted:
                # Validation avec validators.py
                ok_id, team_id = validate_and_clean_input("team_id", team_id_in)
                ok_name, team_name = validate_and_clean_input("text", team_name_in)
                ok_pw, password = validate_and_clean_input("password", pwd_in)
                
                if not ok_id:
                    st.error("‚ùå Identifiant d'√©quipe invalide (lettres/chiffres, max 20)")
                elif not ok_name:
                    st.error("‚ùå Nom d'√©quipe invalide ou vide")
                elif not ok_pw:
                    st.error("‚ùå Mot de passe invalide (minimum 4 caract√®res)")
                elif pwd_in != pwd_conf:
                    st.error("‚ùå Les mots de passe ne correspondent pas")
                else:
                    # Tentative de cr√©ation avec db.create_team
                    try:
                        created = db.create_team(team_id, team_name, password)
                        if created:
                            st.toast(f"‚úÖ √âquipe {team_id} cr√©√©e avec succ√®s", icon="‚úÖ")
                            st.rerun()
                        else:
                            st.error("‚ùå √âchec de cr√©ation (ID d√©j√† existant ?)")
                    except Exception as e:
                        st.error(f"‚ùå Erreur lors de la cr√©ation: {e}")
        
        # === Liste des √©quipes (sans doublon de titre) ===
        try:
            teams_df = db.get_all_teams()
            if teams_df:  # Liste non vide
                st.dataframe(to_dataframe(teams_df), use_container_width=True)
            else:
                st.info("Aucune √©quipe cr√©√©e")
        except Exception as e:
            st.info("Liste des √©quipes non disponible")

        # === üîê Modifier / r√©initialiser le mot de passe ===
        with st.expander("üîê Modifier / r√©initialiser le mot de passe", expanded=False):
            # r√©cup√©rer les √©quipes
            try:
                teams = db.get_teams_list()
                options = [f"{t[1]} ({t[0]})" for t in teams] if teams else []
            except Exception:
                options = []
            
            with st.form("pwd_team_form", clear_on_submit=False):
                choice = st.selectbox("√âquipe", options=options, index=0 if options else None)
                show = st.checkbox("Afficher le mot de passe", value=False)
                ty = "default" if show else "password"
                new1 = st.text_input("Nouveau mot de passe", type=ty, key="pwd_new1")
                new2 = st.text_input("Confirmer", type=ty, key="pwd_new2")
                colU, colR = st.columns(2)
                do_update = colU.form_submit_button("‚úÖ Mettre √† jour", use_container_width=True)
                do_reset  = colR.form_submit_button("üé≤ R√©initialiser (al√©atoire)", use_container_width=True)
            
            # traitement
            team_id = ""
            if choice:
                team_id = choice.split("(")[-1].rstrip(")")
            
            if do_update:
                if not team_id:
                    st.error("Aucune √©quipe s√©lectionn√©e")
                elif len(new1) < 4:
                    st.error("Mot de passe trop court (min 4 caract√®res)")
                elif new1 != new2:
                    st.error("La confirmation ne correspond pas")
                else:
                    try:
                        ok = db.update_team_password(team_id, new1)
                        if ok:
                            st.success(f"Mot de passe mis √† jour pour {team_id}")
                            st.rerun()
                        else:
                            st.error("√âchec de la mise √† jour")
                    except Exception as e:
                        st.error(f"Erreur: {e}")
            
            if do_reset:
                if not team_id:
                    st.error("Aucune √©quipe s√©lectionn√©e")
                else:
                    try:
                        newpwd = db.reset_team_password(team_id)
                        if newpwd:
                            st.success(f"Nouveau mot de passe g√©n√©r√© pour {team_id}")
                            st.code(newpwd)  # √† copier maintenant; ne sera plus affich√© ensuite
                        else:
                            st.error("√âchec de la r√©initialisation")
                    except Exception as e:
                        st.error(f"Erreur: {e}")
    
    with tabs[2]:
        # Assignation v4.1
        page_assignations_v41()
    
    with tabs[3]:
        # Export am√©lior√© v4.1
        page_export_gestionnaire_v41()

    with tabs[4]:
        st.markdown("### üõ† Op√©rations techniques (prot√©g√©es)")

        # -- PIN stock√© dans secrets (config.toml -> [secrets] TECH_PIN="xxxx")
        try:
            TECH_PIN = st.secrets.get("TECH_PIN", "")
        except:
            TECH_PIN = ""  # Pas de fichier secrets.toml

        if "tech_ok" not in st.session_state:
            st.session_state.tech_ok = False

        if not st.session_state.tech_ok:
            pin = st.text_input("Entrer le PIN technique", type="password")
            if st.button("D√©verrouiller"):
                if TECH_PIN and pin == TECH_PIN:
                    st.session_state.tech_ok = True
                    st.success("Acc√®s technique d√©verrouill√©.")
                    st.rerun()
                else:
                    st.error("PIN invalide.")
            st.stop()

        st.info("‚ö†Ô∏è Ces actions sont lourdes et n'affectent pas les statuts/notes. Elles r√©g√©n√®rent les caches OSM.")

        # --- Reconstruire le cache g√©om√©trique (lourd)
        with st.expander("üîÑ Reconstruire cache OSM (g√©om√©tries)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirm = st.checkbox("Je comprends les implications")
            with col2:
                safety = st.text_input('√âcrire "REBUILD" pour confirmer')

            if st.button("Lancer la reconstruction"):
                if confirm and safety.strip().upper() == "REBUILD":
                    with st.spinner("Construction du cache‚Ä¶"):
                        build_geometry_cache()       # reconstruit le fichier osm_cache.json
                        st.cache_data.clear()        # purge cache Streamlit
                    st.success("‚úÖ Cache OSM mis √† jour (g√©om√©tries).")
                    st.rerun()
                else:
                    st.warning("Confirmation incompl√®te.")

        # --- Reconstruire/Importer le cache des adresses
        with st.expander("üìç Mettre √† jour les adresses (OSM)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirmA = st.checkbox("Je confirme")
            with col2:
                safetyA = st.text_input('√âcrire "IMPORT" pour confirmer')

            if st.button("Lancer la mise √† jour des adresses"):
                if confirmA and safetyA.strip().upper() == "IMPORT":
                    with st.spinner("T√©l√©chargement des adresses OSM‚Ä¶"):
                        build_addresses_cache()
                        addr_cache = load_addresses_cache()
                        count = db.import_addresses_from_cache(addr_cache)
                    st.success(f"‚úÖ {count} adresses import√©es depuis OSM.")
                    st.rerun()
                else:
                    st.warning("Confirmation incompl√®te.")

        # --- Gestion des backups
        with st.expander("üíæ Gestion des backups", expanded=False):
            backup_mgr = db.get_backup_manager()  # Sans DB_PATH, utilise config SQLAlchemy
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("üîÑ Cr√©er un backup manuel", width="stretch"):
                    backup_file = backup_mgr.create_backup("manual")
                    if backup_file:
                        st.success(f"Backup cr√©√© : {Path(backup_file).name}")
            
            with col2:
                if st.button("üìã Voir les backups", width="stretch"):
                    backups = backup_mgr.list_backups()
                    if backups:
                        for backup in backups[:5]:  # Montrer les 5 derniers
                            st.text(f"‚Ä¢ {backup['name']} ({backup['size']})")
                    else:
                        st.info("Aucun backup disponible")

def page_superviseur(conn, geo):
    """Interface superviseur"""
    st.header("üéØ Tableau de Bord Superviseur")
    
    # V√©rifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "supervisor":
        render_login_card("superviseur")
        return
    
    # Dashboard moderne
    render_dashboard_gestionnaire(geo)
    
    # Tabs
    tabs = st.tabs([
        "üìä Vue d'ensemble",
        "üë• √âquipes",
        "üó∫Ô∏è Assignation",
        "üì• Export",
        "üõ† Tech"
    ])
    
    with tabs[0]:
        # Carte g√©n√©rale
        st.markdown("### Carte g√©n√©rale")
        df_all = db.list_streets()
        if not df_all.empty:  # Liste non vide
            m = create_map(df_all, geo)
            st_folium(m, height=800, width=None, returned_objects=[])
        
        # Activit√© r√©cente
        st.markdown("### Activit√© r√©cente")
        recent = db.recent_activity(limit=10)
        if recent:  # Liste non vide
            st.dataframe(to_dataframe(recent), use_container_width=True)
    
    with tabs[1]:
        # Gestion des √©quipes
        st.markdown("### Gestion des √©quipes")
        
        with st.expander("Cr√©er une √©quipe"):
            with st.form("new_team", clear_on_submit=True):
                new_id = st.text_input("Identifiant")
                new_name = st.text_input("√âquipe")
                new_pass = st.text_input("Mot de passe", type="password")
                
                if st.form_submit_button("Cr√©er"):
                    if all([new_id, new_name, new_pass]):
                        if db.create_team(new_id, new_name, new_pass):
                            st.success(f"√âquipe {new_id} cr√©√©e")
                            st.rerun()
        
        # Liste des √©quipes
        teams_df = db.get_all_teams()
        if teams_df:  # Liste non vide
            st.dataframe(to_dataframe(teams_df), use_container_width=True)
    
    with tabs[2]:
        # Assignation
        st.markdown("### Assignation des rues")
        
        unassigned = db.get_unassigned_streets()
        
        if unassigned:  # Liste non vide
            with st.form("assign"):
                team = st.selectbox("√âquipe", db.teams())
                streets = st.multiselect("Rues", unassigned)
                
                if st.form_submit_button("Assigner"):
                    if team and streets:
                        db.assign_streets_to_team(streets, team)
                        st.success("Rues assign√©es!")
                        st.rerun()
        else:
            st.success("Toutes les rues sont assign√©es!")
        
        # Tableau des assignations
        df_all = db.list_streets()
        if not df_all.empty:  # Liste non vide
            st.dataframe(
                df_all[['name', 'sector', 'team', 'status']],
                use_container_width=True
            )
    
    with tabs[3]:
        # Export
        st.markdown("### Export des donn√©es")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                "üì• Export rues (CSV)",
                db.export_to_csv(),
                "rapport_rues.csv",
                "text/csv",
                width="stretch"
            )
        
        with col2:
            st.download_button(
                "üì• Export notes (CSV)",
                db.export_notes_csv(),
                "rapport_notes.csv",
                "text/csv",
                width="stretch"
            )

    with tabs[4]:
        st.markdown("### üõ† Op√©rations techniques (prot√©g√©es)")

        # -- PIN stock√© dans secrets (config.toml -> [secrets] TECH_PIN="xxxx")  
        try:
            TECH_PIN = st.secrets.get("TECH_PIN", "")
        except:
            TECH_PIN = ""  # Pas de fichier secrets.toml

        if "tech_ok" not in st.session_state:
            st.session_state.tech_ok = False

        if not st.session_state.tech_ok:
            pin = st.text_input("Entrer le PIN technique", type="password")
            if st.button("D√©verrouiller"):
                if TECH_PIN and pin == TECH_PIN:
                    st.session_state.tech_ok = True
                    st.success("Acc√®s technique d√©verrouill√©.")
                    st.rerun()
                else:
                    st.error("PIN invalide.")
            st.stop()

        st.info("‚ö†Ô∏è Ces actions sont lourdes et n'affectent pas les statuts/notes. Elles r√©g√©n√®rent les caches OSM.")

        # --- Reconstruire le cache g√©om√©trique (lourd)
        with st.expander("üîÑ Reconstruire cache OSM (g√©om√©tries)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirm = st.checkbox("Je comprends les implications")
            with col2:
                safety = st.text_input('√âcrire "REBUILD" pour confirmer')

            if st.button("Lancer la reconstruction"):
                if confirm and safety.strip().upper() == "REBUILD":
                    with st.spinner("Construction du cache‚Ä¶"):
                        build_geometry_cache()       # reconstruit le fichier osm_cache.json
                        st.cache_data.clear()        # purge cache Streamlit
                    st.success("‚úÖ Cache OSM mis √† jour (g√©om√©tries).")
                    st.rerun()
                else:
                    st.warning("Confirmation incompl√®te.")

        # --- Reconstruire/Importer le cache des adresses
        with st.expander("üìç Mettre √† jour les adresses (OSM)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirmA = st.checkbox("Je confirme")
            with col2:
                safetyA = st.text_input('√âcrire "IMPORT" pour confirmer')

            if st.button("Lancer la mise √† jour des adresses"):
                if confirmA and safetyA.strip().upper() == "IMPORT":
                    with st.spinner("T√©l√©chargement des adresses OSM‚Ä¶"):
                        build_addresses_cache()
                        addr_cache = load_addresses_cache()
                        count = db.import_addresses_from_cache(addr_cache)
                    st.success(f"‚úÖ {count} adresses import√©es depuis OSM.")
                    st.rerun()
                else:
                    st.warning("Confirmation incompl√®te.")

# ============================================
# MAIN
# ============================================

# ================================================================================
# NOUVELLES FONCTIONS v4.1 - SUPERVISEUR ET B√âN√âVOLE
# ================================================================================

def page_assignations_v41():
    """Assignations : au choix par secteur (bulk) OU par rue (manuel)."""
    import pandas as pd
    st.subheader("üó∫Ô∏è Assignations", anchor=False)

    tabs = st.tabs(["üéØ Par secteur (rapide)", "üß≠ Par rue (manuel)"])

    # ========== TAB 1 : BULK PAR SECTEUR (inchang√©) ==========
    with tabs[0]:
        try:
            unassigned_count = db.get_unassigned_streets_count()
        except Exception:
            # fallback si la fonction n'existe pas
            _df = db.list_streets()
            unassigned_count = int((_df["team"].isna() | (_df["team"] == "")).sum()) if not _df.empty else 0

        if unassigned_count > 0:
            st.info(f"‚ö†Ô∏è {unassigned_count} rue(s) non assign√©e(s)")

        with st.container():
            c1, c2, c3 = st.columns([1, 1.2, 0.7], vertical_alignment="bottom")

            with c1:
                try:
                    liste_secteurs = db.get_sectors_list()
                except Exception:
                    liste_secteurs = []
                secteur = st.selectbox(
                    "SECTEUR √Ä ASSIGNER",
                    options=[""] + (liste_secteurs or []),
                    index=0,
                    key="assign_sector_v41",
                )

            with c2:
                try:
                    teams = db.get_teams_list()  # [(id, name), ...]
                except Exception:
                    teams = [(t, t) for t in (db.teams() or [])]
                team_display = st.selectbox(
                    "√âQUIPE",
                    options=[""] + [f"{name} ({tid})" for (tid, name) in teams],
                    index=0,
                    key="assign_team_v41",
                )
                team = ""
                if team_display and team_display != "":
                    team = team_display.split("(")[-1].rstrip(")")

            with c3:
                if st.button("Assigner tout le secteur", use_container_width=True, disabled=not (secteur and team)):
                    try:
                        nb = db.bulk_assign_sector(secteur, team)
                        if nb > 0:
                            st.toast(f"‚úÖ {nb} rue(s) assign√©e(s) √† {team}", icon="‚úÖ")
                            st.rerun()
                        else:
                            st.toast("‚ÑπÔ∏è Aucune rue non assign√©e dans ce secteur", icon="‚ÑπÔ∏è")
                    except Exception as e:
                        st.error(f"Erreur lors de l'assignation: {e}")

        st.markdown("### üìã √âtat des assignations")
        try:
            df = db.list_streets()
            if not df.empty:
                df_disp = df.assign(
                    Statut=df["status"].map(STATUS_TO_LABEL).fillna("√Ä faire")
                ).rename(columns={"name": "Rue", "sector": "Secteur", "team": "√âquipe"})[
                    ["Rue", "Secteur", "√âquipe", "Statut"]
                ]
                st.dataframe(df_disp, use_container_width=True)
            else:
                st.info("Aucune rue trouv√©e")
        except Exception as e:
            st.error(f"Erreur d'affichage: {e}")

    # ========== TAB 2 : ASSIGNATION MANUELLE PAR RUE ==========
    with tabs[1]:
        # √âquipe cible
        try:
            teams = db.get_teams_list()
        except Exception:
            teams = [(t, t) for t in (db.teams() or [])]
        team_display = st.selectbox(
            "√âQUIPE CIBLE",
            options=[f"{name} ({tid})" for (tid, name) in teams] if teams else [],
            index=0 if teams else None,
            key="team_for_streets",
        )
        team_id = team_display.split("(")[-1].rstrip(")") if team_display else None

        # Source de rues (non assign√©es ou toutes)
        src = st.radio("Source", ["Rues non assign√©es", "Toutes les rues"], horizontal=True)

        # Donn√©es rues
        df = db.list_streets()
        if df.empty:
            st.info("Aucune rue dans la base.")
            return

        # Filtres
        q = st.text_input("üîé Filtrer par nom (contient)‚Ä¶", "")
        sectors = sorted([s for s in df["sector"].dropna().unique().tolist() if str(s).strip()])
        sector_filter = st.selectbox("Secteur (optionnel)", options=["(Tous)"] + sectors, index=0)

        # Filtrage selon la source
        if src.startswith("Rues non"):
            mask_unassigned = df["team"].isna() | (df["team"].astype(str).str.strip() == "")
            work = df[mask_unassigned].copy()
        else:
            work = df.copy()

        # Appliquer filtres texte/secteur
        if q:
            work = work[work["name"].astype(str).str.contains(q, case=False, na=False)]
        if sector_filter != "(Tous)":
            work = work[work["sector"] == sector_filter]

        options = sorted(work["name"].dropna().unique().tolist())
        selected = st.multiselect("Rues √† assigner", options=options, default=[])

        st.caption(f"{len(options)} rue(s) list√©e(s) ‚Ä¢ {len(selected)} s√©lectionn√©e(s)")
        do_overwrite = st.checkbox("R√©assigner m√™me si d√©j√† affect√©e (√©crase l'√©quipe actuelle)", value=True)

        colA, colB = st.columns([1, 1])
        with colA:
            if st.button("‚úÖ Assigner les rues s√©lectionn√©es", use_container_width=True,
                         disabled=not (team_id and selected)):
                try:
                    if team_id:  # V√©rification suppl√©mentaire
                        db.assign_streets_to_team(selected, team_id)
                        st.success(f"{len(selected)} rue(s) assign√©e(s) √† {team_id}")
                        st.rerun()
                except Exception as e:
                    st.error(f"Assignation √©chou√©e: {e}")

        with colB:
            # Affichage d'aper√ßu des rues choisies
            if selected:
                st.write("Aper√ßu :")
                st.dataframe(
                    work[work["name"].isin(selected)][["name", "sector", "team", "status"]]
                    .rename(columns={"name": "Rue", "sector": "Secteur", "team": "√âquipe", "status": "Statut"}),
                    use_container_width=True
                )

def page_export_gestionnaire_v41():
    """Page d'export v4.1 avec nouvelles fonctionnalit√©s"""
    st.markdown("### üì• Export des donn√©es")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV standard
        try:
            st.download_button(
                "üì• Export CSV Standard",
                db.export_to_csv(),
                "rapport_rues.csv",
                "text/csv",
                width="stretch"
            )
        except Exception as e:
            st.button("üì• CSV (Erreur)", disabled=True, width="stretch")
            st.caption(f"Erreur: {e}")
    
    with col2:
        # Export Excel professionnel
        try:
            from reports import ReportGenerator
            generator = ReportGenerator()
            excel_data = generator.generate_excel()
            st.download_button(
                "üìä Export Excel Pro",
                excel_data,
                "guignolee_2025_rapport.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )
        except ImportError:
            st.button("üìä Excel (Installer xlsxwriter)", disabled=True, width="stretch")
        except Exception as e:
            st.button("üìä Excel (Erreur)", disabled=True, width="stretch")
            st.caption(f"Erreur: {e}")
    
    with col3:
        # Export PDF professionnel
        try:
            from reports import ReportGenerator
            generator = ReportGenerator()
            pdf_data = generator.generate_pdf()
            st.download_button(
                "üìÑ Export PDF Pro",
                pdf_data,
                "guignolee_2025_rapport.pdf",
                "application/pdf",
                width="stretch"
            )
        except ImportError:
            st.button("üìÑ PDF (Installer reportlab)", disabled=True, width="stretch")
        except Exception as e:
            st.button("üìÑ PDF (Erreur)", disabled=True, width="stretch")
            st.caption(f"Erreur: {e}")
    
    # Export CSV assignations (nouveau v4.1)
    st.markdown("---")
    st.markdown("### üìã Export sp√©cialis√©s v4.1")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV assignations
        try:
            assignations_data = db.get_assignations_export_data()
            if assignations_data:  # Liste non vide
                csv_data = pd.DataFrame(assignations_data).to_csv(index=False, encoding='utf-8')
                st.download_button(
                    "üìã Export CSV Assignations",
                    csv_data,
                    "assignations_secteurs.csv",
                    "text/csv",
                    width="stretch",
                    help="Colonnes: secteur, rue, √©quipe, statut"
                )
            else:
                st.button("üìã Assignations (Aucune donn√©e)", disabled=True, width="stretch")
        except Exception as e:
            st.button("üìã Assignations (Erreur)", disabled=True, width="stretch")
            st.caption(f"Erreur: {e}")
    
    with col2:
        # Export notes
        try:
            st.download_button(
                "üìù Export Notes",
                db.export_notes_csv(),
                "rapport_notes.csv",
                "text/csv",
                width="stretch"
            )
        except Exception as e:
            st.button("üìù Notes (Erreur)", disabled=True, width="stretch")
            st.caption(f"Erreur: {e}")
    
    # --- CSV d'assignation (export/import) ---
    st.markdown("---")
    st.markdown("### üìÑ CSV d'assignation des rues")
    with st.expander("Exporter / Importer", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("üì§ Exporter le template (CSV)", use_container_width=True):
                try:
                    df = db.export_streets_template(include_assignments=False)
                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="üì• T√©l√©charger streets_template.csv",
                        data=csv_data,
                        file_name="streets_template.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erreur lors de l'export: {e}")
        with c2:
            up = st.file_uploader("üì• Importer votre CSV modifi√©", type=["csv"], key="csv_upload")
            if up is not None:
                try:
                    from io import BytesIO
                    # Convertir en BytesIO si n√©cessaire
                    if hasattr(up, 'read'):
                        file_content = up.read()
                        if isinstance(file_content, str):
                            file_like = BytesIO(file_content.encode('utf-8'))
                        else:
                            file_like = BytesIO(file_content)
                    else:
                        file_like = up
                    
                    res = db.upsert_streets_from_csv(file_like)
                    st.success(f"‚úÖ Import termin√© ‚Äî inserted={res.get('inserted',0)}, updated={res.get('updated',0)}, skipped={res.get('skipped',0)}, errors={res.get('errors',0)}")
                    if res.get('inserted', 0) > 0 or res.get('updated', 0) > 0:
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'import: {e}")

def page_benevole_mes_rues():
    """Vue 'Mes rues' pour b√©n√©voles v4.1"""
    
    # R√©cup√©rer l'√©quipe du b√©n√©vole connect√©
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        st.warning("Acc√®s r√©serv√© aux b√©n√©voles connect√©s")
        return
    
    team_id = st.session_state.auth.get("team")
    if not team_id:
        st.error("√âquipe non identifi√©e")
        return
    
    st.markdown(f"### üèòÔ∏è Mes rues assign√©es - √âquipe {team_id}")
    
    try:
        # R√©cup√©rer les rues de l'√©quipe
        team_streets = db.get_team_streets(team_id)
        
        if not team_streets:  # Liste vide
            st.info("Aucune rue assign√©e √† votre √©quipe pour le moment.")
            return
        
        # Afficher les statistiques de l'√©quipe
        total_streets = len(team_streets)
        done_streets = len([s for s in team_streets if s.get('status') == 'terminee'])
        in_progress = len([s for s in team_streets if s.get('status') == 'en_cours'])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total rues", total_streets)
        with col2:
            st.metric("Termin√©es", done_streets)
        with col3:
            st.metric("En cours", in_progress)
        with col4:
            progress = (done_streets / total_streets * 100) if total_streets > 0 else 0
            st.metric("Progression", f"{progress:.1f}%")
        
        st.markdown("---")
        
        # Affichage par rue avec actions
        for street in team_streets:
            if isinstance(street, str):
                street_name = street
            else:
                street_name = street.get("name", street)
            street_name = street['street_name']
            current_status = street['status']
            notes_count = street['notes_count']
            
            with st.expander(f"üèòÔ∏è {street_name} ({street['sector']}) - {current_status.replace('_', ' ').title()}", 
                           expanded=current_status == 'en_cours'):
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**Secteur:** {street['sector']}")
                    st.markdown(f"**Statut actuel:** {current_status.replace('_', ' ').title()}")
                    if notes_count > 0:
                        st.markdown(f"**Notes existantes:** {notes_count}")
                
                with col2:
                    # Bouton "En cours"
                    if st.button(
                        "üöÄ En cours", 
                        key=f"progress_{street_name}",
                        disabled=current_status == 'en_cours',
                        width="stretch"
                    ):
                        if db.update_street_status(street_name, 'en_cours', team_id):
                            st.toast(f"‚úÖ {street_name} marqu√©e en cours", icon="üöÄ")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la mise √† jour")
                
                with col3:
                    # Bouton "Termin√©e"
                    if st.button(
                        "‚úÖ Termin√©e", 
                        key=f"done_{street_name}",
                        disabled=current_status == 'terminee',
                        width="stretch"
                    ):
                        if db.update_street_status(street_name, 'terminee', team_id):
                            st.toast(f"üéâ {street_name} termin√©e!", icon="üéâ")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la mise √† jour")
                
                # Section notes
                st.markdown("**Gestion des notes:**")
                
                # Afficher les notes existantes
                existing_notes = db.get_street_notes_for_team(street_name, team_id)
                if existing_notes:
                    st.markdown("*Notes existantes:*")
                    for note in existing_notes:
                        st.markdown(f"‚Ä¢ **#{list(note.values())[0] if isinstance(note, dict) else note[0]}** : {list(note.values())[1] if isinstance(note, dict) else note[1]} _{list(note.values())[2] if isinstance(note, dict) else note[2]}_")
                
                # Ajouter une nouvelle note
                with st.form(f"note_form_{street_name}"):
                    col_addr, col_note = st.columns([1, 3])
                    with col_addr:
                        address_number = st.text_input(
                            "N¬∞ civique", 
                            key=f"addr_{street_name}",
                            placeholder="123A"
                        )
                    with col_note:
                        comment = st.text_area(
                            "Commentaire", 
                            key=f"comment_{street_name}",
                            placeholder="Ex: Absent, refus, don re√ßu...",
                            max_chars=500,
                            height=80
                        )
                    
                    if st.form_submit_button("üíæ Enregistrer note"):
                        if address_number and comment:
                            if db.add_street_note(street_name, team_id, address_number, comment):
                                st.toast(f"üìù Note ajout√©e pour {street_name} #{address_number}", icon="üìù")
                                st.rerun()
                            else:
                                st.error("Erreur lors de l'enregistrement de la note")
                        else:
                            st.warning("Veuillez remplir le num√©ro et le commentaire")
                            
    except Exception as e:
        st.error(f"Erreur lors du chargement de vos rues: {e}")
        st.info("Fonctionnalit√© temporairement indisponible")

def main():
    """Point d'entr√©e principal - Version 2.0 Guignol√©e"""
    
    # CSS moderne
    inject_css()
    
    # Connexion DB
    # Initialisation de la base de donn√©es
    db.init_db()
    
    # Compatibilit√© legacy supprim√©e - utilise SQLAlchemy via src.database
    # Connexion centralis√©e via get_session() au lieu de sqlite3 direct
    
    # Cache g√©om√©trique
    @st.cache_data(ttl=None)
    def get_geo(_sig):
        data = load_geometry_cache()
        return data if data else {}
    
    sig = int(CACHE_FILE.stat().st_mtime_ns) if CACHE_FILE.exists() else 0
    geo = get_geo(sig)
    
    # Header festif
    render_header()
    
    # Navigation modernis√©e dans la sidebar
    with st.sidebar:
        # CSS pour la sidebar sans position absolue
        st.markdown("""
        <style>
        .css-1d391kg { padding-top: 1rem !important; }
        .stSidebar > div:first-child { padding-top: 1rem !important; }
        </style>
        """, unsafe_allow_html=True)
        
        # Logo en haut de la sidebar (position normale)
        logo_path = ASSETS / "logo.png"
        if logo_path.exists():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(str(logo_path), width=150)
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        else:
            # Placeholder centr√©
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #c41e3a, #165b33);
                border-radius: 15px;
                padding: 2rem;
                color: white;
                text-align: center;
                margin: 1rem 0;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            ">
                <div style="font-size: 2.5rem;">üéÅ</div>
                <div style="font-weight: bold; font-size: 1.2rem;">LOGO</div>
                <small>Espace r√©serv√©</small>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        # Navigation
        st.markdown("### üéÑ Navigation")
        
        # Boutons de navigation stylis√©s
        if st.button("üè† Accueil", width="stretch"):
            st.session_state.page = "accueil"
            st.rerun()
        
        if st.button("üéÖ B√©n√©vole", width="stretch"):
            st.session_state.page = "benevole"
            st.rerun()
            
        if st.button("üëî Gestionnaire", width="stretch"):
            st.session_state.page = "gestionnaire"  
            st.rerun()
        
        # D√©connexion si connect√©
        if st.session_state.auth:
            st.markdown("---")
            if st.button("üö™ D√©connexion", width="stretch"):
                st.session_state.auth = None
                st.rerun()
        
        # Compteur temps r√©el
        st.markdown("---")
        stats = db.extended_stats()
        st.markdown(f"""
        <div style="text-align: center;">
            <h4>√âtat de la collecte</h4>
            <div style="font-size: 2rem; color: #FFD700;">
                {stats['done']}/{stats['total']}
            </div>
            <small>Rues compl√©t√©es</small>
        </div>
        """, unsafe_allow_html=True)
    
    # Routing pages
    page = st.session_state.get('page', 'accueil')
    
    if page == "accueil":
        page_accueil_v2(geo)
    elif page == "benevole":
        page_benevole_v2(geo)
    elif page == "gestionnaire":
        page_gestionnaire_v2(geo)
    
    # Footer festif
    st.markdown("""
    <div style="
        text-align: center;
        padding: 2rem;
        margin-top: 3rem;
        border-top: 2px solid rgba(255,215,0,0.3);
        color: #8b92a4;
    ">
        <p>
            üéÑ Guignol√©e 2025 - Le Relais de Mascouche üéÑ<br>
            <small>Ensemble, redonnons espoir | üìû 450-474-4133</small>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Banni√®re en bas de page
    if (ASSETS / "banner.png").exists():
        st.image(str(ASSETS / "banner.png"))

if __name__ == "__main__":
    main()
