import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from db_utils import run_query

# 1. KONFIGURACIJA (Mora biti na vrhu za punu širinu ekrana)
st.set_page_config(page_title="Mapa Opreme", layout="wide")

# CSS za sakrivanje navigacije (ako želiš da sakriješ rakete)
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] ul { display: none; }
        .stMain { padding: 0rem; } /* Smanjuje margine za veću mapu */
    </style>
""", unsafe_allow_html=True)

# 2. NAVIGACIJA
p_oprema = st.Page("pages/oprema.py")
if st.sidebar.button("⬅️ Nazad na Pregled", use_container_width=True):
    st.switch_page(p_oprema)

st.title("📍 Interaktivna Mapa Opreme")

# 3. POVLAČENJE I PRETRAGA
query = "SELECT inventarni_broj, naziv_proizvodjac, gps_koordinate, trenutni_radnik, status, zadnja_lokacija, sektor FROM oprema"
df_all = run_query(query)

if not df_all.empty:
    # --- POLJE ZA PRETRAGU ---
    search = st.text_input("🔍 Pretraži mapu (Sektor, Radnik ili Model):", "").lower()
    
    df = df_all.copy()
    if search:
        mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(search)).any(axis=1)
        df = df[mask]

    # --- OBRADA KOORDINATA ---
    locations = []
    for _, row in df.iterrows():
        gps = row.get('gps_koordinate')
        if gps and "," in str(gps):
            try:
                parts = str(gps).replace(' ', '').split(',')
                lat, lon = float(parts[0]), float(parts[1])
                locations.append({
                    'lat': lat, 'lon': lon,
                    'info': f"<b>Inv:</b> {row['inventarni_broj']}<br><b>Model:</b> {row['naziv_proizvodjac']}",
                    'radnik': row.get('trenutni_radnik', '-'),
                    'status': str(row.get('status', '')).lower(),
                    'grad': row.get('zadnja_lokacija', '-')
                })
            except: continue

    if locations:
        # 4. KREIRANJE MAPE (Širina 100%)
        m = folium.Map(location=[locations[0]['lat'], locations[0]['lon']], zoom_start=8, control_scale=True)
        
        for loc in locations:
            color = 'green' if any(x in loc['status'] for x in ['rad', 'ispravno', 'u radu']) else 'red'
            popup_html = f"<div style='width:200px;'>{loc['info']}<br><b>Lokacija:</b> {loc['grad']}<br><b>Zadužio:</b> {loc['radnik']}</div>"
            
            folium.Marker(
                [loc['lat'], loc['lon']],
                popup=folium.Popup(popup_html, max_width=250),
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)

        # KLJUČ ZA VELIČINU: st_folium sa width=None se širi na ceo kontejner
        st_folium(m, width=1500, height=700, returned_objects=[])
    else:
        st.warning("Nema rezultata za vašu pretragu ili fale GPS koordinate.")
else:
    st.info("Baza je prazna.")
