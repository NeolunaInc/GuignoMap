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
    """Header avec logo et bannière si disponibles"""
    st.markdown('<div class="brand-header">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 6, 2])
    
    with col1:
        logo_file = ASSETS / "logo.png"
        if logo_file.exists():
            st.image(str(logo_file), width=80)
    
    with col2:
        st.markdown("""
        <div class="brand-title">Guigno-Map</div>
        <p class="brand-sub">Suivi en temps réel de la collecte — Le Relais de Mascouche</p>
        """, unsafe_allow_html=True)
    
    with col3:
        st.link_button(
            "💝 Faire un don",
            "https://www.relaismascouche.org/",
            use_container_width=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Bannière si disponible
    banner_file = ASSETS / "banner.png"
    if banner_file.exists():
        st.image(str(banner_file), width=None)

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
    """Crée la carte Folium avec les rues"""
    # Centre de Mascouche
    center = [45.7475, -73.6005]
    
    # Créer la carte
    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles="CartoDB positron",
        control_scale=True
    )
    
    # Vérifier qu'on a des données
    if not geo or df.empty:
        st.warning("Aucune donnée géométrique disponible")
        return m
    
    # Construction robuste du lookup avec gestion correcte des colonnes
    street_info = {}
    for idx, row in df.iterrows():
        name = str(row['name']) if 'name' in df.columns else str(row.get('name', ''))
        
        # Gestion sûre des colonnes qui peuvent ne pas exister
        status = 'a_faire'
        if 'status' in df.columns:
            status = row['status'] if pd.notna(row['status']) else 'a_faire'
        
        team = ''
        if 'team' in df.columns:
            team = row['team'] if pd.notna(row['team']) else ''
        
        notes = ''
        if 'notes' in df.columns:
            notes = str(row['notes']) if pd.notna(row['notes']) else ''
        
        street_info[name] = {
            'status': status,
            'team': team,
            'notes': notes
        }
    
    # Couleurs par statut
    status_colors = {
        'terminee': '#22c55e',
        'en_cours': '#f59e0b', 
        'a_faire': '#ef4444'
    }
    
    # Ajouter les rues
    for name, paths in geo.items():
        # Cherche l'info DB; si absente → défaut "a_faire" sans équipe
        info = street_info.get(name, {'status': 'a_faire', 'team': '', 'notes': ''})
        
        status = info.get('status', 'a_faire')
        team = info.get('team', '')
        
        # Nettoyer team (gérer NaN, None, etc.)
        if team is None or (isinstance(team, float) and pd.isna(team)):
            team = ''
        team = str(team).strip() if team else ''
        
        notes = info.get('notes', '')
        
        # Déterminer la couleur et style
        color = status_colors.get(status, '#ef4444')
        opacity = 0.8 if team else 0.6
        dash = None if team else '5,7'
        
        # Tooltip
        tooltip_html = f"""
        <strong>{name}</strong><br>
        Statut: {status.replace('_', ' ').title()}<br>
        Équipe: {team if team else 'Non assignée'}<br>
        Notes: {notes}
        """
        
        # Ajouter chaque segment
        for path in paths:
            if path and len(path) >= 2:
                folium.PolyLine(
                    path,
                    color=color,
                    weight=5,
                    opacity=opacity,
                    dash_array=dash,
                    tooltip=folium.Tooltip(tooltip_html, sticky=True)
                ).add_to(m)
    
    # Cadrer la carte sur toutes les lignes ajoutées
    all_pts = [pt for paths in geo.values() for path in paths for pt in (path or [])]
    if all_pts:
        lats = [p[0] for p in all_pts]
        lons = [p[1] for p in all_pts]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    
    # Légende
    legend_html = '''
    <div style="position: fixed; bottom: 50px; right: 50px; width: 180px;
                background: white; z-index:9999; font-size:14px;
                border: 2px solid grey; border-radius: 10px; padding: 10px">
        <strong>Légende</strong><br>
        <span style="background:#22c55e; width:20px; height:10px; display:inline-block;"></span> Terminée<br>
        <span style="background:#f59e0b; width:20px; height:10px; display:inline-block;"></span> En cours<br>
        <span style="background:#ef4444; width:20px; height:10px; display:inline-block;"></span> À faire<br>
        <em>Les rues non assignées apparaissent en pointillés</em>
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
        with st.form("login_volunteer"):
            col1, col2 = st.columns(2)
            with col1:
                team_id = st.text_input("Code d'équipe")
            with col2:
                password = st.text_input("Mot de passe", type="password")
            
            if st.form_submit_button("Se connecter", use_container_width=True):
                if db.verify_team(conn, team_id, password):
                    st.session_state.auth = {"role": "volunteer", "team_id": team_id}
                    st.success("✅ Connexion réussie!")
                    st.rerun()
                else:
                    st.error("❌ Identifiants incorrects")
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
        with st.form("login_supervisor"):
            password = st.text_input("Mot de passe superviseur", type="password")
            
            if st.form_submit_button("Accéder", use_container_width=True):
                if db.verify_team(conn, "ADMIN", password):
                    st.session_state.auth = {"role": "supervisor", "team_id": "ADMIN"}
                    st.success("✅ Accès autorisé")
                    st.rerun()
                else:
                    st.error("❌ Mot de passe incorrect")
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
                new_id = st.text_input("Code")
                new_name = st.text_input("Nom")
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