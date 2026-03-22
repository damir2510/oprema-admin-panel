import streamlit as st
from db_utils import run_query

# 1. KONFIGURACIJA
st.set_page_config(page_title="BV Web App - Login", layout="centered", page_icon="🏢")

# Inicijalizacija session_state
if 'ulogovan' not in st.session_state:
    st.session_state['ulogovan'] = False
if 'is_premium' not in st.session_state:
    st.session_state['is_premium'] = 0
if 'ime_korisnika' not in st.session_state:
    st.session_state['ime_korisnika'] = ""

# CSS za sakrivanje sidebara na login strani
st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# 2. FUNKCIJA ZA PROVERU KORISNIKA (Usklađeno sa tvojim kolonama)
def proveri_korisnika(username, password):
    # Koristimo tvoju kolonu 'ime_prezime' i 'is_premium'
    query = "SELECT ime_prezime, is_premium FROM zaposleni WHERE korisnicko_ime = %s AND lozinka = %s"
    res = run_query(query, (username, password))
    if not res.empty:
        return res.iloc[0] # Vraća prvi red podataka
    return None

# 3. SADRŽAJ POČETNE STRANE
def prikazi_pocetnu():
    st.title("👋 Dobrodošli u BV Web App")
    st.write("Sistem za centralnu evidenciju opreme.")
    st.markdown("---")

    if st.session_state['ulogovan']:
        st.success(f"Prijavljeni ste kao: **{st.session_state['ime_korisnika']}**")
        if st.button("🚀 UĐI U EVIDENCIJU OPREME", use_container_width=True):
            st.switch_page(p_oprema)
        
        if st.button("🚪 Odjavi se", type="secondary"):
            st.session_state['ulogovan'] = False
            st.session_state['is_premium'] = 0
            st.rerun()
    else:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔐 Prijava")
            user = st.text_input("Korisničko ime:")
            pwd = st.text_input("Lozinka:", type="password")
            
            if st.button("PRIJAVI SE", use_container_width=True, type="primary"):
                podaci = proveri_korisnika(user, pwd)
                if podaci is not None:
                    st.session_state['ulogovan'] = True
                    st.session_state['is_premium'] = int(podaci['is_premium'])
                    st.session_state['ime_korisnika'] = podaci['ime_prezime']
                    st.success(f"Dobrodošli, {podaci['ime_prezime']}!")
                    st.rerun()
                else:
                    st.error("Pogrešno korisničko ime ili lozinka.")

# 4. DEFINISANJE STRANICA
p_pocetna = st.Page(prikazi_pocetnu, title="Početna", icon="🏠", default=True)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa", icon="🗺️")

# 5. DINAMIČKA NAVIGACIJA
if st.session_state['ulogovan']:
    pg = st.navigation([p_pocetna, p_oprema, p_mapa])
else:
    pg = st.navigation([p_pocetna])

pg.run()
