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

# 2. POMOĆNA FUNKCIJA ZA PROVERU PODATAKA
def ima_podatak(val):
    return str(val).strip() not in ["", "None", "nan", "-", "0", "NoneType"]

# 3. STILIZACIJA (Boje)
def apply_styling(df, should_highlight):
    if not should_highlight or 'vazi_do' not in df.columns:
        return df
    def highlight_logic(val):
        if pd.isna(val) or val == "" or val == "-": return ""
        try:
            if pd.to_datetime(val).date() < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except: pass
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

        # Čišćenje datuma
        for col in ['vazi_do', 'datum_bazdarenja', 'datum_kontrole']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # REORGANIZACIJA KOLONA (Bez ID i Lokacije)
        fiksne_prve = ['sektor', 'vrsta_opreme', 'proizvodjac', 'naziv_proizvodjac']
        fiksne_zadnje = ['putanja_folder', 'zadnja_lokacija', 'status', 'napomena']
        
        izbaci = ['id', 'inventarni_broj', 'stampac', 'gps_koordinate', 'ima_mk', 'period_provere', 
                  'godina_proizvodnje', 'upotreba_od', 'rel_vlaznost', 'opseg_merenja', 
                  'radna_temperatura', 'klasa_tacnosti', 'preciznost', 'podeok', 'lokacija']
        
        preostale = [c for c in df.columns if c not in fiksne_prve and c not in fiksne_zadnje and c not in izbaci]
        novi_poredak = fiksne_prve + preostale + fiksne_zadnje
        
        main_display = df[[c for c in novi_poredak if c in df.columns]]

        # PRIKAZ GLAVNE TABELE
        st.dataframe(apply_styling(main_display, show_colors), use_container_width=True, hide_index=True)
        st.write("---")

        # MATIČNI KARTON
        if izabrani_broj:
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                st.subheader(f"📄 Karton: {ins.get('naziv_proizvodjac', '')} | {ins.get('vrsta_opreme', '')}")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovno", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])

                with t1:
                    # Dinamičko pakovanje podataka u 4 kolone radi lepšeg izgleda
                    podaci_za_prikaz = []
                    
                    # Definišemo listu labela i ključeva koje želimo da prikažemo
                    svi_potencijalni = [
                        ("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"),
                        ("Vrsta", "vrsta_opreme"), ("Serijski br.", "seriski_broj"),
                        ("Opseg merenja", "opseg_merenja"), ("Klasa tačnosti", "klasa_tacnosti"),
                        ("Preciznost (d)", "preciznost"), ("Overeni podeok (e)", "podeok"),
                        ("Radna Temperatura", "radna_temperatura"), ("Rel. Vlažnost", "rel_vlaznost"),
                        ("Godina proizvodnje", "godina_proizvodnje"), ("U upotrebi od", "upotreba_od")
                    ]

                    # Filtriramo samo ono što postoji u bazi
                    for label, key in svi_potencijalni:
                        val = ins.get(key)
                        if ima_podatak(val):
                            podaci_za_prikaz.append((label, val))

                    # Prikazujemo u gridu (4 kolone)
                    cols = st.columns(4)
                    for i, (label, val) in enumerate(podaci_za_prikaz):
                        with cols[i % 4]:
                            st.write(f"**{label}**")
                            st.info(val)

                # OSTALI TABOVI
                with t2:
                    m_name = str(ins.get('naziv_proizvodjac', '')).strip()
                    df_k = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_name.lower()}%",))
                    if not df_k.empty: st.table(df_k.fillna("-"))
                    else: st.warning("Nema podataka o kulturama.")
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
            else:
                st.sidebar.error("Instrument nije pronađen!")
except Exception as e:
    st.error(f"Sistemska greška: {e}")
