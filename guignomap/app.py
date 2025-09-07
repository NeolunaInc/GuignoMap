# Fichier : guignomap/app.py (Version 2.1 - Finale)

from pathlib import Path
import time
from datetime import datetime
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# Import de nos modules locaux
import db
from osm import build_geometry_cache, load_geometry_cache

# --- CONSTANTES ET CONFIGURATION ---
DB_PATH = Path(__file__).parent / "guigno_map.db"
ASSETS = Path(__file__).parent / "assets"

st.set_page_config(
    page_title="Guigno-Map | Relais de Mascouche",
    page_icon="🎁",
    layout="wide"
)

if "auth" not in st.session_state:
    st.session_state.auth = None

# ---------- COMPOSANTS ET STYLES ----------
def inject_css():
    try:
        css_file = ASSETS / "styles.css"
        if css_file.exists():
            st.markdown(f"<style>{css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erreur lors du chargement du CSS : {e}")

def render_header():
    logo_path = ASSETS / "logo.png"
    st.markdown('<div class="brand-header">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 6, 2], vertical_alignment="center")
    with c1:
        if logo_path.exists():
            st.image(str(logo_path), width=80)
    with c2:
        st.markdown('<div class="brand-title">Guigno-Map</div>', unsafe_allow_html=True)
        st.markdown('<p class="brand-sub">Suivi en temps réel de la collecte — Le Relais de Mascouche</p>', unsafe_allow_html=True)
    with c3:
        # CORRECTION AVERTISSEMENT
        st.link_button("💝 Faire un don", "https://www.relaismascouche.org/", width='stretch')
    st.markdown('</div>', unsafe_allow_html=True)

def render_metrics(stats):
    progress = (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Rues", stats['total'])
    with col2: st.metric("Rues Terminées", stats['done'])
    with col3: st.metric("En Cours", stats.get('partial', 0))
    with col4: st.metric("Progression", f"{progress:.1f}%")

def create_map(df, geo):
    center = [45.743, -73.599]
    m = folium.Map(location=center, zoom_start=13, tiles="CartoDB positron", control_scale=True)
    street_info = {row['name']: row for index, row in df.iterrows()}
    for name, paths in geo.items():
        info = street_info.get(name)
        if info is None: continue
        status_styles = {'terminee': {'color': '#22c55e', 'opacity': 0.9}, 'en_cours': {'color': '#f59e0b', 'opacity': 0.9}, 'a_faire': {'color': '#ef4444', 'opacity': 0.7}}
        style = status_styles.get(info['status'], {'color': '#9ca3af', 'opacity': 0.5})
        tooltip_html = f"<strong>{name}</strong><br>Statut: {info['status'].replace('_', ' ').title()}<br>Équipe: {info['team'] or 'N/A'}<br>Notes: {info.get('notes', 0)}"
        for path in paths:
            # CORRECTION CARTE
            folium.PolyLine(path, color=style['color'], weight=4, opacity=style['opacity'], tooltip=folium.Tooltip(tooltip_html, sticky=True)).add_to(m)
    st_folium(m, height=600, width=None, returned_objects=[])

# ---------- PAGES DE L'APPLICATION ----------
def page_accueil(conn, geo):
    st.markdown("### 🎁 Bienvenue sur Guigno-Map !")
    st.info("Sélectionnez votre portail dans le menu de gauche pour commencer.")
    st.markdown("---")
    st.markdown("#### 📊 Aperçu de la collecte")
    stats = db.extended_stats(conn)
    render_metrics(stats)
    df_all = db.list_streets(conn)
    create_map(df_all, geo)

def page_benevole(conn, geo):
    st.header("👥 Espace Bénévole")
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        with st.form("login_volunteer"):
            team_id = st.text_input("Code d'équipe")
            password = st.text_input("Mot de passe", type="password")
            # CORRECTION AVERTISSEMENT
            if st.form_submit_button("Se connecter", width='stretch'):
                if db.verify_team(conn, team_id, password):
                    st.session_state.auth = {"role": "volunteer", "team_id": team_id}
                    st.success("Connexion réussie !"); time.sleep(1); st.rerun()
                else: st.error("Identifiants incorrects.")
        return

    team_id = st.session_state.auth["team_id"]
    st.subheader(f"Tournée de l'équipe : {team_id}")
    df_team_streets = db.list_streets(conn, team=team_id)

    if df_team_streets.empty: st.info("Aucune rue ne vous est assignée."); return

    selected_street = st.selectbox("Sélectionnez une rue à traiter", df_team_streets['name'])
    if selected_street:
        with st.container(border=True):
            st.markdown(f"#### Traitement de : **{selected_street}**")
            with st.form(key=f"note_form_{selected_street}", clear_on_submit=True):
                c1,c2 = st.columns([1,3]); address_num = c1.text_input("N°"); comment = c2.text_input("Commentaire")
                if st.form_submit_button("Ajouter la note") and comment:
                    db.add_note_for_address(conn, selected_street, team_id, address_num, comment)
                    st.success(f"Note ajoutée."); time.sleep(1); st.rerun()
            notes_df = db.get_street_addresses_with_notes(conn, selected_street)
            if not notes_df.empty: st.dataframe(notes_df[['address_number', 'comment', 'created_at']], use_container_width=True)
            current_status = df_team_streets[df_team_streets['name'] == selected_street]['status'].iloc[0]
            st.radio("Marquer la rue comme :", ['a_faire', 'en_cours', 'terminee'], index=['a_faire', 'en_cours', 'terminee'].index(current_status), key=f"status_{selected_street}", horizontal=True, on_change=db.set_status, args=(conn, selected_street, st.session_state[f"status_{selected_street}"]))

def page_superviseur(conn, geo):
    st.header("🎯 Tableau de Bord Superviseur")
    if not st.session_state.auth or st.session_state.auth.get("role") != "supervisor":
        with st.form("login_supervisor"):
            password = st.text_input("Mot de passe Superviseur", type="password")
            if st.form_submit_button("Accéder"):
                if db.verify_team(conn, "ADMIN", password):
                    st.session_state.auth = {"role": "supervisor", "team_id": "ADMIN"}
                    st.success("Accès autorisé."); time.sleep(1); st.rerun()
                else: st.error("Mot de passe incorrect.")
        return

    tabs = st.tabs(["📊 Vue d'ensemble", "👥 Équipes", "🗺️ Assignation", "⚙️ Export & Données"])
    with tabs[0]: render_metrics(db.extended_stats(conn)); st.markdown("### Carte générale"); create_map(db.list_streets(conn), geo); st.markdown("### Activité récente"); st.dataframe(db.recent_activity(conn, limit=10), use_container_width=True)
    with tabs[1]:
        st.markdown("### Gestion des équipes")
        with st.expander("➕ Créer une nouvelle équipe"):
            with st.form("new_team_form", clear_on_submit=True):
                new_id=st.text_input("Code"); new_name=st.text_input("Nom"); new_pass=st.text_input("Passe", type="password")
                if st.form_submit_button("Créer"):
                    if all([new_id,new_name,new_pass]) and db.create_team(conn, new_id, new_name, new_pass):
                        st.success(f"Équipe {new_id} créée."); time.sleep(1); st.rerun()
                    else: st.error("Code déjà existant ou champs vides.")
        st.markdown("#### Équipes actives"); st.dataframe(db.get_all_teams(conn), use_container_width=True)
    with tabs[2]:
        st.markdown("### Assignation des rues")
        unassigned_df = db.get_unassigned_streets(conn)
        if unassigned_df.empty: st.success("Toutes les rues sont assignées !")
        else:
            with st.form("assign_form"):
                team_to_assign = st.selectbox("Choisir équipe", db.teams(conn))
                streets_to_assign = st.multiselect("Choisir rues", unassigned_df['name'])
                if st.form_submit_button("Assigner"):
                    if team_to_assign and streets_to_assign:
                        db.assign_streets_to_team(conn, streets_to_assign, team_to_assign)
                        st.success(f"Rues assignées."); time.sleep(1); st.rerun()
    with tabs[3]:
        st.markdown("### Export & Données Brutes")
        # CORRECTION AVERTISSEMENT
        st.download_button("📥 Exporter rapport des rues (CSV)", db.export_to_csv(conn), "rapport_rues.csv", "text/csv", width='stretch')
        st.download_button("📥 Exporter rapport des notes (CSV)", db.export_notes_csv(conn), "rapport_notes.csv", "text/csv", width='stretch')
        with st.expander("Gérer les données OpenStreetMap"):
            if st.button("🗺️ Rafraîchir le cache des géométries"):
                with st.spinner("Construction du cache..."): build_geometry_cache()
                st.success("Cache mis à jour !"); time.sleep(1); st.rerun()

def main():
    inject_css()
    render_header()
    conn = db.get_conn(DB_PATH)
    db.init_db(conn)
    @st.cache_data(ttl=3600)
    def get_geo_data():
        cache = load_geometry_cache();
        if not cache: build_geometry_cache(); return load_geometry_cache()
        return cache
    geo = get_geo_data()

    with st.sidebar:
        if st.session_state.auth:
            role = st.session_state.auth.get("role", "").title(); team_id = st.session_state.auth.get("team_id", "")
            st.success(f"Connecté: **{role} ({team_id})**")
            # CORRECTION AVERTISSEMENT
            if st.button("Se déconnecter", width='stretch'):
                st.session_state.auth = None; st.rerun()
        page = st.radio("Portails", ["🏠 Accueil", "👥 Bénévole", "🎯 Superviseur"], label_visibility="collapsed")
        if st.toggle("🔄 Auto-refresh (15s)"): time.sleep(15); st.rerun()

    page_map = {"🏠 Accueil": page_accueil, "👥 Bénévole": page_benevole, "🎯 Superviseur": page_superviseur}
    page_map[page](conn, geo)

if __name__ == "__main__":
    main()