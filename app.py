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

# 2. FUNKCIJA ZA BOJENJE (Samo ako je prekidač uključen)
def highlight_expiry(val, should_highlight):
    if not should_highlight:
        return ""
    try:
        date_val = pd.to_datetime(val).date()
        if date_val < datetime.now().date():
            return "background-color: #ff4b4b; color: white"
    except:
        pass
    return ""

st.set_page_config(page_title="Radni Panel", layout="wide")
st.title("🔍 Evidencija Opreme")

# SIDEBAR KONTROLE
st.sidebar.header("⚙️ Podešavanja prikaza")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Unesi Inventarski Broj za Karton:", "").strip()

try:
    df_raw = run_query("SELECT * FROM oprema")
    
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        # OBRADA DATUMA (Uklanjanje vremena)
        date_cols = ['vazi_do', 'datum_bazdarenja', 'datum_kontrole']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # IZBACIVANJE KOLONA IZ GLAVNE TABELE
        kolone_za_izbacivanje = [
            'inventarni_broj', 'stampac', 'gps_koordinate', 'ima_mk',
            'period_provere', 'godina_proizvodnje', 'upotreba_od', 
            'relativna_vlaznost', 'opseg_merenja', 'temperatura', 
            'klasa_tacnosti', 'preciznost', 'podeok'
        ]
        
        # Prikazujemo samo one koje postoje u bazi
        display_df = df.drop(columns=[c for c in kolone_za_izbacivanje if c in df.columns])

        # PRIKAZ GLAVNE TABELE SA BOJAMA
        st.subheader("📋 Pregled instrumenata")
        
        # Primena boja na kolonu 'vazi_do' (bazdarenje)
        if show_colors and 'vazi_do' in display_df.columns:
            styled_df = display_df.style.applymap(
                lambda x: highlight_expiry(x, show_colors), subset=['vazi_do']
            )
        else:
            styled_df = display_df

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        st.write("---")

        # MATIČNI KARTON
        if izabrani_broj:
            # Tražimo u originalnom df_raw da bi imali sve podatke
            rezultat = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            
            if not rezultat.empty:
                ins = rezultat.iloc[0]
                st.subheader(f"📄 Matični Karton: {ins.get('naziv_proizvodjac', 'Nepoznato')} (Inv: {izabrani_broj})")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])

                with t1:
                    # Grupisanje podataka u kolone (ovde idu oni izbačeni iz glavne tabele)
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write("**Tehničke specifikacije:**")
                        st.info(f"Opseg: {ins.get('opseg_merenja', '-')}")
                        st.info(f"Klasa: {ins.get('klasa_tacnosti', '-')}")
                        st.info(f"Preciznost: {ins.get('preciznost', '-')}")
                        st.info(f"Podeok: {ins.get('podeok', '-')}")
                    with c2:
                        st.write("**Istorija i uslovi:**")
                        st.info(f"Godina proizvodnje: {ins.get('godina_proizvodnje', '-')}")
                        st.info(f"U upotrebi od: {ins.get('upotreba_od', '-')}")
                        st.info(f"Period provere: {ins.get('period_provere', '-')}")
                    with c3:
                        st.write("**Radni uslovi:**")
                        st.info(f"Temperatura: {ins.get('temperatura', '-')}")
                        st.info(f"Vlažnost: {ins.get('relativna_vlaznost', '-')}")
                        st.info(f"GPS: {ins.get('gps_koordinate', '-')}")

                with t2:
                    model = str(ins.get('naziv_proizvodjac', '')).strip()
                    df_k = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{model.lower()}%",))
                    st.table(df_k.fillna("-")) if not df_k.empty else st.warning("Nema kultura.")

                with t3:
                    df_s = run_query("SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                    st.dataframe(df_s, use_container_width=True) if not df_s.empty else st.info("Nema servisa.")

                with t4:
                    df_e = run_query("SELECT datum_etaloniranja, broj_sertifikata, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                    st.dataframe(df_e, use_container_width=True) if not df_e.empty else st.info("Nema etaloniranja.")

                with t5:
                    df_b = run_query("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                    # Ovde su izbačene boje po zahtevu (Matični karton je bez boja)
                    st.dataframe(df_b, use_container_width=True) if not df_b.empty else st.info("Nema baždarenja.")
            else:
                st.sidebar.error("Instrument nije pronađen!")

except Exception as e:
    st.error(f"Greška: {e}")
