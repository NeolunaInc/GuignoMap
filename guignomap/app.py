"""
Guigno-Map - Application de gestion de collecte de denrées
Le Relais de Mascouche
Version 3.0 - Production
"""

# pyright: reportCallIssue=false

import os, sys
os.environ.setdefault("PYTHONUTF8", "1")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pathlib import Path
import time
from datetime import datetime
import pandas as pd
import streamlit as st

# Ajout du répertoire parent au path pour importer src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Monkey-patch supprimé - utilisation de composants Streamlit natifs

# Configuration Streamlit (doit être la première commande Streamlit)
st.set_page_config(
    page_title="Guigno-Map | Relais de Mascouche",
    page_icon="🎁",
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

# --- Utilitaire de compatibilité pandas Styler ---
from typing import Callable, Any

def style_map_compat(df: pd.DataFrame, fn: Callable[[Any], str], subset: Any = None):
    """Applique un style cellule-à-cellule en utilisant Styler.map si disponible,
    sinon fallback dynamique vers applymap sans exposer l'attribut (OK pour Pylance).
    
    Args:
        df: DataFrame à styliser
        fn: Fonction qui prend une valeur cellule et retourne une string CSS
        subset: Colonnes à cibler (ex: ['status'] ou None pour toutes)
    """
    styler = df.style
    if hasattr(styler, "map"):
        # Pandas 2.4+ : utilise la nouvelle API map()
        return styler.map(fn, subset=subset)
    # Pandas < 2.4 : fallback vers applymap (sans référence statique)
    return getattr(styler, "applymap")(fn, subset=subset)

# --- Mapping des statuts pour l'affichage ---
STATUS_TO_LABEL = {"a_faire": "À faire", "en_cours": "En cours", "terminee": "Terminée"}
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
    """Header moderne avec logo Guignolée et design festif"""
    
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
        <!-- Flocons de neige animés en CSS -->
        <div style="position: absolute; width: 100%; height: 100%; opacity: 0.1;">
            <span style="position: absolute; top: 10%; left: 10%; font-size: 2rem;">❄️</span>
            <span style="position: absolute; top: 20%; left: 80%; font-size: 1.5rem;">❄️</span>
            <span style="position: absolute; top: 60%; left: 30%; font-size: 1.8rem;">❄️</span>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 5, 2])
    
    with col1:
        # Logo Guignolée
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
            ">🎅 GUIGNOLÉE 2025 🎁</h1>
            <p style="
                color: #FFD700;
                font-size: 1.2rem;
                margin: 0.5rem 0 0 0;
                font-weight: 600;
            ">Le Relais de Mascouche - 1er décembre</p>
            <p style="
                color: rgba(255,255,255,0.9);
                font-size: 1rem;
                margin-top: 0.5rem;
            ">Système de gestion de collecte</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Stats en temps réel
        stats = db.extended_stats()
        # Normalisation anti-KeyError (valeurs par défaut)
        stats = stats or {}
        total = int(stats.get('total') or stats.get('count') or 0)
        done = int(stats.get('done') or stats.get('completed') or 0)
        # Réinjecte pour la suite de l'UI si d'autres blocs lisent ces clés
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
                Complété
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_login_card(role="benevole"):
    """Carte de connexion moderne avec design festif"""
    
    # Container de connexion stylisé
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
    
    # Icône et titre
    if role == "superviseur" or role == "gestionnaire":
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 3rem;">👤</div>
            <h2 style="color: #FFD700; margin: 1rem 0;">Espace Gestionnaire</h2>
            <p style="color: #cbd5e1;">Gérez la collecte et les équipes</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_gestionnaire", clear_on_submit=False):
            password = st.text_input(
                "🔑 Mot de passe",
                type="password",
                placeholder="Entrez le mot de passe gestionnaire"
            )
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                submit = st.form_submit_button(
                    "🔓 Connexion",
                    
                )
            
            if submit:
                if db.verify_team("ADMIN", password):
                    st.session_state.auth = {"role": "supervisor", "team_id": "ADMIN"}
                    st.success("✅ Bienvenue dans l'espace gestionnaire!")
                    st.snow()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Mot de passe incorrect")
    
    else:  # Bénévole
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 3rem;">🎄</div>
            <h2 style="color: #FFD700; margin: 1rem 0;">Espace Bénévole</h2>
            <p style="color: #cbd5e1;">Accédez à vos rues assignées</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_benevole", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                team_id = st.text_input(
                    "👥 Identifiant d'équipe",
                    placeholder="Ex: EQ001"
                )
            
            with col2:
                password = st.text_input(
                    "🔑 Mot de passe",
                    type="password",
                    placeholder="Mot de passe équipe"
                )
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                submit = st.form_submit_button(
                    "🎄 Connexion"
                )
            
            if submit:
                if db.verify_team(team_id, password):
                    st.session_state.auth = {"role": "volunteer", "team_id": team_id}
                    st.success(f"✅ Bienvenue équipe {team_id}!")
                    st.snow()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Identifiants incorrects")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Aide en bas
    st.markdown("""
    <div style="text-align: center; margin-top: 2rem; color: #8b92a4;">
        <small>
        Besoin d'aide? Contactez votre gestionnaire<br>
        📞 450-474-4133
        </small>
    </div>
    """, unsafe_allow_html=True)

def render_metrics(stats):
    """Affiche les métriques principales"""
    progress = (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Rues", stats['total'])
    
    with col2:
        st.metric("Rues Terminées", stats['done'])
    
    with col3:
        st.metric("En Cours", stats.get('partial', 0))
    
    with col4:
        st.metric("Progression", f"{progress:.1f}%")

def render_dashboard_gestionnaire(geo):
    """Dashboard moderne pour gestionnaires avec KPIs visuels"""
    
    # KPIs principaux en cartes colorées
    stats = db.extended_stats()
    progress = (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    st.markdown("### 📊 Tableau de bord en temps réel")
    
    # Ligne de KPIs avec icônes festives
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
            <div style="font-size: 2.5rem;">🏘️</div>
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
            <div style="font-size: 2.5rem;">✅</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{stats['done']}</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">Terminées</div>
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
            <div style="font-size: 2.5rem;">⏳</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{stats.get('partial', 0)}</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">En cours</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Nombre d'équipes actives
        teams_count = len(db.teams())
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(139,92,246,0.3);
        ">
            <div style="font-size: 2.5rem;">👥</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{teams_count}</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">Équipes</div>
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
            <div style="font-size: 2.5rem;">🎯</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{progress:.0f}%</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">Progression</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Barre de progression visuelle
    st.markdown("### 🎄 Progression globale")
    st.progress(progress / 100)
    
    # Graphique par secteur (si disponible)
    st.markdown("### 📈 Performance par équipe")
    try:
        teams_stats = db.stats_by_team()
        if teams_stats:  # Liste non vide
            # Convertir en DataFrame pour plotly
            import pandas as pd
            teams_df = pd.DataFrame(teams_stats)
            
            # Calculer le pourcentage de progression
            teams_df['progress'] = ((teams_df['completed'] / teams_df['total_streets']) * 100).fillna(0)
            
            # Graphique en barres colorées
            import plotly.express as px
            fig = px.bar(
                teams_df, 
                x='id', 
                y='progress',
                color='progress',
                color_continuous_scale=['#ef4444', '#f59e0b', '#22c55e'],
                labels={'team': 'Équipe', 'progress': 'Progression (%)'},
                title="Performance des équipes"
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune statistique d'équipe disponible")
    except Exception as e:
        st.warning("Graphiques non disponibles (module plotly manquant)")
        # Fallback vers un tableau simple
        try:
            teams_stats = db.stats_by_team()
            if teams_stats:  # Liste non vide
                st.dataframe(to_dataframe(teams_stats), use_container_width=True)
        except:
            st.info("Aucune statistique d'équipe disponible")

def add_persistent_legend(m):
    """Ajoute une légende persistante pour les 4 états des rues via contrôle HTML"""
    legend_html = """
    <div id='gm-legend' class='leaflet-control-layers leaflet-control' 
         style='position: absolute; bottom: 10px; right: 10px; z-index: 1000;
                background: white; border: 2px solid rgba(0,0,0,0.2); 
                border-radius: 5px; padding: 10px; box-shadow: 0 1px 5px rgba(0,0,0,0.2);
                font-family: "Helvetica Neue", Arial, Helvetica, sans-serif; 
                font-size: 12px; line-height: 18px; color: #333;'>
        <strong style='margin-bottom: 8px; display: block;'>Légende</strong>
        <div style='margin: 4px 0; display: flex; align-items: center;'>
            <span style='width: 20px; height: 0; border-top: 3px solid #28a745; 
                         display: inline-block; margin-right: 8px;'></span>
            <span>Terminée</span>
        </div>
        <div style='margin: 4px 0; display: flex; align-items: center;'>
            <span style='width: 20px; height: 0; border-top: 3px solid #f1c40f; 
                         display: inline-block; margin-right: 8px;'></span>
            <span>En cours</span>
        </div>
        <div style='margin: 4px 0; display: flex; align-items: center;'>
            <span style='width: 20px; height: 0; border-top: 3px solid #ff4d4f; 
                         display: inline-block; margin-right: 8px;'></span>
            <span>Assignée (à faire)</span>
        </div>
        <div style='margin: 4px 0; display: flex; align-items: center;'>
            <span style='width: 20px; height: 0; border-top: 3px dashed #ff4d4f; 
                         display: inline-block; margin-right: 8px;'></span>
            <span>Non assignée</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

def create_map(df, geo):
    """Crée la carte Folium centrée sur Mascouche avec toutes les rues"""
    # 1) Coercition sûre en DataFrame
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
    
    # Créer la carte
    m = folium.Map(
        location=center,
        zoom_start=13,  # Zoom optimisé pour voir toute la ville
        tiles="https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
        attr='© OpenStreetMap France',
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
        attr='© OpenStreetMap France',
        name='OSM France (Détaillé)',
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
        attr='© CARTO',
        name='CARTO Voyager',
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attr='© Esri',
        name='Esri WorldStreetMap',
        overlay=False,
        control=True
    ).add_to(m)

    # Ajouter le contrôle des couches
    folium.LayerControl().add_to(m)
    
    # Définir les limites de la carte sur Mascouche
    m.fit_bounds([[bounds["south"], bounds["west"]], 
                  [bounds["north"], bounds["east"]]])
    
    if not geo:
        st.warning("Aucune donnée géométrique disponible")
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
    
    # Ajouter TOUTES les rues de la géométrie
    for name, paths in geo.items():
        stats["total"] += 1
        
        # Info depuis DB ou défaut (rouge pointillé)
        info = street_info.get(name, {
            'status': 'a_faire',
            'team': '',
            'notes': '0'
        })
        
        status = info['status']
        team = info['team']
        notes = info['notes']
        
        # Style: TOUJOURS pointillé si pas d'équipe
        has_team = bool(team)
        color = status_colors.get(status, '#ef4444')  # Rouge par défaut
        opacity = 0.9 if has_team else 0.7
        dash = None if has_team else '8,12'  # Pointillés si non assigné
        weight = 7 if has_team else 5
        
        if has_team:
            stats["assigned"] += 1
        else:
            stats["unassigned"] += 1
        
        # Tooltip informatif
        tooltip_html = f"""
        <div style='font-family: sans-serif'>
            <strong style='font-size: 14px'>{name}</strong><br>
            <span style='color: {color}'>'óè Statut: {status.replace('_', ' ').title()}</span><br>
            <span>📋 Équipe: {team if team else '⚠️ NON ASSIGNÉE'}</span><br>
            <span>📝 Notes: {notes}</span>
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
    
    # Ajouter la légende persistante
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
        # Fallback si les dépendances ne sont pas installées
        return db.export_to_csv()


# ============================================
# FONCTIONNALITÉS AVANCÉES
# ============================================

def detect_mobile():
    """Détecte si l'utilisateur est sur mobile"""
    try:
        # Récupérer les paramètres de l'URL pour forcer le mode mobile
        query_params = st.experimental_get_query_params()
        if 'mobile' in query_params:
            return True
        
        # Mobile-first approach pour l'instant
        return True
    except:
        return False

def show_notification(message, type="success"):
    """Affiche une notification stylisée"""
    icons = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️"
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
    """Affiche les badges de réussite de l'équipe"""
    try:
        df = db.list_streets(team=team_id)
        done = len(df[df['status'] == 'terminee'])
        total = len(df)
        
        badges = []
        if done >= 1:
            badges.append("🏆 Première rue!")
        if done >= total * 0.25:
            badges.append("🥉 25% complété")
        if done >= total * 0.5:
            badges.append("🥈 50% complété")
        if done >= total * 0.75:
            badges.append("🥇 75% complété")
        if done == total:
            badges.append("🏆 CHAMPION!")
        
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
    """Génère une liste de téléphones pour SMS de groupe"""
    try:
        # Cette fonction nécessiterait une table de téléphones
        # Pour l'instant, retourne un exemple
        return "# Liste des téléphones bénévoles\n# 450-XXX-XXXX\n# 438-XXX-XXXX"
    except:
        return "Liste non disponible"

def page_export_gestionnaire(conn):
    """Section export avec formats multiples"""
    
    st.markdown("### 📊 Centre d'export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; border: 2px dashed #ccc; border-radius: 10px;">
            <h4>🧾 Rapport PDF</h4>
            <p><small>Format professionnel pour présentation</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            from reports import ReportGenerator
            generator = ReportGenerator()
            pdf_data = generator.generate_pdf()
            st.download_button(
                "📥 Télécharger PDF",
                pdf_data,
                "rapport_guignolee_2025.pdf",
                "application/pdf",
                
            )
        except ImportError:
            st.button("PDF (Installer reportlab)", disabled=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; border: 2px dashed #ccc; border-radius: 10px;">
            <h4>📊 Excel détaillé</h4>
            <p><small>Avec graphiques et mise en forme</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            excel_data = export_excel_professionnel(conn)
            st.download_button(
                "📥 Télécharger Excel",
                excel_data,
                "guignolee_2025.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                
            )
        except:
            st.button("Excel (Non disponible)", disabled=True)
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; border: 2px dashed #ccc; border-radius: 10px;">
            <h4>📄 Liste SMS</h4>
            <p><small>Téléphones des bénévoles</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        sms_list = generate_sms_list(conn)
        st.download_button(
            "📥 Liste téléphones",
            sms_list,
            "telephones_benevoles.txt",
            "text/plain",
            
        )


# ============================================
# PAGES
# ============================================

def page_accueil(conn, geo):
    """Page d'accueil"""
    st.markdown("### 🎁 Bienvenue sur Guigno-Map!")
    st.info("Sélectionnez votre mode dans le menu de gauche pour commencer.")
    
    st.markdown("---")
    st.markdown("#### 📊 Aperçu de la collecte")
    
    stats = db.extended_stats()
    render_metrics(stats)
    
    df_all = db.list_streets()
    if not df_all.empty:  # Liste non vide
        m = create_map(df_all, geo)
        st_folium(m, height=800, width=None, returned_objects=[])

def page_accueil_v2(geo):
    """Page d'accueil festive avec compte à rebours"""
    
    # Compte à rebours jusqu'au 1er décembre
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
            <h2 style="color: #FFD700; margin: 0;">⏰ Compte à rebours Guignolée</h2>
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
            <h2 style="color: #c41e3a; margin: 0;">🎉 C'EST AUJOURD'HUI!</h2>
            <div style="font-size: 2rem; color: #165b33; margin: 1rem 0;">
                Bonne Guignolée 2025!
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
        <h1 style="font-size: 3rem; margin: 0;">🎄 Bienvenue sur Guigno-Map 🎄</h1>
        <p style="font-size: 1.3rem; color: #666; margin: 1rem 0;">
            Votre plateforme digitale pour la Guignolée 2025
        </p>
        <p style="color: #888;">
            Gérez efficacement votre collecte de denrées avec une interface moderne
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats visuelles améliorées
    stats = db.extended_stats()
    progress = (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    st.markdown("### 📊 État de la collecte en temps réel")
    
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
            <div style="font-size: 3rem;">🏘️</div>
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
            <div style="font-size: 3rem;">✅</div>
            <div style="font-size: 2.5rem; font-weight: bold;">{stats['done']}</div>
            <div>Complétées</div>
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
            <div style="font-size: 3rem;">⏳</div>
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
            <div style="font-size: 3rem;">🎯</div>
            <div style="font-size: 2.5rem; font-weight: bold;">{progress:.0f}%</div>
            <div>Progression</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Barre de progression globale
    st.markdown("### 🎄 Progression globale de la collecte")
    st.progress(progress / 100)
    
    # Carte festive
    st.markdown("### 🗺️ Vue d'ensemble de Mascouche")
    df_all = db.list_streets()
    if not df_all.empty:  # Liste non vide
        m = create_map(df_all, geo)
        st_folium(m, height=750, width=None, returned_objects=[])
    
    # CSS pour réduire l'espace après la carte
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
        <h3>🎅 Prêt à participer ?</h3>
        <p>Choisissez votre rôle dans le menu de gauche pour commencer</p>
        <p style="font-size: 0.9rem; color: #666;">
            Bénévoles : Accédez à vos rues assignées<br>
            Gestionnaires : Supervisez toute la collecte
        </p>
    </div>
    """, unsafe_allow_html=True)

def page_benevole(geo):
    """Interface bénévole moderne avec vue limitée"""
    
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        render_login_card("benevole")
        return
    
    team_id = st.session_state.auth["team_id"]
    
    # Header d'équipe personnalisé
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #165b33, #c41e3a);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
    ">
        <h2 style="color: white; margin: 0;">🎅 Équipe {team_id}</h2>
        <p style="color: #FFD700; margin: 0.5rem 0 0 0;">Bonne collecte!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats de l'équipe
    df_team = db.list_streets(team=team_id)
    if df_team.empty:  # Liste vide
        st.warning("Aucune rue assignée. Contactez votre superviseur.")
        return
    
    done = len(df_team[df_team['status'] == 'terminee'])
    total = len(df_team)
    progress = (done / total * 100) if total > 0 else 0
    
    # Mini dashboard équipe
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📌 Vos rues", total)
    with col2:
        st.metric("✅ Complétées", done)
    with col3:
        st.metric("🎯 Progression", f"{progress:.0f}%")
    
    # Système de badges
    show_team_badges(team_id)
    
    # Barre de progression
    st.progress(progress / 100)
    
    # Tabs modernisés
    tab1, tab2, tab3 = st.tabs(["🗺️ Ma carte", "📝 Collecte", "📊 Historique"])
    
    with tab1:
        # CARTE LIMITÉE AUX RUES DE L'ÉQUIPE
        st.markdown("### Vos rues assignées")
        
        # Créer une carte avec SEULEMENT les rues de l'équipe
        m = folium.Map(
            location=[45.7475, -73.6005],
            zoom_start=14,
            tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
            attr='© CARTO'
        )
        
        # Filtrer geo pour n'afficher QUE les rues de l'équipe
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
                            weight=8,  # Plus épais pour mobile
                            opacity=0.9,
                            tooltip=f"{street_name} - {status.replace('_', ' ').title()}"
                        ).add_to(m)
        
        # Centrer sur les rues de l'équipe
        if team_streets and team_streets[0] in geo:
            first_street = geo[team_streets[0]][0]
            if first_street:
                m.location = first_street[0]
        
        st_folium(m, height=650, width=None, returned_objects=[])
    
    with tab2:
        st.markdown("### ✅ Checklist de collecte")
        
        # Liste interactive des rues
        for _, row in df_team.iterrows():
            name = str(row.get('name', '')) if pd.notna(row.get('name', '')) else ''
            status = row.get('status', 'a_faire')
            status = status if pd.notna(status) else 'a_faire'
            notes = str(row.get('notes', '0')) if pd.notna(row.get('notes', '0')) else '0'
            
            # Carte de rue stylisée
            status_emoji = {'terminee': '✅', 'en_cours': '🚶', 'a_faire': '⭕'}
            status_color = {'terminee': '#22c55e', 'en_cours': '#f59e0b', 'a_faire': '#ef4444'}
            
            with st.expander(f"{status_emoji.get(status, '⭕')} **{name}** ({notes} notes)"):
                
                # Changement rapide de statut
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("⭕ À faire", key=f"todo_{name}"):
                        db.set_status(name, 'a_faire')
                        st.rerun()
                with col2:
                    if st.button("⏳ En cours", key=f"progress_{name}"):
                        db.set_status(name, 'en_cours')
                        st.rerun()
                with col3:
                    if st.button("✅ Terminée", key=f"done_{name}"):
                        db.set_status(name, 'terminee')
                        st.rerun()
                
                st.markdown("---")
                
                # Ajout de note rapide
                st.markdown("**Ajouter une note:**")
                with st.form(f"note_{name}", clear_on_submit=True):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        num = st.text_input("N°", placeholder="123")
                    with col2:
                        note = st.text_input("Note", placeholder="Personne absente")
                    
                    if st.form_submit_button("'ûï Ajouter"):
                        if num and note:
                            db.add_note_for_address(name, team_id, num, note)
                            st.success("Note ajoutée!")
                            st.rerun()
                
                # Notes existantes
                notes_list = db.get_street_addresses_with_notes(name)
                if notes_list:  # Liste non vide
                    st.markdown("**Notes existantes:**")
                    for n in notes_list:
                        st.markdown(f"• **{n['address_number']}** : {n['comment']}")

                # ===== 📌 Adresses de la rue (nouveau) =====
                with st.expander("📌 Adresses de la rue", expanded=False):
                    if st.button("Afficher les adresses", key=f"show_addr_{name}"):
                        try:
                            addrs = db.get_addresses_by_street(name)
                        except Exception:
                            addrs = []
                        if addrs:
                            import pandas as pd
                            df_addr = pd.DataFrame(addrs)
                            st.dataframe(df_addr.head(300), use_container_width=True)
                            # Ajout note rapide liée à un numéro
                            colA, colB = st.columns([1,3])
                            with colA:
                                sel_num = st.selectbox(
                                    "Numéro",
                                    options=[a["house_number"] for a in addrs][:300],
                                    key=f"addr_sel_{name}",
                                )
                            with colB:
                                txt_note = st.text_input(
                                    "Note", key=f"addr_note_{name}", placeholder="Ex.: Absent / Don / Refus…"
                                )
                            if st.button("'ûï Ajouter note", key=f"addr_add_{name}"):
                                ok = False
                                # team_id déjà dispo dans la fonction (variable plus haut)
                                try:
                                    ok = bool(db.add_note_for_address(name, team_id, sel_num, txt_note))
                                except Exception:
                                    try:
                                        ok = bool(db.add_street_note(name, team_id, sel_num, txt_note))
                                    except Exception:
                                        ok = False
                                if ok:
                                    st.success(f"Note ajoutée pour {name} #{sel_num}")
                                    st.rerun()
                                else:
                                    st.error("Échec de l'ajout de note")
                        else:
                            st.info("Aucune adresse trouvée pour cette rue")
    
    with tab3:
        st.markdown("### 📊 Votre historique")
        try:
            notes = db.get_team_notes(team_id)
            if notes:  # Liste non vide
                st.dataframe(to_dataframe(notes), use_container_width=True)
            else:
                st.info("Aucune note encore")
        except:
            st.info("Historique non disponible")

def page_benevole_v2(geo):
    """Interface bénévole moderne v4.1 avec vue 'Mes rues'"""
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        # Afficher la page de connexion bénévole
        return page_benevole(geo)
    
    # Interface bénévole connecté avec tabs
    st.header("🎅 Espace Bénévole")
    team_id = st.session_state.auth.get("team", "Équipe inconnue")
    st.markdown(f"**Équipe:** {team_id}")
    
    # Tabs pour bénévoles
    tabs = st.tabs([
        "🏘️ Mes rues",
        "🗺️ Carte de terrain", 
        "📝 Journal d'activité"
    ])
    
    with tabs[0]:
        # Nouvelle vue "Mes rues" v4.1
        page_benevole_mes_rues()
    
    with tabs[1]:
        # Carte traditionnelle (réutilise l'ancienne interface)
        page_benevole(geo)
    
    with tabs[2]:
        # Journal d'activité de l'équipe
        st.markdown("### 📝 Journal d'activité de votre équipe")
        try:
            # Afficher les activités récentes de l'équipe
            from src.database.sqlite_pure import get_conn
            
            # Fonction locale SQLite pour recent_activity
            def recent_activity(limit=20):
                with get_conn() as conn:
                    cur = conn.execute(
                        "SELECT team_id, action, details, created_at FROM activity_log "
                        "ORDER BY created_at DESC LIMIT ?", (limit,)
                    )
                    cols = [d[0] for d in cur.description]
                    return [dict(zip(cols, row)) for row in cur.fetchall()]
            
            activities = recent_activity(20)
            
            if activities:
                team_activities = [a for a in activities if a.get('team_id') == team_id]
                for activity in team_activities:
                    action = activity.get('action', '')
                    details = activity.get('details', '')
                    created_at = activity.get('created_at', '')
                    st.markdown(f"**{created_at}** - {action}: {details}")
            else:
                st.info("Aucune activité enregistrée pour votre équipe")
                
        except Exception as e:
            st.info("Journal d'activité temporairement indisponible")
            st.caption(f"Erreur: {e}")

def page_gestionnaire_v2(geo):
    """Interface gestionnaire moderne (ancien superviseur)"""
    st.header("👤 Tableau de Bord Gestionnaire")
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "supervisor":
        render_login_card("gestionnaire")
        return
    
    # Dashboard moderne
    render_dashboard_gestionnaire(geo)
    
    # Tabs
    tabs = st.tabs([
        "📊 Vue d'ensemble",
        "👥 Équipes",
        "🗺️ Assignation",
        "📊 Export",
        "🛠️ Tech"
    ])
    
    with tabs[0]:
        # Carte générale
        st.markdown("### Carte générale")
        df_all = db.list_streets()
        if not df_all.empty:  # Liste non vide
            m = create_map(df_all, geo)
            st_folium(m, height=800, width=None, returned_objects=[])
        
        # Activité récente
        st.markdown("### Activité récente")
        try:
            recent = db.recent_activity(limit=10)
            if recent:  # Liste non vide
                st.dataframe(to_dataframe(recent), use_container_width=True)
            else:
                st.info("Aucune activité récente")
        except:
            st.info("Historique d'activité non disponible")
    
    with tabs[1]:
        # Gestion des équipes
        st.subheader("👥 Gestion des équipes", anchor=False)
        
        # === Formulaire de création d'équipe (robuste) ===
        with st.expander("➕ Créer une nouvelle équipe", expanded=False):
            with st.form("create_team_form", clear_on_submit=True):
                team_id_in = st.text_input(
                    "Identifiant d'équipe", 
                    key="new_team_id", 
                    placeholder="Ex: EQUIPE1",
                    help="Lettres et chiffres uniquement, max 20 caractères"
                )
                team_name_in = st.text_input(
                    "Nom d'équipe", 
                    key="new_team_name", 
                    placeholder="Ex: Équipe Centre",
                    help="Nom descriptif de l'équipe"
                )
                
                # Toggle pour afficher/masquer les mots de passe
                show_pw = st.checkbox("Afficher les mots de passe", value=False)
                pw_type = "default" if show_pw else "password"
                
                pwd_in = st.text_input(
                    "Mot de passe", 
                    type=pw_type, 
                    key="new_team_pwd", 
                    placeholder="Minimum 4 caractères",
                    help="Tout caractère accepté, min 4 / max 128"
                )
                pwd_conf = st.text_input(
                    "Confirmer le mot de passe", 
                    type=pw_type, 
                    key="new_team_pwd_conf", 
                    placeholder="Retapez le mot de passe",
                    help="Doit correspondre au mot de passe ci-dessus"
                )
                
                submitted = st.form_submit_button("✅ Créer l'équipe")

            if submitted:
                # Validation avec validators.py
                ok_id, team_id = validate_and_clean_input("team_id", team_id_in)
                ok_name, team_name = validate_and_clean_input("text", team_name_in)
                ok_pw, password = validate_and_clean_input("password", pwd_in)
                
                if not ok_id:
                    st.error("❌ Identifiant d'équipe invalide (lettres/chiffres, max 20)")
                elif not ok_name:
                    st.error("❌ Nom d'équipe invalide ou vide")
                elif not ok_pw:
                    st.error("❌ Mot de passe invalide (minimum 4 caractères)")
                elif pwd_in != pwd_conf:
                    st.error("❌ Les mots de passe ne correspondent pas")
                else:
                    # Tentative de création avec db.create_team
                    try:
                        created = db.create_team(team_id, team_name, password)
                        if created:
                            st.toast(f"✅ Équipe {team_id} créée avec succès", icon="✅")
                            st.rerun()
                        else:
                            st.error("❌ Échec de création (ID déjà existant ?)")
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la création: {e}")
        
        # === Liste des équipes (sans doublon de titre) ===
        try:
            teams_df = db.get_all_teams()
            if teams_df:  # Liste non vide
                st.dataframe(to_dataframe(teams_df), use_container_width=True)
            else:
                st.info("Aucune équipe créée")
        except Exception as e:
            st.info("Liste des équipes non disponible")

        # === 🔐 Modifier / réinitialiser le mot de passe ===
        with st.expander("🔐 Modifier / réinitialiser le mot de passe", expanded=False):
            # récupérer les équipes
            try:
                teams = db.get_teams_list()
                options = [f"{t[1]} ({t[0]})" for t in teams] if teams else []
            except Exception:
                options = []
            
            with st.form("pwd_team_form", clear_on_submit=False):
                choice = st.selectbox("Équipe", options=options, index=0 if options else None)
                show = st.checkbox("Afficher le mot de passe", value=False)
                ty = "default" if show else "password"
                new1 = st.text_input("Nouveau mot de passe", type=ty, key="pwd_new1")
                new2 = st.text_input("Confirmer", type=ty, key="pwd_new2")
                colU, colR = st.columns(2)
                do_update = colU.form_submit_button("✅ Mettre à jour", use_container_width=True)
                do_reset  = colR.form_submit_button("🎲 Réinitialiser (aléatoire)", use_container_width=True)
            
            # traitement
            team_id = ""
            if choice:
                team_id = choice.split("(")[-1].rstrip(")")
            
            if do_update:
                if not team_id:
                    st.error("Aucune équipe sélectionnée")
                elif len(new1) < 4:
                    st.error("Mot de passe trop court (min 4 caractères)")
                elif new1 != new2:
                    st.error("La confirmation ne correspond pas")
                else:
                    try:
                        ok = db.update_team_password(team_id, new1)
                        if ok:
                            st.success(f"Mot de passe mis à jour pour {team_id}")
                            st.rerun()
                        else:
                            st.error("Échec de la mise à jour")
                    except Exception as e:
                        st.error(f"Erreur: {e}")
            
            if do_reset:
                if not team_id:
                    st.error("Aucune équipe sélectionnée")
                else:
                    try:
                        newpwd = db.reset_team_password(team_id)
                        if newpwd:
                            st.success(f"Nouveau mot de passe généré pour {team_id}")
                            st.code(newpwd)  # à copier maintenant; ne sera plus affiché ensuite
                        else:
                            st.error("Échec de la réinitialisation")
                    except Exception as e:
                        st.error(f"Erreur: {e}")
    
    with tabs[2]:
        # Assignation v4.1
        page_assignations_v41()
    
    with tabs[3]:
        # Export amélioré v4.1
        page_export_gestionnaire_v41()

    with tabs[4]:
        st.markdown("### 🛠 Opérations techniques (protégées)")

        # -- PIN stocké dans secrets (config.toml -> [secrets] TECH_PIN="xxxx")
        from src.config import settings
        TECH_PIN = settings.TECH_PIN

        if "tech_ok" not in st.session_state:
            st.session_state.tech_ok = False

        if not st.session_state.tech_ok:
            pin = st.text_input("Entrer le PIN technique", type="password")
            if st.button("Déverrouiller"):
                if TECH_PIN and pin == TECH_PIN:
                    st.session_state.tech_ok = True
                    st.success("Accès technique déverrouillé.")
                    st.rerun()
                else:
                    st.error("PIN invalide.")
            st.stop()

        st.info("⚠️ Ces actions sont lourdes et n'affectent pas les statuts/notes. Elles régénèrent les caches OSM.")

        # --- Reconstruire le cache géométrique (lourd)
        with st.expander("🔄 Reconstruire cache OSM (géométries)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirm = st.checkbox("Je comprends les implications")
            with col2:
                safety = st.text_input('Écrire "REBUILD" pour confirmer')

            if st.button("Lancer la reconstruction"):
                if confirm and safety.strip().upper() == "REBUILD":
                    with st.spinner("Construction du cache…"):
                        build_geometry_cache()       # reconstruit le fichier osm_cache.json
                        st.cache_data.clear()        # purge cache Streamlit
                    st.success("✅ Cache OSM mis à jour (géométries).")
                    st.rerun()
                else:
                    st.warning("Confirmation incomplète.")

        # --- Reconstruire/Importer le cache des adresses
        with st.expander("📍 Mettre à jour les adresses (OSM)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirmA = st.checkbox("Je confirme")
            with col2:
                safetyA = st.text_input('Écrire "IMPORT" pour confirmer')

            if st.button("Lancer la mise à jour des adresses"):
                if confirmA and safetyA.strip().upper() == "IMPORT":
                    with st.spinner("Téléchargement des adresses OSM…"):
                        build_addresses_cache()
                        addr_cache = load_addresses_cache()
                        count = db.import_addresses_from_cache(addr_cache)
                    st.success(f"✅ {count} adresses importées depuis OSM.")
                    st.rerun()
                else:
                    st.warning("Confirmation incomplète.")

        # --- Gestion des backups
        with st.expander("🗃️ Gestion des backups", expanded=False):
            backup_mgr = db.get_backup_manager()  # Sans DB_PATH, utilise config SQLAlchemy
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("🔄 Créer un backup manuel"):
                    backup_file = backup_mgr.create_backup("manual")
                    if backup_file:
                        st.success(f"Backup créé : {Path(backup_file).name}")
            
            with col2:
                if st.button("✅ Voir les backups"):
                    backups = backup_mgr.list_backups()
                    if backups:
                        for backup in backups[:5]:  # Montrer les 5 derniers
                            st.text(f"• {backup['name']} ({backup['size']})")
                    else:
                        st.info("Aucun backup disponible")

def page_superviseur(conn, geo):
    """Interface superviseur"""
    st.header("🎯 Tableau de Bord Superviseur")
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "supervisor":
        render_login_card("superviseur")
        return
    
    # Dashboard moderne
    render_dashboard_gestionnaire(geo)
    
    # Tabs
    tabs = st.tabs([
        "📊 Vue d'ensemble",
        "👥 Équipes",
        "🗺️ Assignation",
        "📊 Export",
        "🛠️ Tech"
    ])
    
    with tabs[0]:
        # Carte générale
        st.markdown("### Carte générale")
        df_all = db.list_streets()
        if not df_all.empty:  # Liste non vide
            m = create_map(df_all, geo)
            st_folium(m, height=800, width=None, returned_objects=[])
        
        # Activité récente
        st.markdown("### Activité récente")
        recent = db.recent_activity(limit=10)
        if recent:  # Liste non vide
            st.dataframe(to_dataframe(recent), use_container_width=True)
    
    with tabs[1]:
        # Gestion des équipes
        st.markdown("### Gestion des équipes")
        
        with st.expander("Créer une équipe"):
            with st.form("new_team", clear_on_submit=True):
                new_id = st.text_input("Identifiant")
                new_name = st.text_input("Équipe")
                new_pass = st.text_input("Mot de passe", type="password")
                new_pass_confirm = st.text_input("Confirmer le mot de passe", type="password")
                
                # Validation du mot de passe
                password_valid = True
                error_messages = []
                
                if new_pass or new_pass_confirm:  # Si au moins un champ est rempli
                    if len(new_pass) < 4:
                        password_valid = False
                        error_messages.append("Le mot de passe doit contenir au moins 4 caractères")
                    
                    if new_pass != new_pass_confirm:
                        password_valid = False
                        error_messages.append("Les mots de passe ne correspondent pas")
                
                # Affichage des erreurs
                if error_messages:
                    for msg in error_messages:
                        st.error(msg)
                
                # Bouton désactivé si validation échoue
                button_disabled = not (all([new_id, new_name, new_pass, new_pass_confirm]) and password_valid)
                
                if st.form_submit_button("Créer", disabled=button_disabled):
                    if all([new_id, new_name, new_pass]) and password_valid:
                        if db.create_team(new_id, new_name, new_pass):
                            st.success(f"Équipe {new_id} créée")
                            st.rerun()
        
        # Liste des équipes
        teams_df = db.get_all_teams()
        if teams_df:  # Liste non vide
            st.dataframe(to_dataframe(teams_df), use_container_width=True)
    
    with tabs[2]:
        # Assignation
        st.markdown("### Assignation des rues")
        
        unassigned = db.get_unassigned_streets()
        
        if unassigned:  # Liste non vide
            with st.form("assign"):
                team = st.selectbox("Équipe", db.teams())
                streets = st.multiselect("Rues", unassigned)
                
                if st.form_submit_button("Assigner"):
                    if team and streets:
                        db.assign_streets_to_team(streets, team)
                        st.success("Rues assignées!")
                        st.rerun()
        else:
            st.success("Toutes les rues sont assignées!")
        
        # Tableau des assignations
        df_all = db.list_streets()
        if not df_all.empty:  # Liste non vide
            st.dataframe(
                df_all[['name', 'sector', 'team', 'status']],
                use_container_width=True
            )
    
    with tabs[3]:
        # Export
        st.markdown("### Export des données")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                "📊 Export rues (CSV)",
                db.export_to_csv(),
                "rapport_rues.csv",
                "text/csv",
                
            )
        
        with col2:
            st.download_button(
                "📊 Export notes (CSV)",
                db.export_notes_csv(),
                "rapport_notes.csv",
                "text/csv",
                
            )

    with tabs[4]:
        st.markdown("### 🛠 Opérations techniques (protégées)")

        # -- PIN stocké dans secrets (config.toml -> [secrets] TECH_PIN="xxxx")  
        from src.config import settings
        TECH_PIN = settings.TECH_PIN

        if "tech_ok" not in st.session_state:
            st.session_state.tech_ok = False

        if not st.session_state.tech_ok:
            pin = st.text_input("Entrer le PIN technique", type="password")
            if st.button("Déverrouiller"):
                if TECH_PIN and pin == TECH_PIN:
                    st.session_state.tech_ok = True
                    st.success("Accès technique déverrouillé.")
                    st.rerun()
                else:
                    st.error("PIN invalide.")
            st.stop()

        st.info("⚠️ Ces actions sont lourdes et n'affectent pas les statuts/notes. Elles régénèrent les caches OSM.")

        # --- Reconstruire le cache géométrique (lourd)
        with st.expander("🔄 Reconstruire cache OSM (géométries)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirm = st.checkbox("Je comprends les implications")
            with col2:
                safety = st.text_input('Écrire "REBUILD" pour confirmer')

            if st.button("Lancer la reconstruction"):
                if confirm and safety.strip().upper() == "REBUILD":
                    with st.spinner("Construction du cache…"):
                        build_geometry_cache()       # reconstruit le fichier osm_cache.json
                        st.cache_data.clear()        # purge cache Streamlit
                    st.success("✅ Cache OSM mis à jour (géométries).")
                    st.rerun()
                else:
                    st.warning("Confirmation incomplète.")

        # --- Reconstruire/Importer le cache des adresses
        with st.expander("📍 Mettre à jour les adresses (OSM)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirmA = st.checkbox("Je confirme")
            with col2:
                safetyA = st.text_input('Écrire "IMPORT" pour confirmer')

            if st.button("Lancer la mise à jour des adresses"):
                if confirmA and safetyA.strip().upper() == "IMPORT":
                    with st.spinner("Téléchargement des adresses OSM…"):
                        build_addresses_cache()
                        addr_cache = load_addresses_cache()
                        count = db.import_addresses_from_cache(addr_cache)
                    st.success(f"✅ {count} adresses importées depuis OSM.")
                    st.rerun()
                else:
                    st.warning("Confirmation incomplète.")

# ============================================
# MAIN
# ============================================

# ================================================================================
# NOUVELLES FONCTIONS v4.1 - SUPERVISEUR ET BÉNÉVOLE
# ================================================================================

def page_assignations_v41():
    """Assignations : au choix par secteur (bulk) OU par rue (manuel)."""
    import pandas as pd
    st.subheader("🗺️ Assignations", anchor=False)

    tabs = st.tabs(["🎯 Par secteur (rapide)", "🧭 Par rue (manuel)", "📋 Assignation simple"])

    # ========== TAB 1 : BULK PAR SECTEUR (inchangé) ==========
    with tabs[0]:
        try:
            unassigned_count = db.get_unassigned_streets_count()
        except Exception:
            # fallback si la fonction n'existe pas
            _df = db.list_streets()
            unassigned_count = int((_df["team"].isna() | (_df["team"] == "")).sum()) if not _df.empty else 0

        if unassigned_count > 0:
            st.info(f"⚠️ {unassigned_count} rue(s) non assignée(s)")

        with st.container():
            c1, c2, c3 = st.columns([1, 1.2, 0.7], vertical_alignment="bottom")

            with c1:
                try:
                    liste_secteurs = db.get_sectors_list()
                except Exception:
                    liste_secteurs = []
                secteur = st.selectbox(
                    "SECTEUR À ASSIGNER",
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
                    "ÉQUIPE",
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
                            st.toast(f"✅ {nb} rue(s) assignée(s) à {team}", icon="✅")
                            st.rerun()
                        else:
                            st.toast("ℹ️ Aucune rue non assignée dans ce secteur", icon="ℹ️")
                    except Exception as e:
                        st.error(f"Erreur lors de l'assignation: {e}")

        st.markdown("### 📋 État des assignations")
        try:
            df = db.list_streets()
            if not df.empty:
                df_disp = df.assign(
                    Statut=df["status"].map(STATUS_TO_LABEL).fillna("À faire")
                ).rename(columns={"name": "Rue", "sector": "Secteur", "team": "Équipe"})[
                    ["Rue", "Secteur", "Équipe", "Statut"]
                ]
                st.dataframe(df_disp, use_container_width=True)
            else:
                st.info("Aucune rue trouvée")
        except Exception as e:
            st.error(f"Erreur d'affichage: {e}")

    # ========== TAB 2 : ASSIGNATION MANUELLE PAR RUE ==========
    with tabs[1]:
        # Équipe cible
        try:
            teams = db.get_teams_list()
        except Exception:
            teams = [(t, t) for t in (db.teams() or [])]
        team_display = st.selectbox(
            "ÉQUIPE CIBLE",
            options=[f"{name} ({tid})" for (tid, name) in teams] if teams else [],
            index=0 if teams else None,
            key="team_for_streets",
        )
        team_id = team_display.split("(")[-1].rstrip(")") if team_display else None

        # Source de rues (non assignées ou toutes)
        src = st.radio("Source", ["Rues non assignées", "Toutes les rues"], horizontal=True)

        # Données rues
        df = db.list_streets()
        if df.empty:
            st.info("Aucune rue dans la base.")
            return

        # Filtres
        q = st.text_input("🔎 Filtrer par nom (contient)…", "")
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
        selected = st.multiselect("Rues à assigner", options=options, default=[])

        st.caption(f"{len(options)} rue(s) listée(s) • {len(selected)} sélectionnée(s)")
        do_overwrite = st.checkbox("Réassigner même si déjà affectée (écrase l'équipe actuelle)", value=True)

        colA, colB = st.columns([1, 1])
        with colA:
            if st.button("✅ Assigner les rues sélectionnées", use_container_width=True,
                         disabled=not (team_id and selected)):
                try:
                    if team_id:  # Vérification supplémentaire
                        db.assign_streets_to_team(selected, team_id)
                        st.success(f"{len(selected)} rue(s) assignée(s) à {team_id}")
                        st.rerun()
                except Exception as e:
                    st.error(f"Assignation échouée: {e}")

        with colB:
            # Affichage d'aperçu des rues choisies
            if selected:
                st.write("Aperçu :")
                st.dataframe(
                    work[work["name"].isin(selected)][["name", "sector", "team", "status"]]
                    .rename(columns={"name": "Rue", "sector": "Secteur", "team": "Équipe", "status": "Statut"}),
                    use_container_width=True
                )

    # ========== TAB 3 : ASSIGNATION SIMPLE PAR RUE ==========
    with tabs[2]:
        st.markdown("### 📋 Assignation par rue (simple)")
        
        # Récupérer les équipes disponibles  
        try:
            teams = db.get_teams_list()  # [(id, name), ...]
        except Exception:
            teams = [(t, t) for t in (db.teams() or [])]
        
        # Récupérer les rues non assignées
        try:
            unassigned_streets = db.get_unassigned_streets()
        except Exception:
            unassigned_streets = []
        
        if not teams:
            st.warning("Aucune équipe disponible. Créez d'abord une équipe.")
            return
            
        if not unassigned_streets:
            st.success("✅ Toutes les rues sont déjà assignées !")
            return
        
        # Interface de sélection
        with st.container():
            col1, col2 = st.columns([1, 2])
            
            with col1:
                team_options = [f"{name} ({tid})" for (tid, name) in teams]
                selected_team_display = st.selectbox(
                    "Équipe",
                    options=[""] + team_options,
                    index=0,
                    key="simple_assign_team"
                )
                
                # Extraire l'ID de l'équipe
                team_id = ""
                if selected_team_display and selected_team_display != "":
                    team_id = selected_team_display.split("(")[-1].rstrip(")")
            
            with col2:
                selected_streets = st.multiselect(
                    "Rues à assigner",
                    options=unassigned_streets,
                    default=[],
                    key="simple_assign_streets"
                )
        
        # Option de réassignation (masquée pour simplification)
        # do_overwrite = st.checkbox("Réassigner si déjà affectée", value=False)
        
        # Informations et validation
        st.caption(f"📊 {len(unassigned_streets)} rue(s) non assignée(s) • {len(selected_streets)} sélectionnée(s)")
        
        # Validation et bouton
        if not team_id or not selected_streets:
            if st.button("Assigner", disabled=True, use_container_width=True):
                pass
            if not team_id and not selected_streets:
                st.error("Sélectionnez au moins une rue et une équipe.")
            elif not team_id:
                st.error("Sélectionnez une équipe.")
            elif not selected_streets:
                st.error("Sélectionnez au moins une rue.")
        else:
            if st.button("Assigner", use_container_width=True):
                try:
                    # Appel à la fonction d'assignation
                    db.assign_streets_to_team(selected_streets, team_id)
                    st.toast(f"✅ {len(selected_streets)} rue(s) assignée(s) à {team_id}", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'assignation: {e}")


def page_export_gestionnaire_v41():
    """Page d'export v4.1 avec nouvelles fonctionnalités"""
    st.markdown("### 📥 Export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV standard
        try:
            st.download_button(
                "📊 Export CSV Standard",
                db.export_to_csv(),
                "rapport_rues.csv",
                "text/csv",
                
            )
        except Exception as e:
            st.button("📊 CSV (Erreur)", disabled=True)
            st.caption(f"Erreur: {e}")
    
    with col2:
        # Export Excel professionnel
        try:
            from reports import ReportGenerator
            generator = ReportGenerator()
            excel_data = generator.generate_excel()
            st.download_button(
                "📊 Export Excel Pro",
                excel_data,
                "guignolee_2025_rapport.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                
            )
        except ImportError:
            st.button("📊 Excel (Installer xlsxwriter)", disabled=True)
        except Exception as e:
            st.button("📊 Excel (Erreur)", disabled=True)
            st.caption(f"Erreur: {e}")
    
    with col3:
        # Export PDF professionnel
        try:
            from reports import ReportGenerator
            generator = ReportGenerator()
            pdf_data = generator.generate_pdf()
            st.download_button(
                "📄 Export PDF Pro",
                pdf_data,
                "guignolee_2025_rapport.pdf",
                "application/pdf",
                
            )
        except ImportError:
            st.button("📄 PDF (Installer reportlab)", disabled=True)
        except Exception as e:
            st.button("📄 PDF (Erreur)", disabled=True)
            st.caption(f"Erreur: {e}")
    
    # Export CSV assignations (nouveau v4.1)
    st.markdown("---")
    st.markdown("### 📋 Export spécialisés v4.1")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV assignations
        try:
            assignations_data = db.get_assignations_export_data()
            if assignations_data:  # Liste non vide
                csv_data = pd.DataFrame(assignations_data).to_csv(index=False, encoding='utf-8')
                st.download_button(
                    "✅ Export CSV Assignations",
                    csv_data,
                    "assignations_secteurs.csv",
                    "text/csv", help="Colonnes: secteur, rue, équipe, statut"
                )
            else:
                st.button("📋 Assignations (Aucune donnée)", disabled=True)
        except Exception as e:
            st.button("✅ Assignations (Erreur)", disabled=True)
            st.caption(f"Erreur: {e}")
    
    with col2:
        # Export notes
        try:
            st.download_button(
                "📝 Export Notes",
                db.export_notes_csv(),
                "rapport_notes.csv",
                "text/csv",
                
            )
        except Exception as e:
            st.button("📝 Notes (Erreur)", disabled=True)
            st.caption(f"Erreur: {e}")
    
    # --- CSV d'assignation (export/import) ---
    st.markdown("---")
    st.markdown("### 📄 CSV d'assignation des rues")
    with st.expander("Exporter / Importer", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📤 Exporter le template (CSV)", use_container_width=True):
                try:
                    df = db.export_streets_template(include_assignments=False)
                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Télécharger streets_template.csv",
                        data=csv_data,
                        file_name="streets_template.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erreur lors de l'export: {e}")
        with c2:
            up = st.file_uploader("📥 Importer votre CSV modifié", type=["csv"], key="csv_upload")
            if up is not None:
                try:
                    from io import BytesIO
                    # Convertir en BytesIO si nécessaire
                    if hasattr(up, 'read'):
                        file_content = up.read()
                        if isinstance(file_content, str):
                            file_like = BytesIO(file_content.encode('utf-8'))
                        else:
                            file_like = BytesIO(file_content)
                    else:
                        file_like = up
                    
                    res = db.upsert_streets_from_csv(file_like)
                    st.success(f"✅ Import terminé — inserted={res.get('inserted',0)}, updated={res.get('updated',0)}, skipped={res.get('skipped',0)}, errors={res.get('errors',0)}")
                    if res.get('inserted', 0) > 0 or res.get('updated', 0) > 0:
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'import: {e}")

def page_benevole_mes_rues():
    """Vue 'Mes rues' pour bénévoles v4.1"""
    
    # Récupérer l'équipe du bénévole connecté
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        st.warning("Accès réservé aux bénévoles connectés")
        return
    
    team_id = st.session_state.auth.get("team")
    if not team_id:
        st.error("Équipe non identifiée")
        return
    
    st.markdown(f"### 🏘️ Mes rues assignées - Équipe {team_id}")
    
    try:
        # Récupérer les rues de l'équipe
        team_streets = db.get_team_streets(team_id)
        
        if not team_streets:  # Liste vide
            st.info("Aucune rue assignée à votre équipe pour le moment.")
            return
        
        # Afficher les statistiques de l'équipe
        total_streets = len(team_streets)
        done_streets = len([s for s in team_streets if s.get('status') == 'terminee'])
        in_progress = len([s for s in team_streets if s.get('status') == 'en_cours'])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total rues", total_streets)
        with col2:
            st.metric("Terminées", done_streets)
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
            
            with st.expander(f"🏘️ {street_name} ({street['sector']}) - {current_status.replace('_', ' ').title()}", 
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
                        "🔓 En cours", 
                        key=f"progress_{street_name}",
                        disabled=current_status == 'en_cours',
                        
                    ):
                        if db.update_street_status(street_name, 'en_cours', team_id):
                            st.toast(f"✅ {street_name} marquée en cours", icon="🚀")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la mise à jour")
                
                with col3:
                    # Bouton "Terminée"
                    if st.button(
                        "✅ Terminée", 
                        key=f"done_{street_name}",
                        disabled=current_status == 'terminee',
                        
                    ):
                        if db.update_street_status(street_name, 'terminee', team_id):
                            st.toast(f"🎉 {street_name} terminée!", icon="🎉")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la mise à jour")
                
                # Section notes
                st.markdown("**Gestion des notes:**")
                
                # Afficher les notes existantes
                existing_notes = db.get_street_notes_for_team(street_name, team_id)
                if existing_notes:
                    st.markdown("*Notes existantes:*")
                    for note in existing_notes:
                        st.markdown(f"• **#{list(note.values())[0] if isinstance(note, dict) else note[0]}** : {list(note.values())[1] if isinstance(note, dict) else note[1]} _{list(note.values())[2] if isinstance(note, dict) else note[2]}_")
                
                # Ajouter une nouvelle note
                with st.form(f"note_form_{street_name}"):
                    col_addr, col_note = st.columns([1, 3])
                    with col_addr:
                        address_number = st.text_input(
                            "N° civique", 
                            key=f"addr_{street_name}",
                            placeholder="123A"
                        )
                    with col_note:
                        comment = st.text_area(
                            "Commentaire", 
                            key=f"comment_{street_name}",
                            placeholder="Ex: Absent, refus, don reçu...",
                            max_chars=500,
                            height=80
                        )
                    
                    if st.form_submit_button("🗃️ Enregistrer note"):
                        if address_number and comment:
                            if db.add_street_note(street_name, team_id, address_number, comment):
                                st.toast(f"📝 Note ajoutée pour {street_name} #{address_number}", icon="📝")
                                st.rerun()
                            else:
                                st.error("Erreur lors de l'enregistrement de la note")
                        else:
                            st.warning("Veuillez remplir le numéro et le commentaire")
                            
    except Exception as e:
        st.error(f"Erreur lors du chargement de vos rues: {e}")
        st.info("Fonctionnalité temporairement indisponible")

def main():
    """Point d'entrée principal - Version 2.0 Guignolée"""
    
    # CSS moderne
    inject_css()
    
    # Connexion DB
    # Initialisation de la base de données
    db.init_db()
    
    # Compatibilité legacy supprimée - utilise SQLAlchemy via src.database
    # Connexion centralisée via get_session() au lieu de sqlite3 direct
    
    # Cache géométrique
    @st.cache_data(ttl=None)
    def get_geo(_sig):
        data = load_geometry_cache()
        return data if data else {}
    
    sig = int(CACHE_FILE.stat().st_mtime_ns) if CACHE_FILE.exists() else 0
    geo = get_geo(sig)
    
    # Header festif
    render_header()
    
    # Navigation modernisée dans la sidebar
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
            # Placeholder centré
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
                <div style="font-size: 2.5rem;">🎁</div>
                <div style="font-weight: bold; font-size: 1.2rem;">LOGO</div>
                <small>Espace réservé</small>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        # Navigation
        st.markdown("### 🎄 Navigation")
        
        # Boutons de navigation stylisés
        if st.button("🏠 Accueil"):
            st.session_state.page = "accueil"
            st.rerun()
        
        if st.button("🎅 Bénévole"):
            st.session_state.page = "benevole"
            st.rerun()
            
        if st.button("👤 Gestionnaire"):
            st.session_state.page = "gestionnaire"  
            st.rerun()
        
        # Déconnexion si connecté
        if st.session_state.auth:
            st.markdown("---")
            if st.button("🚪 Déconnexion"):
                st.session_state.auth = None
                st.rerun()
        
        # Compteur temps réel
        st.markdown("---")
        stats = db.extended_stats()
        st.markdown(f"""
        <div style="text-align: center;">
            <h4>État de la collecte</h4>
            <div style="font-size: 2rem; color: #FFD700;">
                {stats['done']}/{stats['total']}
            </div>
            <small>Rues complétées</small>
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
            🎄 Guignolée 2025 - Le Relais de Mascouche 🎄<br>
            <small>Ensemble, redonnons espoir | 📞 450-474-4133</small>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Bannière en bas de page
    if (ASSETS / "banner.png").exists():
        st.image(str(ASSETS / "banner.png"))

if __name__ == "__main__":
    main()

