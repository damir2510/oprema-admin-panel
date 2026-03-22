import streamlit as st

# 1. KONFIGURACIJA (Centrirano i bez menija)
st.set_page_config(page_title="BV Web App - Login", layout="centered", page_icon="🏢")

# CSS za potpuno sakrivanje sidebara na početnoj strani
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# 2. DEFINICIJA SADRŽAJA (Funkcija za login i dobrodošlicu)
def prikazi_pocetnu():
    st.title("👋 Dobrodošli u BV Web App")
    st.write("Sistem za evidenciju i praćenje terenske opreme.")
    st.markdown("---")

    # Polje za logovanje na sredini ekrana
    kol1, kol2, kol3 = st.columns([1, 2, 1])
    with kol2:
        lozinka = st.text_input("🔐 Unesite pristupnu lozinku:", type="password")
        
        # Provera lozinke (stavi svoju lozinku, npr. "bv2024")
        if lozinka == "damir123":
            st.success("Pristup odobren!")
            if st.button("🚀 UĐI U APLIKACIJU", use_container_width=True):
                st.switch_page(p_oprema)
        elif lozinka != "":
            st.error("Pogrešna lozinka. Pokušajte ponovo.")

    st.markdown("---")
    st.caption("© 2024 BV Web App | Sva prava zadržana")

# 3. DEFINISANJE STRANICA (Mora postojati da bi switch_page radio)
p_pocetna = st.Page(prikazi_pocetnu, title="Početna", icon="🏠", default=True)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa opreme")
p_admin = st.Page("pages/oprema_admin.py", title="Admin Panel")

# 4. NAVIGACIJA (Prazna lista [] znači da se ništa ne vidi u meniju levo)
pg = st.navigation([p_pocetna, p_oprema, p_mapa, p_admin], position="hidden")
pg.run()
