import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# 1. FUNKCIJA ZA RAD SA BAZOM (Automatsko zatvaranje konekcije)
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
            result = cur.fetchall()
            return pd.DataFrame(result)
    except Exception as e:
        st.error(f"Greška pri povezivanju sa bazom: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals():
            conn.close()

# 2. FUNKCIJA ZA BOJENJE ISTEKLIH DATUMA
def highlight_expiry(val):
    try:
        # Pretvaramo u datum ako je string/timestamp
        date_val = pd.to_datetime(val).date()
        if date_val < datetime.now().date():
            return "background-color: #ff4b4b; color: white"
    except:
        pass
    return ""

# KONFIGURACIJA STRANICE
st.set_page_config(page_title="Radni Panel - Oprema", layout="wide")
st.title("🔍 Radni Panel - Evidencija Opreme")

try:
    # Učitavanje glavne tabele
    df = run_query("SELECT * FROM oprema")
    
    if not df.empty:
        # Standardizacija kolona
        df.columns = [c.strip().lower() for c in df.columns]
        # Čišćenje ako su naslovi ubačeni kao redovi u bazu
        df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        # Glavna pretraga
        search_query = st.text_input("🔍 Brza pretraga kroz celu tabelu:", key="main_search")
        if search_query:
            mask = df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        st.dataframe(
            df_display, 
            use_container_width=True, 
            hide_index=True,
            column_config={"vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY")}
        )
        
        st.write("---")

        # SIDEBAR - Izbor instrumenta
        st.sidebar.header("📍 Detalji uređaja")
        izabrani_broj = st.sidebar.text_input("Unesi Inventarski Broj:", "").strip()

        if izabrani_broj:
            # Tražimo tačan red u DF-u
            rezultat = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            
            if not rezultat.empty:
                instrument = rezultat.iloc[0]
                model_iz_opreme = str(instrument.get('naziv_proizvodjac', '')).strip()
                
                st.subheader(f"📄 Matični Karton br: {izabrani_broj}")
                
                # TABS
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📋 Osnovni podaci", "🌾 Kulture", "🛠 Servis", "📏 Etaloniranje", "⚖ Baždarenje"
                ])

                # TAB 1: OSNOVNI PODACI (Vizuelno unapređeno sa metricama)
                with tab1:
                    c1, c2, c3, c4 = st.columns(4)
                    polja = [
                        ("Vrsta", "vrsta_opreme"), ("Proizvođač", "proizvodjac"),
                        ("Model", "naziv_proizvodjac"), ("Serijski br.", "seriski_broj"),
                        ("Opseg", "opseg_merenja"), ("Klasa", "klasa_tacnosti"),
                        ("Preciznost", "preciznost"), ("Podeok", "podeok")
                    ]
                    for i, (label, col) in enumerate(polja):
                        val = instrument.get(col, "-")
                        with [c1, c2, c3, c4][i % 4]:
                            st.write(f"**{label}:**")
                            st.info(val)

                # TAB 2: KULTURE (Fleksibilna pretraga)
                with tab2:
                    st.write(f"Kulture za model: **{model_iz_opreme}**")
                    # Koristimo LIKE da izbegnemo probleme sa razmacima
                    q_k = "SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s"
                    df_k = run_query(q_k, (f"%{model_iz_opreme.lower()}%",))
                    
                    if not df_k.empty:
                        df_k = df_k[df_k['kultura'].astype(str).str.lower() != 'kultura']
                        st.table(df_k.fillna("-"))
                    else:
                        st.warning("Nisu pronađene kulture u bazi.")

                # TAB 3: SERVIS (Ispravljeno prikazivanje)
                with tab3:
                    q_s = "SELECT datum_servisa, broj_zapisnika, opis_intervencije, izvrsio_servis FROM istorija_servisa WHERE inventarni_broj = %s ORDER BY datum_servisa DESC"
                    df_s = run_query(q_s, (izabrani_broj,))
                    
                    if not df_s.empty:
                        df_s = df_s[df_s['datum_servisa'].astype(str).str.lower() != 'datum_servisa']
                        st.dataframe(df_s, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nema registrovanih servisa.")

                # TAB 4: ETALONIRANJE
                with tab4:
                    q_e = "SELECT datum_etaloniranja, broj_sertifikata, vazi_do, laboratorija FROM istorija_etaloniranja WHERE inventarni_broj = %s ORDER BY datum_etaloniranja DESC"
                    df_e = run_query(q_e, (izabrani_broj,))
                    
                    if not df_e.empty:
                        df_e = df_e[df_e['datum_etaloniranja'].astype(str).str.lower() != 'datum_etaloniranja']
                        st.dataframe(df_e.style.applymap(highlight_expiry, subset=['vazi_do']), use_container_width=True, hide_index=True)
                    else:
                        st.info("Nema etaloniranja.")

                # TAB 5: BAŽDARENJE
                with tab5:
                    q_b = "SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s ORDER BY datum_bazdarenja DESC"
                    df_b = run_query(q_b, (izabrani_broj,))
                    
                    if not df_b.empty:
                        df_b = df_b[df_b['datum_bazdarenja'].astype(str).str.lower() != 'datum_bazdarenja']
                        st.dataframe(df_b.style.applymap(highlight_expiry, subset=['vazi_do']), use_container_width=True, hide_index=True)
                    else:
                        st.info("Nema baždarenja.")
            else:
                st.sidebar.error("Instrument nije pronađen!")
    else:
        st.error("Baza podataka je prazna ili nedostupna.")

except Exception as e:
    st.error(f"Kritična greška u aplikaciji: {e}")
