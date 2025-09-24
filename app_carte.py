import streamlit as st
import folium
from streamlit_folium import st_folium
import sqlite3
import pandas as pd

# Connexion à la base
DB_PATH = "guignomap/guigno_map.db"
conn = sqlite3.connect(DB_PATH)

# Stats globales
stats = {}
stats["total_rues"] = pd.read_sql_query("SELECT COUNT(DISTINCT street_name) FROM addresses", conn).iloc[0,0]
stats["total_adresses"] = pd.read_sql_query("SELECT COUNT(*) FROM addresses", conn).iloc[0,0]
stats["adresses_gps"] = pd.read_sql_query("SELECT COUNT(*) FROM addresses WHERE latitude IS NOT NULL AND longitude IS NOT NULL", conn).iloc[0,0]

st.title("Carte des rues - Mascouche")
st.write(f"**Total rues:** {stats['total_rues']} | **Total adresses:** {stats['total_adresses']} | **Avec GPS:** {stats['adresses_gps']}")

# Récupérer les rues avec au moins une adresse GPS
# Nouvelle requête SQL avec jointure streets
# Récupérer la liste des secteurs pour le sélecteur
secteurs = pd.read_sql_query("SELECT DISTINCT secteur FROM streets WHERE secteur IS NOT NULL ORDER BY secteur", conn)["secteur"].dropna().tolist()
secteur_select = st.selectbox("Filtrer par secteur", ["Tous"] + secteurs)

# Requête pour récupérer les rues et leur statut
# Requête pour calculer le centre de chaque rue avec alias lat/lon
sql_points = """
SELECT
    s.name AS street_name,
    s.status,
    s.team,
    a.latitude,
    a.longitude
FROM
    addresses a
JOIN
    streets s ON a.street_name = s.name
WHERE
    a.latitude IS NOT NULL AND a.longitude IS NOT NULL
ORDER BY
    s.name, CAST(a.house_number AS INTEGER)
"""
points_df = pd.read_sql_query(sql_points, conn)

# Créer la carte Folium centrée sur Mascouche
m = folium.Map(location=[45.7475, -73.6005], zoom_start=13)

# Couleurs par status
status_colors = {
    "a_faire": "red",
    "en_cours": "orange",
    "terminee": "green"
}

# Pour chaque rue, tracer la ligne
# Dictionnaire pour les couleurs
couleurs = {
    "terminee": "green",
    "en_cours": "orange",
    "a_faire": "red"
}

# On groupe tous les points par nom de rue
for nom_rue, groupe in points_df.groupby("street_name"):
    statut = groupe["status"].iloc[0]
    couleur_ligne = couleurs.get(statut, "gray")
    coordonnees_rue = groupe[['latitude', 'longitude']].values.tolist()
    if len(coordonnees_rue) > 1:
        folium.PolyLine(
            coordonnees_rue,
            color=couleur_ligne,
            weight=6,
            opacity=0.8,
            tooltip=f"<b>{nom_rue}</b><br>Statut: {statut}"
        ).add_to(m)

# Créer la carte Folium centrée sur Mascouche
m = folium.Map(location=[45.7475, -73.6005], zoom_start=13)

# Couleurs par status
status_colors = {
    "a_faire": "red",
    "en_cours": "orange",
    "terminee": "green"
}

# Dictionnaire pour les couleurs
couleurs = {
    "terminee": "green",
    "en_cours": "orange",
    "a_faire": "red"
}

# On groupe tous les points par nom de rue
for nom_rue, groupe in points_df.groupby("street_name"):
    statut = groupe["status"].iloc[0]
    couleur_ligne = couleurs.get(statut, "gray")
    coordonnees_rue = groupe[['latitude', 'longitude']].values.tolist()
    if len(coordonnees_rue) > 1:
        folium.PolyLine(
            coordonnees_rue,
            color=couleur_ligne,
            weight=6,
            opacity=0.8,
            tooltip=f"<b>{nom_rue}</b><br>Statut: {statut}"
        ).add_to(m)

# Afficher la carte dans Streamlit
st_folium(m, height=700)

conn.close()
