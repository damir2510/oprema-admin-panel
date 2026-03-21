import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime
import io

# --- 1. LOGIN LOGIKA (Lozinka nestaje nakon unosa) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

login_placeholder = st.empty()

if not st.session_state.authenticated:
    with login_placeholder.container():
        st.subheader("🔐 Admin Pristup")
        password = st.text_input("Unesite lozinku:", type="password")
        if password == "tvoja_lozinka": # <--- OVDE POSTAVI SVOJU LOZINKU
            st.session_state.authenticated = True
            login_placeholder.empty()
            st.rerun()
        elif password:
            st.error("Pogrešna lozinka")
        st.stop()

# --- 2. KONEKCIJA KA BAZI ---
def get_conn():
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin", password="AVNS_0qoNdSQVUuF9wTfHN8D",
        port=27698, database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'},
        autocommit=True
    )

# --- 3. GPS LOGIKA (Iz GPS kolone izvlači Grad) ---
def get_city_from_gps(coords):
    if pd.isna(coords) or str(coords).strip() in ["", "0", "-", "nan"]:
        return "-"
    try:
        # Čišćenje i razdvajanje koordinata (npr. "45.77, 19.11")
        parts = str(coords).replace(',', ' ').split()
        lat = float(parts[0])
        lon = float(parts[1])
        # Širi opsezi za gradove
        if 45.70 <= lat <= 45.85 and 19.00 <= lon <= 19.25: return "Sombor"
        if 45.15 <= lat <= 45.35 and 19.70 <= lon <= 19.95: return "Novi Sad"
        if 46.00 <= lat <= 46.15 and 19.55 <= lon <= 19.75: return "Subotica"
    except:
        pass
    return "Nepoznata lokacija"

# --- 4. GLAVNI ADMIN PANEL ---
st.set_page_config(page_title="Admin Panel - Uređivanje", layout="wide")
st.title("🛠 Admin Panel - Upravljanje i Lokacije")

try:
    conn = get_conn()
    # Povlačimo sve podatke (uključujući ID koji ćemo sakriti)
    df_raw = pd.read_sql("SELECT * FROM oprema", conn)
    
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        
        # 1. Automatsko pretvaranje GPS-a u Grad (da bi SQL video promenu)
        if 'gps_koordinate' in df.columns:
            df['zadnja_lokacija'] = df['gps_koordinate'].apply(get_city_from_gps)

        # 2. Sređivanje datuma za prikaz (bez vremena)
        for col in ['vazi_do', 'datum_bazdarenja', 'datum_kontrole']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # 3. Definisanje redosleda kolona
        prve = ['sektor', 'vrsta_opreme', 'proizvodjac', 'naziv_proizvodjac', 'zadnja_lokacija']
        zadnje = ['putanja_folder', 'status', 'napomena']
        # Kolone koje ne želimo da vidimo (ali ID ostaje u podacima)
        izbaci = ['id', 'gps_koordinate', 'stampac', 'ima_mk', 'period_provere', 'godina_proizvodnje', 
                  'upotreba_od', 'rel_vlaznost', 'opseg_merenja', 'radna_temperatura', 
                  'klasa_tacnosti', 'preciznost', 'podeok']
        
        preostale = [c for c in df.columns if c not in prve and c not in zadnje and c not in izbaci]
        # Redosled za prikaz (uključujemo 'id' jer nam treba za UPDATE, ali ćemo ga sakriti preko config-a)
        novi_poredak = ['id'] + prve + preostale + zadnje

        st.subheader("📝 Brza izmena podataka")
        st.caption("Izmenite Status, Napomenu ili bilo koje polje direktno u tabeli i kliknite na dugme ispod.")

        # DATA EDITOR (Glavni alat za Admina)
        edited_df = st.data_editor(
            df[novi_poredak],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, # <--- SAKRIVA ID KOLONU (Korisnik je ne vidi, ali Python je koristi)
                "status": st.column_config.SelectboxColumn("Status", options=["U radu", "Van upotrebe", "Na servisu", "Otpisano"]),
                "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY"),
                "putanja_folder": st.column_config.LinkColumn("Link")
            },
            key="admin_main_editor"
        )

        st.write("##")

        # 4. DUGME ZA TRAJNO ČUVANJE U SQL BAZU
        if st.button("💾 SAČUVAJ SVE IZMENE", type="primary", use_container_width=True):
            try:
                with conn.cursor() as cursor:
                    for index, row in edited_df.iterrows():
                        # Koristimo ID direktno iz reda editora za precizan upis
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
                
                st.success("✅ Izmene i lokacije su uspešno upisane u bazu podataka!")
                # Pauza mala pre osvežavanja
                st.rerun()
                
            except Exception as db_err:
                st.error(f"Greška pri upisu u SQL: {db_err}")

    conn.close()

except Exception as e:
    st.error(f"Sistemska greška: {e}")

# --- DODATAK: EXCEL EXPORT (Opciono za Admina) ---
if not df_raw.empty:
    st.sidebar.divider()
    if st.sidebar.button("📥 Export u Excel"):
        output = io.BytesIO()
        df_raw.to_excel(output, index=False)
        st.sidebar.download_button("Preuzmi fajl", output.getvalue(), "evidencija_admin.xlsx")
