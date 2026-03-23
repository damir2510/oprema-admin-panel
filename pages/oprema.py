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

try:
    pdfmetrics.registerFont(TTFont('Serbian', 'Arial.ttf'))
    FONT_NAME = 'Serbian'
except:
    FONT_NAME = 'Helvetica'

if not st.session_state.get('ulogovan'):
    st.switch_page("glavna.py")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 2. SIDEBAR
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")

tabela_opcije = {
    "Glavna Oprema": "oprema",
    "Istorija Servisa": "istorija_servisa",
    "Etaloniranje": "istorija_etaloniranja",
    "Baždarenje": "istorija_bazdarenja",
    "Kulture": "kulture_opsezi"
}

izabrana_tabela = "oprema"
izbor_prikaza = "Glavna Oprema"

if is_admin:
    st.sidebar.header("📊 Admin Kontrole")
    izbor_prikaza = st.sidebar.selectbox("Izaberi tabelu za rad:", list(tabela_opcije.keys()))
    izabrana_tabela = tabela_opcije[izbor_prikaza]

    # --- NOVO: Dugme za izvoz odmah ispod selektora ---
    df_za_export = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df_za_export.empty:
        buffer = io.BytesIO()
        df_za_export.to_excel(buffer, index=False)
        st.sidebar.download_button("📥 IZVEZI EXCEL", data=buffer.getvalue(), file_name=f"{izabrana_tabela}.xlsx", use_container_width=True)

    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader("Uvezi Excel", type=["xlsx"])
    if uploaded_file and st.sidebar.button("🚀 POKRENI UVOZ", use_container_width=True):
        try:
            new_data = pd.read_excel(uploaded_file)
            conn = get_conn(); cur = conn.cursor()
            cur.execute(f"TRUNCATE TABLE {izabrana_tabela}")
            cols = [c.strip().lower() for c in new_data.columns]
            placeholders = ", ".join(["%s"] * len(cols))
            for _, row in new_data.iterrows():
                cur.execute(f"INSERT INTO {izabrana_tabela} ({', '.join(cols)}) VALUES ({placeholders})", list(row))
            conn.commit(); conn.close()
            st.sidebar.success("Uvoz uspešan!"); st.cache_data.clear(); st.rerun()
        except Exception as e: st.sidebar.error(f"Greška: {e}")

st.sidebar.markdown("---")
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.switch_page("glavna.py")

izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

# 3. POMOĆNE FUNKCIJE
def apply_styling(df_st):
    if 'vazi_do' not in df_st.columns: return df_st
    def highlight(v):
        try:
            if pd.notnull(v) and pd.to_datetime(v).date() < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except: pass
        return ""
    return df_st.style.map(highlight, subset=['vazi_do'])

def formatiraj_datume(df_f):
    for col in df_f.columns:
        if 'datum' in col or 'vazi_do' in col or 'upotreba_od' in col:
            try:
                df_f[col] = pd.to_datetime(df_f[col]).dt.date
            except: pass
    return df_f

# 4. GLAVNI PROGRAM
st.title(f"🔍 {izbor_prikaza}")

try:
    df_raw = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        df = formatiraj_datume(df)

        # --- REORGANIZACIJA KOLONA ---
        cols = list(df.columns)
        # 1. Proizvođač ispred Naziva
        if 'proizvodjac' in cols and 'naziv_proizvodjac' in cols:
            cols.insert(cols.index('naziv_proizvodjac'), cols.pop(cols.index('proizvodjac')))
        # 2. Napomena i Putanja na kraj
        for c_end in ['napomena', 'putanja_folder']:
            if c_end in cols:
                cols.append(cols.pop(cols.index(c_end)))
        df = df[cols]

        # --- PRETRAGA IZNAD TABELE ---
        pretraga = st.text_input("🔍 Pretraži tabelu (uneti bilo koji podatak):", "").lower()
        if pretraga:
            df = df[df.astype(str).apply(lambda x: x.str.lower().str.contains(pretraga)).any(axis=1)]

        # --- PRIKAZ ---
        za_izbacivanje = ['ima_mk', 'gps_koordinate', 'radna_temperatura', 'rel_vlaznost', 'godina_proizvodnje', 'opseg_merenja', 'klasa_tacnosti', 'preciznost', 'podeok', 'upotreba_od', 'period_provere', 'bar_kod', 'stampac', 'status', 'zadnja_lokacija']
        df_prikaz = df.drop(columns=[c for c in za_izbacivanje if c in df.columns])

        if is_admin:
            st.data_editor(apply_styling(df_prikaz), use_container_width=True, key=f"ed_{izabrana_tabela}")
        else:
            st.dataframe(apply_styling(df_prikaz), use_container_width=True, hide_index=True)

        # --- MATIČNI KARTON (Ostaje isti kao pre) ---
        if izabrani_broj and izabrana_tabela == "oprema":
            # ... (ovde ide tvoj postojeći kod za tabove) ...
            st.write(f"Prikaz kartona za {izabrani_broj}") # Placeholder

    else: st.warning("Tabela je prazna.")
except Exception as e: st.error(f"Greška: {e}")
