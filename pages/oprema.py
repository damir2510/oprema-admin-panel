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

# 1. KONFIGURACIJA STRANE I STILIZACIJA (ARIAL)
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

# CSS za promenu fonta cele aplikacije na ekranu (Arial)
st.markdown("""
    <style>
        html, body, [class*="st-"], .stMarkdown, .stTable, .stDataFrame {
            font-family: 'Arial', sans-serif !important;
        }
        h1, h2, h3, h4 {
            font-family: 'Arial', sans-serif !important;
            font-weight: bold;
        }
        /* Smanjivanje fonta za info boxove u kartonu */
        .stAlert {
            padding: 0.5rem;
            margin-bottom: 0rem;
        }
    </style>
""", unsafe_allow_html=True)

# REGISTRACIJA FONTA ZA PDF (Pazi na veliko slovo Arial.ttf sa GitHuba)
try:
    pdfmetrics.registerFont(TTFont('Serbian', 'Arial.ttf'))
    FONT_NAME = 'Serbian'
except Exception as e:
    FONT_NAME = 'Helvetica'
    # st.sidebar.warning(f"Font Arial.ttf nije pronađen: {e}")

# SIGURNOSNA PROVERA
if 'ulogovan' not in st.session_state or not st.session_state['ulogovan']:
    st.switch_page("glavna.py")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje standardne navigacije
st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 2. SIDEBAR - ADMIN I NAVIGACIJA
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

    # IZVOZ EXCEL ODMAH ISPOD SELEKTORA
    df_za_exp = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df_za_exp.empty:
        buffer_ex = io.BytesIO()
        df_za_exp.to_excel(buffer_ex, index=False)
        st.sidebar.download_button("📥 IZVEZI EXCEL", data=buffer_ex.getvalue(), file_name=f"{izabrana_tabela}.xlsx", use_container_width=True)

    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader("Uvezi Excel (Upload)", type=["xlsx"])
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
    detalji_pdf = [
        ("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"),
        ("Serijski br.", "seriski_broj"), ("Sektor", "sektor"),
        ("Upotreba od", "upotreba_od"), ("Važi do", "vazi_do"),
        ("Opseg", "opseg_merenja"), ("Klasa", "klasa_tacnosti"),
        ("Preciznost", "preciznost"), ("Podeok", "podeok")
    ]
    for l, k in detalji_pdf:
        val = ins.get(k)
        if val and str(val).strip() not in ["", "None", "nan", "-"]:
            podaci_lista.append([l, str(val)])
    
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
        else:
            elements.append(Paragraph("Nema zabeleženih podataka.", s_normal))

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
            if 'datum' in col or 'vazi_do' in col or 'upotreba_od' in col:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # REDOSLED KOLONA
        cols = list(df.columns)
        if 'proizvodjac' in cols and 'naziv_proizvodjac' in cols:
            cols.insert(cols.index('naziv_proizvodjac'), cols.pop(cols.index('proizvodjac')))
        for c_end in ['napomena', 'putanja_folder']:
            if c_end in cols: cols.append(cols.pop(cols.index(c_end)))
        df = df[cols]

        # SAKRIVANJE KOLONA IZ TABELE (Ali ostaju u df za Karton)
        za_izbacivanje = ['id', 'datum_bazdarenja', 'ima_mk', 'gps_koordinate', 'radna_temperatura', 'rel_vlaznost', 'godina_proizvodnje', 'opseg_merenja', 'klasa_tacnosti', 'preciznost', 'podeok', 'upotreba_od', 'period_provere', 'bar_kod', 'stampac', 'status', 'zadnja_lokacija']
        df_prikaz = df.drop(columns=[c for c in za_izbacivanje if c in df.columns])
        if 'inventarni_broj' in df_prikaz.columns:
            df_prikaz = df_prikaz.rename(columns={'inventarni_broj': 'In. broj'})

        # PRETRAGA IZNAD TABELE
        pretraga = st.text_input("", placeholder="🔍 Brza pretraga po bilo kom polju...", label_visibility="collapsed").lower()
        if pretraga:
            df_prikaz = df_prikaz[df_prikaz.astype(str).apply(lambda x: x.str.lower().str.contains(pretraga)).any(axis=1)]

        # PRIKAZ TABELE
        if is_admin:
            st.data_editor(apply_styling(df_prikaz), use_container_width=True, key=f"ed_{izabrana_tabela}")
        else:
            st.dataframe(apply_styling(df_prikaz), use_container_width=True, hide_index=True)

        # --- MATIČNI KARTON ---
        if izabrani_broj and izabrana_tabela == "oprema":
            st.markdown("---")
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                
                # Sakupljanje istorije
                ds = run_query(f"SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = '{izabrani_broj}'")
                de = run_query(f"SELECT datum_etaloniranja, vazi_do, broj_sertifikata FROM istorija_etaloniranja WHERE inventarni_broj = '{izabrani_broj}'")
                db = run_query(f"SELECT datum_bazdarenja, vazi_do, broj_uverenja FROM istorija_bazdarenja WHERE inventarni_broj = '{izabrani_broj}'")
                
                c_head1, c_head2 = st.columns([3, 1])
                with c_head1:
                    st.subheader(f"📑 Karton: {ins.get('naziv_proizvodjac', '')} (Inv. br: {izabrani_broj})")
                with c_head2:
                    pdf_data = generisi_pdf(ins, ds, de, db)
                    st.download_button("💾 PREUZMI PDF KARTON", data=pdf_data, file_name=f"Karton_{izabrani_broj}.pdf", mime="application/pdf", use_container_width=True)

                t_tabs = st.tabs(["📋 Podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                
                with t_tabs[0]:
                    detalji_tab1 = [
                        ("🏭 Proizvođač", "proizvodjac"), ("📦 Model", "naziv_proizvodjac"),
                        ("🔢 Serijski br.", "seriski_broj"), ("📍 Sektor", "sektor"),
                        ("📅 Važi do", "vazi_do"), ("⏳ Upotreba od", "upotreba_od"),
                        ("📏 Opseg", "opseg_merenja"), ("🎯 Klasa", "klasa_tacnosti"),
                        ("⚖ Preciznost", "preciznost"), ("🔘 Podeok", "podeok")
                    ]
                    cols_k = st.columns(4)
                    count_k = 0
                    for lab, key in detalji_tab1:
                        val = ins.get(key)
                        if val and str(val).strip() not in ["", "None", "nan", "-"]:
                            with cols_k[count_k % 4]:
                                st.markdown(f"<p style='margin-bottom:-10px; font-size:0.9em; color:gray;'>{lab}</p>", unsafe_allow_html=True)
                                st.info(val)
                            count_k += 1

                with t_tabs[1]:
                    m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                    dk = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                    if not dk.empty: st.table(dk)
                with t_tabs[2]:
                    if not ds.empty: st.dataframe(ds, use_container_width=True, hide_index=True)
                with t_tabs[3]:
                    if not de.empty: st.dataframe(de, use_container_width=True, hide_index=True)
                with t_tabs[4]:
                    if not db.empty: st.dataframe(db, use_container_width=True, hide_index=True)

    else: st.warning("Tabela je prazna.")
except Exception as e: st.error(f"Greška: {e}")
