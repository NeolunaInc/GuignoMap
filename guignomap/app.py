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
    if role == "superviseur":
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 3rem;">👔</div>
            <h2 style="color: #FFD700; margin: 1rem 0;">Espace Superviseur</h2>
            <p style="color: #cbd5e1;">Gérez la collecte et les équipes</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_superviseur", clear_on_submit=False):
            password = st.text_input(
                "🔐 Mot de passe",
                type="password",
                placeholder="Entrez le mot de passe superviseur"
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
                    st.success("✅ Bienvenue dans l'espace superviseur!")
                    st.balloons()
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
        Besoin d'aide? Contactez votre superviseur<br>
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
        st_folium(m, height=600, width=None, returned_objects=[])

def page_benevole(conn, geo):
    """Interface bénévole"""
    st.header("👥 Espace Bénévole")
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        render_login_card("benevole", conn)
        return
    
    # Interface connectée
    team_id = st.session_state.auth["team_id"]
    st.subheader(f"Équipe: {team_id}")
    
    df_team = db.list_streets(conn, team=team_id)
    
    if df_team.empty:
        st.info("Aucune rue assignée à votre équipe.")
        return
    
    # Sélection de la rue
    selected_street = st.selectbox(
        "Sélectionner une rue",
        df_team['name'].tolist()
    )
    
    if selected_street:
        st.markdown("---")
        st.markdown(f"#### 📍 {selected_street}")
        
        # Formulaire pour notes
        with st.form(f"note_{selected_street}", clear_on_submit=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                address = st.text_input("N° civique")
            with col2:
                comment = st.text_area("Commentaire", height=100)
            
            if st.form_submit_button("Ajouter la note"):
                if address and comment:
                    db.add_note_for_address(conn, selected_street, team_id, address, comment)
                    st.success("Note ajoutée!")
                    st.rerun()
        
        # Changement de statut
        current_status = df_team[df_team['name'] == selected_street]['status'].iloc[0]
        
        new_status = st.radio(
            "Statut de la rue",
            ['a_faire', 'en_cours', 'terminee'],
            index=['a_faire', 'en_cours', 'terminee'].index(current_status),
            format_func=lambda x: x.replace('_', ' ').title(),
            horizontal=True
        )
        
        if st.button("Mettre à jour le statut"):
            db.set_status(conn, selected_street, new_status)
            st.success("Statut mis à jour!")
            st.rerun()
        
        # Notes existantes
        notes = db.get_street_addresses_with_notes(conn, selected_street)
        if not notes.empty:
            st.markdown("#### Notes existantes")
            st.dataframe(notes[['address_number', 'comment', 'created_at']], use_container_width=True)

def page_superviseur(conn, geo):
    """Interface superviseur"""
    st.header("🎯 Tableau de Bord Superviseur")
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "supervisor":
        render_login_card("superviseur", conn)
        return
    
    # Métriques
    stats = db.extended_stats(conn)
    render_metrics(stats)
    
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
            st_folium(m, height=600, width=None, returned_objects=[])
        
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
        TECH_PIN = st.secrets.get("TECH_PIN", "")

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

def main():
    """Point d'entrée principal"""
    
    # CSS
    inject_css()
    
    # Header
    render_header()
    
    # DB
    conn = db.get_conn(DB_PATH)
    db.init_db(conn)
    
    # Cache géométrique avec gestion d'erreur améliorée
    @st.cache_data(ttl=None)
    def get_geo(_sig):
        try:
            geo_data = load_geometry_cache()
            if not geo_data:
                st.warning("⚠️ Cache géométrique vide. Utilisez l'onglet Tech pour reconstruire.")
                return {}
            return geo_data
        except Exception as e:
            st.error(f"Erreur chargement cache: {e}")
            return {}

    sig = int(CACHE_FILE.stat().st_mtime_ns) if CACHE_FILE.exists() else 0
    geo = get_geo(sig)
    
    # Vérifier l'intégrité des données au démarrage
    if not geo:
        st.warning("""
        ⚠️ **Aucune donnée géométrique disponible**
        
        Pour initialiser l'application :
        1. Allez dans **Superviseur** → **Onglet Tech**
        2. Lancez **Reconstruire cache OSM**
        """)
    
    # Sidebar
    with st.sidebar:
        if st.session_state.auth:
            role = st.session_state.auth.get("role", "").replace("_", " ").title()
            team = st.session_state.auth.get("team_id", "")
            st.success(f"**{role}** ({team})")
            
            if st.button("Se déconnecter", use_container_width=True):
                st.session_state.auth = None
                st.rerun()
        
        page = st.radio(
            "Navigation",
            ["🏠 Accueil", "👥 Bénévole", "🎯 Superviseur"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        if st.toggle("🔄 Auto-refresh (15s)"):
            time.sleep(15)
            st.rerun()
        
        # Infos
        st.markdown(f"""
        **Version:** 3.0  
        **MAJ:** {datetime.now().strftime('%H:%M')}  
        **Rues:** {len(geo)}
        """)
    
    # Routing
    if page == "🏠 Accueil":
        page_accueil(conn, geo)
    elif page == "👥 Bénévole":
        page_benevole(conn, geo)
    elif page == "🎯 Superviseur":
        page_superviseur(conn, geo)

if __name__ == "__main__":
    main()