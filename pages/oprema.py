import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
from db_utils import run_query, get_conn
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 1. KONFIGURACIJA STRANE I STILIZACIJA
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

st.markdown("""
    <style>
        html, body, [class*="st-"], .stMarkdown, .stTable, .stDataFrame { font-family: 'Arial', sans-serif !important; }
        h1, h2, h3, h4 { font-family: 'Arial', sans-serif !important; font-weight: bold; }
        .stAlert { padding: 0.5rem; margin-bottom: 0rem; }
        [data-testid="stSidebarNav"] ul { display: none; }
    </style>
""", unsafe_allow_html=True)

try:
    pdfmetrics.registerFont(TTFont('Serbian', 'Arial.ttf'))
    FONT_NAME = 'Serbian'
except:
    FONT_NAME = 'Helvetica'

# SIGURNOSNA PROVERA
if 'ulogovan' not in st.session_state or not st.session_state['ulogovan']:
    st.switch_page("glavna.py")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# 2. SIDEBAR - ADMIN I NAVIGACIJA
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")

tabela_opcije = {
    "Glavna Oprema": "oprema",
    "Istorija Servisa": "istorija_servisa",
    "Etaloniranje": "istorija_etaloniranja",
    "Baždarenje": "istorija_bazdarenja",
    "Kulture": "kulture_opsezi"
}

izbor_prikaza = "Glavna Oprema"
izabrana_tabela = "oprema"

if is_admin:
    st.sidebar.header("📊 Admin Kontrole")
    izbor_prikaza = st.sidebar.selectbox("Izaberi tabelu za rad:", list(tabela_opcije.keys()))
    izabrana_tabela = tabela_opcije[izbor_prikaza]

    # IZVOZ EXCEL
    df_za_exp = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df_za_exp.empty:
        buffer_ex = io.BytesIO()
        df_za_exp.to_excel(buffer_ex, index=False)
        st.sidebar.download_button("📥 IZVEZI EXCEL", data=buffer_ex.getvalue(), file_name=f"{izabrana_tabela}.xlsx", use_container_width=True)

    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader("Uvezi Excel (Update/Insert)", type=["xlsx"])
    if uploaded_file and st.sidebar.button("🚀 POKRENI UVOZ", use_container_width=True):
        try:
            new_data = pd.read_excel(uploaded_file)
            conn = get_conn(); cur = conn.cursor()
            cols = [c.strip().lower() for c in new_data.columns]
            
            # REŠENJE ZA FOREIGN KEY: INSERT ... ON DUPLICATE KEY UPDATE
            update_part = ", ".join([f"{c} = VALUES({c})" for c in cols])
            placeholders = ", ".join(["%s"] * len(cols))
            sql = f"INSERT INTO {izabrana_tabela} ({','.join(cols)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_part}"
            
            for _, row in new_data.iterrows():
                values = [None if pd.isna(x) else x for x in row]
                cur.execute(sql, values)
            
            conn.commit(); conn.close()
            st.sidebar.success("Podaci uspešno osveženi!"); st.cache_data.clear(); st.rerun()
        except Exception as e: st.sidebar.error(f"Greška pri uvozu: {e}")

st.sidebar.markdown("---")
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.rerun()

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

def generisi_pdf(ins, ds, de, db):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    s_normal = styles['Normal']; s_normal.fontName = FONT_NAME
    s_title = styles['Title']; s_title.fontName = FONT_NAME
    s_h2 = styles['Heading2']; s_h2.fontName = FONT_NAME
    elements = []
    inv_br = ins.get('inventarni_broj', 'N/A')
    elements.append(Paragraph(f"MATIČNI KARTON INSTRUMENTA br: {inv_br}", s_title))
    elements.append(Paragraph(f"Izveštaj generisan: {datetime.now().strftime('%d.%m.%Y.')}", s_normal))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("1. OSNOVNI PODACI", s_h2))
    
    podaci_lista = []
    detalji_pdf = [("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"), ("Serijski br.", "seriski_broj"), ("Sektor", "sektor"), ("Upotreba od", "upotreba_od"), ("Važi do", "vazi_do"), ("Opseg", "opseg_merenja"), ("Klasa", "klasa_tacnosti")]
    for l, k in detalji_pdf:
        val = ins.get(k)
        if val and str(val).strip() not in ["", "None", "nan", "-"]: podaci_lista.append([l, str(val)])
    
    if podaci_lista:
        t = Table(podaci_lista, colWidths=[150, 300])
        t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,-1), FONT_NAME)]))
        elements.append(t)

    sekcije = [("2. SERVISI", ds), ("3. ETALONIRANJA", de), ("4. BAŽDARENJA", db)]
    for naslov, df_sec in sekcije:
        elements.append(Spacer(1, 15)); elements.append(Paragraph(naslov, s_h2))
        if not df_sec.empty:
            data = [df_sec.columns.to_list()] + df_sec.values.tolist()
            t_sec = Table(data, hAlign='LEFT')
            t_sec.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.lightgrey), ('GRID',(0,0),(-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,-1), FONT_NAME)]))
            elements.append(t_sec)
        else: elements.append(Paragraph("Nema zabeleženih podataka.", s_normal))
    doc.build(elements)
    return buffer.getvalue()

# 4. GLAVNI PROGRAM
st.title(f"🔍 {izbor_prikaza}")

try:
    df_raw = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        for col in df.columns:
            if any(x in col for x in ['datum', 'vazi_do', 'upotreba_od']):
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # REDOSLED KOLONA
        cols = list(df.columns)
        if 'proizvodjac' in cols and 'naziv_proizvodjac' in cols:
            cols.insert(cols.index('naziv_proizvodjac'), cols.pop(cols.index('proizvodjac')))
        for c_end in ['napomena', 'putanja_folder']:
            if c_end in cols: cols.append(cols.pop(cols.index(c_end)))
        df = df[cols]

        # SAKRIVANJE KOLONA ZA PRIKAZ
        za_izbacivanje = ['id', 'datum_bazdarenja', 'ima_mk', 'gps_koordinate', 'radna_temperatura', 'rel_vlaznost', 'godina_proizvodnje', 'opseg_merenja', 'klasa_tacnosti', 'preciznost', 'podeok', 'upotreba_od', 'period_provere', 'bar_kod', 'stampac', 'status', 'zadnja_lokacija']
        df_prikaz = df.drop(columns=[c for c in za_izbacivanje if c in df.columns])
        if 'inventarni_broj' in df_prikaz.columns: df_prikaz = df_prikaz.rename(columns={'inventarni_broj': 'In. broj'})

        pretraga = st.text_input("", placeholder="🔍 Brza pretraga...", label_visibility="collapsed").lower()
        if pretraga:
            df_prikaz = df_prikaz[df_prikaz.astype(str).apply(lambda x: x.str.lower().str.contains(pretraga)).any(axis=1)]

        if is_admin:
            st.data_editor(apply_styling(df_prikaz), use_container_width=True, key="editor_glavni")
        else:
            st.dataframe(apply_styling(df_prikaz), use_container_width=True)

    # --- MATIČNI KARTON I ADMIN UNOS ---
    if izabrani_broj:
        st.markdown("---")
        aparat_res = run_query("SELECT * FROM oprema WHERE inventarni_broj = %s", (izabrani_broj,))
        
        if not aparat_res.empty:
            ins = aparat_res.iloc[0].to_dict()
            st.subheader(f"📑 Karton: {ins.get('naziv_proizvodjac')} ({izabrani_broj})")
            
            # Google Drive logka
            putanja_drive = ins.get('putanja_folder')
            if putanja_drive and str(putanja_drive) != 'None':
                st.link_button("📂 OTVORI GOOGLE DRIVE FOLDER", putanja_drive, type="primary")
            else:
                search_url = f"https://drive.google.com{izabrani_broj}"
                st.link_button(f"🔍 PRETRAŽI DRIVE (Inv. br. {izabrani_broj})", search_url)

            t1, t2, t3, t4 = st.tabs(["🔧 Servis", "🧪 Etaloniranje", "📐 Baždarenje", "🖨️ Izveštaj"])
            
            for tab, tab_ime, naslov in [(t1,"istorija_servisa","Servis"), (t2,"istorija_etaloniranja","Etaloniranje"), (t3,"istorija_bazdarenja","Baždarenje")]:
                with tab:
                    df_h = run_query(f"SELECT * FROM {tab_ime} WHERE inventarni_broj = %s ORDER BY datum DESC", (izabrani_broj,))
                    st.dataframe(df_h, use_container_width=True)
                    if is_admin:
                        with st.form(f"f_{tab_ime}"):
                            c1, c2 = st.columns(2)
                            d_rada = c1.date_input("Datum", datetime.now())
                            br_dok = c2.text_input("Broj uverenja/naloga")
                            if st.form_submit_button(f"Spremi novi {naslov}"):
                                period = ins.get('period_provere', 1)
                                novi_rok = d_rada + pd.DateOffset(years=int(period))
                                conn = get_conn(); cur = conn.cursor()
                                cur.execute(f"INSERT INTO {tab_ime} (inventarni_broj, datum, broj_uverenja, vazi_do) VALUES (%s,%s,%s,%s)", (izabrani_broj, d_rada, br_dok, novi_rok.date()))
                                cur.execute("UPDATE oprema SET vazi_do = %s WHERE inventarni_broj = %s", (novi_rok.date(), izabrani_broj))
                                conn.commit(); conn.close()
                                st.success("Ažurirano!"); st.rerun()
            with t4:
                if st.button("🚀 GENERIŠI PDF"):
                    ds = run_query("SELECT datum, opis_kvara FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                    de = run_query("SELECT datum, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                    db = run_query("SELECT datum, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                    st.download_button("📥 Preuzmi", generisi_pdf(ins, ds, de, db), f"Karton_{izabrani_broj}.pdf")
        else:
            st.warning("Aparat nije pronađen.")

except Exception as e:
    st.error(f"Greška: {e}")
