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
        # Čistimo nazive kolona (mala slova i bez razmaka)
        df.columns = [c.strip().lower() for c in df.columns]
    return df

# Funkcija za bojenje isteklih datuma
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

        # --- GLAVNA PRETRAGA ---
        search_query = st.text_input("🔍 Brza pretraga kroz celu tabelu:", key="main_search")
        if search_query:
            mask = df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        st.dataframe(df_display, use_container_width=True, hide_index=True, 
                     column_config={"id": None, "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY")})

        st.write("---")
        
        # --- MATIČNI KARTON (SIDEBAR) ---
        izabrani_broj = st.sidebar.text_input("🔢 Unesi Inventarski Broj:", "")

        if izabrani_broj:
            # Tražimo podatke za konkretan instrument
            rezultat = df[df['inventarni_broj'].astype(str) == str(izabrani_broj)]
            
            if not rezultat.empty:
                instrument = rezultat.iloc[0]
                model_iz_opreme = str(instrument.get('naziv_proizvodjac', '')).strip()
                inv_broj_str = str(izabrani_broj)

                st.subheader(f"📄 Matični Karton br: {izabrani_broj}")
                
                # DEFINICIJA TABOVA (Svi moraju biti unutar 'if ne rezultat.empty' bloka)
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture", "🛠️ Servis", "📏 Etaloniranje", "⚖️ Baždarenje"])

                # --- TAB 1: OSNOVNI PODACI ---
                with tab1:
                    polja = {
                        "Vrsta": "vrsta_opreme", "Proizvođač": "proizvodjac", "Model": "naziv_proizvodjac",
                        "Serijski br.": "seriski_broj", "Zadnje baždarenje": "datum_bazdarenja", "Važi do": "vazi_do",
                        "Opseg": "opseg_merenja", "Klasa": "klasa_tacnosti", "Preciznost": "preciznost", "Podeok": "podeok"
                    }
                    popunjena = [(l, instrument[c]) for l, c in polja.items() if c in instrument and pd.notna(instrument[c]) and str(instrument[c]).strip() not in ["", "-", "nan", "None", "0"]]
                    cols = st.columns(4)
                    for i, (label, val) in enumerate(popunjena):
                        with cols[i % 4]:
                            st.caption(label)
                            st.write(f"**{val}**")

                # --- TAB 2: KULTURE (POVEZIVANJE I ČIŠĆENJE) ---
                with tab2:
                    st.write(f"Kulture i opsezi za: **{model_iz_opreme}**")
                    try:
                        conn = get_conn()
                        # SQL JOIN preko očišćenih naziva
                        query_k = """
                            SELECT k.kultura, k.opseg_vlage, k.protein 
                            FROM kulture_opsezi k
                            JOIN oprema o ON TRIM(k.naziv_proizvodjac) = TRIM(o.naziv_proizvodjac)
                            WHERE o.inventarni_broj = %s
                        """
                        df_k = pd.read_sql(query_k, conn, params=(inv_broj_str,))
                        conn.close()

                        if not df_k.empty:
                            # ČIŠĆENJE: Izbacujemo redove gde je kultura = "kultura" (naslovi iz uvoza)
                            df_k = df_k[df_k['kultura'].astype(str).str.lower().str.strip() != 'kultura']
                            
                            # TRANSFORMACIJA: Popunjavamo praznine i brišemo skroz prazne kolone
                            df_k = df_k.replace(['nan', 'None', '0', '0.0'], pd.NA).dropna(axis=1, how='all').fillna('-')
                            
                            if not df_k.empty:
                                st.dataframe(df_k, use_container_width=True, hide_index=True)
                            else:
                                st.error("Svi podaci za ovaj model u bazi su naslovi redova.")
                        else:
                            st.info("Nema definisanih kultura za ovaj model.")
                    except Exception as e:
                        st.error(f"Greška u Tabu 2: {e}")

                # --- TAB 3: SERVIS ---
                with tab3:
                    conn = get_conn()
                    df_s = pd.read_sql("SELECT datum_servisa, broj_zapisnika, opis_intervencije, izvrsio_servis FROM istorija_servisa WHERE inventarni_broj = %s ORDER BY datum_servisa DESC", conn, params=(inv_broj_str,))
                    conn.close()
                    if not df_s.empty:
                        df_s = df_s[df_s['datum_servisa'].astype(str).str.lower().str.strip() != 'datum_servisa']
                        st.dataframe(df_s, use_container_width=True, hide_index=True)
                    else: st.write("Nema servisa.")

                # --- TAB 4: ETALONIRANJE ---
                with tab4:
                    conn = get_conn()
                    df_e = pd.read_sql("SELECT datum_etaloniranja, broj_sertifikata, vazi_do, laboratorija FROM istorija_etaloniranja WHERE inventarni_broj = %s ORDER BY datum_etaloniranja DESC", conn, params=(inv_broj_str,))
                    conn.close()
                    if not df_e.empty:
                        df_e = df_e[df_e['datum_etaloniranja'].astype(str).str.lower().str.strip() != 'datum_etaloniranja']
                        st.dataframe(df_e.style.map(highlight_expiry, subset=['vazi_do']), use_container_width=True, hide_index=True)
                    else: st.info("Nema etaloniranja.")

                # --- TAB 5: BAŽDARENJE ---
                with tab5:
                    conn = get_conn()
                    df_b = pd.read_sql("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s ORDER BY datum_bazdarenja DESC", conn, params=(inv_broj_str,))
                    conn.close()
                    if not df_b.empty:
                        df_b = df_b[df_b['datum_bazdarenja'].astype(str).str.lower().str.strip() != 'datum_bazdarenja']
                        st.dataframe(df_b.style.map(highlight_expiry, subset=['vazi_do']), use_container_width=True, hide_index=True)
                    else: st.info("Nema baždarenja.")
            else:
                st.warning("Instrument nije pronađen.")
        else:
            st.info("👈 Ukucaj inventarski broj u polje levo za detaljan karton.")
    else:
        st.warning("Tabela oprema je prazna.")
except Exception as e:
    st.error(f"Sistemska greška: {e}")
