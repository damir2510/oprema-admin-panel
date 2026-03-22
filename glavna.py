import streamlit as st
from db_utils import run_query

# 1. KONFIGURACIJA
st.set_page_config(page_title="BV Web App - Login", layout="centered", page_icon="🏢")

# CSS za sakrivanje sidebara na login strani
st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# 2. FUNKCIJA ZA PROVERU KORISNIKA
def proveri_korisnika(username, password):
    query = "SELECT korisnicko_ime, lozinka, is_premium FROM zaposleni WHERE korisnicko_ime = %s AND lozinka = %s"
    res = run_query(query, (username, password))
    if not res.empty:
        return res.iloc[0] # Vraća red sa podacima o korisniku
    return None

# 3. SADRŽAJ POČETNE STRANE
def prikazi_pocetnu():
    st.title("👋 Dobrodošli u BV Web App")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user = st.text_input("👤 Korisničko ime:")
        pwd = st.text_input("🔐 Lozinka:", type="password")
        
        if st.button("🚀 PRIJAVI SE", use_container_width=True):
            korisnik = proveri_korisnika(user, pwd)
            
            if korisnik is not None:
                # Čuvamo podatke u session_state da ih aplikacija "pamti"
                st.session_state['ulogovan'] = True
                st.session_state['is_premium'] = int(korisnik['is_premium'])
                st.success(f"Zdravo, {user}!")
                st.rerun()
            else:
                st.error("Neispravno korisničko ime ili lozinka.")

    st.markdown("---")

# 4. DEFINISANJE STRANICA
p_pocetna = st.Page(prikazi_pocetnu, title="Početna", icon="🏠", default=True)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa opreme", icon="🗺️")
p_admin = st.Page("pages/oprema_admin.py", title="Admin Panel", icon="⚙️")

# 5. DINAMIČKA NAVIGACIJA NA OSNOVU ROLI
if st.session_state.get('ulogovan'):
    # Ako je is_premium == 5, vidi SVE
    if st.session_state.get('is_premium') == 5:
        pg = st.navigation([p_pocetna, p_oprema, p_mapa, p_admin])
    # Ako je 0 (ili bilo šta drugo), vidi samo Mapu i Opremu
    else:
        pg = st.navigation([p_pocetna, p_oprema, p_mapa])
else:
    # Ako nije ulogovan, vidi samo početnu (Login)
    pg = st.navigation([p_pocetna])

pg.run()
