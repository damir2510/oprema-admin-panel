import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn

# 1. SIGURNOSNA PROVERA
if not st.session_state.get('ulogovan'):
    st.rerun()

# 2. KONFIGURACIJA
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje standardne navigacije
st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 3. SIDEBAR
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")
st.sidebar.header("🚀 Navigacija")

if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.rerun()

st.sidebar.markdown("---")

# --- ADMIN SELEKTOR TABELA ---
izabrana_tabela = "oprema"
if is_admin:
    st.sidebar.header("📊 Upravljanje bazom")
    opcije = {
        "Glavna Oprema": "oprema",
        "Istorija Servisa": "istorija_servisa",
        "Etaloniranje": "istorija_etaloniranja",
        "Baždarenje": "istorija_bazdarenja",
        "Kulture": "kulture_opsezi"
    }
    izbor = st.sidebar.selectbox("Izaberi tabelu za rad:", list(opcije.keys()))
    izabrana_tabela = opcije[izbor]

st.sidebar.header("⚙️ Filteri")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (KARTON):", "").strip()

# 4. POMOĆNE FUNKCIJE
def apply_styling(df_st, active):
    if not active or 'vazi_do' not in df_st.columns: return df_st
    def highlight(v):
        try:
            if pd.notnull(v) and pd.to_datetime(v).date() < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except: pass
        return ""
    return df_st.style.applymap(highlight, subset=['vazi_do'])

def export_to_excel(df_exp, name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_exp.to_excel(writer, index=False, sheet_name=name)
    return output.getvalue()

# 5. GLAVNI PROGRAM
st.title(f"🔍 Centralna Evidencija: {izabrana_tabela.replace('_', ' ').title()}")

try:
    df = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]

        if is_admin:
            st.info(f"🔓 Uređujete tabelu: **{izabrana_tabela}**")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"editor_{izabrana_tabela}")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 SAČUVAJ IZMENE", use_container_width=True, type="primary"):
                    conn = get_conn(); cur = conn.cursor()
                    try:
                        # Logika za brisanje i update (uprošćena verzija)
                        cur.execute(f"DELETE FROM {izabrana_tabela}") # Restart tabele ili precizniji DELETE
                        for _, row in edited_df.iterrows():
                            cols = [c for c in edited_df.columns]
                            vals = [None if pd.isna(row[c]) or str(row[c]) in ['nan','None',''] else row[c] for c in cols]
                            cur.execute(f"INSERT INTO {izabrana_tabela} ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))})", vals)
                        conn.commit()
                        st.success("Tabela ažurirana!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Greška: {e}")
                    finally: conn.close()
            with c2:
                st.download_button(f"📥 PREUZMI {izbor}", data=export_to_excel(df, izabrana_tabela), file_name=f"{izabrana_tabela}.xlsx", use_container_width=True)
        else:
            st.dataframe(apply_styling(df, show_colors), use_container_width=True, hide_index=True)

        # MATIČNI KARTON (Samo ako gledamo glavnu tabelu oprema)
        if izabrani_broj and izabrana_tabela == "oprema":
            st.markdown("---")
            rez = df[df['inventarni_broj'].astype(str).strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                st.subheader(f"📄 Karton: {ins.get('naziv_proizvodjac', 'Nezavedeno')}")
                t1, t2, t3, t4, t5 = st.tabs(["📋 Podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                with t1:
                    st.json(ins.to_dict()) # Brzi prikaz svih polja
                with t2:
                    dk = run_query("SELECT * FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{str(ins.get('naziv_proizvodjac','')).lower()}%",))
                    st.table(dk) if not dk.empty else st.warning("Nema podataka.")
                # ... ostali tabovi rade na isti if-else princip
            else:
                st.error("Instrument nije pronađen.")
    else:
        st.warning("Tabela je prazna.")
except Exception as e:
    st.error(f"Greška: {e}")
