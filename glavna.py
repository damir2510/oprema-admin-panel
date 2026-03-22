import streamlit as st
from db_utils import run_query

# 1. KONFIGURACIJA
st.set_page_config(page_title="BV Web App - Login", layout="centered", page_icon="🏢")

# Inicijalizacija session_state (da ne bi dobijali greške ako polja ne postoje)
if 'ulogovan' not in st.session_state:
    st.session_state['ulogovan'] = False
if 'is_premium' not in st.session_state:
    st.session_state['is_premium'] = 0

# CSS za sakrivanje sidebara na login strani
st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# 2. FUNKCIJA ZA PROVERU KORISNIKA
def proveri_korisnika(username, password):
    # Koristimo tvoju tabelu 'zaposleni'
    query = "SELECT korisnicko_ime, lozinka, is_premium FROM zaposleni WHERE korisnicko_ime = %s AND lozinka = %s"
    res = run_query(query, (username, password))
    if not res.empty:
        return res.iloc[0] # Vraćamo prvi red kao Series
    return None

# 3. SADRŽAJ POČETNE STRANE
def prikazi_pocetnu():
    if st.session_state['ulogovan']:
        st.title("✅ Uspešno ste prijavljeni")
        st.write(f"Dobrodošli nazad!")
        if st.button("🚀 UĐI U APLIKACIJU", use_container_width=True):
            st.switch_page(p_oprema)
        if st.button("🚪 Odjavi se", type="secondary"):
            st.session_state['ulogovan'] = False
            st.rerun()
    else:
        st.title("👋 Dobrodošli u BV Web App")
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            user = st.text_input("👤 Korisničko ime:")
            pwd = st.text_input("🔐 Lozinka:", type="password")
            
            if st.button("🚀 PRIJAVI SE", use_container_width=True):
                korisnik = proveri_korisnika(user, pwd)
                if korisnik is not None:
                    st.session_state['ulogovan'] = True
                    st.session_state['is_premium'] = int(korisnik['is_premium'])
                    st.success("Pristup odobren!")
                    st.rerun()
                else:
                    st.error("Pogrešno korisničko ime ili lozinka.")

# 4. DEFINISANJE STRANICA
p_pocetna = st.Page(prikazi_pocetnu, title="Početna", icon="🏠", default=True)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa opreme", icon="🗺️")
p_admin = st.Page("pages/oprema_admin.py", title="Admin Panel", icon="⚙️")

# 5. DINAMIČKA NAVIGACIJA
if st.session_state['ulogovan']:
    if st.session_state['is_premium'] == 5:
        pg = st.navigation([p_pocetna, p_oprema, p_mapa, p_admin])
    else:
        pg = st.navigation([p_pocetna, p_oprema, p_mapa])
else:
    pg = st.navigation([p_pocetna])

pg.run()
