import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# 1. KONEKCIJA SA BAZOM
def get_conn():
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin", 
        password="AVNS_0qoNdSQVUuF9wTfHN8D", 
        port=27698, 
        database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'}
    )

# 2. DOBAVLJANJE GLAVNE TABELE
def get_working_data():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM oprema")
        rows = cur.fetchall()
    conn.close()
    df = pd.DataFrame(rows)
    if not df.empty:
        # Standardizacija naziva kolona (mala slova)
        df.columns = [c.strip().lower() for c in df.columns]
    return df

# Funkcija za bojenje isteklih datuma (crveno ako je prošao rok)
def highlight_expiry(val):
    if pd.isna(val) or str(val) in ['-', '', 'None', 'nan', '0']: return ""
    try:
        if pd.to_datetime(val).date() < datetime.now().date():
            return "background-color: #ff4b4b; color: white"
    except: pass
    return ""

# KONFIGURACIJA STRANICE
st.set_page_config(page_title="Radni Panel - Oprema", layout="wide")
st.title("🔍 Radni Panel - Evidencija Opreme")

try:
    df = get_working_data()
    if not df.empty:
        # Čišćenje glavne tabele od naslova u redovima (ako su ušli pri importu)
        if 'inventarni_broj' in df.columns:
            df = df[df['inventarni_broj'].astype(str).str.lower().str.strip() != 'inventarni_broj']

        # --- SEKCIJA 1: GLAVNA TABELA I PRETRAGA ---
        search_query = st.text_input("🔍 Brza pretraga kroz celu tabelu (ukucaj bilo šta):", key="main_search")
        if search_query:
            mask = df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        st.dataframe(
            df_display, 
            use_container_width=True, 
            hide_index=True, 
            column_config={
                "id": None, 
                "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY")
            }
        )

        st.write("---")
        
        # --- SEKCIJA 2: MATIČNI KARTON (UNOS BROJA U SIDEBAR-U) ---
        izabrani_broj = st.sidebar.text_input("🔢 Unesi Inventarski Broj za detalje:", "")

        if izabrani_broj:
            # Tražimo podatke za taj specifičan instrument
            rezultat = df[df['inventarni_broj'].astype(str) == str(izabrani_broj)]
            
            if not rezultat.empty:
                instrument = rezultat.iloc[0]
                model_iz_opreme = str(instrument.get('naziv_proizvodjac', '')).strip()
                inv_broj_str = str(izabrani_broj)

                st.subheader(f"📄 Matični Karton br: {izabrani_broj}")
                
                # DEFINICIJA TABOVA
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture", "🛠️ Servis", "📏 Etaloniranje", "⚖️ Baždarenje"])

                # --- TAB 1: TEHNIČKE KARAKTERISTIKE ---
                with tab1:
                    polja = {
                        "Vrsta": "vrsta_opreme", "Proizvođač": "proizvodjac", "Model": "naziv_proizvodjac",
                        "Serijski br.": "seriski_broj", "Zadnje baždarenje": "datum_bazdarenja", "Važi do": "vazi_do",
                        "Opseg": "opseg_merenja", "Klasa": "klasa_tacnosti", "Preciznost": "preciznost", "Podeok": "podeok"
                    }
                    popunjena = [(l, instrument[c]) for l, c in polja.items() if c in instrument and pd.notna(instrument[c]) and str(instrument[c]).strip() not in ["", "-", "nan", "None", "0"]]
                    
                    if popunjena:
                        cols = st.columns(4)
                        for i, (label, val) in enumerate(popunjena):
                            with cols[i % 4]:
                                st.caption(label)
                                st.write(f"**{val}**")
                    else:
                        st.info("Nema unetih tehničkih podataka.")

                # --- TAB 2: KULTURE (DIJAGNOSTIČKA PRETRAGA) ---
                with tab2:
                    st.write(f"Tražim kulture za model: **'{model_iz_opreme}'**")
                    try:
                        conn = get_conn()
                        # "Nuklearni" SQL upit: briše razmake i pretvara u mala slova u bazi tokom pretrage
                        query_k = """
                            SELECT kultura, opseg_vlage, protein, naziv_proizvodjac 
                            FROM kulture_opsezi 
                            WHERE LOWER(REPLACE(naziv_proizvodjac, ' ', '')) = LOWER(REPLACE(%s, ' ', ''))
                        """
                        df_k = pd.read_sql(query_k, conn, params=(model_iz_opreme,))
                        conn.close()

                        if not df_k.empty:
                            # Čišćenje preostalih naslova iz Excela
                            df_k = df_k[df_k['kultura'].astype(str).str.lower().str.strip() != 'kultura']
                            
                            if not df_k.empty:
                                # Prikazujemo samo bitne kolone radniku
                                st.dataframe(df_k[['kultura', 'opseg_vlage', 'protein']].fillna('-'), use_container_width=True, hide_index=True)
                            else:
                                st.error("Pronađen je red, ali je obrisan jer je naslov ('kultura').")
                        else:
                            st.warning(f"Baza ne pronalazi model '{model_iz_opreme}' u tabeli kultura.")
                            
                            # POMOĆ ZA TEBE: Ispisujemo šta uopšte ima u bazi da vidiš razliku
                            conn = get_conn()
                            dostupni = pd.read_sql("SELECT DISTINCT naziv_proizvodjac FROM kulture_opsezi", conn)
                            conn.close()
                            st.info("U tabeli kultura piše ovako: " + ", ".join(dostupni['naziv_proizvodjac'].astype(str).tolist()))
                    except Exception as e:
                        st.error(f"Greška u Tabu 2: {e}")

                # --- TAB 3: ISTORIJA SERVISA ---
                with tab3:
                    conn = get_conn()
                    df_s = pd.read_sql("SELECT datum_servisa, broj_zapisnika, opis_intervencije, izvrsio_servis FROM istorija_servisa WHERE inventarni_broj = %s ORDER BY datum_servisa DESC", conn, params=(inv_broj_str,))
                    conn.close()
                    if not df_s.empty:
                        df_s = df_s[df_s['datum_servisa'].astype(str).str.lower().str.strip() != 'datum_servisa']
                        st.dataframe(df_s, use_container_width=True, hide_index=True)
                    else: st.write("Nema zabeleženih servisa.")

                # --- TAB 4: ETALONIRANJE ---
                with tab4:
                    conn = get_conn()
                    df_e = pd.read_sql("SELECT datum_etaloniranja, broj_sertifikata, vazi_do, laboratorija FROM istorija_etaloniranja WHERE inventarni_broj = %s ORDER BY datum_etaloniranja DESC", conn, params=(inv_broj_str,))
                    conn.close()
                    if not df_e.empty:
                        df_e = df_e[df_e['datum_etaloniranja'].astype(str).str.lower().str.strip() != 'datum_etaloniranja']
                        st.dataframe(df_e.style.map(highlight_expiry, subset=['vazi_do']), use_container_width=True, hide_index=True)
                    else: st.info("Nema podataka o etaloniranju.")

                # --- TAB 5: BAŽDARENJE ---
                with tab5:
                    conn = get_conn()
                    df_b = pd.read_sql("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s ORDER BY datum_bazdarenja DESC", conn, params=(inv_broj_str,))
                    conn.close()
                    if not df_b.empty:
                        df_b = df_b[df_b['datum_bazdarenja'].astype(str).str.lower().str.strip() != 'datum_bazdarenja']
                        st.dataframe(df_b.style.map(highlight_expiry, subset=['vazi_do']), use_container_width=True, hide_index=True)
                    else: st.info("Nema podataka o baždarenju.")

            else:
                st.warning(f"Instrument sa inventarnim brojem '{izabrani_broj}' nije pronađen.")
        else:
            st.info("👈 Ukucajte inventarski broj u polje sa leve strane da vidite Matični Karton.")
    else:
        st.warning("Tabela 'oprema' u bazi podataka je prazna.")
except Exception as e:
    st.error(f"Sistemska greška: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("Sistem za praćenje mernih instrumenata v2.1")
