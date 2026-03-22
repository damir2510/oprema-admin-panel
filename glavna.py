import streamlit as st
from db_utils import run_query

# 1. KONFIGURACIJA
st.set_page_config(page_title="BV Login", layout="centered", page_icon="🏢")

if 'ulogovan' not in st.session_state: st.session_state['ulogovan'] = False

# Funkcija za Login (poziva se na Enter ili Dugme)
def pokusaj_login():
    u = st.session_state.user_input
    p = st.session_state.pwd_input
    res = run_query("SELECT ime_prezime, is_premium FROM zaposleni WHERE korisnicko_ime = %s AND lozinka = %s", (u, p))
    if not res.empty:
        st.session_state['ulogovan'] = True
        st.session_state['is_premium'] = int(res.iloc[0]['is_premium'])
        st.session_state['ime_korisnika'] = res.iloc[0]['ime_prezime']
    else:
        st.error("Pogrešni podaci!")

# CSS za sakrivanje sidebara
st.markdown("<style>[data-testid='stSidebar'] {display:none;}</style>", unsafe_allow_html=True)

if not st.session_state['ulogovan']:
    st.title("👋 BV Web App")
    st.subheader("Prijavite se za pristup sistemu")
    st.text_input("Korisničko ime:", key="user_input")
    # type="password" i taster Enter automatski okidaju login
    st.text_input("Lozinka:", type="password", key="pwd_input", on_change=pokusaj_login)
    if st.button("Uloguj se", use_container_width=True):
        pokusaj_login()
        if st.session_state['ulogovan']: st.rerun()
else:
    # Ako je ulogovan, odmah ga baci na Opremu (nema više "međustrane")
    st.switch_page("pages/oprema.py")

# DEFINICIJA STRANICA (Mora biti ovde radi switch_page-a)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa", icon="🗺️")
# Navigacija je nevidljiva na login strani
pg = st.navigation([p_oprema, p_mapa], position="hidden")
pg.run()
