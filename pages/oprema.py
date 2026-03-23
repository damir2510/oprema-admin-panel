import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# 1. KONFIGURACIJA
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

if not st.session_state.get('ulogovan'):
    st.switch_page("glavna.py")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# 2. POMOĆNA FUNKCIJA ZA PDF
def generisi_pdf(ins, tabele):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Naslov
    inv_br = ins.get('inventarni_broj', 'N/A')
    elements.append(Paragraph(f"MATIČNI KARTON INSTRUMENTA br: {inv_br}", styles['Title']))
    elements.append(Paragraph(f"Datum izveštaja: {datetime.now().strftime('%d.%m.%Y.')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Osnovni podaci (Samo popunjena polja)
    elements.append(Paragraph("1. OSNOVNI PODACI", styles['Heading2']))
    podaci_lista = []
    detalji = [
        ("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"),
        ("Serijski br.", "seriski_broj"), ("Godina pr.", "godina_proizvodnje"),
        ("Sektor", "sektor"), ("Važi do", "vazi_do"), ("Upotreba od", "upotreba_od"),
        ("Opseg", "opseg_merenja"), ("Klasa", "klasa_tacnosti"),
        ("Preciznost", "preciznost"), ("Podeok", "podeok"),
        ("Radna Temp.", "radna_temperatura"), ("Vlažnost", "rel_vlaznost")
    ]
    
    for l, k in detalji:
        val = ins.get(k)
        if val and str(val).strip() not in ["", "None", "nan", "-"]:
            podaci_lista.append([l, str(val)])
    
    if podaci_lista:
        t = Table(podaci_lista, colWidths=[150, 300])
        t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('PADDING', (0,0), (-1,-1), 6)]))
        elements.append(t)
    
    # Istorija (Servis, Etaloniranje, Baždarenje)
    sekcije = [("2. ISTORIJA SERVISA", "servis"), ("3. ISTORIJA ETALONIRANJA", "etalon"), ("4. ISTORIJA BAŽDARENJA", "bazdarenje")]
    
    for naslov, kljuc in sekcije:
        df_sec = tabele.get(kljuc)
        elements.append(Spacer(1, 15))
        elements.append(Paragraph(naslov, styles['Heading2']))
        if df_sec is not None and not df_sec.empty:
            data = [df_sec.columns.to_list()] + df_sec.values.tolist()
            t_sec = Table(data, hAlign='LEFT')
            t_sec.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.lightgrey), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
            elements.append(t_sec)
        else:
            elements.append(Paragraph("Nema zabeleženih podataka.", styles['Italic']))

    doc.build(elements)
    return buffer.getvalue()

# 3. SIDEBAR I NAVIGACIJA (Standardno)
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")
# ... (Ostatak sidebara ostaje isti kao u prethodnom kodu) ...

# 4. GLAVNI PROGRAM
izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

try:
    df_raw = run_query("SELECT * FROM oprema")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]

        # --- MATIČNI KARTON ---
        if izabrani_broj:
            st.markdown("---")
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                
                # Sakupljanje istorije za PDF i prikaz
                ds = run_query("SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                de = run_query("SELECT datum_etaloniranja, vazi_do, broj_sertifikata FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                db = run_query("SELECT datum_bazdarenja, vazi_do, broj_uverenja FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.subheader(f"📑 Karton: {ins.get('naziv_proizvodjac', '')} (Inv. br: {izabrani_broj})")
                with c2:
                    pdf_data = generisi_pdf(ins, {"servis": ds, "etalon": de, "bazdarenje": db})
                    st.download_button("💾 PREUZMI PDF KARTON", data=pdf_data, file_name=f"Karton_{izabrani_broj}.pdf", mime="application/pdf", use_container_width=True)

                t1, t2, t3, t4, t5 = st.tabs(["📋 Podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                
                with t1:
                    detalji = [
                        ("🏭 Proizvođač", "proizvodjac"), ("📦 Model", "naziv_proizvodjac"),
                        ("🔢 Serijski br.", "seriski_broj"), ("📅 Godina pr.", "godina_proizvodnje"),
                        ("📍 Sektor", "sektor"), ("📅 Važi do", "vazi_do"),
                        ("📏 Opseg", "opseg_merenja"), ("🎯 Klasa", "klasa_tacnosti"),
                        ("⚖ Preciznost", "preciznost"), ("🔘 Podeok", "podeok"),
                        ("🌡️ Temp.", "radna_temperatura"), ("💧 Vlažnost", "rel_vlaznost"),
                        ("⏳ Upotreba od", "upotreba_od"), ("🔄 Period provere", "period_provere")
                    ]
                    cols = st.columns(4)
                    count = 0
                    for label, key in detalji:
                        val = ins.get(key)
                        # FILTRIRANJE PRAZNIH POLJA ZA PRIKAZ
                        if val and str(val).strip() not in ["", "None", "nan", "-"]:
                            with cols[count % 4]:
                                st.metric(label=label, value=str(val))
                            count += 1
                
                # Tabovi za prikaz na ekranu (ds, de, db) ostaju isti...
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

    else: st.warning("Baza je prazna.")
except Exception as e: st.error(f"Greška: {e}")
