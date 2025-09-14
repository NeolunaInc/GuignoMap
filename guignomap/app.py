"""
Guigno-Map - Application de gestion de collecte de denrées
Le Relais de Mascouche
Version 3.0 - Production
"""

from pathlib import Path
import time
from datetime import datetime
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# Import des modules locaux
import db
from osm import build_geometry_cache, load_geometry_cache, build_addresses_cache, load_addresses_cache, CACHE_FILE

# Configuration des chemins
DB_PATH = Path(__file__).parent / "guigno_map.db"
ASSETS = Path(__file__).parent / "assets"

# Configuration Streamlit
st.set_page_config(
    page_title="Guigno-Map | Relais de Mascouche",
    page_icon="🎁",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        stats = db.extended_stats(st.session_state.get('conn'))
        progress = (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
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

def render_login_card(role="benevole", conn=None):
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
            <div style="font-size: 3rem;">👔</div>
            <h2 style="color: #FFD700; margin: 1rem 0;">Espace Gestionnaire</h2>
            <p style="color: #cbd5e1;">Gérez la collecte et les équipes</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_gestionnaire", clear_on_submit=False):
            password = st.text_input(
                "🔐 Mot de passe",
                type="password",
                placeholder="Entrez le mot de passe gestionnaire"
            )
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                submit = st.form_submit_button(
                    "🚀 Connexion",
                    use_container_width=True
                )
            
            if submit:
                if db.verify_team(conn, "ADMIN", password):
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
            <div style="font-size: 3rem;">🎅</div>
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
                    "🔐 Mot de passe",
                    type="password",
                    placeholder="Mot de passe équipe"
                )
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                submit = st.form_submit_button(
                    "🎄 Connexion",
                    use_container_width=True
                )
            
            if submit:
                if db.verify_team(conn, team_id, password):
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
        📞 450-474-4133
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

def render_dashboard_gestionnaire(conn, geo):
    """Dashboard moderne pour gestionnaires avec KPIs visuels"""
    
    # KPIs principaux en cartes colorées
    stats = db.extended_stats(conn)
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
            <div style="font-size: 2.5rem;">🚶</div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{stats.get('partial', 0)}</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">En cours</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Nombre d'équipes actives
        teams_count = len(db.teams(conn))
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(139,92,246,0.3);
        ">
            <div style="font-size: 2.5rem;">👥</div>
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
        teams_stats = db.stats_by_team(conn)
        if not teams_stats.empty:
            # Graphique en barres colorées
            import plotly.express as px
            fig = px.bar(
                teams_stats, 
                x='team', 
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
            teams_stats = db.stats_by_team(conn)
            if not teams_stats.empty:
                st.dataframe(teams_stats, use_container_width=True)
        except:
            st.info("Aucune statistique d'équipe disponible")

def create_map(df, geo):
    """Crée la carte Folium centrée sur Mascouche avec toutes les rues"""
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
    if not df.empty:
        for idx, row in df.iterrows():
            name = str(row['name']) if 'name' in df.columns else ''
            status = row['status'] if 'status' in df.columns and pd.notna(row['status']) else 'a_faire'
            team = row['team'] if 'team' in df.columns and pd.notna(row['team']) else ''
            notes = str(row['notes']) if 'notes' in df.columns and pd.notna(row['notes']) else '0'
            
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
            <span style='color: {color}'>● Statut: {status.replace('_', ' ').title()}</span><br>
            <span>📋 Équipe: {team if team else '⚠️ NON ASSIGNÉE'}</span><br>
            <span>📝 Notes: {notes}</span>
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
    
    # Légende améliorée
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; right: 50px; width: 220px;
                background: white; z-index:9999; font-size:14px;
                border: 2px solid #8B0000; border-radius: 10px; padding: 15px;
                box-shadow: 0 0 15px rgba(0,0,0,0.2)">
        <h4 style="margin: 0 0 10px 0; color: #8B0000;">Légende</h4>
        <div><span style="background:#22c55e; width:30px; height:3px; display:inline-block;"></span> Terminée</div>
        <div><span style="background:#f59e0b; width:30px; height:3px; display:inline-block;"></span> En cours</div>
        <div><span style="background:#ef4444; width:30px; height:3px; display:inline-block;"></span> À faire</div>
        <hr style="margin: 8px 0;">
        <div><span style="border-bottom: 3px dashed #666; width:30px; display:inline-block;"></span> Non assignée</div>
        <div><span style="border-bottom: 3px solid #666; width:30px; display:inline-block;"></span> Assignée</div>
        <hr style="margin: 8px 0;">
        <small>
            <strong>Total:</strong> {stats["total"]} voies<br>
            <strong>Assignées:</strong> {stats["assigned"]}<br>
            <strong>Non assignées:</strong> {stats["unassigned"]}
        </small>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m


# ============================================
# UTILITAIRES EXPORT
# ============================================

def export_excel_professionnel(conn):
    """Export Excel avec mise en forme professionnelle"""
    try:
        from reports import ReportGenerator
        generator = ReportGenerator(conn)
        return generator.generate_excel()
    except ImportError:
        # Fallback si les dépendances ne sont pas installées
        return db.export_to_csv(conn)


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

def show_team_badges(conn, team_id):
    """Affiche les badges de réussite de l'équipe"""
    try:
        df = db.list_streets(conn, team=team_id)
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
            badges.append("🌟 CHAMPION!")
        
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

def create_festive_map(df, geo):
    """Carte avec thème festif de Noël"""
    center = [45.7475, -73.6005]
    
    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attr='© Esri',
        control_scale=True
    )
    
    # Marqueur spécial pour le Relais
    folium.Marker(
        [45.7475, -73.6005],
        popup="🎁 Le Relais de Mascouche",
        tooltip="Point de départ de la Guignolée",
        icon=folium.Icon(color='red', icon='gift', prefix='fa')
    ).add_to(m)
    
    # Construction du lookup
    street_info = {}
    if not df.empty:
        for _, row in df.iterrows():
            name = str(row['name']) if 'name' in df.columns else ''
            street_info[name] = {
                'status': row.get('status', 'a_faire'),
                'team': row.get('team', ''),
                'notes': str(row.get('notes', 0))
            }
    
    # Couleurs festives
    status_colors = {
        'terminee': '#165b33',  # Vert sapin
        'en_cours': '#FFD700',   # Or
        'a_faire': '#c41e3a'     # Rouge Noël
    }
    
    for name, paths in geo.items():
        info = street_info.get(name, {'status': 'a_faire', 'team': '', 'notes': '0'})
        
        color = status_colors.get(info['status'], '#c41e3a')
        team = info['team']
        opacity = 0.9 if team else 0.5
        dash = None if team else '10,10'
        weight = 8 if team else 5
        
        tooltip_html = f"""
        <div style='font-family: sans-serif; font-size: 14px;'>
            <strong>{name}</strong><br>
            <span style='color: {color};'>● {info['status'].replace('_', ' ').title()}</span><br>
            👥 {team if team else 'Non assignée'}<br>
            📝 {info['notes']} notes
        </div>
        """
        
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
    
    # Légende festive
    legend_html = '''
    <div style="position: fixed; bottom: 50px; right: 50px; width: 220px;
                background: linear-gradient(135deg, white, #f0f0f0);
                border: 3px solid #c41e3a; border-radius: 15px; padding: 15px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0; color: #c41e3a; text-align: center;">
            🎄 Légende 🎄
        </h4>
        <div><span style="background:#165b33; width:30px; height:4px; display:inline-block;"></span> Collecte terminée</div>
        <div><span style="background:#FFD700; width:30px; height:4px; display:inline-block;"></span> En cours</div>
        <div><span style="background:#c41e3a; width:30px; height:4px; display:inline-block;"></span> À faire</div>
        <hr style="margin: 8px 0; border-color: #c41e3a;">
        <div><span style="border-bottom: 4px dashed #999; width:30px; display:inline-block;"></span> Non assignée</div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def page_export_gestionnaire(conn):
    """Section export avec formats multiples"""
    
    st.markdown("### 📊 Centre d'export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; border: 2px dashed #ccc; border-radius: 10px;">
            <h4>� Rapport PDF</h4>
            <p><small>Format professionnel pour présentation</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            from reports import ReportGenerator
            generator = ReportGenerator(conn)
            pdf_data = generator.generate_pdf()
            st.download_button(
                "📥 Télécharger PDF",
                pdf_data,
                "rapport_guignolee_2025.pdf",
                "application/pdf",
                use_container_width=True
            )
        except ImportError:
            st.button("PDF (Installer reportlab)", disabled=True, use_container_width=True)
    
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
                use_container_width=True
            )
        except:
            st.button("Excel (Non disponible)", disabled=True, use_container_width=True)
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; border: 2px dashed #ccc; border-radius: 10px;">
            <h4>📱 Liste SMS</h4>
            <p><small>Téléphones des bénévoles</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        sms_list = generate_sms_list(conn)
        st.download_button(
            "📥 Liste téléphones",
            sms_list,
            "telephones_benevoles.txt",
            "text/plain",
            use_container_width=True
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
    
    stats = db.extended_stats(conn)
    render_metrics(stats)
    
    df_all = db.list_streets(conn)
    if not df_all.empty:
        m = create_map(df_all, geo)
        st_folium(m, height=800, width=None, returned_objects=[])

def page_accueil_v2(conn, geo):
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
            <h2 style="color: #c41e3a; margin: 0;">🎉 C'EST AUJOURD'HUI!</h2>
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
    stats = db.extended_stats(conn)
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
            <div style="font-size: 3rem;">🚶</div>
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
    df_all = db.list_streets(conn)
    if not df_all.empty:
        m = create_festive_map(df_all, geo)
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

def page_benevole(conn, geo):
    """Interface bénévole moderne avec vue limitée"""
    
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        render_login_card("benevole", conn)
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
    df_team = db.list_streets(conn, team=team_id)
    if df_team.empty:
        st.warning("Aucune rue assignée. Contactez votre superviseur.")
        return
    
    done = len(df_team[df_team['status'] == 'terminee'])
    total = len(df_team)
    progress = (done / total * 100) if total > 0 else 0
    
    # Mini dashboard équipe
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📍 Vos rues", total)
    with col2:
        st.metric("✅ Complétées", done)
    with col3:
        st.metric("🎯 Progression", f"{progress:.0f}%")
    
    # Système de badges
    show_team_badges(conn, team_id)
    
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
        st.markdown("### 📋 Checklist de collecte")
        
        # Liste interactive des rues
        for _, row in df_team.iterrows():
            street = row['name']
            status = row['status']
            notes_count = row.get('notes', 0)
            
            # Carte de rue stylisée
            status_emoji = {'terminee': '✅', 'en_cours': '🚶', 'a_faire': '⭕'}
            status_color = {'terminee': '#22c55e', 'en_cours': '#f59e0b', 'a_faire': '#ef4444'}
            
            with st.expander(f"{status_emoji.get(status, '⭕')} **{street}** ({notes_count} notes)"):
                
                # Changement rapide de statut
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("⭕ À faire", key=f"todo_{street}", use_container_width=True):
                        db.set_status(conn, street, 'a_faire')
                        st.rerun()
                with col2:
                    if st.button("🚶 En cours", key=f"progress_{street}", use_container_width=True):
                        db.set_status(conn, street, 'en_cours')
                        st.rerun()
                with col3:
                    if st.button("✅ Terminée", key=f"done_{street}", use_container_width=True):
                        db.set_status(conn, street, 'terminee')
                        st.rerun()
                
                st.markdown("---")
                
                # Ajout de note rapide
                st.markdown("**Ajouter une note:**")
                with st.form(f"note_{street}", clear_on_submit=True):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        num = st.text_input("N°", placeholder="123")
                    with col2:
                        note = st.text_input("Note", placeholder="Personne absente")
                    
                    if st.form_submit_button("➕ Ajouter"):
                        if num and note:
                            db.add_note_for_address(conn, street, team_id, num, note)
                            st.success("Note ajoutée!")
                            st.rerun()
                
                # Notes existantes
                notes = db.get_street_addresses_with_notes(conn, street)
                if not notes.empty:
                    st.markdown("**Notes existantes:**")
                    for _, n in notes.iterrows():
                        st.markdown(f"• **{n['address_number']}** : {n['comment']}")
    
    with tab3:
        st.markdown("### 📊 Votre historique")
        try:
            notes = db.get_team_notes(conn, team_id)
            if not notes.empty:
                st.dataframe(notes, use_container_width=True)
            else:
                st.info("Aucune note encore")
        except:
            st.info("Historique non disponible")

def page_benevole_v2(conn, geo):
    """Interface bénévole moderne v4.1 avec vue 'Mes rues'"""
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        # Afficher la page de connexion bénévole
        return page_benevole(conn, geo)
    
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
        page_benevole_mes_rues(conn)
    
    with tabs[1]:
        # Carte traditionnelle (réutilise l'ancienne interface)
        page_benevole(conn, geo)
    
    with tabs[2]:
        # Journal d'activité de l'équipe
        st.markdown("### 📝 Journal d'activité de votre équipe")
        try:
            # Afficher les activités récentes de l'équipe
            cursor = conn.execute("""
                SELECT action, details, created_at
                FROM activity_log
                WHERE team_id = ?
                ORDER BY created_at DESC
                LIMIT 20
            """, (team_id,))
            
            activities = cursor.fetchall()
            if activities:
                for activity in activities:
                    action, details, created_at = activity
                    st.markdown(f"**{created_at}** - {action}: {details}")
            else:
                st.info("Aucune activité enregistrée pour votre équipe")
                
        except Exception as e:
            st.info("Journal d'activité temporairement indisponible")
            st.caption(f"Erreur: {e}")

def page_gestionnaire_v2(conn, geo):
    """Interface gestionnaire moderne (ancien superviseur)"""
    st.header("👔 Tableau de Bord Gestionnaire")
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "supervisor":
        render_login_card("gestionnaire", conn)
        return
    
    # Dashboard moderne
    render_dashboard_gestionnaire(conn, geo)
    
    # Tabs
    tabs = st.tabs([
        "📊 Vue d'ensemble",
        "👥 Équipes",
        "🗺️ Assignation",
        "📥 Export",
        "🛠 Tech"
    ])
    
    with tabs[0]:
        # Carte générale
        st.markdown("### Carte générale")
        df_all = db.list_streets(conn)
        if not df_all.empty:
            m = create_map(df_all, geo)
            st_folium(m, height=800, width=None, returned_objects=[])
        
        # Activité récente
        st.markdown("### Activité récente")
        try:
            recent = db.recent_activity(conn, limit=10)
            if not recent.empty:
                st.dataframe(recent, use_container_width=True)
            else:
                st.info("Aucune activité récente")
        except:
            st.info("Historique d'activité non disponible")
    
    with tabs[1]:
        # Gestion des équipes
        st.markdown("### Gestion des équipes")
        
        with st.expander("Créer une équipe"):
            with st.form("new_team", clear_on_submit=True):
                new_id = st.text_input("Identifiant")
                new_name = st.text_input("Équipe")
                new_pass = st.text_input("Mot de passe", type="password")
                
                if st.form_submit_button("Créer"):
                    if all([new_id, new_name, new_pass]):
                        if db.create_team(conn, new_id, new_name, new_pass):
                            st.success(f"Équipe {new_id} créée")
                            st.rerun()
        
        # Liste des équipes
        try:
            teams_df = db.get_all_teams(conn)
            if not teams_df.empty:
                st.dataframe(teams_df, use_container_width=True)
            else:
                st.info("Aucune équipe créée")
        except:
            st.info("Liste des équipes non disponible")
    
    with tabs[2]:
        # Assignation v4.1
        page_assignations_v41(conn)
    
    with tabs[3]:
        # Export amélioré v4.1
        page_export_gestionnaire_v41(conn)

    with tabs[4]:
        st.markdown("### 🛠 Opérations techniques (protégées)")

        # -- PIN stocké dans secrets (config.toml -> [secrets] TECH_PIN="xxxx")
        try:
            TECH_PIN = st.secrets.get("TECH_PIN", "")
        except:
            TECH_PIN = ""  # Pas de fichier secrets.toml

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
                        count = db.import_addresses_from_cache(conn, addr_cache)
                    st.success(f"✅ {count} adresses importées depuis OSM.")
                    st.rerun()
                else:
                    st.warning("Confirmation incomplète.")

        # --- Gestion des backups
        with st.expander("💾 Gestion des backups", expanded=False):
            backup_mgr = db.get_backup_manager(DB_PATH)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("🔄 Créer un backup manuel", use_container_width=True):
                    backup_file = backup_mgr.create_backup("manual")
                    if backup_file:
                        st.success(f"Backup créé : {Path(backup_file).name}")
            
            with col2:
                if st.button("📋 Voir les backups", use_container_width=True):
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
        render_login_card("superviseur", conn)
        return
    
    # Dashboard moderne
    render_dashboard_gestionnaire(conn, geo)
    
    # Tabs
    tabs = st.tabs([
        "📊 Vue d'ensemble",
        "👥 Équipes",
        "🗺️ Assignation",
        "📥 Export",
        "🛠 Tech"
    ])
    
    with tabs[0]:
        # Carte générale
        st.markdown("### Carte générale")
        df_all = db.list_streets(conn)
        if not df_all.empty:
            m = create_map(df_all, geo)
            st_folium(m, height=800, width=None, returned_objects=[])
        
        # Activité récente
        st.markdown("### Activité récente")
        recent = db.recent_activity(conn, limit=10)
        if not recent.empty:
            st.dataframe(recent, use_container_width=True)
    
    with tabs[1]:
        # Gestion des équipes
        st.markdown("### Gestion des équipes")
        
        with st.expander("Créer une équipe"):
            with st.form("new_team", clear_on_submit=True):
                new_id = st.text_input("Identifiant")
                new_name = st.text_input("Équipe")
                new_pass = st.text_input("Mot de passe", type="password")
                
                if st.form_submit_button("Créer"):
                    if all([new_id, new_name, new_pass]):
                        if db.create_team(conn, new_id, new_name, new_pass):
                            st.success(f"Équipe {new_id} créée")
                            st.rerun()
        
        # Liste des équipes
        teams_df = db.get_all_teams(conn)
        if not teams_df.empty:
            st.dataframe(teams_df, use_container_width=True)
    
    with tabs[2]:
        # Assignation
        st.markdown("### Assignation des rues")
        
        unassigned = db.get_unassigned_streets(conn)
        
        if not unassigned.empty:
            with st.form("assign"):
                team = st.selectbox("Équipe", db.teams(conn))
                streets = st.multiselect("Rues", unassigned['name'].tolist())
                
                if st.form_submit_button("Assigner"):
                    if team and streets:
                        db.assign_streets_to_team(conn, streets, team)
                        st.success("Rues assignées!")
                        st.rerun()
        else:
            st.success("Toutes les rues sont assignées!")
        
        # Tableau des assignations
        df_all = db.list_streets(conn)
        if not df_all.empty:
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
                "📥 Export rues (CSV)",
                db.export_to_csv(conn),
                "rapport_rues.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            st.download_button(
                "📥 Export notes (CSV)",
                db.export_notes_csv(conn),
                "rapport_notes.csv",
                "text/csv",
                use_container_width=True
            )

    with tabs[4]:
        st.markdown("### 🛠 Opérations techniques (protégées)")

        # -- PIN stocké dans secrets (config.toml -> [secrets] TECH_PIN="xxxx")  
        try:
            TECH_PIN = st.secrets.get("TECH_PIN", "")
        except:
            TECH_PIN = ""  # Pas de fichier secrets.toml

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
                        count = db.import_addresses_from_cache(conn, addr_cache)
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

def page_assignations_v41(conn):
    """Panneau d'assignations v4.1 pour superviseurs"""
    st.markdown("### 🗺️ Assignations par secteur")
    
    try:
        # Compteur de rues non assignées
        unassigned_count = db.get_unassigned_streets_count(conn)
        if unassigned_count > 0:
            st.warning(f"⚠️ {unassigned_count} rue(s) non assignée(s)")
        else:
            st.success("✅ Toutes les rues sont assignées")
        
        # Panneau d'assignation en bloc par secteur
        with st.expander("🎯 Assignation par secteur", expanded=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # Selectbox secteur
                sectors = db.get_sectors_list(conn)
                if sectors:
                    selected_sector = st.selectbox(
                        "Secteur à assigner",
                        [""] + sectors,
                        help="Choisir un secteur pour l'assignation en bloc"
                    )
                else:
                    st.info("Aucun secteur disponible")
                    selected_sector = ""
            
            with col2:
                # Selectbox équipe
                teams = db.get_teams_list(conn)
                if teams:
                    team_options = [""] + [f"{team[1]} ({team[0]})" for team in teams]
                    selected_team_display = st.selectbox(
                        "Équipe destinataire",
                        team_options,
                        help="Équipe qui recevra toutes les rues du secteur"
                    )
                    
                    # Extraire l'ID de l'équipe
                    selected_team = ""
                    if selected_team_display and selected_team_display != "":
                        selected_team = selected_team_display.split("(")[-1].rstrip(")")
                else:
                    st.info("Aucune équipe disponible")
                    selected_team = ""
            
            with col3:
                st.markdown("&nbsp;")  # Espacement
                if st.button(
                    "🎯 Assigner tout le secteur",
                    disabled=not (selected_sector and selected_team),
                    use_container_width=True,
                    help="Assigne toutes les rues non assignées du secteur à l'équipe choisie"
                ):
                    if selected_sector and selected_team:
                        try:
                            affected_rows = db.bulk_assign_sector(conn, selected_sector, selected_team)
                            if affected_rows > 0:
                                st.toast(f"✅ Assignation effectuée: {affected_rows} rue(s)", icon="🎉")
                                st.rerun()
                            else:
                                st.toast("ℹ️ Aucune rue non assignée dans ce secteur", icon="ℹ️")
                        except Exception as e:
                            st.error(f"Erreur lors de l'assignation: {e}")
        
        # Tableau des assignations actuelles
        st.markdown("### 📋 État des assignations")
        df_all = db.list_streets(conn)
        if not df_all.empty:
            # Ajouter des couleurs selon le statut
            def color_status(val):
                if val == 'terminee':
                    return 'background-color: #d4edda'
                elif val == 'en_cours':
                    return 'background-color: #fff3cd'
                elif val == 'a_faire':
                    return 'background-color: #f8d7da'
                return ''
            
            # Afficher le tableau avec style
            styled_df = df_all[['name', 'sector', 'team', 'status']].style.applymap(
                color_status, subset=['status']
            )
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("Aucune rue trouvée")
            
    except Exception as e:
        st.error(f"Erreur dans le panneau d'assignations: {e}")
        st.info("Fonctionnalité temporairement indisponible")

def page_export_gestionnaire_v41(conn):
    """Page d'export v4.1 avec nouvelles fonctionnalités"""
    st.markdown("### 📥 Export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV standard
        try:
            st.download_button(
                "📥 Export CSV Standard",
                db.export_to_csv(conn),
                "rapport_rues.csv",
                "text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.button("📥 CSV (Erreur)", disabled=True, use_container_width=True)
            st.caption(f"Erreur: {e}")
    
    with col2:
        # Export Excel professionnel
        try:
            from reports import ReportGenerator
            generator = ReportGenerator(conn)
            excel_data = generator.generate_excel()
            st.download_button(
                "📊 Export Excel Pro",
                excel_data,
                "guignolee_2025_rapport.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except ImportError:
            st.button("📊 Excel (Installer xlsxwriter)", disabled=True, use_container_width=True)
        except Exception as e:
            st.button("📊 Excel (Erreur)", disabled=True, use_container_width=True)
            st.caption(f"Erreur: {e}")
    
    with col3:
        # Export PDF professionnel
        try:
            from reports import ReportGenerator
            generator = ReportGenerator(conn)
            pdf_data = generator.generate_pdf()
            st.download_button(
                "📄 Export PDF Pro",
                pdf_data,
                "guignolee_2025_rapport.pdf",
                "application/pdf",
                use_container_width=True
            )
        except ImportError:
            st.button("📄 PDF (Installer reportlab)", disabled=True, use_container_width=True)
        except Exception as e:
            st.button("📄 PDF (Erreur)", disabled=True, use_container_width=True)
            st.caption(f"Erreur: {e}")
    
    # Export CSV assignations (nouveau v4.1)
    st.markdown("---")
    st.markdown("### 📋 Export spécialisés v4.1")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV assignations
        try:
            assignations_data = db.get_assignations_export_data(conn)
            if not assignations_data.empty:
                csv_data = assignations_data.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    "📋 Export CSV Assignations",
                    csv_data,
                    "assignations_secteurs.csv",
                    "text/csv",
                    use_container_width=True,
                    help="Colonnes: secteur, rue, équipe, statut"
                )
            else:
                st.button("📋 Assignations (Aucune donnée)", disabled=True, use_container_width=True)
        except Exception as e:
            st.button("📋 Assignations (Erreur)", disabled=True, use_container_width=True)
            st.caption(f"Erreur: {e}")
    
    with col2:
        # Export notes
        try:
            st.download_button(
                "📝 Export Notes",
                db.export_notes_csv(conn),
                "rapport_notes.csv",
                "text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.button("📝 Notes (Erreur)", disabled=True, use_container_width=True)
            st.caption(f"Erreur: {e}")

def page_benevole_mes_rues(conn):
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
        team_streets = db.get_team_streets(conn, team_id)
        
        if team_streets.empty:
            st.info("Aucune rue assignée à votre équipe pour le moment.")
            return
        
        # Afficher les statistiques de l'équipe
        total_streets = len(team_streets)
        done_streets = len(team_streets[team_streets['status'] == 'terminee'])
        in_progress = len(team_streets[team_streets['status'] == 'en_cours'])
        
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
        for _, street in team_streets.iterrows():
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
                        "🚀 En cours", 
                        key=f"progress_{street_name}",
                        disabled=current_status == 'en_cours',
                        use_container_width=True
                    ):
                        if db.update_street_status(conn, street_name, 'en_cours', team_id):
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
                        use_container_width=True
                    ):
                        if db.update_street_status(conn, street_name, 'terminee', team_id):
                            st.toast(f"🎉 {street_name} terminée!", icon="🎉")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la mise à jour")
                
                # Section notes
                st.markdown("**Gestion des notes:**")
                
                # Afficher les notes existantes
                existing_notes = db.get_street_notes_for_team(conn, street_name, team_id)
                if existing_notes:
                    st.markdown("*Notes existantes:*")
                    for note in existing_notes:
                        st.markdown(f"• **#{note[0]}** : {note[1]} _{note[2]}_")
                
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
                    
                    if st.form_submit_button("💾 Enregistrer note"):
                        if address_number and comment:
                            if db.add_street_note(conn, street_name, team_id, address_number, comment):
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
    conn = db.get_conn(DB_PATH)
    db.init_db(conn)
    st.session_state['conn'] = conn
    
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
        if st.button("🏠 Accueil", use_container_width=True):
            st.session_state.page = "accueil"
            st.rerun()
        
        if st.button("🎅 Bénévole", use_container_width=True):
            st.session_state.page = "benevole"
            st.rerun()
            
        if st.button("👔 Gestionnaire", use_container_width=True):
            st.session_state.page = "gestionnaire"  
            st.rerun()
        
        # Déconnexion si connecté
        if st.session_state.auth:
            st.markdown("---")
            if st.button("🚪 Déconnexion", use_container_width=True):
                st.session_state.auth = None
                st.rerun()
        
        # Compteur temps réel
        st.markdown("---")
        stats = db.extended_stats(conn)
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
        page_accueil_v2(conn, geo)
    elif page == "benevole":
        page_benevole_v2(conn, geo)
    elif page == "gestionnaire":
        page_gestionnaire_v2(conn, geo)
    
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
            <small>Ensemble, redonnons espoir | 📞 450-474-4133</small>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Bannière en bas de page
    if (ASSETS / "banner.png").exists():
        st.image(str(ASSETS / "banner.png"), use_column_width=True)

if __name__ == "__main__":
    main()
