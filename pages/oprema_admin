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

# --- 2. LOGIN LOGIKA (Lozinka nestaje nakon unosa) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

login_placeholder = st.empty()

if not st.session_state.authenticated:
    with login_placeholder.container():
        st.subheader("🔐 Admin Pristup")
        password = st.text_input("Unesite lozinku:", type="password")
        if password == "bvadmin": # <--- OVDE POSTAVI SVOJU LOZINKU
            st.session_state.authenticated = True
            login_placeholder.empty()
            st.rerun()
        elif password:
            st.error("Pogrešna lozinka")
        st.stop()

# --- 3. KONEKCIJA KA BAZI ---
def get_conn():
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin", password="AVNS_0qoNdSQVUuF9wTfHN8D",
        port=27698, database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'},
        autocommit=True
    )

# --- 4. GPS LOGIKA (Iz GPS kolone izvlači Grad) ---
def get_city_from_gps(coords):
    if pd.isna(coords) or str(coords).strip() in ["", "0", "-", "nan"]:
        return "-"
    try:
        parts = str(coords).replace(',', ' ').split()
        if len(parts) >= 2:
            lat = float(parts[0])
            lon = float(parts[1])
            if 45.70 <= lat <= 45.85 and 19.00 <= lon <= 19.25: return "Sombor"
            if 45.15 <= lat <= 45.35 and 19.70 <= lon <= 19.95: return "Novi Sad"
            if 46.00 <= lat <= 46.15 and 19.55 <= lon <= 19.75: return "Subotica"
    except:
        pass
    return "Nepoznata lokacija"

# --- 5. GLAVNI ADMIN PANEL ---
st.title("🛠 Admin Panel - Upravljanje")

try:
    conn = get_conn()
    df_raw = pd.read_sql("SELECT * FROM oprema", conn)
    
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        
        # 1. Automatsko pretvaranje GPS-a u Grad
        if 'gps_koordinate' in df.columns:
            df['zadnja_lokacija'] = df['gps_koordinate'].apply(get_city_from_gps)

        # 2. Sređivanje datuma
        for col in ['vazi_do', 'datum_bazdarenja', 'datum_kontrole']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # 3. Kolone i poredak
        prve = ['sektor', 'vrsta_opreme', 'proizvodjac', 'naziv_proizvodjac', 'zadnja_lokacija']
        zadnje = ['putanja_folder', 'status', 'napomena']
        izbaci = ['id', 'gps_koordinate', 'stampac', 'ima_mk', 'period_provere', 'godina_proizvodnje', 
                  'upotreba_od', 'rel_vlaznost', 'opseg_merenja', 'radna_temperatura', 
                  'klasa_tacnosti', 'preciznost', 'podeok']
        
        preostale = [c for c in df.columns if c not in prve and c not in zadnje and c not in izbaci]
        novi_poredak = ['id'] + prve + preostale + zadnje

        st.subheader("📝 Brza izmena baze podataka")
        
        # DATA EDITOR
        edited_df = st.data_editor(
            df[novi_poredak],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, # Sakrivamo ID da ne smeta
                "status": st.column_config.SelectboxColumn("Status", options=["U radu", "Van upotrebe", "Na servisu", "Otpisano"]),
                "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY"),
                "putanja_folder": st.column_config.LinkColumn("Link")
            },
            key="admin_editor_v3"
        )

        st.write("##")

        # 4. DUGME ZA ČUVANJE
        if st.button("💾 SAČUVAJ SVE IZMENE", type="primary", use_container_width=True):
            try:
                with conn.cursor() as cursor:
                    for index, row in edited_df.iterrows():
                        row_id = row['id']
                        sql = """
                            UPDATE oprema 
                            SET sektor=%s, vrsta_opreme=%s, proizvodjac=%s, 
                                naziv_proizvodjac=%s, status=%s, napomena=%s, 
                                vazi_do=%s, zadnja_lokacija=%s 
                            WHERE id=%s
                        """
                        cursor.execute(sql, (
                            row.get('sektor'), row.get('vrsta_opreme'), row.get('proizvodjac'),
                            row.get('naziv_proizvodjac'), row.get('status'), row.get('napomena'),
                            row.get('vazi_do'), row.get('zadnja_lokacija'), row_id
                        ))
                st.success("✅ Podaci su uspešno ažurirani u bazi!")
                st.rerun()
            except Exception as db_err:
                st.error(f"Greška pri upisu u SQL: {db_err}")

    conn.close()
except Exception as e:
    st.error(f"Sistemska greška: {e}")

# EXCEL EXPORT
if not df_raw.empty:
    st.sidebar.divider()
    output = io.BytesIO()
    df_raw.to_excel(output, index=False)
    st.sidebar.download_button("📥 Preuzmi bazu (Excel)", output.getvalue(), "admin_export.xlsx", use_container_width=True)
