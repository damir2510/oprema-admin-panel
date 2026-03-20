import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# 1. FUNKCIJA ZA RAD SA BAZOM
def run_query(query, params=None):
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
            cur.execute(query, params)
            return pd.DataFrame(cur.fetchall())
    finally:
        if 'conn' in locals(): conn.close()

# 2. POMOĆNA FUNKCIJA ZA GPS -> GRAD (Primer logike)
def get_city_from_gps(coords):
    coords = str(coords).strip().lower()
    if "45.77" in coords or "sombor" in coords: return "Sombor"
    if "45.25" in coords or "novi sad" in coords: return "Novi Sad"
    if "44.81" in coords or "beograd" in coords: return "Beograd"
    if coords in ["nan", "none", "", "0"]: return "-"
    return "Nepoznato"

# 3. FUNKCIJA ZA BOJENJE
def apply_styling(df, should_highlight):
    if not should_highlight or 'vazi_do' not in df.columns:
        return df
    
    def highlight_row(val):
        try:
            if pd.to_datetime(val).date() < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except:
            pass
        return ""

    return df.style.applymap(highlight_row, subset=['vazi_do'])

st.set_page_config(page_title="Radni Panel", layout="wide")
st.title("🔍 Evidencija Opreme")

# SIDEBAR
st.sidebar.header("⚙️ Podešavanja")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski Broj:", "").strip()

try:
    df_raw = run_query("SELECT * FROM oprema")
    
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        # OBRADA PODATAKA ZA GLAVNU TABELU
        if 'gps_koordinate' in df.columns:
            df['lokacija'] = df['gps_koordinate'].apply(get_city_from_gps)

        for col in ['vazi_do', 'datum_bazdarenja', 'datum_kontrole']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # KOLONE ZA IZBACIVANJE IZ GLAVNE TABELE
        izbaci = [
            'inventarni_broj', 'stampac', 'gps_koordinate', 'ima_mk',
            'period_provere', 'godina_proizvodnje', 'upotreba_od', 
            'rel_vlaznost', 'opseg_merenja', 'radna_temperatura', 
            'klasa_tacnosti', 'preciznost', 'podeok'
        ]
        
        main_display = df.drop(columns=[c for c in izbaci if c in df.columns])

        # PRIKAZ GLAVNE TABELE
        st.subheader("📋 Pregled instrumenata")
        styled_df = apply_styling(main_display, show_colors)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        st.write("---")

        # MATIČNI KARTON
        if izabrani_broj:
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            
            if not rez.empty:
                ins = rez.iloc[0]
                st.subheader(f"📄 Matični Karton: {ins.get('naziv_proizvodjac', '')}")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovno", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])

                with t1:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write("**Identifikacija:**")
                        st.info(f"Proizvođač: {ins.get('proizvodjac', '-')}")
                        st.info(f"Model: {ins.get('naziv_proizvodjac', '-')}")
                        st.info(f"Serijski br: {ins.get('seriski_broj', '-')}")
                    with c2:
                        st.write("**Tehnički podaci:**")
                        st.info(f"Opseg: {ins.get('opseg_merenja', '-')}")
                        st.info(f"Klasa: {ins.get('klasa_tacnosti', '-')}")
                        st.info(f"Preciznost: {ins.get('preciznost', '-')}")
                        st.info(f"Podeok: {ins.get('podeok', '-')}")
                    with c3:
                        st.write("**Uslovi i Proizvodnja:**")
                        st.info(f"Radna Temp: {ins.get('radna_temperatura', '-')}")
                        st.info(f"Rel. Vlažnost: {ins.get('rel_vlaznost', '-')}")
                        st.info(f"Godina proizv: {ins.get('godina_proizvodnje', '-')}")
                        st.info(f"Upotreba od: {ins.get('upotreba_od', '-')}")

                # TABOVI (Rešen DeltaGenerator problem razdvajanjem redova)
                with t2:
                    model_name = str(ins.get('naziv_proizvodjac', '')).strip()
                    df_k = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{model_name.lower()}%",))
                    if not df_k.empty:
                        st.table(df_k.fillna("-"))
                    else:
                        st.warning("Nema podataka o kulturama.")

                with t3:
                    df_s = run_query("SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_s.empty:
                        st.dataframe(df_s, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nema servisa.")

                with t4:
                    df_e = run_query("SELECT datum_etaloniranja, broj_sertifikata, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_e.empty:
                        st.dataframe(df_e, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nema etaloniranja.")

                with t5:
                    df_b = run_query("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_b.empty:
                        st.dataframe(df_b, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nema baždarenja.")
            else:
                st.sidebar.error("Instrument nije pronađen!")

except Exception as e:
    st.error(f"Sistemska greška: {e}")
