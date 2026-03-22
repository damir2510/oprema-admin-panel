import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from db_utils import run_query

# --- 1. DEFINICIJA NAVIGACIJE (Dosledno korišćenje objekata) ---


st.sidebar.header("🚀 Navigacija")

if st.sidebar.button("🗺️ Mapa opreme", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🛠️ Admin Panel", use_container_width=True):
    st.switch_page("pages/oprema_admin.py")



st.sidebar.markdown("---")

st.title("📍 Interaktivna Mapa Opreme")

# --- 2. POVLAČENJE PODATAKA ---
query = """
SELECT inventarni_broj, naziv_proizvodjac, gps_koordinate, 
       trenutni_radnik, status, zadnja_lokacija 
FROM oprema
"""
df = run_query(query)

if not df.empty:
    locations = []
    for _, row in df.iterrows():
        gps = row.get('gps_koordinate')
        if gps and "," in str(gps):
            try:
                # Popravljeno: uzimanje elemenata iz split liste
                parts = str(gps).replace(' ', '').split(',')
                lat, lon = float(parts[0]), float(parts[1])
                
                locations.append({
                    'lat': lat, 'lon': lon,
                    'info': f"**Inv:** {row['inventarni_broj']} <br> **Model:** {row['naziv_proizvodjac']}",
                    'radnik': row.get('trenutni_radnik', '-'),
                    'status': str(row.get('status', '')).lower(),
                    'grad': row.get('zadnja_lokacija', '-')
                })
            except:
                continue

    if locations:
        # Centriranje na prvu lokaciju
        m = folium.Map(location=[locations[0]['lat'], locations[0]['lon']], zoom_start=8)

        for loc in locations:
            # Boja čiode
            color = 'green' if any(x in loc['status'] for x in ['rad', 'ispravno', 'u radu']) else 'red'

            popup_text = f"""
                <div style='font-family: sans-serif; font-size: 13px;'>
                    {loc['info']} <br>
                    <b>Lokacija:</b> {loc['grad']} <br>
                    <b>Zadužio:</b> {loc['radnik']}
                </div>
            """

            folium.Marker(
                [loc['lat'], loc['lon']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip="Klikni za detalje",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)

        # Prikaz mape
        st_folium(m, width="100%", height=600)
    else:
        st.warning("⚠️ Nema validnih GPS koordinata (format: lat, lon).")
else:
    st.info("Baza je trenutno prazna ili nema podataka za prikaz.")

st.sidebar.info("💡 GPS format u bazi: **45.834, 19.123**")
