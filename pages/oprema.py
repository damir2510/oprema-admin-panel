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

# REGISTRACIJA FONTA (Ako imas Arial.ttf na GitHubu)
try:
    pdfmetrics.registerFont(TTFont('Serbian', 'Arial.ttf'))
    FONT_NAME = 'Serbian'
except:
    FONT_NAME = 'Helvetica' # Rezervna opcija ako nema fajla

if not st.session_state.get('ulogovan'):
    st.switch_page("glavna.py")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje navigacije
st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 2. SIDEBAR - ADMIN KONTROLE
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

    # UVOZ (IMPORT)
    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader(f"Uvezi Excel u {izabrana_tabela}", type=["xlsx"])
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

# 3. PDF FUNKCIJA SA SVIM TABELAMA
def generisi_pdf(ins, ds, de, db):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Prilagođavanje stila za naša slova
    style_normal = styles['Normal']
    style_normal.fontName = FONT_NAME
    style_title = styles['Title']
    style_title.fontName = FONT_NAME
    style_h2 = styles['Heading2']
    style_h2.fontName = FONT_NAME

    elements = []
    
    inv_br = ins.get('inventarni_broj', 'N/A')
    elements.append(Paragraph(f"MATIČNI KARTON INSTRUMENTA br: {inv_br}", style_title))
    elements.append(Paragraph(f"Datum izveštaja: {datetime.now().strftime('%d.%m.%Y.')}", style_normal))
    elements.append(Spacer(1, 20))

    # OSNOVNI PODACI (Filtrirani)
    elements.append(Paragraph("1. OSNOVNI PODACI", style_h2))
    podaci_lista = []
    detalji = [
        ("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"),
        ("Serijski br.", "seriski_broj"), ("Godina pr.", "godina_proizvodnje"),
        ("Sektor", "sektor"), ("Važi do", "vazi_do"), ("Upotreba od", "upotreba_od"),
        ("Opseg", "opseg_merenja"), ("Klasa", "klasa_tacnosti"),
        ("Preciznost", "preciznost"), ("Podeok", "podeok")
    ]
    for l, k in detalji:
        val = ins.get(k)
        if val and str(val).strip() not in ["", "None", "nan", "-"]:
            podaci_lista.append([l, str(val)])
    
    if podaci_lista:
        t = Table(podaci_lista, colWidths=[150, 300])
        t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,-1), FONT_NAME)]))
        elements.append(t)

    # ISTORIJSKE TABELE (VRAĆENE)
    sekcije = [
        ("2. ISTORIJA SERVISA", ds),
        ("3. ISTORIJA ETALONIRANJA", de),
        ("4. ISTORIJA BAŽDARENJA", db)
    ]
    
    for naslov, df_sec in sekcije:
        elements.append(Spacer(1, 15))
        elements.append(Paragraph(naslov, style_h2))
        if not df_sec.empty:
            data = [df_sec.columns.to_list()] + df_sec.values.tolist()
            t_sec = Table(data, hAlign='LEFT')
            t_sec.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0), colors.lightgrey),
                ('GRID',(0,0),(-1,-1), 0.5, colors.grey),
                ('FONTNAME', (0,0), (-1,-1), FONT_NAME)
            ]))
            elements.append(t_sec)
        else:
            elements.append(Paragraph("Nema zabeleženih podataka.", style_normal))

    doc.build(elements)
    return buffer.getvalue()

# 4. GLAVNI PROGRAM
st.title(f"🔍 {izbor_prikaza}")

try:
    df = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Sakrivanje tehničkih kolona iz glavne tabele
        za_izbacivanje = ['ima_mk', 'gps_koordinate', 'radna_temperatura', 'rel_vlaznost', 'godina_proizvodnje', 'opseg_merenja', 'klasa_tacnosti', 'preciznost', 'podeok', 'upotreba_od', 'period_provere', 'bar_kod', 'stampac', 'status', 'putanja_folder', 'zadnja_lokacija']
        df_prikaz = df.drop(columns=[c for c in za_izbacivanje if c in df.columns])

        if is_admin:
            st.info(f"🔓 Admin Mod: `{izabrana_tabela}`")
            # Editor prikazuje samo bitne kolone, ostale čuva u bazi
            edited_df = st.data_editor(df_prikaz, use_container_width=True, key=f"ed_{izabrana_tabela}")
            st.download_button("📥 IZVEZI EXCEL", data=io.BytesIO().getvalue(), file_name=f"{izabrana_tabela}.xlsx")
        else:
            st.dataframe(df_prikaz, use_container_width=True, hide_index=True)

        # --- MATIČNI KARTON ---
        if izabrani_broj and izabrana_tabela == "oprema":
            st.markdown("---")
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                
                # Sakupljanje istorije za PDF
                ds = run_query("SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                de = run_query("SELECT datum_etaloniranja, vazi_do, broj_sertifikata FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                db = run_query("SELECT datum_bazdarenja, vazi_do, broj_uverenja FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.subheader(f"📑 Karton: {ins.get('naziv_proizvodjac', '')} (Inv. br: {izabrani_broj})")
                with c2:
                    pdf_data = generisi_pdf(ins, ds, de, db)
                    st.download_button("💾 PREUZMI PDF", data=pdf_data, file_name=f"Karton_{izabrani_broj}.pdf", mime="application/pdf", use_container_width=True)

                # Tabovi za prikaz na ekranu (Isto kao ranije)
                t1, t2, t3, t4, t5 = st.tabs(["📋 Podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                with t1:
                    detalji_k = [("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"), ("Serijski br.", "seriski_broj"), ("Sektor", "sektor"), ("Važi do", "vazi_do"), ("Upotreba od", "upotreba_od"), ("Period provere", "period_provere"), ("Opseg", "opseg_merenja"), ("Klasa", "klasa_tacnosti"), ("Preciznost", "preciznost"), ("Podeok", "podeok"), ("Temp.", "radna_temperatura"), ("Vlažnost", "rel_vlaznost")]
                    cols = st.columns(4)
                    count = 0
                    for l, k in detalji_k:
                        val = ins.get(k)
                        if val and str(val).strip() not in ["", "None", "nan", "-"]:
                            with cols[count % 4]: st.metric(label=l, value=str(val))
                            count += 1
                with t2:
                    m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                    dk = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                    if not dk.empty: st.table(dk)
                with t3:
                    if not ds.empty: st.dataframe(ds, use_container_width=True, hide_index=True)
                with t4:
                    if not de.empty: st.dataframe(de, use_container_width=True, hide_index=True)
                with t5:
                    if not db.empty: st.dataframe(db, use_container_width=True, hide_index=True)

    else: st.warning("Tabela je prazna.")
except Exception as e: st.error(f"Greška: {e}")
