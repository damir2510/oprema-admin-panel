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

# Registracija fonta za PDF (proveri da li je Arial.ttf u root folderu na GitHubu)
try:
    pdfmetrics.registerFont(TTFont('Serbian', 'Arial.ttf'))
    FONT_NAME = 'Serbian'
except:
    FONT_NAME = 'Helvetica'

# --- FUNKCIJA ZA GENERISANJE PDF-a ---
def generisi_pdf_karton(ins, df_s, df_e, df_b, df_k):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Stilovi sa podrškom za font
    s_naslov = styles['Title']; s_naslov.fontName = FONT_NAME
    s_h2 = styles['Heading2']; s_h2.fontName = FONT_NAME
    s_n = styles['Normal']; s_n.fontName = FONT_NAME

    elements = []
    inv_br = ins.get('inventarni_broj', 'N/A')
    
    # NASLOV
    elements.append(Paragraph(f"MATIČNI KARTON INSTRUMENTA br: {inv_br}", s_naslov))
    elements.append(Paragraph(f"Datum izveštaja: {datetime.now().strftime('%d.%m.%Y.')}", s_n))
    elements.append(Spacer(1, 20))

    # 1. TEHNIČKI PODACI
    elements.append(Paragraph("1. TEHNIČKE KARAKTERISTIKE", s_h2))
    teh_podaci = [
        ["Proizvođač:", ins.get('proizvodjac', '-')],
        ["Model:", ins.get('naziv_proizvodjac', '-')],
        ["Serijski broj:", ins.get('seriski_broj', '-')],
        ["Vrsta aparata:", ins.get('vrsta_aparata', '-')],
        ["Godina proizvodnje:", str(ins.get('godina_proizvodnje', '-'))],
        ["U upotrebi od:", str(ins.get('upotreba_od', '-'))],
        ["Opseg merenja:", ins.get('opseg_merenja', '-')],
        ["Klasa tačnosti:", ins.get('klasa_tacnosti', '-')],
        ["Preciznost / Podeok:", f"{ins.get('preciznost', '-')} / {ins.get('podeok', '-')}"]
    ]
    t1 = Table(teh_podaci, colWidths=[150, 300])
    t1.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,-1), FONT_NAME)]))
    elements.append(t1)
    elements.append(Spacer(1, 20))

    # 2. ISTORIJE (BAŽDARENJE, ETALONIRANJE, SERVIS)
    sekcije = [("2. BAŽDARENJA", df_b), ("3. ETALONIRANJA", df_e), ("4. SERVISI", df_s), ("5. KULTURE / OPSEZI", df_k)]
    
    for naslov, df_sec in sekcije:
        elements.append(Paragraph(naslov, s_h2))
        if not df_sec.empty:
            # Pretvaranje DF-a u listu za tabelu
            data = [df_sec.columns.to_list()] + df_sec.values.tolist()
            t_sec = Table(data, hAlign='LEFT', repeatRows=1)
            t_sec.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
                ('FONTSIZE', (0,0), (-1,-1), 8)
            ]))
            elements.append(t_sec)
        else:
            elements.append(Paragraph("Nema zabeleženih podataka.", s_n))
        elements.append(Spacer(1, 15))

    doc.build(elements)
    return buffer.getvalue()

# --- GLAVNI KOD STRANICE ---
# ... (Sidebar i login provera ostaju isti) ...

try:
    df_raw = run_query("SELECT * FROM oprema")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Redosled u glavnoj tabeli
        red_kolona = ['inventarni_broj', 'sektor', 'vrsta_aparata', 'proizvodjac', 'naziv_proizvodjac', 'seriski_broj', 'trenutni_radnik', 'zadnja_lokacija', 'vazi_do']
        df_prikaz = df[[c for c in red_kolona if c in df.columns]]
        st.dataframe(apply_styling(df_prikaz), use_container_width=True)

    if izabrani_broj:
        res = run_query("SELECT * FROM oprema WHERE inventarni_broj = %s", (izabrani_broj,))
        if not res.empty:
            ins = res.iloc[0].to_dict()
            st.subheader(f"📑 Karton: {ins.get('naziv_proizvodjac')} - {izabrani_broj}")
            
            # (INFO PANEL PRIKAZ ...)
            
            # --- PDF DUGME ---
            if st.button("🖨️ GENERIŠI I SAČUVAJ PDF KARTON", use_container_width=True):
                # Prikupljanje svih podataka za PDF
                df_s = run_query("SELECT datum_servisa, opis_kvara, broj_uverenja FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                df_e = run_query("SELECT datum_etaloniranja, broj_uverenja, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                df_b = run_query("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                df_k = run_query("SELECT kultura, opseg_od, opseg_do FROM kulture_opsezi WHERE naziv_proizvodjac = %s", (ins.get('naziv_proizvodjac'),))
                
                pdf_bin = generisi_pdf_karton(ins, df_s, df_e, df_b, df_k)
                st.download_button(
                    label="📥 PREUZMI GENERISANI PDF",
                    data=pdf_bin,
                    file_name=f"Karton_{izabrani_broj}.pdf",
                    mime="application/pdf"
                )

            # (TABOVI OSTAJU ISTI ...)

except Exception as e:
    st.error(f"Greška: {e}")
