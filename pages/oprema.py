import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 1. KONFIGURACIJA
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

st.markdown("""
    <style>
        html, body, [class*="st-"], .stMarkdown, .stTable, .stDataFrame { font-family: 'Arial', sans-serif !important; }
        .stAlert { padding: 0.5rem; margin-bottom: 0.5rem; }
        [data-testid="stSidebarNav"] ul { display: none; }
    </style>
""", unsafe_allow_html=True)

try:
    pdfmetrics.registerFont(TTFont('Serbian', 'Arial.ttf'))
    FONT_NAME = 'Serbian'
except:
    FONT_NAME = 'Helvetica'

if 'ulogovan' not in st.session_state or not st.session_state['ulogovan']:
    st.switch_page("glavna.py")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# 2. SIDEBAR
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")

tabela_opcije = {
    "Glavna Oprema": "oprema",
    "Istorija Servisa": "istorija_servisa",
    "Etaloniranje": "istorija_etaloniranja",
    "Baždarenje": "istorija_bazdarenja"
}

izabrana_tabela = "oprema"
if is_admin:
    izbor_prikaza = st.sidebar.selectbox("Izaberi tabelu za rad:", list(tabela_opcije.keys()))
    izabrana_tabela = tabela_opcije[izbor_prikaza]

    # BEZBEDAN UVOZ (ON DUPLICATE KEY UPDATE)
    uploaded_file = st.sidebar.file_uploader("Uvezi Excel (Update)", type=["xlsx"])
    if uploaded_file and st.sidebar.button("🚀 POKRENI UVOZ", use_container_width=True):
        try:
            new_data = pd.read_excel(uploaded_file)
            conn = get_conn(); cur = conn.cursor()
            cols = [c.strip().lower() for c in new_data.columns]
            update_part = ", ".join([f"{c} = VALUES({c})" for c in cols])
            placeholders = ", ".join(["%s"] * len(cols))
            sql = f"INSERT INTO {izabrana_tabela} ({','.join(cols)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_part}"
            for _, row in new_data.iterrows():
                cur.execute(sql, [None if pd.isna(x) else x for x in row])
            conn.commit(); conn.close()
            st.sidebar.success("Podaci uspešno osveženi!"); st.cache_data.clear(); st.rerun()
        except Exception as e: st.sidebar.error(f"Greška: {e}")

if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True): st.switch_page("pages/mapa_opreme.py")
if st.sidebar.button("🚪 Odjavi se", use_container_width=True): 
    st.session_state['ulogovan'] = False
    st.rerun()

izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

# 3. POMOĆNE FUNKCIJE
def apply_styling(df_st):
    if 'vazi_do' not in df_st.columns: return df_st
    return df_st.style.map(lambda v: "background-color: #ff4b4b; color: white" if pd.notnull(v) and pd.to_datetime(v).date() < datetime.now().date() else "", subset=['vazi_do'])

# 4. GLAVNI PROGRAM
try:
    df_raw = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        for col in df.columns:
            if any(x in col for x in ['datum', 'vazi_do', 'upotreba_od']):
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # IZBACIVANJE KOLONA IZ GLAVNOG PREGLEDA
        za_izbacivanje = ['id', 'putanja_folder', 'gps_koordinate', 'radna_temperatura', 'rel_vlaznost', 'ima_mk', 'bar_kod', 'status']
        df_prikaz = df.drop(columns=[c for c in za_izbacivanje if c in df.columns])
        
        pretraga = st.text_input("🔍 Pretraži bazu (Sektor, Naziv, Radnik):", "").lower()
        if pretraga:
            df_prikaz = df_prikaz[df_prikaz.astype(str).apply(lambda x: x.str.lower().str.contains(pretraga)).any(axis=1)]

        st.dataframe(apply_styling(df_prikaz), use_container_width=True)

    # --- MATIČNI KARTON ---
    if izabrani_broj:
        st.markdown("---")
        res = run_query("SELECT * FROM oprema WHERE inventarni_broj = %s", (izabrani_broj,))
        if not res.empty:
            ins = res.iloc[0].to_dict()
            st.subheader(f"📑 Matični karton: {ins.get('naziv_proizvodjac')} - {izabrani_broj}")
            
            # INFO PANEL (Kao u originalu)
            c1, c2, c3, c4 = st.columns(4)
            c1.info(f"**Proizvođač:**\n\n{ins.get('proizvodjac', '-')}")
            c2.info(f"**Serijski broj:**\n\n{ins.get('seriski_broj', '-')}")
            c3.info(f"**Sektor:**\n\n{ins.get('sektor', '-')}")
            c4.info(f"**Zadnja lokacija:**\n\n{ins.get('zadnja_lokacija', '-')}")
            
            # GOOGLE DRIVE DUGME
            putanja = ins.get('putanja_folder')
            if putanja and str(putanja) != 'None':
                st.link_button("📂 OTVORI GOOGLE DRIVE FOLDER", putanja, type="primary", use_container_width=True)
            else:
                st.link_button("🔍 PRETRAŽI DRIVE (Po broju)", f"https://drive.google.com{izabrani_broj}", use_container_width=True)

            # TABOVI SA ISPRAVLJENIM KOLONAMA DATUMA
            t1, t2, t3 = st.tabs(["🔧 Servis", "🧪 Etaloniranje", "📐 Baždarenje"])
            
            konfig = [
                (t1, "istorija_servisa", "datum_servisa", "Servis"),
                (t2, "istorija_etaloniranja", "datum_etaloniranja", "Etaloniranje"),
                (t3, "istorija_bazdarenja", "datum_bazdarenja", "Baždarenje")
            ]

            for tab, tab_ime, kolona_datuma, naslov in konfig:
                with tab:
                    df_h = run_query(f"SELECT * FROM {tab_ime} WHERE inventarni_broj = %s ORDER BY {kolona_datuma} DESC", (izabrani_broj,))
                    st.dataframe(df_h, use_container_width=True)
                    
                    if is_admin:
                        with st.form(f"f_{tab_ime}"):
                            d_rada = st.date_input(f"Datum {naslov.lower()}a")
                            br_dok = st.text_input("Broj dokumenta / Uverenja")
                            if st.form_submit_button(f"Sačuvaj {naslov}"):
                                period = ins.get('period_provere', 1)
                                novi_rok = d_rada + pd.DateOffset(years=int(period))
                                conn = get_conn(); cur = conn.cursor()
                                cur.execute(f"INSERT INTO {tab_ime} (inventarni_broj, {kolona_datuma}, broj_uverenja, vazi_do) VALUES (%s,%s,%s,%s)", (izabrani_broj, d_rada, br_dok, novi_rok.date()))
                                cur.execute("UPDATE oprema SET vazi_do = %s WHERE inventarni_broj = %s", (novi_rok.date(), izabrani_broj))
                                conn.commit(); conn.close()
                                st.success("Podaci uspešno upisani!"); st.rerun()

except Exception as e:
    st.error(f"❌ Greška sa bazom podataka: {e}")
