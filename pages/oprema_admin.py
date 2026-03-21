import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime
import io

# --- 1. NAVIGACIJA (Dugmići za brzi prelaz) ---
st.sidebar.header("🚀 Navigacija")
if st.sidebar.button("📋 Pregled Opreme", use_container_width=True):
    st.switch_page("pages/oprema.py")
if st.sidebar.button("📍 Mapa opreme", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")
st.sidebar.markdown("---")

# --- 2. LOGIN LOGIKA ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

login_placeholder = st.empty()
if not st.session_state.authenticated:
    with login_placeholder.container():
        st.subheader("🔐 Admin Pristup")
        password = st.text_input("Lozinka:", type="password")
        if password == "bvadmin2024": # <--- POSTAVI LOZINKU
            st.session_state.authenticated = True
            login_placeholder.empty()
            st.rerun()
        st.stop()

# --- 3. KONEKCIJA ---
def get_conn():
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin", password="AVNS_0qoNdSQVUuF9wTfHN8D",
        port=27698, database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'},
        autocommit=True
    )

# --- 4. GPS LOGIKA ---
def get_city_from_gps(coords):
    if pd.isna(coords) or str(coords).strip() in ["", "0", "-", "nan"]:
        return "-"
    try:
        parts = str(coords).replace(',', ' ').split()
        lat, lon = float(parts[0]), float(parts[1])
        if 45.70 <= lat <= 45.85 and 19.00 <= lon <= 19.25: return "Sombor"
        if 45.15 <= lat <= 45.35 and 19.70 <= lon <= 19.95: return "Novi Sad"
        return "Nepoznato"
    except: return "-"

# --- 5. GLAVNI PANEL ---
st.title("🛠 Admin Panel - Upravljanje Opremom")

try:
    conn = get_conn()
    df_raw = pd.read_sql("SELECT * FROM oprema", conn)
    
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        
        # BRISANJE DUPLIH NASLOVA (Ako u redovima piše 'sektor', 'vrsta' itd)
        df = df[df['sektor'].astype(str).str.lower() != 'sektor']

        # GPS u Grad
        if 'gps_koordinate' in df.columns:
            df['zadnja_lokacija'] = df['gps_koordinate'].apply(get_city_from_gps)

        # Datumi
        for col in ['vazi_do', 'datum_bazdarenja', 'datum_kontrole']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # Poredak kolona
        prve = ['sektor', 'vrsta_opreme', 'proizvodjac', 'naziv_proizvodjac', 'zadnja_lokacija']
        zadnje = ['putanja_folder', 'status', 'napomena']
        izbaci = ['id', 'gps_koordinate', 'stampac', 'ima_mk', 'period_provere', 'godina_proizvodnje', 
                  'upotreba_od', 'rel_vlaznost', 'opseg_merenja', 'radna_temperatura', 
                  'klasa_tacnosti', 'preciznost', 'podeok']
        
        preostale = [c for c in df.columns if c not in prve and c not in zadnje and c not in izbaci]
        novi_poredak = ['id'] + prve + preostale + zadnje

        # ŠIROKI PRIKAZ TABELE
        st.subheader("📝 Brza izmena")
        edited_df = st.data_editor(
            df[novi_poredak],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, 
                "status": st.column_config.SelectboxColumn("Status", options=["U radu", "Van upotrebe", "Na servisu", "Otpisano"]),
                "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY"),
                "putanja_folder": st.column_config.LinkColumn("Link")
            }
        )

        if st.button("💾 SAČUVAJ SVE IZMENE", type="primary", use_container_width=True):
            with conn.cursor() as cursor:
                for _, row in edited_df.iterrows():
                    sql = """UPDATE oprema SET sektor=%s, vrsta_opreme=%s, proizvodjac=%s, 
                             naziv_proizvodjac=%s, status=%s, napomena=%s, vazi_do=%s, zadnja_lokacija=%s WHERE id=%s"""
                    cursor.execute(sql, (row.get('sektor'), row.get('vrsta_opreme'), row.get('proizvodjac'),
                                       row.get('naziv_proizvodjac'), row.get('status'), row.get('napomena'),
                                       row.get('vazi_do'), row.get('zadnja_lokacija'), row.get('id')))
            st.success("✅ Uspešno sačuvano!")
            st.rerun()

    conn.close()
except Exception as e:
    st.error(f"Greška: {e}")

# EXPORT
if not df_raw.empty:
    st.sidebar.divider()
    output = io.BytesIO()
    df_raw.to_excel(output, index=False, engine='openpyxl')
    st.sidebar.download_button("📥 Excel Export", output.getvalue(), "admin_oprema.xlsx", use_container_width=True)
