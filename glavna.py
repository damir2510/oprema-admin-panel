import streamlit as st
from db_utils import run_query

# 1. KONFIGURACIJA
st.set_page_config(page_title="BV Login", layout="centered", page_icon="🏢")

# Inicijalizacija sesije
if 'ulogovan' not in st.session_state:
    st.session_state['ulogovan'] = False

# Funkcija koja radi proveru i LOGOVANJE
def izvrsi_prijava():
    u = st.session_state.korisnik_input
    p = st.session_state.lozinka_input
    
    # Provera u bazi (tabela zaposleni)
    res = run_query("SELECT ime_prezime, is_premium FROM zaposleni WHERE korisnicko_ime = %s AND lozinka = %s", (u, p))
    
    if not res.empty:
        st.session_state['ulogovan'] = True
        st.session_state['is_premium'] = int(res.iloc[0]['is_premium'])
        st.session_state['ime_korisnika'] = res.iloc[0]['ime_prezime']
        # KLJUČ: Odmah prebacujemo na Opremu
        st.switch_page(p_oprema)
    else:
        st.error("❌ Pogrešno korisničko ime ili lozinka!")

# 2. DEFINISANJE STRANICA (Mora biti pre bilo kakve akcije)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa", icon="🗺️")
# Početna je funkcija da bi izbegli fajl-petlju
def prazna_pocetna(): pass
p_home = st.Page(prazna_pocetna, default=True)

# 3. LOGIKA PRIKAZA
if not st.session_state['ulogovan']:
    # Sakrivanje sidebara na login ekranu
    st.markdown("<style>[data-testid='stSidebar'] {display:none;}</style>", unsafe_allow_html=True)
    
    st.title("👋 BV Web App")
    st.write("Unesite podatke za pristup sistemu evidencije.")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input("Korisničko ime:", key="korisnik_input")
        # on_change hvata taster ENTER
        st.text_input("Lozinka:", type="password", key="lozinka_input", on_change=izvrsi_prijava)
        
        if st.button("🚀 PRIJAVI SE", use_container_width=True, type="primary"):
            izvrsi_prijava()
else:
    # Ako je korisnik ulogovan, navigacija mu dozvoljava ulaz
    pg = st.navigation([p_oprema, p_mapa])
    pg.run()
