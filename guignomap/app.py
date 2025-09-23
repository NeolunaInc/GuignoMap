import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
# ================= Navigation unifiée (append-only, stable keys) =============
def create_simple_map(conn):
    """Carte basique avec marqueurs pour les rues géocodées"""
    import folium
    import pandas as pd
    # Centre de Mascouche
    m = folium.Map(location=[45.7475, -73.6005], zoom_start=12)
    # Récupérer quelques rues avec GPS pour affichage
    query = """
        SELECT 
            s.name as rue,
            s.status,
            AVG(a.latitude) as lat,
            AVG(a.longitude) as lon,
            COUNT(a.id) as nb_addr
        FROM streets s
        JOIN addresses a ON s.name = a.street_name
        WHERE a.latitude IS NOT NULL
        GROUP BY s.name
        LIMIT 100
    """
    df = pd.read_sql_query(query, conn)
    if not df.empty:
        for _, row in df.iterrows():
            color = 'green' if row['status'] == 'terminee' else 'red'
            folium.Marker(
                [row['lat'], row['lon']],
                popup=f"{row['rue']} ({row['nb_addr']} adresses)",
                icon=folium.Icon(color=color)
            ).add_to(m)
    else:
        # Si pas de GPS, au moins un marqueur au centre
        folium.Marker(
            [45.7475, -73.6005],
            popup="Centre de Mascouche - Géocodage en cours",
            icon=folium.Icon(color='blue')
        ).add_to(m)
    return m
def render_nav():
    import streamlit as st
    nav = {
        "nav_accueil": "Accueil",
        "nav_benevole": "Bénévole",
        "nav_carte": "Carte",
        "nav_gestion": "Gestionnaire"
    }
    for key, label in nav.items():
        if st.button(f" {label}", key=key, use_container_width=True):
            st.session_state.page = label.lower()
            st.rerun()

# ================= Correction des keys dans les boutons en boucle ============
def safe_button(label, base_key, use_container_width=True):
    import streamlit as st
    return st.button(label, key=base_key, use_container_width=use_container_width)

# ================= Remplacement navigation dans main_with_carte =============
def main_with_carte():
    # ...existing code...
    conn = db.get_conn(DB_PATH)
    db.init_db(conn)
    st.session_state['conn'] = conn
    geo = {}
    render_header()
    # Phase 2 — router unifié
    with st.sidebar:
        nav_choice = st.radio(
            "Navigation",
            options=["Accueil", "Carte", "Bénévole"],
            key="nav_radio"
        )
        # Ancien groupe de boutons conservé mais commenté :
        # render_nav()
        # if st.button(" Accueil", width="stretch"):
        #     st.session_state.page = "accueil"
        #     st.rerun()
        # if st.button(" Bénévole", width="stretch"):
        #     st.session_state.page = "benevole"
        #     st.rerun()
        # if st.button(" Carte", width="stretch"):
        #     st.session_state.page = "carte"
        #     st.rerun()
        # if st.button(" Gestionnaire", width="stretch"):
        #     st.session_state.page = "gestionnaire"
        #     st.rerun()
    # Routing selon le choix radio
    try:
        if nav_choice == "Accueil":
            page_accueil_v2(conn, geo)
        elif nav_choice == "Carte":
            page_carte(conn)
        elif nav_choice == "Bénévole":
            page_benevole_table(conn)
    except Exception as e:
        st.error(f"Erreur lors du routage : {e}")

# --- Correction des keys pour les boutons générés en boucle (exemple) ---
# Remplacez st.button(label, key=...) par safe_button(label, base_key, use_container_width=True)
# Exemple dans page_carte(conn) ou page_benevole_simple :
# for i, row in enumerate(df.iterrows()):
#     safe_button("En cours", f"start-{row['id']}")
def page_carte(conn):
    # --- Append-only, robust ---
    import pandas as pd
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import MarkerCluster
    st.header("Carte des rues — Guignolée")
    # Chargement points depuis DB
    points = []
    df = None
    try:
        if hasattr(conn, 'execute'):
            try:
                df = pd.read_sql_query("SELECT * FROM streets", conn)
            except Exception:
                df = None
        if df is None or df.empty:
            # Fallback Excel
            try:
                df = pd.read_excel("import/nocivique_cp_complement.xlsx")
            except Exception:
                df = pd.DataFrame()
        # Construction des points
        if not df.empty:
            lat_col = next((c for c in df.columns if c.lower().startswith("lat")), None)
            lon_col = next((c for c in df.columns if c.lower().startswith("lon")), None)
            name_col = next((c for c in df.columns if "name" in c.lower() or "adresse" in c.lower()), None)
            status_col = next((c for c in df.columns if "stat" in c.lower()), None)
            team_col = next((c for c in df.columns if "team" in c.lower()), None)
            sector_col = next((c for c in df.columns if "sector" in c.lower()), None)
            for _, row in df.iterrows():
                lat = row.get(lat_col, None)
                lon = row.get(lon_col, None)
                label = row.get(name_col, "")
                statut = row.get(status_col, None) if status_col else None
                equipe = row.get(team_col, None) if team_col else None
                secteur = row.get(sector_col, None) if sector_col else None
                if pd.notnull(lat) and pd.notnull(lon):
                    points.append({
                        "lat": lat,
                        "lon": lon,
                        "label": label,
                        "statut": statut,
                        "equipe": equipe,
                        "secteur": secteur
                    })
    except Exception as e:
        st.warning(f"Erreur chargement points: {e}")
        points = []

    # Filtres Streamlit
    statuts = ["a_faire", "en_cours", "terminee"]
    statut_labels = {"a_faire": "À faire", "en_cours": "En cours", "terminee": "Terminée"}
    try:
        statut_choices = st.multiselect("Statut", options=statuts, default=statuts, format_func=lambda x: statut_labels.get(x, x) or str(x))
        equipes = sorted(set(p["equipe"] for p in points if p["equipe"]))
        secteurs = sorted(set(p["secteur"] for p in points if p["secteur"]))
        equipe_choices = st.multiselect("Équipe", options=equipes, default=equipes) if equipes else None
        secteur_choices = st.multiselect("Secteur", options=secteurs, default=secteurs) if secteurs else None
        # Filtrage
        filtered = [p for p in points if (not p["statut"] or p["statut"] in statut_choices)
                    and (not equipe_choices or not p["equipe"] or p["equipe"] in equipe_choices)
                    and (not secteur_choices or not p["secteur"] or p["secteur"] in secteur_choices)]
        with st.sidebar:
            nav_choice = st.radio(
                "Navigation",
                options=["Accueil", "Carte", "Bénévole"],
                key="nav_radio"
            )
            # Ancien groupe de boutons conservé mais commenté :
            # render_nav()
            # if st.button(" Accueil", width="stretch"):
            #     st.session_state.page = "accueil"
            #     st.rerun()
            # --- Affichage DataFrame filtré (append-only) ---
            import pandas as pd
            df_affiche = pd.DataFrame(filtered)
            st.dataframe(df_affiche)

            # === EXPORTS: Excel + PDF (append-only) ======================================
            try:
                from guignomap.export_utils import df_to_excel_bytes, df_to_pdf_bytes
                EXPORTS_OK = True
            except Exception:
                EXPORTS_OK = False

            def _render_export_buttons(df_affiche: "pd.DataFrame", export_basename: str = "export_carte"):
                import streamlit as st
                if not EXPORTS_OK:
                    st.info("Exports désactivés (module d’export manquant).")
                    return

                if df_affiche is None or df_affiche.empty:
                    st.info("Rien à exporter (table vide).")
                    return

                # Limite les colonnes à celles qui ont du sens pour le partage
                cols = [c for c in df_affiche.columns if c.lower() not in {"notes_raw", "internal_id"}]
                df_export = df_affiche[cols].copy()

                # Excel
                try:
                    xlsx_bytes = df_to_excel_bytes(df_export)
                    st.download_button(
                        "📥 Exporter Excel",
                        data=xlsx_bytes,
                        file_name=f"{export_basename}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_xlsx_{export_basename}"
                    )
                except Exception as e:
                    st.warning(f"Export Excel indisponible : {e}")

                # PDF
                try:
                    pdf_bytes = df_to_pdf_bytes(df_export, title="Export GuignoMap")
                    if pdf_bytes:
                        st.download_button(
                            "📄 Exporter PDF",
                            data=pdf_bytes,
                            file_name=f"{export_basename}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{export_basename}"
                        )
                    else:
                        st.info("Export PDF indisponible (ReportLab non installé).")
                except Exception as e:
                    st.warning(f"Export PDF indisponible : {e}")

            # 👉 Appelle _render_export_buttons juste sous la table
            _render_export_buttons(df_affiche, export_basename="carte_table")
            # =============================================================================
            # if st.button(" Bénévole", width="stretch"):
            #     st.session_state.page = "benevole"
            #     st.rerun()
            # if st.button(" Carte", width="stretch"):
            #     st.session_state.page = "carte"
            #     st.rerun()
            # if st.button(" Gestionnaire", width="stretch"):
            #     st.session_state.page = "gestionnaire"
            #     st.rerun()
        # Routing selon le choix radio
        try:
            if nav_choice == "Accueil":
                page_accueil_v2(conn, geo)
            elif nav_choice == "Carte":
                page_carte(conn)
            elif nav_choice == "Bénévole":
                # Fallback si page_benevole_table non définie
                if 'page_benevole_table' in globals():
                    page_benevole_table(conn)
                elif 'page_benevole_v2' in globals():
                    page_benevole_v2(conn, geo)
                else:
                    st.info("Vue bénévole non disponible.")
        except Exception as e:
            st.error(f"Erreur lors du routage : {e}")
                    popup=p["label"],
                    icon=folium.Icon(color=color)
                ).add_to(m)
        st_folium(m, height=600)
    except Exception as e:
        st.warning(f"Erreur carte: {e}")
    import streamlit as st
    import pandas as pd
    st.header("Carte des rues — Guignolée")
    if not FOLIUM_OK:
        st.warning("Carte désactivée (folium manquant).")
        return
    # 1. Essayer de récupérer points depuis la DB
    points = []
    df = None
    try:
        try:
            df = pd.DataFrame(conn.execute("SELECT * FROM streets").fetchall(), columns=[d[0] for d in conn.execute("PRAGMA table_info(streets)").fetchall()])
        except Exception:
            from guignomap.db import list_streets
            df = list_streets(conn)
        if df is not None and all(col in df.columns for col in ["latitude", "longitude", "street_name"]):
            for _, row in df.iterrows():
                lat, lon, label = row["latitude"], row["longitude"], row["street_name"]
                if pd.notnull(lat) and pd.notnull(lon):
                    points.append({
                        "lat": lat,
                        "lon": lon,
                        "label": label,
                        "statut": row["status"] if "status" in df.columns else None,
                        "equipe": row["team"] if "team" in df.columns else None,
                        "secteur": row["sector"] if "sector" in df.columns else None
                    })
    except Exception:
        pass
    # 2. Fallback: lire import/nocivique_cp_complement.xlsx
    if not points:
        try:
            import os
            xlsx_path = os.path.join("import", "nocivique_cp_complement.xlsx")
            if os.path.exists(xlsx_path):
                df_xl = pd.read_excel(xlsx_path)
                if all(col in df_xl.columns for col in ["Latitude", "Longitude", "Adresse"]):
                    for _, row in df_xl.iterrows():
                        lat, lon, label = row["Latitude"], row["Longitude"], row["Adresse"]
                        if pd.notnull(lat) and pd.notnull(lon):
                            points.append({
                                "lat": lat,
                                "lon": lon,
                                "label": label,
                                "statut": None,
                                "equipe": None,
                                "secteur": None
                            })
        except Exception:
            pass
    # --- Filtres basiques (append-only) ---
    if points:
        statuts = ["a_faire", "en_cours", "terminee"]
        statut_labels = {"a_faire": "À faire", "en_cours": "En cours", "terminee": "Terminée"}
    statut_choices = st.multiselect("Statut", options=statuts, default=statuts, format_func=lambda x: statut_labels.get(x, x) or str(x))
        equipes = sorted(set(p["equipe"] for p in points if p["equipe"]))
        secteurs = sorted(set(p["secteur"] for p in points if p["secteur"]))
        equipe_choices = st.multiselect("Équipe", options=equipes, default=equipes) if equipes else None
        secteur_choices = st.multiselect("Secteur", options=secteurs, default=secteurs) if secteurs else None
        # Filtrage
        filtered = [p for p in points if (not p["statut"] or p["statut"] in statut_choices)
                    and (not equipe_choices or not p["equipe"] or p["equipe"] in equipe_choices)
                    and (not secteur_choices or not p["secteur"] or p["secteur"] in secteur_choices)]
        if not filtered:
            st.info("Aucun résultat avec les filtres actuels.")
            return
        points = filtered
    # 3. Aucun point ?
    if not points:
        st.info("Aucune donnée géolocalisée pour le moment.")
        return
    # 4. Centre et zoom
    lats = [float(p["lat"]) for p in points]
    lons = [float(p["lon"]) for p in points]
    center = [sum(lats)/len(lats), sum(lons)/len(lons)]
    m = folium.Map(location=center, zoom_start=12)
    # 5. MarkerCluster si dispo
    try:
        cluster = MarkerCluster().add_to(m)
        for p in points:
            folium.Marker([p["lat"], p["lon"]], popup=p["label"]).add_to(cluster)
    except Exception:
        for p in points:
            folium.Marker([p["lat"], p["lon"]], popup=p["label"]).add_to(m)
    st_folium(m, height=600)
import sqlite3
import streamlit as st
from guignomap.db import (
    init_street_status_schema,
    get_team_streets_status,
    mark_street_in_progress,
    mark_street_complete,
    save_checkpoint,
)

def _get_conn():
    return sqlite3.connect("guignomap/guigno_map.db", check_same_thread=False)

def page_benevole_simple(team_id: str) -> None:
    st.title(f"Équipe {team_id}")
    try:
        conn = _get_conn()
        init_street_status_schema(conn)
        rows = get_team_streets_status(conn, team_id)
    except Exception as e:
        st.error(f"Erreur DB: {e}")
        return

    if not rows:
        st.info(f"Aucune rue assignée pour {team_id}.")
        return

    st.markdown(
    """
    <style>
    .gm-btn { padding: 16px 12px; font-size: 20px; }
    .gm-badge { padding: 4px 8px; border-radius: 8px; font-weight: 600; }
    .gm-green { background:#e7f8ec; color:#177245; }
    .gm-yellow{ background:#fff7da; color:#8a6d00; }
    .gm-red   { background:#ffe5e5; color:#b10000; }
    </style>
    """
    , unsafe_allow_html=True)

    for r in rows:
        street = r["street_name"]
        status = r["status"] or "a_faire"
        badge_cls = "gm-red" if status=="a_faire" else ("gm-yellow" if status=="en_cours" else "gm-green")

        col1, col2 = st.columns([2,1])
        with col1:
            st.subheader(street)
            st.markdown(f'<span class="gm-badge {badge_cls}">{status}</span>', unsafe_allow_html=True)
        with col2:
            if st.button("En cours", key=f"start-{street}", use_container_width=True):
                try:
                    conn = _get_conn()
                    mark_street_in_progress(conn, street, team_id, "")
                    st.success(f"{street} → en cours")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {e}")

            if st.button("Terminée", key=f"done-{street}", use_container_width=True):
                try:
                    conn = _get_conn()
                    mark_street_complete(conn, street, team_id)
                    st.success(f"{street} → terminée")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {e}")

        note = st.text_area("Note", key=f"note-{street}", height=80, placeholder="Observations…")
        if st.button("Enregistrer la note", key=f"save-{street}", use_container_width=True):
            if note.strip():
                try:
                    conn = _get_conn()
                    save_checkpoint(conn, street, team_id, note.strip())
                    st.success("Note enregistrée")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {e}")
            else:
                st.warning("Note vide.")
        st.divider()

# --- Sidebar rôle bénévole (append-only, non destructif) ---
SHOW_ROLE_SELECT = False
if SHOW_ROLE_SELECT:
    role = st.sidebar.selectbox("Rôle", ["gestionnaire", "benevole"], index=0)
    if role == "benevole":
        team_id = st.sidebar.text_input("ID équipe", value=st.session_state.get("team_id", ""))
        if st.sidebar.button("Entrer") and (team_id.strip() if team_id else ""):
            st.session_state["team_id"] = team_id.strip() if team_id else ""
        team_id = st.session_state.get("team_id")
        if team_id:
            page_benevole_simple(team_id)
            st.stop()  # ne pas exécuter la suite de la page
"""GuignoMap — fichier réparé (UTF-8).
Ce bloc contenait du texte libre/©/accents, il est désormais dans une docstring.
"""

from pathlib import Path
import time
from datetime import datetime
import pandas as pd
import streamlit as st

# --- Helpers pandas/NumPy: force un SCALAIRE natif ---
from typing import Any
def to_scalar(x: Any) -> Any:
    try:
        import pandas as pd
        if isinstance(x, pd.Series):
            if len(x) == 0: return 0
            x = x.iloc[0]
    except Exception:
        pass
    try:
        import numpy as np
        if isinstance(x, np.ndarray):
            if x.size == 0: return 0
            try: return x.item()
            except Exception: return x.reshape(-1)[0]
    except Exception:
        pass
    try:
        return x.item()  # numpy scalar
    except Exception:
        return x

    ################################################################################
    # --- Minimal Volunteer UI (append-only, robust, deduplicated) ------------------
    ################################################################################

    def volunteer_ui():
        """
        Minimal, robust volunteer UI: displays assigned streets for current team,
        allows status updates (a_faire, en_cours, terminee), and note entry per street.
        All DB/API calls are protected against missing tables or errors.
        """
        import streamlit as st
        from guignomap.db import (
            list_streets,
            update_street_status,
            add_street_note,
            get_street_notes_for_team,
        )
        import sqlite3

        st.header("Bénévole — Suivi des rues")
        team_id = st.sidebar.text_input("ID équipe", value=st.session_state.get("team_id", ""))
        if st.sidebar.button("Entrer") and team_id.strip():
            st.session_state["team_id"] = team_id.strip()
        team_id = st.session_state.get("team_id")
        if not team_id:
            st.info("Veuillez entrer l'ID de votre équipe.")
            return

        try:
            conn = sqlite3.connect("guignomap/guigno_map.db", check_same_thread=False)
            df = list_streets(conn, team=team_id)
        except Exception as e:
            st.error(f"Erreur DB: {e}")
            return

        if df.empty:
            st.info(f"Aucune rue assignée pour {team_id}.")
            return

        st.dataframe(df[["name", "sector", "status"]], use_container_width=True)

            # === EXPORTS: Excel + PDF (append-only) ======================================
            try:
                import pandas as pd
                from guignomap.export_utils import df_to_excel_bytes, df_to_pdf_bytes
                EXPORTS_OK = True
            except Exception:
                EXPORTS_OK = False

            def _render_export_buttons(df_affiche: "pd.DataFrame", export_basename: str = "export_benevoles"):
                import streamlit as st
                if not EXPORTS_OK:
                    st.info("Exports désactivés (module d’export manquant).")
                    return
                if df_affiche is None or df_affiche.empty:
                    st.info("Rien à exporter (table vide).")
                    return

                cols = [c for c in df_affiche.columns if c.lower() not in {"notes_raw", "internal_id"}]
                df_export = df_affiche[cols].copy()

                # Excel
                try:
                    xlsx_bytes = df_to_excel_bytes(df_export)
                    st.download_button(
                        "📥 Exporter Excel",
                        data=xlsx_bytes,
                        file_name=f"{export_basename}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_xlsx_{export_basename}"
                    )
                except Exception as e:
                    st.warning(f"Export Excel indisponible : {e}")

                # PDF
                try:
                    pdf_bytes = df_to_pdf_bytes(df_export, title="Export GuignoMap")
                    if pdf_bytes:
                        st.download_button(
                            "📄 Exporter PDF",
                            data=pdf_bytes,
                            file_name=f"{export_basename}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{export_basename}"
                        )
                    else:
                        st.info("Export PDF indisponible (ReportLab non installé).")
                except Exception as e:
                    st.warning(f"Export PDF indisponible : {e}")
            # =============================================================================

            # Appel juste sous la table bénévole
            _render_export_buttons(df, "benevoles_table")

        for _, row in df.iterrows():
            street = row["name"]
            status = row["status"]
            st.subheader(f"{street} — Statut: {status}")
            col1, col2, col3 = st.columns([1,1,2])
            with col1:
                if st.button("À faire", key=f"afaire-{street}"):
                    try:
                        update_street_status(conn, street, team_id, "a_faire")
                        st.toast(f"{street} → à faire", icon="🟥")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur: {e}")
                if st.button("En cours", key=f"encours-{street}"):
                    try:
                        update_street_status(conn, street, team_id, "en_cours")
                        st.toast(f"{street} → en cours", icon="🟨")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur: {e}")
                if st.button("Terminée", key=f"terminee-{street}"):
                    try:
                        update_street_status(conn, street, team_id, "terminee")
                        st.toast(f"{street} → terminée", icon="🟩")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur: {e}")
            with col2:
                notes = ""
                try:
                    notes = get_street_notes_for_team(conn, street, team_id)
                except Exception:
                    notes = ""
                st.caption(f"Notes existantes: {notes if notes else 'Aucune'}")
            with col3:
                note = st.text_area(f"Note pour {street}", key=f"note-{street}", height=60)
                if st.button("Enregistrer la note", key=f"save-{street}"):
                    if note.strip():
                        try:
                            add_street_note(conn, street, team_id, note.strip())
                            st.success("Note enregistrée")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Erreur: {e}")
                    else:
                        st.warning("Note vide.")
            st.divider()

    # --- Entry point for minimal volunteer UI (append-only) ---
    if __name__ == "__main__":
        volunteer_ui()

def gt_zero(x: Any) -> bool:
    v = to_scalar(x)
    try:
        return float(v) > 0.0
    except Exception:
        # bool sur tout objet Python (Series déjà aplatie)
        return bool(v)
# -----------------------------------------------------

import folium
from streamlit_folium import st_folium
import PIL.Image

# Augmenter la limite d'images PIL pour éviter DecompressionBombError
PIL.Image.MAX_IMAGE_PIXELS = 500000000


# Import des modules locaux
from guignomap import db
from guignomap.validators import validate_and_clean_input

OSM_AVAILABLE = False
try:
    from guignomap.osm import *
    OSM_AVAILABLE = True
except Exception:
    # Module OSM absent après cleanup : carte désactivée
    pass

# --- Fallback si OSM indisponible (post-cleanup) ---
if not OSM_AVAILABLE:
    CACHE_FILE = None
    def load_geometry_cache(): 
        return {}
    def build_geometry_cache():
        return None
    def build_addresses_cache():
        return None
    def load_addresses_cache():
        return {}

# Configuration des chemins
DB_PATH = Path(__file__).parent / "guigno_map.db"

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
STATUS_TO_LABEL = {"a_faire": " faire", "en_cours": "En cours", "terminee": "Terminée"}
LABEL_TO_STATUS = {v: k for k, v in STATUS_TO_LABEL.items()}

ASSETS = Path(__file__).parent / "assets"

# Configuration Streamlit
st.set_page_config(
    page_title="Guigno-Map | Relais de Mascouche",
    page_icon="",
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
            <span style="position: absolute; top: 10%; left: 10%; font-size: 2rem;">️</span>
            <span style="position: absolute; top: 20%; left: 80%; font-size: 1.5rem;">️</span>
            <span style="position: absolute; top: 60%; left: 30%; font-size: 1.8rem;">️</span>
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
            "> GUIGNOLE 2025 </h1>
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
        stats_fn = getattr(db, "extended_stats", None)
        if callable(stats_fn):
            stats = stats_fn(st.session_state.get('conn'))
        else:
            stats = {"total": 0, "done": 0, "partial": 0}
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
            <div style="font-size: 3rem;"></div>
            <h2 style="color: #FFD700; margin: 1rem 0;">Espace Gestionnaire</h2>
            <p style="color: #cbd5e1;">Gérez la collecte et les équipes</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_gestionnaire", clear_on_submit=False):
            password = st.text_input(
                " Mot de passe",
                type="password",
                placeholder="Entrez le mot de passe gestionnaire"
            )
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                submit = st.form_submit_button(
                    " Connexion",
                    width="stretch"
                )
            
            if submit:
                if db.verify_team(conn, "ADMIN", password):
                    st.session_state.auth = {"role": "supervisor", "team_id": "ADMIN"}
                    st.success(" Bienvenue dans l'espace gestionnaire!")
                    st.snow()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(" Mot de passe incorrect")
    
    else:  # Bénévole
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 3rem;"></div>
            <h2 style="color: #FFD700; margin: 1rem 0;">Espace Bénévole</h2>
            <p style="color: #cbd5e1;">Accédez à vos rues assignées</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_benevole", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                team_id = st.text_input(
                    " Identifiant d'équipe",
                    placeholder="Ex: EQ001"
                )
            
            with col2:
                password = st.text_input(
                    " Mot de passe",
                    type="password",
                    placeholder="Mot de passe équipe"
                )
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                submit = st.form_submit_button(
                    " Connexion",
                    width="stretch"
                )
            
            if submit:
                if db.verify_team(conn, team_id, password):
                    st.session_state.auth = {"role": "volunteer", "team_id": team_id}
                    st.success(f" Bienvenue équipe {team_id}!")
                    st.snow()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(" Identifiants incorrects")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Aide en bas
    st.markdown("""
    <div style="text-align: center; margin-top: 2rem; color: #8b92a4;">
        <small>
        Besoin d'aide? Contactez votre gestionnaire<br>
         450-474-4133
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
    
    st.markdown("###  Tableau de bord en temps réel")
    
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
            <div style="font-size: 2.5rem;">️</div>
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
            <div style="font-size: 2.5rem;"></div>
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
            <div style="font-size: 2.5rem;"></div>
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
            <div style="font-size: 2.5rem;"></div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{teams_count}</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">quipes</div>
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
            <div style="font-size: 2.5rem;"></div>
            <div style="color: white; font-size: 2rem; font-weight: bold;">{progress:.0f}%</div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">Progression</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Barre de progression visuelle
    st.markdown("###  Progression globale")
    st.progress(progress / 100)
    
    # Graphique par secteur (si disponible)
    st.markdown("###  Performance par équipe")
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
                labels={'team': 'quipe', 'progress': 'Progression (%)'},
                title="Performance des équipes"
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Aucune statistique d'équipe disponible")
    except Exception as e:
        st.warning("Graphiques non disponibles (module plotly manquant)")
        # Fallback vers un tableau simple
        try:
            teams_stats = db.stats_by_team(conn)
            if not teams_stats.empty:
                st.dataframe(teams_stats, width="stretch")
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
            <span style='color: {color}'> Statut: {status.replace('_', ' ').title()}</span><br>
            <span> quipe: {team if team else '️ NON ASSIGNE'}</span><br>
            <span> Notes: {notes}</span>
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

REPORTS_AVAILABLE = False
try:
    from guignomap.reports import ReportGenerator
    REPORTS_AVAILABLE = True
except Exception:
    # Exports désactivés si module absent
    class ReportGenerator:
        def __init__(self, *a, **k):
            raise RuntimeError("Reports module not available (cleanup).")

def export_excel_professionnel(conn):
    """Export Excel avec mise en forme professionnelle"""
    if REPORTS_AVAILABLE:
        generator = ReportGenerator(conn)
        return generator.generate_excel()
    else:
        # Fallback si les dépendances ne sont pas installées
        return db.export_to_csv(conn)


# ============================================
# FONCTIONNALITS AVANCES
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
        "success": "",
        "error": "",
        "warning": "️",
        "info": "️"
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
            badges.append(" Première rue!")
        if done >= total * 0.25:
            badges.append(" 25% complété")
        if done >= total * 0.5:
            badges.append(" 50% complété")
        if done >= total * 0.75:
            badges.append(" 75% complété")
        if done == total:
            badges.append(" CHAMPION!")
        
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
    
    st.markdown("###  Centre d'export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 1rem; border: 2px dashed #ccc; border-radius: 10px;">
            <h4>  Rapport PDF</h4>
            <p><small>Format professionnel pour présentation</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            from reports import ReportGenerator
            generator = ReportGenerator(conn)
            pdf_data = generator.generate_pdf()
            st.download_button(
                " Télécharger PDF",
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
            <h4> Excel détaillé</h4>
            <p><small>Avec graphiques et mise en forme</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            excel_data = export_excel_professionnel(conn)
            st.download_button(
                " Télécharger Excel",
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
            <h4> Liste SMS</h4>
            <p><small>Téléphones des bénévoles</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        sms_list = generate_sms_list(conn)
        st.download_button(
            " Liste téléphones",
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
    st.markdown("###  Bienvenue sur Guigno-Map!")
    st.info("Sélectionnez votre mode dans le menu de gauche pour commencer.")
    
    st.markdown("---")
    st.markdown("####  Aperçu de la collecte")
    
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
            <h2 style="color: #c41e3a; margin: 0;"> C'EST AUJOURD'HUI!</h2>
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
        <h1 style="font-size: 3rem; margin: 0;"> Bienvenue sur Guigno-Map </h1>
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
    
    st.markdown("###  tat de la collecte en temps réel")
    
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
            <div style="font-size: 3rem;">️</div>
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
            <div style="font-size: 3rem;"></div>
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
            <div style="font-size: 3rem;"></div>
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
            <div style="font-size: 3rem;"></div>
            <div style="font-size: 2.5rem; font-weight: bold;">{progress:.0f}%</div>
            <div>Progression</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Barre de progression globale
    st.markdown("###  Progression globale de la collecte")
    st.progress(progress / 100)
    
    # Carte festive
    st.markdown("### ️ Vue d'ensemble de Mascouche")
    import pandas as pd
    list_fn = getattr(db, "list_streets", None)
    df_all = list_fn(conn) if callable(list_fn) else pd.DataFrame(columns=["name","sector","team","status"])
    if not df_all.empty:
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
        <h3> Prêt à participer ?</h3>
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
        <h2 style="color: white; margin: 0;"> quipe {team_id}</h2>
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
        st.metric(" Vos rues", total)
    with col2:
        st.metric(" Complétées", done)
    with col3:
        st.metric(" Progression", f"{progress:.0f}%")
    
    # Système de badges
    show_team_badges(conn, team_id)
    
    # Barre de progression
    st.progress(progress / 100)
    
    # Tabs modernisés
    tab1, tab2, tab3 = st.tabs(["️ Ma carte", " Collecte", " Historique"])
    
    with tab1:
        # CARTE LIMITE AUX RUES DE L'QUIPE
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
        st.markdown("###  Checklist de collecte")
        
        # Liste interactive des rues
        for _, row in df_team.iterrows():
            street = row['name']
            status = row['status']
            notes_count = row.get('notes', 0)
            
            # Carte de rue stylisée
            status_emoji = {'terminee': '', 'en_cours': '', 'a_faire': ''}
            status_color = {'terminee': '#22c55e', 'en_cours': '#f59e0b', 'a_faire': '#ef4444'}
            
            with st.expander(f"{status_emoji.get(str(to_scalar(status)), '')} **{street}** ({notes_count} notes)"):
                
                # Changement rapide de statut
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("  faire", key=f"todo_{street}", width="stretch"):
                        db.set_status(conn, street, 'a_faire')
                        st.rerun()
                with col2:
                    if st.button(" En cours", key=f"progress_{street}", width="stretch"):
                        db.set_status(conn, street, 'en_cours')
                        st.rerun()
                with col3:
                    if st.button(" Terminée", key=f"done_{street}", width="stretch"):
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
                    
                    if st.form_submit_button(" Ajouter"):
                        if num and note:
                            db.add_note_for_address(conn, street, team_id, num, note)
                            st.success("Note ajoutée!")
                            st.rerun()
                
                # Notes existantes
                notes = db.get_street_addresses_with_notes(conn, street)
                if not notes.empty:
                    st.markdown("**Notes existantes:**")
                    for _, n in notes.iterrows():
                        st.markdown(f" **{n['address_number']}** : {n['comment']}")
    
    with col3:
        # Export PDF professionnel
        if REPORTS_AVAILABLE:
            try:
                generator = ReportGenerator(conn)
                if hasattr(generator, "generate_pdf"):
                    pdf_data = generator.generate_pdf()
                    st.download_button(
                        " Export PDF Pro",
                        pdf_data,
                        "guignolee_2025_rapport.pdf",
                        "application/pdf",
                        width="stretch"
                    )
                else:
                    st.button(" PDF (Fonction manquante)", disabled=True, width="stretch")
            except Exception as e:
                st.button(" PDF (Erreur)", disabled=True, width="stretch")
                st.caption(f"Erreur: {e}")
        else:
            st.button(" PDF (Module reports manquant)", disabled=True, width="stretch")
def page_benevole_v2(conn, geo):
    """Interface bénévole moderne v4.1 avec vue 'Mes rues'"""
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "volunteer":
        # Afficher la page de connexion bénévole
        return page_benevole(conn, geo)
    
    # Interface bénévole connecté avec tabs
    st.header(" Espace Bénévole")
    team_id = st.session_state.auth.get("team", "quipe inconnue")
    st.markdown(f"**quipe:** {team_id}")
    
    # Tabs pour bénévoles
    tabs = st.tabs([
        "️ Mes rues",
        "️ Carte de terrain", 
        " Journal d'activité"
    ])
    
    with tabs[0]:
        # Nouvelle vue "Mes rues" v4.1
        page_benevole_mes_rues(conn)
    
    with tabs[1]:
        # Carte traditionnelle (réutilise l'ancienne interface)
        page_benevole(conn, geo)
    
    with tabs[2]:
        # Journal d'activité de l'équipe
        st.markdown("###  Journal d'activité de votre équipe")
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
    st.header(" Tableau de Bord Gestionnaire")
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "supervisor":
        render_login_card("gestionnaire", conn)
        return
    
    # Dashboard moderne
    render_dashboard_gestionnaire(conn, geo)
    
    # Tabs
    tabs = st.tabs([
        "📊 Vue d'ensemble",
        "🗺️ Secteurs",
        "👥 Équipes",
        "✏️ Assignation",
        "📤 Export",
        "⚙️ Tech"
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
                st.dataframe(recent, width="stretch")
            else:
                st.info("Aucune activité récente")
        except:
            st.info("Historique d'activité non disponible")
    
    with tabs[1]: # Onglet "Secteurs"
        st.subheader("🗺️ Gestion des Secteurs")

        # --- Section de création de secteur ---
        with st.expander("➕ Créer un nouveau secteur"):
            with st.form("create_sector_form", clear_on_submit=True):
                sector_name = st.text_input("Nom du nouveau secteur", placeholder="Ex: Domaine des Fleurs")
                submitted = st.form_submit_button("Créer le secteur")
                if submitted and sector_name:
                    success, message = db.create_sector(conn, sector_name)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

        # --- Section d'assignation des rues ---
        st.markdown("---")
        st.subheader("Assigner des rues à un secteur")

        # Récupérer les rues non assignées et les secteurs existants
        unassigned_streets_df = db.get_unassigned_streets_by_sector(conn) # Note: cette fonction doit être créée
        sectors_df = db.get_all_sectors(conn)

        if unassigned_streets_df.empty:
            st.info("Toutes les rues sont déjà assignées à un secteur.")
        elif sectors_df.empty:
            st.warning("Veuillez d'abord créer au moins un secteur.")
        else:
            with st.form("assign_streets_to_sector_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_sector_id = st.selectbox(
                        "Choisir un secteur",
                        options=sectors_df.to_records(index=False),
                        format_func=lambda x: x[1] # Affiche le nom du secteur
                    )[0] # Récupère l'ID

                with col2:
                    streets_to_assign = st.multiselect(
                        "Choisir des rues à assigner",
                        options=unassigned_streets_df['name'].tolist()
                    )

                assign_button = st.form_submit_button("Assigner les rues sélectionnées")

                if assign_button and selected_sector_id and streets_to_assign:
                    assigned_count = db.assign_streets_to_sector(conn, streets_to_assign, selected_sector_id)
                    st.success(f"{assigned_count} rue(s) assignée(s) au secteur.")
                    st.rerun()
                team_name_in = st.text_input(
                    "Nom d'équipe", 
                    key="new_team_name", 
                    placeholder="Ex: quipe Centre",
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
                
                submitted = st.form_submit_button(" Créer l'équipe", width="stretch")

            if submitted:
                # Validation avec validators.py
                ok_id, team_id = validate_and_clean_input("team_id", team_id_in)
                ok_name, team_name = validate_and_clean_input("text", team_name_in)
                ok_pw, password = validate_and_clean_input("password", pwd_in)
                
                if not ok_id:
                    st.error(" Identifiant d'équipe invalide (lettres/chiffres, max 20)")
                elif not ok_name:
                    st.error(" Nom d'équipe invalide ou vide")
                elif not ok_pw:
                    st.error(" Mot de passe invalide (minimum 4 caractères)")
                elif pwd_in != pwd_conf:
                    st.error(" Les mots de passe ne correspondent pas")
                else:
                    # Tentative de création avec db.create_team
                    try:
                        created = db.create_team(conn, team_id, team_name, password)
                        if created:
                            st.toast(f" quipe {team_id} créée avec succès", icon="")
                            st.rerun()
                        else:
                            st.error(" chec de création (ID déjà existant ?)")
                    except Exception as e:
                        st.error(f" Erreur lors de la création: {e}")
        
        # === Liste des équipes (sans doublon de titre) ===
        try:
            teams_df = db.get_all_teams(conn)
            if not teams_df.empty:
                st.dataframe(teams_df, width="stretch")
            else:
                st.info("Aucune équipe créée")
        except Exception as e:
            st.info("Liste des équipes non disponible")
    
    with tabs[2]:
        # Assignation v4.1
        page_assignations_v41(conn)
    
    with tabs[3]:
        # Export amélioré v4.1
        page_export_gestionnaire_v41(conn)

    with tabs[4]:
        st.markdown("###  Opérations techniques (protégées)")

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


        # --- Opérations techniques OSM ---
        if not OSM_AVAILABLE:
            st.info("Fonctions OSM désactivées (cleanup).")
            return

        st.info("️ Ces actions sont lourdes et n'affectent pas les statuts/notes. Elles régénèrent les caches OSM.")

        # --- Reconstruire le cache géométrique (lourd)
        with st.expander(" Reconstruire cache OSM (géométries)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirm = st.checkbox("Je comprends les implications")
            with col2:
                safety = st.text_input('crire "REBUILD" pour confirmer')

            if st.button("Lancer la reconstruction"):
                if confirm and safety.strip().upper() == "REBUILD":
                    with st.spinner("Construction du cache"):
                        build_geometry_cache()       # reconstruit le fichier osm_cache.json
                        st.cache_data.clear()        # purge cache Streamlit
                    st.success(" Cache OSM mis à jour (géométries).")
                    st.rerun()
                else:
                    st.warning("Confirmation incomplète.")

        # --- Reconstruire/Importer le cache des adresses
        with st.expander(" Mettre à jour les adresses (OSM)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirmA = st.checkbox("Je confirme")
            with col2:
                safetyA = st.text_input('crire "IMPORT" pour confirmer')

            if st.button("Lancer la mise à jour des adresses"):
                if confirmA and safetyA.strip().upper() == "IMPORT":
                    with st.spinner("Téléchargement des adresses OSM"):
                        build_addresses_cache()
                        addr_cache = load_addresses_cache()
                        count = db.import_addresses_from_cache(conn, addr_cache)
                    st.success(f" {count} adresses importées depuis OSM.")
                    st.rerun()
                else:
                    st.warning("Confirmation incomplète.")

        # --- Gestion des backups
        with st.expander(" Gestion des backups", expanded=False):
            backup_mgr = db.get_backup_manager(DB_PATH)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button(" Créer un backup manuel", width="stretch"):
                    backup_file = backup_mgr.create_backup("manual")
                    if backup_file:
                        st.success(f"Backup créé : {Path(backup_file).name}")
            
            with col2:
                if st.button(" Voir les backups", width="stretch"):
                    backups = backup_mgr.list_backups()
                    if backups:
                        for backup in backups[:5]:  # Montrer les 5 derniers
                            size_mb = backup.stat().st_size / (1024 * 1024)
                            st.text(f" {backup.name} ({size_mb:.1f} MB)")
                    else:
                        st.info("Aucun backup disponible")

def page_superviseur(conn, geo):
    """Interface superviseur"""
    st.header(" Tableau de Bord Superviseur")
    
    # Vérifier l'authentification
    if not st.session_state.auth or st.session_state.auth.get("role") != "supervisor":
        render_login_card("superviseur", conn)
        return
    
    # Dashboard moderne
    render_dashboard_gestionnaire(conn, geo)
    
    # Tabs
    tabs = st.tabs([
        " Vue d'ensemble",
        " quipes",
        "️ Assignation",
        " Export",
        " Tech"
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
            st.dataframe(recent, width="stretch")
    
    with tabs[1]:
        # Gestion des équipes
        st.markdown("### Gestion des équipes")
        
        with st.expander("Créer une équipe"):
            with st.form("new_team", clear_on_submit=True):
                new_id = st.text_input("Identifiant")
                new_name = st.text_input("quipe")
                new_pass = st.text_input("Mot de passe", type="password")
                
                if st.form_submit_button("Créer"):
                    if all([new_id, new_name, new_pass]):
                        if db.create_team(conn, new_id, new_name, new_pass):
                            st.success(f"quipe {new_id} créée")
                            st.rerun()
        
        # Liste des équipes
        teams_df = db.get_all_teams(conn)
        if not teams_df.empty:
            st.dataframe(teams_df, width="stretch")
    
    with tabs[2]:
        # Assignation
        st.markdown("### Assignation des rues")
        # --- Bloc navigation remplacé par render_sidebar_nav() ---
    # render_sidebar_nav()
# ================= Sidebar navigation unifiée (append-only) ===================
def render_sidebar_nav():
    import streamlit as st
    nav_items = [
        ("nav_accueil", "Accueil", "accueil"),
        ("nav_benevole", "Bénévole", "benevole"),
        ("nav_carte", "Carte", "carte"),
        ("nav_gestionnaire", "Gestionnaire", "gestionnaire")
    ]
    for key, label, page in nav_items:
        if st.button(f" {label}", key=key, use_container_width=True):
            st.session_state.page = page
            st.rerun()
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
                width="stretch"
            )
    
    with tabs[3]:
        # Export
        st.markdown("### Export des données")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                " Export rues (CSV)",
                db.export_to_csv(conn),
                "rapport_rues.csv",
                "text/csv",
                width="stretch"
            )
        
        with col2:
            st.download_button(
                " Export notes (CSV)",
                db.export_notes_csv(conn),
                "rapport_notes.csv",
                "text/csv",
                width="stretch"
            )

    with tabs[4]:
        st.markdown("###  Opérations techniques (protégées)")

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

        st.info("️ Ces actions sont lourdes et n'affectent pas les statuts/notes. Elles régénèrent les caches OSM.")

        # --- Reconstruire le cache géométrique (lourd)
        with st.expander(" Reconstruire cache OSM (géométries)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirm = st.checkbox("Je comprends les implications")
            with col2:
                safety = st.text_input('crire "REBUILD" pour confirmer')

            if st.button("Lancer la reconstruction"):
                if confirm and safety.strip().upper() == "REBUILD":
                    with st.spinner("Construction du cache"):
                        build_geometry_cache()       # reconstruit le fichier osm_cache.json
                        st.cache_data.clear()        # purge cache Streamlit
                    st.success(" Cache OSM mis à jour (géométries).")
                    st.rerun()
                else:
                    st.warning("Confirmation incomplète.")

        # --- Reconstruire/Importer le cache des adresses
        with st.expander(" Mettre à jour les adresses (OSM)", expanded=False):
            col1, col2 = st.columns([1,2])
            with col1:
                confirmA = st.checkbox("Je confirme")
            with col2:
                safetyA = st.text_input('crire "IMPORT" pour confirmer')

            if st.button("Lancer la mise à jour des adresses"):
                if confirmA and safetyA.strip().upper() == "IMPORT":
                    with st.spinner("Téléchargement des adresses OSM"):
                        build_addresses_cache()
                        addr_cache = load_addresses_cache()
                        count = db.import_addresses_from_cache(conn, addr_cache)
                    st.success(f" {count} adresses importées depuis OSM.")
                    st.rerun()
                else:
                    st.warning("Confirmation incomplète.")

# ================================================================================
# NOUVELLES FONCTIONS v4.1 - SUPERVISEUR ET BNVOLE
# ================================================================================

def page_assignations_v41(conn):
    """Panneau d'assignations v4.1 pour superviseurs"""
    
    try:
        # ===== Bloc Assignations (refactor propre) =====
        st.subheader("️ Assignations par secteur", anchor=False)
        
        # Compteur de rues non assignées (bannière info)
        unassigned_count = db.get_unassigned_streets_count(conn)
        if unassigned_count > 0:
            st.info(f"️ {unassigned_count} rue(s) non assignée(s)")
        
        with st.container():
            c1, c2, c3 = st.columns([1, 1.2, 0.7], vertical_alignment="bottom")
            
            with c1:
                # Récupérer la liste des secteurs
                liste_secteurs = db.get_sectors_list(conn)
                secteur = st.selectbox(
                    "SECTEUR  ASSIGNER",
                    options=[""] + (liste_secteurs if liste_secteurs else []),
                    index=0,
                    key="assign_sector",
                    help="Choisissez le secteur à assigner",
                    label_visibility="visible",
                )
            
            with c2:
                # Récupérer la liste des équipes
                teams = db.get_teams_list(conn)
                liste_equipes = [f"{team[1]} ({team[0]})" for team in teams] if teams else []
                
                if liste_equipes:
                    team_display = st.selectbox(
                        "QUIPE", 
                        options=[""] + liste_equipes, 
                        index=0, 
                        key="assign_team"
                    )
                    # Extraire l'ID de l'équipe
                    team = ""
                    if team_display and team_display != "":
                        team = team_display.split("(")[-1].rstrip(")")
                else:
                    st.info("Aucune équipe disponible")
                    team = None
            
            with c3:
                disabled = not (secteur and team)
                if st.button(" Assigner tout le secteur", width="stretch", disabled=disabled):
                    # Appel métier : assigner toutes les rues non assignées du secteur à l'équipe
                    if secteur and team:
                        try:
                            nb = db.bulk_assign_sector(conn, secteur, team)
                            if nb > 0:
                                st.toast(f" {nb} rue(s) assignée(s) à l'équipe {team}", icon="")
                                st.rerun()
                            else:
                                st.toast("️ Aucune rue non assignée dans ce secteur", icon="️")
                        except Exception as e:
                            st.error(f"Erreur lors de l'assignation: {e}")
        
        # ===== Tableau d'état (uniforme, sans style spécial) =====
        st.markdown("###  tat des assignations")
        
        df = db.list_streets(conn)
        if not df.empty:
            df_disp = df.assign(
                Statut=df["status"].map(STATUS_TO_LABEL).fillna(" faire")
            ).rename(columns={
                "name": "Rue", 
                "sector": "Secteur", 
                "team": "quipe"
            })[["Rue", "Secteur", "quipe", "Statut"]]
            
            st.dataframe(df_disp, width="stretch")  # aucun Styler, aucun CSS cellule
        else:
            st.info("Aucune rue trouvée")
            
    except Exception as e:
        st.error(f"Erreur dans le panneau d'assignations: {e}")
        st.info("Fonctionnalité temporairement indisponible")

def page_export_gestionnaire_v41(conn):
    """Page d'export v4.1 avec nouvelles fonctionnalités"""
    st.markdown("###  Export des données")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV standard
        try:
            st.download_button(
                " Export CSV Standard",
                db.export_to_csv(conn),
                "rapport_rues.csv",
                "text/csv",
                width="stretch"
            )
        except Exception as e:
            st.button(" CSV (Erreur)", disabled=True, width="stretch")
            st.caption(f"Erreur: {e}")
    
    with col2:
        # Export Excel professionnel
        if REPORTS_AVAILABLE:
            try:
                generator = ReportGenerator(conn)
                excel_data = generator.generate_excel()
                st.download_button(
                    " Export Excel Pro",
                    excel_data,
                    "guignolee_2025_rapport.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch"
                )
            except Exception as e:
                st.button(" Excel (Erreur)", disabled=True, width="stretch")
                st.caption(f"Erreur: {e}")
        else:
            st.button(" Excel (Module reports manquant)", disabled=True, width="stretch")

    with col3:
        # Export PDF professionnel
        if REPORTS_AVAILABLE:
            try:
                generator = ReportGenerator(conn)
                pdf_data = generator.generate_pdf()
                st.download_button(
                    " Export PDF Pro",
                    pdf_data,
                    "guignolee_2025_rapport.pdf",
                    "application/pdf",
                    width="stretch"
                )
            except ImportError:
                st.button(" PDF (Installer reportlab)", disabled=True, width="stretch")
            except Exception as e:
                import streamlit as st
                st.error(f"Erreur: {e}")
    
    # Export CSV assignations (nouveau v4.1)
    st.markdown("---")
    st.markdown("###  Export spécialisés v4.1")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV assignations
        try:
            assignations_data = db.get_assignations_export_data(conn)
            if not assignations_data.empty:
                csv_data = assignations_data.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    " Export CSV Assignations",
                    csv_data,
                    "assignations_secteurs.csv",
                    "text/csv",
                    width="stretch",
                    help="Colonnes: secteur, rue, équipe, statut"
                )
            else:
                st.button(" Assignations (Aucune donnée)", disabled=True, width="stretch")
        except Exception as e:
            import streamlit as st
            st.button(" Assignations (Erreur)", disabled=True, width="stretch")
            st.caption(f"Erreur: {e}")
    
    with col2:
        # Export notes
        try:
            st.download_button(
                " Export Notes",
                db.export_notes_csv(conn),
                "rapport_notes.csv",
                "text/csv",
                width="stretch"
            )
        except Exception as e:
            import streamlit as st
            st.button(" Notes (Erreur)", disabled=True, width="stretch")
            st.caption(f"Erreur: {e}")

def page_benevole_mes_rues(conn):
    """Vue 'Mes rues' pour bénévoles avec checklist des adresses v5.0."""
    if not st.session_state.get('auth') or st.session_state.auth.get("role") != "volunteer":
        st.warning("Accès réservé aux bénévoles connectés.")
        return
    
    team_id = st.session_state.auth.get("team_id")
    if not team_id:
        st.error("Équipe non identifiée.")
        return

    st.markdown(f"### 🗺️ Mes rues assignées - Équipe {team_id}")

    try:
        team_streets = db.list_streets(conn, team=team_id)
        
        if team_streets.empty:
            st.info("Aucune rue n'est assignée à votre équipe pour le moment.")
            return

        for _, street_row in team_streets.iterrows():
            street_name = street_row['name']
            
            # Récupérer toutes les adresses de cette rue depuis la DB
            addresses_df = db.get_addresses_for_street(conn, street_name)
            # Récupérer les adresses déjà visitées
            visited_addresses = db.get_visited_addresses_for_street(conn, street_name, team_id)

            expander_title = f"📍 {street_name} ({len(visited_addresses)} / {len(addresses_df)} adresses visitées)"
            
            with st.expander(expander_title):
                if addresses_df.empty:
                    st.text("Aucune adresse civique trouvée pour cette rue.")
                    continue

                # Affichage en grille pour être compact
                cols = st.columns(4)
                
                # Trier les numéros civiques (gère les numéros comme '123' et '123A')
                sorted_addresses = sorted(addresses_df['house_number'].tolist(), key=lambda x: (int(str(x).rstrip('ABCD')), str(x)[-1]) if str(x)[-1].isalpha() else (int(str(x)), ''))

                for idx, house_number in enumerate(sorted_addresses):
                    col = cols[idx % 4]
                    is_visited = str(house_number) in visited_addresses
                    
                    # La clé unique est cruciale pour que Streamlit gère chaque checkbox individuellement
                    key = f"{team_id}_{street_name}_{house_number}"
                    
                    if col.checkbox(f"#{house_number}", value=is_visited, key=key):
                        # Si la case est cochée et qu'elle ne l'était pas avant, on marque comme visitée
                        if not is_visited:
                            db.mark_address_visited(conn, street_name, str(house_number), team_id)
                            st.rerun() # Rafraîchit l'interface pour mettre à jour les comptes
    except Exception as e:
        st.error(f"Une erreur est survenue lors du chargement de vos rues : {e}")
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
            
            with st.expander(f"️ {street_name} ({street['sector']}) - {current_status.replace('_', ' ').title()}", 
                           expanded=current_status == 'en_cours'):
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**Secteur:** {street['sector']}")
                    st.markdown(f"**Statut actuel:** {current_status.replace('_', ' ').title()}")
                    if gt_zero(notes_count):
                        st.markdown(f"**Notes existantes:** {notes_count}")
                
                with col2:
                    # Bouton "En cours"
                    if st.button(
                        " En cours", 
                        key=f"progress_{street_name}",
                        disabled=current_status == 'en_cours',
                        width="stretch"
                    ):
                        if db.update_street_status(conn, street_name, 'en_cours', team_id):
                            st.toast(f" {street_name} en cours!", icon="")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la mise à jour")

                    if st.button(
                        " Terminée", 
                        key=f"done_{street_name}",
                        disabled=current_status == 'terminee',
                        width="stretch"
                    ):
                        if db.update_street_status(conn, street_name, 'terminee', team_id):
                            st.toast(f" {street_name} terminée!", icon="")
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
                        st.markdown(f" **#{note[0]}** : {note[1]} _{note[2]}_")
                
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
                    
                    if st.form_submit_button(" Enregistrer note"):
                        if address_number and comment:
                            if db.add_street_note(conn, street_name, team_id, address_number, comment):
                                st.toast(f" Note ajoutée pour {street_name} #{address_number}", icon="")
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

    # --- Initialisation conditionnelle de geo selon OSM_AVAILABLE ---
    if OSM_AVAILABLE and CACHE_FILE:
        @st.cache_data(ttl=None)
        def get_geo(_sig):
            return load_geometry_cache() or {}
        sig = int(CACHE_FILE.stat().st_mtime_ns) if CACHE_FILE.exists() else 0
        geo = get_geo(sig)
    else:
        geo = {}
    
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
                <div style="font-size: 2.5rem;"></div>
                <div style="font-weight: bold; font-size: 1.2rem;">LOGO</div>
                <small>Espace réservé</small>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        # Navigation
        st.markdown("###  Navigation")
        
        # Boutons de navigation stylisés (désactivés, remplacés par radio sidebar)
        # if st.button(" Accueil", width="stretch", key="nav_home_btn"):
        #     st.session_state.page = "accueil"
        #     st.rerun()
        # if st.button(" Bénévole", width="stretch", key="nav_benevole_btn"):
        #     st.session_state.page = "benevole"
        #     st.rerun()
        # if st.button(" Gestionnaire", width="stretch", key="nav_gestion_btn"):
        #     st.session_state.page = "gestionnaire"  
        #     st.rerun()
        # Déconnexion si connecté
        # if st.session_state.auth:
        #     st.markdown("---")
        #     if st.button(" Déconnexion", width="stretch", key="nav_logout_btn"):
        #         st.session_state.auth = None
                st.rerun()
        
        # Compteur temps réel
        st.markdown("---")
        stats = db.extended_stats(conn)
        st.markdown(f"""
        <div style="text-align: center;">
            <h4>tat de la collecte</h4>
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
             Guignolée 2025 - Le Relais de Mascouche <br>
            <small>Ensemble, redonnons espoir |  450-474-4133</small>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Bannière en bas de page
    if (ASSETS / "banner.png").exists():
        st.image(str(ASSETS / "banner.png"), width="stretch")

if __name__ == "__main__":
    main()

# ================= MVP Carte (append-only, robuste) ==========================
# Imports protégés folium/streamlit-folium
try:
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import MarkerCluster
    FOLIUM_OK = True
except Exception:
    FOLIUM_OK = False

def page_carte(conn):
    import streamlit as st
    import pandas as pd
    st.header("Carte des rues — Guignolée")
    if not FOLIUM_OK:
        st.warning("Carte désactivée (folium manquant).")
        return
    m = create_simple_map(conn)
    from streamlit_folium import st_folium
    st_folium(m, height=600)

# ================= Append-only : bouton Carte dans la sidebar =================
def main_with_carte():
    # ...existing code...
    conn = db.get_conn(DB_PATH)
    db.init_db(conn)
    st.session_state['conn'] = conn
    # ...existing code...
    geo = {}
    render_header()
    with st.sidebar:
        # ...existing code...
        if st.button(" Accueil", width="stretch"):
            st.session_state.page = "accueil"
            st.rerun()
        if st.button(" Bénévole", width="stretch"):
            st.session_state.page = "benevole"
            st.rerun()
        if st.button(" Carte", width="stretch"):
            st.session_state.page = "carte"
            st.rerun()
        if st.button(" Gestionnaire", width="stretch"):
            st.session_state.page = "gestionnaire"
            st.rerun()
        # ...existing code...
    page = st.session_state.get('page', 'accueil')
    if page == "accueil":
        page_accueil_v2(conn, geo)
    elif page == "benevole":
        page_benevole_v2(conn, geo)
    elif page == "carte":
        page_carte(conn)
    elif page == "gestionnaire":
        page_gestionnaire_v2(conn, geo)
    # ...existing code...

# --- Entrée principale avec carte ---
if __name__ == "__main__":
    main_with_carte()



