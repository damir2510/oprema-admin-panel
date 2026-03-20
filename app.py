import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# 1. OPTIMIZOVANA KONEKCIJA (Sa automatskim zatvaranjem)
def run_query(query, params=None):
    conn = pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin",
        password="AVNS_0qoNdSQVUuF9wTfHN8D",
        port=27698,
        database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'}
    )
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return pd.DataFrame(cur.fetchall())
    finally:
        conn.close()

# Bojenje isteka
def highlight_expiry(val):
    try:
        if pd.to_datetime(val).date() < datetime.now().date():
            return "background-color: #ff4b4b; color: white"
    except:
        pass
    return ""

st.set_page_config(page_title="Radni Panel", layout="wide")
st.title("🔍 Evidencija Opreme")

# 2. GLAVNI PODACI
try:
    df = run_query("SELECT * FROM oprema")
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]
        # Čišćenje duplih headera iz baze
        df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        search_query = st.text_input("🔍 Brza pretraga:", key="main_search")
        df_display = df[df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)] if search_query else df
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.sidebar.header("Filter")
        izabrani_broj = st.sidebar.text_input("🔢 Inventarski Broj:", "").strip()

        if izabrani_broj:
            # Precizno filtriranje (trimujemo sve za svaki slučaj)
            rezultat = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            
            if not rezultat.empty:
                instrument = rezultat.iloc[0]
                model_iz_opreme = str(instrument.get('naziv_proizvodjac', '')).strip()
                
                st.subheader(f"📄 Karton: {izabrani_broj} - {model_iz_opreme}")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovno", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])

                with t1:
                    c1, c2, c3, c4 = st.columns(4)
                    fields = [
                        ("Vrsta", "vrsta_opreme"), ("Proizvođač", "proizvodjac"),
                        ("Model", "naziv_proizvodjac"), ("Serijski br.", "seriski_broj"),
                        ("Opseg", "opseg_merenja"), ("Klasa", "klasa_tacnosti"),
                        ("Preciznost", "preciznost"), ("Podeok", "podeok")
                    ]
                    for i, (label, col) in enumerate(fields):
                        val = instrument.get(col, "-")
                        with [c1, c2, c3, c4][i % 4]:
                            st.metric(label, str(val))

                with t2:
                    # FLEKSIBILNA PRETRAGA KULTURA (LIKE operator je sigurniji)
                    q_kulture = "SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s"
                    df_k = run_query(q_kulture, (f"%{model_iz_opreme.lower()}%",))
                    
                    if not df_k.empty:
                        # Izbacujemo red koji je možda header u bazi
                        df_k = df_k[df_k['kultura'].astype(str).str.lower() != 'kultura']
                        st.table(df_k.fillna("-"))
                    else:
                        st.warning(f"Nema definisanih kultura za model: {model_iz_opreme}")

                with t3:
                    df_s = run_query("SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                    st.dataframe(df_s, use_container_width=True) if not df_s.empty else st.info("Nema servisa.")

                with t4:
                    df_e = run_query("SELECT datum_etaloniranja, broj_sertifikata, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_e.empty:
                        st.dataframe(df_e.style.applymap(highlight_expiry, subset=['vazi_do']), use_container_width=True)
                    else: st.info("Nema etaloniranja.")

                with t5:
                    df_b = run_query("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_b.empty:
                        st.dataframe(df_b.style.applymap(highlight_expiry, subset=['vazi_do']), use_container_width=True)
                    else: st.info("Nema baždarenja.")

            else:
                st.error("Instrument sa tim brojem nije pronađen u bazi.")
except Exception as e:
    st.error(f"Sistemska greška: {e}")

