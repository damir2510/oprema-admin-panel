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

# 2. GPS LOKATOR
def get_city_from_gps(coords):
    c = str(coords).strip().lower()
    if any(x in c for x in ["45.77", "sombor"]): return "Sombor"
    if any(x in c for x in ["45.25", "novi sad"]): return "Novi Sad"
    if c in ["nan", "none", "", "0"]: return "-"
    return "Ostalo"

# 3. POPRAVLJENA STILIZACIJA (Otporna na NaT/NaN greške)
def apply_styling(df, should_highlight):
    if not should_highlight or 'vazi_do' not in df.columns:
        return df
    
    def highlight_logic(val):
        if pd.isna(val) or val == "" or val == "-":
            return ""
        try:
            # Pretvaranje u datum radi sigurnog poređenja
            check_date = pd.to_datetime(val).date()
            if check_date < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except:
            pass
        return ""

    return df.style.applymap(highlight_logic, subset=['vazi_do'])

st.set_page_config(page_title="Radni Panel", layout="wide")
st.title("🔍 Evidencija Opreme")

# SIDEBAR
st.sidebar.header("⚙️ Kontrole")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski Broj:", "").strip()

try:
    df_raw = run_query("SELECT * FROM oprema")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        # LOGIKA ZA LOKACIJU I DATUME
        df['lokacija'] = df['gps_koordinate'].apply(get_city_from_gps)
        
        # Čišćenje datuma - pretvaramo u date format, nevalidne u NaT
        for col in ['vazi_do', 'datum_bazdarenja', 'datum_kontrole']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # REORGANIZACIJA KOLONA ZA GLAVNI EKRAN
        fiksne_prve = ['sektor', 'vrsta_opreme', 'proizvodjac', 'naziv_proizvodjac', 'lokacija']
        fiksne_zadnje = ['putanja_folder', 'zadnja_lokacija', 'status', 'napomena']
        
        izbaci = ['inventarni_broj', 'stampac', 'gps_koordinate', 'ima_mk', 'period_provere', 
                  'godina_proizvodnje', 'upotreba_od', 'rel_vlaznost', 'opseg_merenja', 
                  'radna_temperatura', 'klasa_tacnosti', 'preciznost', 'podeok']
        
        preostale = [c for c in df.columns if c not in fiksne_prve and c not in fiksne_zadnje and c not in izbaci]
        novi_poredak = fiksne_prve + preostale + fiksne_zadnje
        
        main_display = df[[c for c in novi_poredak if c in df.columns]]

        # PRIKAZ TABELE SA NOVOM STILIZACIJOM
        st.dataframe(apply_styling(main_display, show_colors), use_container_width=True, hide_index=True)
        st.write("---")

        # MATIČNI KARTON
        if izabrani_broj:
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc
                st.subheader(f"📄 Karton: {ins.get('naziv_proizvodjac', '')} | {ins.get('vrsta_opreme', '')}")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovno", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])

                with t1:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("**Identifikacija:**")
                        st.info(f"Proizvođač: {ins.get('proizvodjac', '-')}")
                        st.info(f"Model: {ins.get('naziv_proizvodjac', '-')}")
                        st.info(f"Vrsta: {ins.get('vrsta_opreme', '-')}")
                        st.info(f"Serijski br: {ins.get('seriski_broj', '-')}")
                    with c2:
                        st.markdown("**Tehnički podaci:**")
                        st.info(f"Opseg: {ins.get('opseg_merenja', '-')}")
                        # Pametno sakrivanje praznih polja
                        if str(ins.get('klasa_tacnosti', '')).strip() not in ["", "None", "nan", "-", "0"]:
                            st.info(f"Klasa: {ins.get('klasa_tacnosti')}")
                        if str(ins.get('preciznost', '')).strip() not in ["", "None", "nan", "-", "0"]:
                            st.info(f"Preciznost (d): {ins.get('preciznost')}")
                        if str(ins.get('podeok', '')).strip() not in ["", "None", "nan", "-", "0"]:
                            st.info(f"Overeni podeok (e): {ins.get('podeok')}")
                    with c3:
                        st.markdown("**Uslovi:**")
                        st.info(f"Radna Temp: {ins.get('radna_temperatura', '-')}")
                        st.info(f"Rel. Vlažnost: {ins.get('rel_vlaznost', '-')}")
                        st.info(f"Godina proizv: {ins.get('godina_proizvodnje', '-')}")

                with t2:
                    m_name = str(ins.get('naziv_proizvodjac', '')).strip()
                    df_k = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_name.lower()}%",))
                    if not df_k.empty: st.table(df_k.fillna("-"))
                    else: st.warning("Nema podataka.")
                with t3:
                    df_s = run_query("SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_s.empty: st.dataframe(df_s, use_container_width=True, hide_index=True)
                    else: st.info("Nema servisa.")
                with t4:
                    df_e = run_query("SELECT datum_etaloniranja, broj_sertifikata, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_e.empty: st.dataframe(df_e, use_container_width=True, hide_index=True)
                    else: st.info("Nema etaloniranja.")
                with t5:
                    df_b = run_query("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_b.empty: st.dataframe(df_b, use_container_width=True, hide_index=True)
                    else: st.info("Nema baždarenja.")
            else: st.sidebar.error("Nije pronađen!")
except Exception as e:
    st.error(f"Sistemska greška: {e}")
