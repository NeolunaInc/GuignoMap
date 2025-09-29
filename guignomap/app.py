# -*- coding: utf-8 -*-
"""
GuignoMap – Application Streamlit unifiée (réécriture complète)
Rôle : Accueil / Bénévole / Gestionnaire

Hypothèses basées sur l'audit:
- Base SQLite : guignomap/guigno_map.db (tables: sectors, streets, teams, notes, activity_log, addresses)
- Tous les points d'adresses sont déjà géocodés (latitude/longitude non nuls)
- Statuts rues : 'a_faire' | 'en_cours' | 'terminee'
- teams.active = 1 pour les équipes actives
- Passwords en bcrypt (fallback SHA256 legacy toléré)

Dépendances (audit): streamlit, streamlit-folium, folium, pandas, plotly, bcrypt, openpyxl (pour Excel)
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from datetime import datetime, date, time, timedelta
import hashlib

import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
import base64
import math

try:
    import bcrypt
except Exception:  # pragma: no cover
    bcrypt = None

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

# -----------------------------------------------------------------------------
# CONFIG GLOBALE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="GuignoMap – Guignolée Mascouche",
    page_icon="🎄",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "guigno_map.db"
ASSETS_DIR = APP_DIR / "assets"
CSS_PATH = ASSETS_DIR / "styles.css"

def _inject_css_with_fallback():
    """Charge assets/styles.css si présent; sinon injecte un style minimal de secours."""
    try:
        if CSS_PATH.exists():
            css = CSS_PATH.read_text(encoding="utf-8")
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        else:
            # Fallback minimal pour prouver l’application du thème si le fichier manque
            fallback = """
            :root{--card-bg:#111827;--card-b:#1f2937;--fg:#fff;--bg:#0b1220}
            body,.stApp{background:var(--bg);color:var(--fg)}
            .brand-header{border:1px solid var(--card-b);border-radius:16px;padding:16px 20px;margin:8px 0 16px;background:#151c2c}
            .brand-title{font-size:28px;font-weight:800}
            .brand-sub{color:#9ca3af}
            .card{background:var(--card-bg);border:1px solid var(--card-b);border-radius:16px;padding:16px;margin-bottom:16px}
            """
            st.markdown(f"<style>{fallback}</style>", unsafe_allow_html=True)
    except Exception:
        pass

_inject_css_with_fallback()

# -----------------------------------------------------------------------------
# UTILITAIRES TEMPS
# -----------------------------------------------------------------------------

def _tz():
    try:
        return ZoneInfo("America/Toronto") if ZoneInfo else None
    except Exception:
        return None

def _now(tz=None):
    return datetime.now(tz) if tz else datetime.now()


def _first_sunday_of_december(year: int) -> date:
    d = date(year, 12, 1)
    offset = (6 - d.weekday()) % 7  # Monday=0 ... Sunday=6
    return d + timedelta(days=offset)


def get_compte_a_rebours() -> str:
    """Prochain premier dimanche de décembre à 08:00 (heure locale).
    Le jour J: renvoie "C'est aujourd'hui !" toute la journée.
    """
    tz = _tz()
    now = _now(tz)

    dec_sunday = _first_sunday_of_december(now.year)
    target_dt = datetime.combine(dec_sunday, time(8, 0), tz)

    if now > target_dt and now.date() != dec_sunday:
        dec_sunday = _first_sunday_of_december(now.year + 1)
        target_dt = datetime.combine(dec_sunday, time(8, 0), tz)

    if now.date() == dec_sunday:
        return "C'est aujourd'hui !"

    delta = target_dt - now
    days = max(delta.days, 0)
    hours = max(delta.seconds // 3600, 0)
    return f"Dans {days} jours et {hours} heures"

# -----------------------------------------------------------------------------
# DB LAYER (minimale, robuste)
# -----------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_connection() -> sqlite3.Connection:
    """Connexion SQLite mise en cache. Initialise row_factory.
    Si la DB est vide/partielle, on tente un init minimal.
    """
    try:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"❌ Connexion DB impossible: {e}")
        st.stop()


def verify_password(plain: str, hashed: str | None) -> bool:
    if not plain or not hashed:
        return False
    # bcrypt (préféré)
    try:
        if hashed.startswith("$2") and bcrypt is not None:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        pass
    # fallback legacy SHA256
    try:
        return hashlib.sha256(plain.encode("utf-8")).hexdigest() == hashed
    except Exception:
        return False


# -------------------------
# Requêtes de lecture
# -------------------------

def db_stats_globales(conn: sqlite3.Connection) -> dict:
    try:
        c = conn.cursor()
        total = c.execute("SELECT COUNT(*) FROM streets").fetchone()[0]
        row = c.execute(
            "SELECT SUM(CASE WHEN status='terminee' THEN 1 ELSE 0 END),\n                    SUM(CASE WHEN status='en_cours' THEN 1 ELSE 0 END)\n             FROM streets"
        ).fetchone()
        terminee = row[0] or 0
        en_cours = row[1] or 0
        ass = c.execute("SELECT COUNT(*) FROM streets WHERE team IS NOT NULL AND team != ''").fetchone()[0]
        return {
            "total": total,
            "terminee": terminee,
            "en_cours": en_cours,
            "a_faire": max(total - terminee - en_cours, 0),
            "assignees": ass,
            "non_assignees": max(total - ass, 0),
            "pourcentage": (terminee * 100.0 / total) if total else 0.0,
        }
    except Exception as e:
        st.warning(f"Stats indisponibles: {e}")
        return {"total": 0, "terminee": 0, "en_cours": 0, "a_faire": 0, "assignees": 0, "non_assignees": 0, "pourcentage": 0.0}


def db_team_name(conn: sqlite3.Connection, team_id: str) -> str:
    row = conn.execute("SELECT name FROM teams WHERE id = ?", (team_id,)).fetchone()
    return row[0] if row else team_id


def db_team_progress(conn: sqlite3.Connection, team_id: str) -> tuple[int, int]:
    row = conn.execute(
        "SELECT COUNT(*) as total,\n                SUM(CASE WHEN status='terminee' THEN 1 ELSE 0 END) as done\n         FROM streets WHERE team = ?",
        (team_id,),
    ).fetchone()
    total = row[0] or 0
    done = row[1] or 0
    return total, done


def db_last_checkpoint(conn: sqlite3.Connection, team_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT street_name
        FROM notes
        WHERE team_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (team_id,),
    ).fetchone()
    return row[0] if row else None


def db_assigned_streets(conn: sqlite3.Connection, team_id: str) -> pd.DataFrame:
    query = (
        """
        SELECT s.name as rue, s.status,
               COUNT(DISTINCT a.id) as nb_adresses
        FROM streets s
        LEFT JOIN addresses a ON a.street_name = s.name
        WHERE s.team = ?
        GROUP BY s.name, s.status
        ORDER BY CASE s.status WHEN 'en_cours' THEN 0 WHEN 'a_faire' THEN 1 ELSE 2 END, s.name
        """
    )
    try:
        return pd.read_sql_query(query, conn, params=(team_id,))
    except Exception as e:
        st.error(f"Lecture rues équipe impossible: {e}")
        return pd.DataFrame(columns=["rue", "status", "nb_adresses"])


def db_non_assigned_streets(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT name FROM streets WHERE team IS NULL OR team='' ORDER BY name").fetchall()]


def db_teams(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    return conn.execute("SELECT id, name FROM teams WHERE id != 'ADMIN' AND active = 1 ORDER BY id").fetchall()


def db_sectors(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    return conn.execute("SELECT id, name FROM sectors ORDER BY name").fetchall()


def db_stats_by_team(conn: sqlite3.Connection) -> pd.DataFrame:
    query = (
        """
        SELECT t.name as equipe,
               COUNT(s.id) as total,
               SUM(CASE WHEN s.status='terminee' THEN 1 ELSE 0 END) as terminees,
               ROUND(SUM(CASE WHEN s.status='terminee' THEN 1.0 ELSE 0 END) * 100.0 / NULLIF(COUNT(s.id),0), 1) as pourcentage
        FROM teams t
        LEFT JOIN streets s ON s.team = t.id
        WHERE t.id != 'ADMIN'
        GROUP BY t.id
        HAVING COUNT(s.id) > 0
        ORDER BY pourcentage DESC
        """
    )
    try:
        return pd.read_sql_query(query, conn)
    except Exception as e:
        st.warning(f"Stats équipes indisponibles: {e}")
        return pd.DataFrame(columns=["equipe", "total", "terminees", "pourcentage"])


# -------------------------
# Mutations & journalisation
# -------------------------

def log_activity(conn: sqlite3.Connection, team_id: str | None, action: str, details: str) -> None:
    try:
        conn.execute(
            "INSERT INTO activity_log (team_id, action, details) VALUES (?, ?, ?)",
            (team_id or "SYSTEM", action, details),
        )
        conn.commit()
    except Exception:
        pass


def set_street_status(conn: sqlite3.Connection, street_name: str, status: str, team_id: str | None = None) -> bool:
    try:
        conn.execute("UPDATE streets SET status = ? WHERE name = ?", (status, street_name))
        conn.commit()
        log_activity(conn, team_id, "STATUS_UPDATE", f"{street_name} -> {status}")
        return True
    except Exception as e:
        st.error(f"Maj statut impossible: {e}")
        return False


def add_note(conn: sqlite3.Connection, street_name: str, team_id: str, address_number: str, comment: str) -> bool:
    try:
        conn.execute(
            "INSERT INTO notes (street_name, team_id, address_number, comment) VALUES (?, ?, ?, ?)",
            (street_name, team_id, address_number.strip(), comment.strip()),
        )
        conn.commit()
        log_activity(conn, team_id, "NOTE_ADD", f"{street_name} #{address_number}")
        return True
    except Exception as e:
        st.error(f"Ajout note impossible: {e}")
        return False


# -----------------------------------------------------------------------------
# CARTOGRAPHIE (Folium)
# -----------------------------------------------------------------------------

STATUS_COLORS = {
    "terminee": "#22c55e",  # vert
    "en_cours": "#f59e0b",  # orange
    "a_faire": "#ef4444",   # rouge
}


def _fetch_street_points(conn: sqlite3.Connection, where_clause: str = "", params: tuple = ()) -> pd.DataFrame:
    """Récupère les points (lat/lon) par rue. where_clause peut filtrer s.team etc.
    Retourne colonnes: rue, status, team, lat, lon.
    """
    base = f"""
        SELECT s.name AS rue, s.status, s.team,
               a.latitude AS lat, a.longitude AS lon
        FROM streets s
        JOIN addresses a ON a.street_name = s.name
        WHERE a.latitude IS NOT NULL AND a.longitude IS NOT NULL {(' AND ' + where_clause) if where_clause else ''}
    """
    try:
        df = pd.read_sql_query(base, conn, params=params)
        return df
    except Exception as e:
        st.error(f"Lecture points carte impossible: {e}")
        return pd.DataFrame(columns=["rue", "status", "team", "lat", "lon"]) 


def map_global(conn: sqlite3.Connection) -> folium.Map:
    m = folium.Map(location=[45.7475, -73.6005], zoom_start=12, tiles="OpenStreetMap")
    df = _fetch_street_points(conn)
    if df.empty:
        return m

    # Groupement par rue + tri
    for (rue, status, team), g in df.groupby(["rue", "status", "team"], sort=False):
        g = g.dropna(subset=["lat", "lon"]).copy()
        if g.empty:
            continue
        # Tri approximatif: angle autour du centroïde
        cx, cy = g["lat"].mean(), g["lon"].mean()
        g["_ang"] = g.apply(lambda r: math.atan2(r["lat"] - cx, r["lon"] - cy), axis=1)
        g = g.sort_values("_ang")
        pts = g[["lat", "lon"]].values.tolist()
        if len(pts) < 2:
            folium.CircleMarker(
                location=pts[0],
                radius=4,
                color=STATUS_COLORS.get(status, "#6b7280"),
                fill=True,
                fill_opacity=0.7,
                popup=f"<b>{rue}</b><br>Statut: {status}<br>Équipe: {team or '—'}",
            ).add_to(m)
            continue

        is_unassigned = (team is None) or (str(team).strip() == "")
        style_kwargs = {
            "color": STATUS_COLORS.get(status, "#6b7280"),
            "weight": 4 if not is_unassigned else 3,
            "opacity": 0.9 if not is_unassigned else 0.6,
        }
        if is_unassigned:
            style_kwargs["dash_array"] = "5, 10"
        folium.PolyLine(pts, **style_kwargs, tooltip=rue).add_to(m)

    return m


def map_team(conn: sqlite3.Connection, team_id: str) -> folium.Map:
    m = folium.Map(location=[45.7475, -73.6005], zoom_start=13, tiles="OpenStreetMap")
    df = _fetch_street_points(conn, where_clause="s.team = ?", params=(team_id,))
    if df.empty:
        return m

    for (rue, status), g in df.groupby(["rue", "status"], sort=False):
        g = g.dropna(subset=["lat", "lon"]).copy()
        if g.empty:
            continue
        cx, cy = g["lat"].mean(), g["lon"].mean()
        g["_ang"] = g.apply(lambda r: math.atan2(r["lat"] - cx, r["lon"] - cy), axis=1)
        g = g.sort_values("_ang")
        pts = g[["lat", "lon"]].values.tolist()
        if len(pts) < 2:
            folium.CircleMarker(location=pts[0], radius=6,
                                color=STATUS_COLORS.get(status, "#6b7280"), fill=True, fill_opacity=0.9,
                                popup=f"<b>{rue}</b>").add_to(m)
            continue
        folium.PolyLine(pts, color=STATUS_COLORS.get(status, "#6b7280"), weight=6, opacity=0.9,
                        tooltip=rue).add_to(m)
    return m

# -----------------------------------------------------------------------------
# HEADER / FOOTER (branding)
# -----------------------------------------------------------------------------

def _img_b64(p: Path | str) -> str | None:
    try:
        p = Path(p)
        if not p.exists():
            return None
        return base64.b64encode(p.read_bytes()).decode("utf-8")
    except Exception:
        return None


def render_header(subtitle: str | None = None) -> None:
    """Bandeau supérieur cohérent (logo + titre + sous-titre)."""
    logo = _img_b64(ASSETS_DIR / "logo.png") or _img_b64(APP_DIR / "logo.png")
    title = "GuignoMap 2025"
    sub = subtitle or "Ensemble, Redonnons espoir"
    if logo:
        img_html = f'<img src="data:image/png;base64,{logo}" style="height:48px;margin-right:12px;" />'
    else:
        # Fallback: Unicode emoji or blank
        img_html = '<span style="font-size:40px;margin-right:12px;">🎄</span>'
    st.markdown(
        f"""
        <div class="brand-header">
          <div style="display:flex;align-items:center;gap:12px;">
            {img_html}
            <div class="brand-title">{title}</div>
          </div>
          <p class="brand-sub">{sub}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    y = datetime.now().year
    st.markdown(
        f"<div class='footer'>© {y} Le Relais de Mascouche — Ensemble, Redonnons espoir.</div>",
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# PAGES
# -----------------------------------------------------------------------------

def page_accueil() -> None:
    conn = get_connection()
    render_header("Tableau de bord public (aperçu global)")

    # Compte à rebours
    st.info(f"⏰ Prochain rendez-vous : {get_compte_a_rebours()}")

    stats = db_stats_globales(conn)
    st.markdown('<div class="card metrics-card">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total rues", stats["total"])
    c2.metric("Terminées", stats["terminee"])
    c3.metric("En cours", stats["en_cours"])
    c4.metric("Non assignées", stats["non_assignees"])
    c5.metric("Progression", f"{stats['pourcentage']:.1f}%")
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("🗺️ Carte d'ensemble des rues (code couleur par statut / pointillé = non assignée)")
    with st.spinner("Génération de la carte…"):
        m = map_global(conn)
        st_folium(m, height=680, use_container_width=True)
    render_footer()


# -----------------------------
# BÉNÉVOLE
# -----------------------------

def page_benevole() -> None:
    conn = get_connection()
    render_header("Espace bénévole — simple et clair")

    # État d'authentification
    auth_key = "auth_benevole"
    if auth_key not in st.session_state:
        st.session_state[auth_key] = None

    if st.session_state[auth_key] is None:
        st.header("🙋 Connexion Bénévole")
        with st.form("login_benevole"):
            col1, col2 = st.columns(2)
            with col1:
                team_id = st.text_input("Identifiant d'équipe", placeholder="EQ001")
            with col2:
                password = st.text_input("Mot de passe", type="password")
            login = st.form_submit_button("Se connecter", use_container_width=True)
        if login:
            try:
                row = conn.execute(
                    "SELECT password_hash FROM teams WHERE id = ? AND active = 1",
                    (team_id,),
                ).fetchone()
                if row and verify_password(password, row[0]):
                    st.session_state[auth_key] = team_id
                    st.success("✅ Connexion réussie")
                    st.rerun()
                else:
                    st.error("Identifiants invalides")
            except Exception as e:
                st.error(f"Connexion impossible: {e}")
        return

    # Bénévole connecté
    team_id = st.session_state[auth_key]
    team_name = db_team_name(conn, team_id)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header(f"👥 Équipe {team_name}")
    if st.button("🚪 Se déconnecter", key="logout_benev"):
        st.session_state[auth_key] = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    total, done = db_team_progress(conn, team_id)
    pct = (done * 100.0 / total) if total else 0.0

    # Badges
    badges = []
    if done >= 1:
        badges.append("🏅 1ère rue")
    if total and done >= 0.25 * total:
        badges.append("⭐ 25%")
    if total and done >= 0.50 * total:
        badges.append("🌟 50%")
    if total and done >= 0.75 * total:
        badges.append("💫 75%")
    if total and done == total:
        badges.append("🎉 100%")

    st.markdown('<div class="card metrics-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.info(f"Progression: **{done}/{total}** rues terminées ({pct:.0f}%)")
        st.progress(done / total if total else 0.0)
        last = db_last_checkpoint(conn, team_id)
        if last:
            st.success(f"📍 Dernière activité: {last}")
    with c2:
        if badges:
            st.markdown("**🎯 Objectifs atteints**")
            st.write(" ".join(badges))
    st.markdown('</div>', unsafe_allow_html=True)

    tab_list, tab_map = st.tabs(["📋 Mes rues", "🗺️ Ma carte"])

    with tab_list:
        df = db_assigned_streets(conn, team_id)
        if df.empty:
            st.warning("Aucune rue assignée pour votre équipe.")
        else:
            for _, row in df.iterrows():
                rue = row["rue"]
                status = row["status"]
                nb = int(row["nb_adresses"]) if pd.notna(row["nb_adresses"]) else 0

                icon = "✅" if status == "terminee" else ("🛠️" if status == "en_cours" else "📍")
                st.markdown('<div class="card street-card">', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="center")
                with c1:
                    st.markdown(f"### {icon} {rue}")
                    st.caption(f"📫 {nb} adresses")
                with c2:
                    if st.button("🔄 En cours", key=f"encours_{rue}", disabled=(status == "en_cours"), use_container_width=True):
                        if set_street_status(conn, rue, "en_cours", team_id):
                            st.rerun()
                with c3:
                    if st.button("✅ Terminée", key=f"terminee_{rue}", disabled=(status == "terminee"), use_container_width=True):
                        if set_street_status(conn, rue, "terminee", team_id):
                            st.balloons()
                            st.rerun()

                with st.expander("📝 Ajouter une note"):
                    with st.form(f"note_{rue}"):
                        cA, cB = st.columns([1, 3])
                        with cA:
                            num = st.text_input("N° civique", placeholder="123", key=f"num_{rue}")
                        with cB:
                            note = st.text_area("Note", placeholder="Ex: Personne absente", key=f"txt_{rue}")
                        if st.form_submit_button("Enregistrer"):
                            if num.strip() and note.strip():
                                if add_note(conn, rue, team_id, num, note):
                                    st.success("Note enregistrée")
                            else:
                                st.warning("Veuillez saisir le numéro civique et la note.")
                st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

    with tab_map:
        with st.spinner("Carte de votre équipe…"):
            m = map_team(conn, team_id)
            st_folium(m, height=640, use_container_width=True)
    render_footer()


# -----------------------------
# GESTIONNAIRE
# -----------------------------

def page_gestionnaire() -> None:
    conn = get_connection()
    render_header("Outils du gestionnaire — équipes, secteurs, rapports")

    # Auth gestionnaire
    auth_key = "auth_admin"
    if auth_key not in st.session_state:
        st.session_state[auth_key] = False

    if not st.session_state[auth_key]:
        st.header("👔 Connexion Gestionnaire")
        with st.form("login_admin"):
            pwd = st.text_input("Mot de passe administrateur", type="password")
            ok = st.form_submit_button("Se connecter", use_container_width=True)
        if ok:
            try:
                row = conn.execute("SELECT password_hash FROM teams WHERE id='ADMIN'").fetchone()
                if row and verify_password(pwd, row[0]):
                    st.session_state[auth_key] = True
                    st.success("Connexion réussie")
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect")
            except Exception as e:
                st.error(f"Connexion impossible: {e}")
        return

    # Gestionnaire connecté
    st.header("🎛️ Tableau de bord Gestionnaire")
    if st.button("🚪 Se déconnecter", key="logout_admin"):
        st.session_state[auth_key] = False
        st.rerun()

    tabs = st.tabs(["📊 Vue d'ensemble", "👥 Gestion & Assignation", "📈 Rapports & Exports", "💳 Dons & Financement"])

    # --- Vue d'ensemble ---
    with tabs[0]:
        stats = db_stats_globales(conn)
        st.markdown('<div class="card metrics-card">', unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Rues", stats["total"])
        c2.metric("Terminées", stats["terminee"])
        c3.metric("En cours", stats["en_cours"])
        c4.metric("Non assignées", stats["non_assignees"])
        c5.metric("Progression", f"{stats['pourcentage']:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)

        st.subheader("📈 Performance par équipe")
        df_equipes = db_stats_by_team(conn)
        if not df_equipes.empty:
            fig = px.bar(df_equipes, x="equipe", y="pourcentage", title="Progression par équipe (%)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune rue encore attribuée aux équipes.")

        st.subheader("🗺️ Carte maîtresse (toutes rues)")
        with st.expander("📖 Légende", expanded=False):
            st.markdown("""
            - 🟢 **Vert** : Rue terminée
            - 🟡 **Orange** : Rue en cours
            - 🔴 **Rouge plein** : Rue assignée non commencée
            - 🔴 **Rouge pointillé** : Rue non assignée
            """)
        with st.spinner("Génération de la carte…"):
            m = map_global(conn)
            st_folium(m, height=720, use_container_width=True)
    # --- Gestion & Assignation ---
    with tabs[1]:
        pass
        st.subheader("👥 Équipes & Secteurs")
        c1, c2 = st.columns(2)

        with c1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("### ➕ Créer une équipe")
                with st.form("create_team"):
                    team_id = st.text_input("Code équipe", placeholder="EQ001")
                    team_name = st.text_input("Nom de l'équipe")
                    team_pwd = st.text_input("Mot de passe", type="password")
                    create = st.form_submit_button("Créer l'équipe")
                if create:
                    if not all([team_id, team_name, team_pwd]):
                        st.warning("Complétez tous les champs")
                    else:
                        try:
                            if bcrypt is None:
                                st.error("Module bcrypt non disponible.")
                            else:
                                hashed = bcrypt.hashpw(team_pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                                conn.execute("INSERT INTO teams (id, name, password_hash, active) VALUES (?, ?, ?, 1)",
                                             (team_id.strip(), team_name.strip(), hashed))
                                conn.commit()
                                st.success(f"Équipe {team_name} créée")
                        except sqlite3.IntegrityError:
                            st.error("Ce code d'équipe existe déjà")
                        except Exception as e:
                            st.error(f"Création impossible: {e}")
                st.markdown('</div>', unsafe_allow_html=True)

        with c2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("### 🗂️ Créer un secteur")
                with st.form("create_sector"):
                    sector_name = st.text_input("Nom du secteur")
                    add = st.form_submit_button("Créer le secteur")
                if add:
                    if not sector_name.strip():
                        st.warning("Nom de secteur requis")
                    else:
                        try:
                            conn.execute("INSERT INTO sectors (name) VALUES (?)", (sector_name.strip(),))
                            conn.commit()
                            st.success(f"Secteur {sector_name} créé")
                        except sqlite3.IntegrityError:
                            st.error("Ce secteur existe déjà")
                        except Exception as e:
                            st.error(f"Création secteur impossible: {e}")
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🎯 Assigner des rues à une équipe")

        teams = db_teams(conn)
        sectors = db_sectors(conn)
        rues_non_assignees = db_non_assigned_streets(conn)

        if not teams:
            st.info("Créez d'abord une équipe.")
        elif not rues_non_assignees:
            st.success("🎉 Toutes les rues sont déjà assignées !")
        else:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                with st.form("assign_streets_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        team_sel = st.selectbox("Équipe", options=teams, format_func=lambda t: f"{t[0]} – {t[1]}")
                    with c2:
                        sector_sel = st.selectbox(
                            "Filtrer par secteur (optionnel)",
                            options=[(None, "Tous")] + sectors,
                            format_func=lambda x: x[1] if x and x[0] is not None else "Tous",
                        )

                    options = rues_non_assignees
                    # Filtre par secteur si une colonne sector_id existe dans streets
                    try:
                        if sector_sel and sector_sel[0] is not None:
                            sid = int(sector_sel[0])
                            options = [r[0] for r in conn.execute(
                                "SELECT name FROM streets WHERE (team IS NULL OR team='') AND sector_id = ? ORDER BY name",
                                (sid,),
                            ).fetchall()]
                    except Exception:
                        pass

                    selected = st.multiselect("Rues à assigner", options=options)
                    go = st.form_submit_button("Assigner")

                if go:
                    try:
                        for rue in selected:
                            conn.execute("UPDATE streets SET team = ?, status = CASE WHEN status='a_faire' THEN 'a_faire' ELSE status END WHERE name = ?", (team_sel[0], rue))
                        conn.commit()
                        st.success(f"{len(selected)} rues assignées à {team_sel[1]}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Assignation impossible: {e}")
                st.markdown('</div>', unsafe_allow_html=True)
    # --- Rapports & Exports ---
    with tabs[2]:
        pass
        st.subheader("📦 Exports")
        st.markdown('<div class="card export-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)

        # Essayer d'utiliser un module reports dédié si présent
        reports = None
        try:
            from guignomap import reports as _reports  # type: ignore
            reports = _reports
        except Exception:
            reports = None

        with c1:
            st.markdown("#### Excel (rues & notes)")
            if st.button("Générer Excel", key="btn_excel"):
                try:
                    from io import BytesIO
                    output = BytesIO()
                    if reports and hasattr(reports, "generate_full_excel"):
                        # API optionnelle: reports.generate_full_excel(conn) -> bytes
                        data = reports.generate_full_excel(get_connection())  # type: ignore[attr-defined]
                        output.write(data)
                    else:
                        # Fallback minimal
                        df_rues = pd.read_sql_query(
                            """
                            SELECT s.name AS Rue,
                                   COALESCE(c.name, 'Non défini') AS Secteur,
                                   COALESCE(t.name, 'Non assignée') AS Équipe,
                                   CASE s.status WHEN 'terminee' THEN 'Terminée'
                                                 WHEN 'en_cours' THEN 'En cours'
                                                 ELSE 'À faire' END AS Statut,
                                   COUNT(DISTINCT a.id) AS Nb_adresses
                            FROM streets s
                            LEFT JOIN sectors c ON c.id = s.sector_id
                            LEFT JOIN teams t   ON t.id = s.team
                            LEFT JOIN addresses a ON a.street_name = s.name
                            GROUP BY s.id
                            ORDER BY c.name, s.name
                            """,
                            conn,
                        )
                        df_notes = pd.read_sql_query(
                            """
                            SELECT n.street_name AS Rue,
                                   n.address_number AS Numero,
                                   t.name AS Équipe,
                                   n.comment AS Note,
                                   n.created_at AS Date
                            FROM notes n LEFT JOIN teams t ON t.id = n.team_id
                            ORDER BY n.created_at DESC
                            """,
                            conn,
                        )
                        with pd.ExcelWriter(output, engine="openpyxl") as w:
                            df_rues.to_excel(w, sheet_name="Rues", index=False)
                            df_notes.to_excel(w, sheet_name="Notes", index=False)
                    st.download_button(
                        label="📥 Télécharger Excel",
                        data=output.getvalue(),
                        file_name=f"GuignoMap_Export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception as e:
                    st.error(f"Export Excel impossible: {e}")

        with c2:
            st.markdown("#### CSV – Rues")
            if st.button("Exporter CSV rues"):
                try:
                    if reports and hasattr(reports, "export_streets_csv"):
                        data = reports.export_streets_csv(conn)  # type: ignore[attr-defined]
                    else:
                        df = pd.read_sql_query(
                            "SELECT s.name as rue, COALESCE(c.name,'N/A') as secteur, s.team as equipe, s.status FROM streets s LEFT JOIN sectors c ON c.id = s.sector_id ORDER BY s.team, s.name",
                            conn,
                        )
                        data = df.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Télécharger CSV rues", data, file_name="guignomap_rues.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Export CSV rues impossible: {e}")

        with c3:
            st.markdown("#### CSV – Notes bénévoles")
            if st.button("Exporter CSV notes"):
                try:
                    if reports and hasattr(reports, "export_notes_csv"):
                        data = reports.export_notes_csv(conn)  # type: ignore[attr-defined]
                    else:
                        df = pd.read_sql_query(
                            "SELECT n.street_name as rue, n.address_number as numero, n.team_id as equipe, n.comment, n.created_at FROM notes n ORDER BY n.street_name, CAST(n.address_number AS INTEGER)",
                            conn,
                        )
                        data = df.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Télécharger CSV notes", data, file_name="guignomap_notes.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Export CSV notes impossible: {e}")

        st.markdown("---")
        st.info("Carré réservé à l'avenir pour PDF/rapports visuels avancés (ReportLab).")
        st.markdown('</div>', unsafe_allow_html=True)
    # --- Dons & Financement ---
    with tabs[3]:
        st.info("Intégration Square prévue ultérieurement.")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="square-cta"><img src="https://developer.squareup.com/images/logos/square-logo.svg"/> '
            'Configurer les dons en ligne avec Square (bientôt)</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
    render_footer()


# -----------------------------------------------------------------------------
# ROUTAGE PRINCIPAL
# -----------------------------------------------------------------------------

def main() -> None:
    with st.sidebar:
        st.title("🎄 Navigation")
        page = st.radio(
            "Aller à…",
            options=["🏠 Accueil", "🙋 Bénévole", "👔 Gestionnaire"],
            index=0,
            label_visibility="collapsed",
        )
        st.caption("GuignoMap v5 – 2025")

    try:
        if page.startswith("🏠"):
            page_accueil()
        elif page.startswith("🙋"):
            page_benevole()
        else:
            page_gestionnaire()
    except Exception as e:
        st.error(f"Erreur inattendue: {e}")
        st.info("Cliquez pour recharger l'application.")
        if st.button("🔄 Recharger"):
            st.rerun()


# Exécution
main()
