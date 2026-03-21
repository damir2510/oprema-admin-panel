import streamlit as st
import pandas as pd
import pymysql
import folium
from streamlit_folium import st_folium

# --- 1. NAVIGACIJA (Dugmići za brzi prelaz) ---
st.sidebar.header("🚀 Navigacija")
if st.sidebar.button("📋 Pregled Opreme", use_container_width=True):
    st.switch_page("pages/oprema.py")

if st.sidebar.button("🛠️ Admin Panel", use_container_width=True):
    st.switch_page("pages/oprema_admin.py")

st.sidebar.markdown("---")

# --- 2. FUNKCIJA ZA PODATKE ---
def get_map_data():
    try:
        conn = pymysql.connect(
            host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
            user="avnadmin", password="AVNS_0qoNdSQVUuF9wTfHN8D",
            port=27698, database="defaultdb",
            cursorclass=pymysql.cursors.DictCursor,
            ssl={'ssl-mode': 'REQUIRED'}
        )
        with conn.cursor() as cursor:
            # Povlačimo i zadnju_lokaciju radi boljeg info-prozora
            cursor.execute("SELECT inventarni_broj, naziv_proizvodjac, gps_koordinate, trenutni_radnik, status, zadnja_lokacija FROM oprema")
            result = cursor.fetchall()
        conn.close()
        return pd.DataFrame(result)
    except Exception as e:
        st.error(f"Greška sa bazom: {e}")
        return pd.DataFrame()

st.title("📍 Interaktivna Mapa Opreme")

df = get_map_data()

if not df.empty:
    # --- 3. OBRADA GPS KOORDINATA ---
    locations = []
    for _, row in df.iterrows():
        gps = row['gps_koordinate']
        if gps and "," in str(gps):
            try:
                # Čistimo razmake i delimo koordinate
                parts = str(gps).replace(' ', '').split(',')
                lat, lon = float(parts[0]), float(parts[1])
                
                locations.append({
                    'lat': lat, 'lon': lon,
                    'info': f"**Inv:** {row['inventarni_broj']} <br> **Model:** {row['naziv_proizvodjac']}",
                    'radnik': row.get('trenutni_radnik', '-'),
                    'status': str(row['status']).lower(),
                    'grad': row.get('zadnja_lokacija', '-')
                })
            except:
                continue

    if locations:
        # Centriramo mapu na prvu lokaciju ili fiksno na Srbiju (44.8, 20.4)
        m = folium.Map(location=[locations[0]['lat'], locations[0]['lon']], zoom_start=8)

        for loc in locations:
            # Boja čiode: zelena za 'u radu' ili 'ispravno', crvena za ostalo
            color = 'green' if any(x in loc['status'] for x in ['rad', 'ispravno']) else 'red'

            # HTML za Popup prozorčić
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
                tooltip=f"Klikni: {row['naziv_proizvodjac']}",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)

        # Prikaz mape preko celog ekrana
        st_folium(m, width="100%", height=600)
    else:
        st.warning("⚠️ Nema validnih GPS koordinata za prikaz (format u bazi mora biti: lat, lon).")
else:
    st.info("Baza je trenutno prazna.")
