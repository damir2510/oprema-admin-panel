import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn

# 1. KONFIGURACIJA (Mora biti prva komanda)
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

# SIGURNOSNA PROVERA
if not st.session_state.get('ulogovan'):
    st.warning("Niste ulogovani. Molimo prijavite se.")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje standardne navigacije
st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 2. SIDEBAR (Admin opcije na vrhu)
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")

# --- ADMIN SELEKTOR TABELA ---
tabela_opcije = {
    "Glavna Oprema": "oprema",
    "Istorija Servisa": "istorija_servisa",
    "Etaloniranje": "istorija_etaloniranja",
    "Baždarenje": "istorija_bazdarenja",
    "Kulture": "kulture_opsezi"
}

if is_admin:
    st.sidebar.header("📊 Admin Kontrole")
    izbor_labela = st.sidebar.selectbox("Izaberi tabelu za rad:", list(tabela_opcije.keys()))
    izabrana_tabela = tabela_opcije[izbor_labela]
else:
    izabrana_tabela = "oprema"
    izbor_labela = "Glavna Oprema"

st.sidebar.markdown("---")
st.sidebar.header("🚀 Navigacija")
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.rerun()

st.sidebar.markdown("---")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

# 3. POMOĆNE FUNKCIJE
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
        df_exp.to_excel(writer, index=False, sheet_name=name[:31])
    return output.getvalue()

# 4. GLAVNI PROGRAM
st.title(f"🔍 {izbor_labela}")

try:
    # Dobavljanje podataka
    df = run_query(f"SELECT * FROM {izabrana_tabela}")
    
    if not df.empty:
        # Standardizacija kolona
        df.columns = [c.strip().lower() for c in df.columns]

        if is_admin:
            st.info(f"🔓 **Admin Mod**: Uređivanje tabele `{izabrana_tabela}`")
            # Koristimo dinamički key za editor da bi se osvežio pri promeni tabele
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"editor_{izabrana_tabela}")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 SAČUVAJ IZMENE", use_container_width=True, type="primary"):
                    conn = get_conn(); cur = conn.cursor()
                    try:
                        # Brisanje starih i upis novih (najjednostavniji način za testiranje)
                        cur.execute(f"DELETE FROM {izabrana_tabela}")
                        for _, row in edited_df.iterrows():
                            cols = edited_df.columns.tolist()
                            vals = [None if pd.isna(row[c]) or str(row[c]) in ['nan','None',''] else row[c] for c in cols]
                            cur.execute(f"INSERT INTO {izabrana_tabela} ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))})", vals)
                        conn.commit()
                        st.success("Uspešno sačuvano!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Greška pri upisu: {e}")
                    finally: conn.close()
            with c2:
                excel_data = export_to_excel(df, izabrana_tabela)
                st.download_button(f"📥 PREUZMI {izbor_labela}", data=excel_data, file_name=f"{izabrana_tabela}.xlsx", use_container_width=True)
        else:
            # Korisnički prikaz
            st.dataframe(apply_styling(df, show_colors), use_container_width=True, hide_index=True)

        # --- MATIČNI KARTON ---
        if izabrani_broj:
            st.markdown("---")
            # Pronalaženje reda (osiguravamo da poredimo stringove)
            if 'inventarni_broj' in df.columns:
                rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
                
                if not rez.empty:
                    ins = rez.iloc[0] # KLJUČNA ISPRAVKA: iloc[0] uzima prvi red kao Series
                    st.subheader(f"📄 Matični karton: {ins.get('naziv_proizvodjac', 'Nezavedeno')}")
                    
                    t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                    
                    with t1:
                        # Detaljan prikaz u kolonama
                        d_cols = st.columns(3)
                        for i, (k, v) in enumerate(ins.to_dict().items()):
                            with d_cols[i % 3]:
                                st.text_input(label=k.replace('_',' ').title(), value=str(v), disabled=True)
                    
                    with t2:
                        m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                        dk = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                        if not dk.empty: st.table(dk)
                        else: st.warning("Nema podataka o kulturama.")
                    
                    # Ostali tabovi koriste direktne upite
                    with t3:
                        ds = run_query(f"SELECT * FROM istorija_servisa WHERE inventarni_broj = '{izabrani_broj}'")
                        st.dataframe(ds) if not ds.empty else st.info("Nema servisa.")
                    
                    with t4:
                        de = run_query(f"SELECT * FROM istorija_etaloniranja WHERE inventarni_broj = '{izabrani_broj}'")
                        st.dataframe(de) if not de.empty else st.info("Nema etaloniranja.")

                    with t5:
                        db = run_query(f"SELECT * FROM istorija_bazdarenja WHERE inventarni_broj = '{izabrani_broj}'")
                        st.dataframe(db) if not db.empty else st.info("Nema baždarenja.")
                else:
                    st.error(f"Inventarni broj '{izabrani_broj}' nije pronađen u bazi.")
    else:
        st.warning(f"Tabela `{izabrana_tabela}` je trenutno prazna.")

except Exception as e:
    st.error(f"Sistemska greška: {e}")
