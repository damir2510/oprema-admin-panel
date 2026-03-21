import streamlit as st
import pandas as pd
import pymysql

# --- KONFIGURACIJA STRANE ---
st.set_page_config(page_title="Mapa Opreme", layout="wide", page_icon="🗺️")

# 1. DEFINISANJE STRANICA ZA NAVIGACIJU (Da switch_page radi)
p_oprema = st.Page("pages/oprema.py", title="Oprema")

# 2. DUGME ZA POVRATAK (Na vrhu sidebara)
if st.sidebar.button("⬅️ Nazad na Pregled", use_container_width=True):
    st.switch_page(p_oprema)

st.sidebar.markdown("---")

# 3. FUNKCIJA ZA RAD SA BAZOM
def run_query(query):
    try:
        conn = pymysql.connect(
            host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
            user="avnadmin",
            password="AVNS_0qoNdSQVUuF9wTfHN8D",
            port=27698,
            database="defaultdb",
            cursorclass=pymysql.cursors.DictCursor,
            ssl={'ssl-mode': 'REQUIRED'}
        )
        with conn.cursor() as cur:
            cur.execute(query)
            return pd.DataFrame(cur.fetchall())
    except Exception as e:
        st.error(f"Greška sa bazom: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals(): conn.close()

st.title("🗺️ Mapa Lokacija Opreme")
st.write("Prikaz instrumenata na terenu na osnovu GPS koordinata iz baze.")

# 4. IZVLAČENJE I OBRADA PODATAKA
df = run_query("SELECT inventarni_broj, naziv_proizvodjac, vrsta_opreme, gps_koordinate, zadnja_lokacija FROM oprema")

if not df.empty:
    # Filtriramo samo one koji imaju upisane koordinate
    df = df[df['gps_koordinate'].fillna('').str.contains(',')]
    
    def ocisti_koordinate(coord_str):
        try:
            # Razdvajamo npr "45.123, 19.456" na lat i lon
            lat, lon = coord_str.split(',')
            return float(lat.strip()), float(lon.strip())
        except:
            return None, None

    # Primena čišćenja
    df[['latitude', 'longitude']] = df['gps_koordinate'].apply(lambda x: pd.Series(ocisti_koordinate(x)))
    
    # Izbacujemo redove gde čišćenje nije uspelo
    df = df.dropna(subset=['latitude', 'longitude'])

    if not df.empty:
        # Prikaz mape
        # Streamlit automatski prepoznaje kolone 'latitude' i 'longitude'
        st.map(df, size=20, color='#ff4b4b')
        
        # Tabela ispod mape za proveru
        with st.expander("📍 Lista lokacija (tabela)"):
            st.dataframe(df[['inventarni_broj', 'naziv_proizvodjac', 'zadnja_lokacija', 'gps_koordinate']], use_container_width=True, hide_index=True)
    else:
        st.warning("Pronađeni su zapisi, ali format GPS koordinata nije ispravan (mora biti: lat, lon).")
else:
    st.info("Nema podataka sa GPS koordinatama u bazi.")

st.sidebar.info("💡 Savet: GPS koordinate u bazi treba da budu u formatu: **45.834, 19.123**")
