import streamlit as st
from db_utils import run_query

# 1. OSNOVNA KONFIGURACIJA
st.set_page_config(page_title="BV Web App - Login", layout="centered", page_icon="🏢")

# Inicijalizacija session_state
if 'ulogovan' not in st.session_state:
    st.session_state['ulogovan'] = False
if 'is_premium' not in st.session_state:
    st.session_state['is_premium'] = 0

# --- 2. DEFINISANJE STRANICA (MORA BITI OVDE NA VRHU) ---
def prikazi_pocetnu():
    st.title("👋 Dobrodošli u BV Web App")
    st.write("Sistem za centralnu evidenciju opreme.")
    st.markdown("---")

    if st.session_state['ulogovan']:
        st.success(f"Prijavljeni ste kao: **{st.session_state.get('ime_korisnika', '')}**")
        if st.button("🚀 UĐI U EVIDENCIJU OPREME", use_container_width=True):
            st.switch_page(p_oprema) # Sada p_oprema sigurno postoji
    else:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.subheader("🔐 Prijava")
            user = st.text_input("Korisničko ime:", key="user_input")
            pwd = st.text_input("Lozinka:", type="password", key="pwd_input")
            
            if st.button("PRIJAVI SE", use_container_width=True, type="primary"):
                # Provera u bazi
                res = run_query("SELECT ime_prezime, is_premium FROM zaposleni WHERE korisnicko_ime = %s AND lozinka = %s", (user, pwd))
                if not res.empty:
                    st.session_state['ulogovan'] = True
                    st.session_state['is_premium'] = int(res.iloc[0]['is_premium'])
                    st.session_state['ime_korisnika'] = res.iloc[0]['ime_prezime']
                    st.success("Uspešna prijava!")
                    st.rerun()
                else:
                    st.error("Pogrešni podaci!")

# Kreiranje objekata stranica
p_pocetna = st.Page(prikazi_pocetnu, title="Početna", icon="🏠", default=True)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa", icon="🗺️")

# 3. NAVIGACIJA I SAKRIVANJE SIDEBARA
st.markdown("<style>[data-testid='stSidebar'] {display:none;}</style>", unsafe_allow_html=True)

# Ako je ulogovan, dozvoli navigaciju, inače samo početna
if st.session_state['ulogovan']:
    pg = st.navigation([p_pocetna, p_oprema, p_mapa], position="hidden")
else:
    pg = st.navigation([p_pocetna], position="hidden")

pg.run()
