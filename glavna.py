import streamlit as st

# 1. KONFIGURACIJA
st.set_page_config(page_title="BV Web App", layout="centered", page_icon="🏢")

# 2. DEFINICIJA SADRŽAJA POČETNE STRANE
def prikazi_pocetnu():
    # CSS koji sakriva sidebar SAMO na početnoj stranici
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none; }
        </style>
    """, unsafe_allow_html=True)

    st.title("👋 Dobrodošli u BV Web App")
    st.write("Sistem za evidenciju i praćenje opreme.")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        lozinka = st.text_input("🔐 Lozinka za pristup:", type="password")
        if lozinka == "damir123":
            st.success("Pristup odobren!")
            if st.button("🚀 UĐI U APLIKACIJU", use_container_width=True):
                st.switch_page(p_oprema)
        elif lozinka != "":
            st.error("Pogrešna lozinka.")

# 3. DEFINISANJE STRANICA (Mora biti ovde da bi navigacija znala za njih)
p_pocetna = st.Page(prikazi_pocetnu, title="Početna", icon="🏠", default=True)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa opreme")
p_admin = st.Page("pages/oprema_admin.py", title="Admin Panel")

# 4. NAVIGACIJA
# Koristimo position="sidebar" ali ga sakrivamo CSS-om samo na login strani
pg = st.navigation([p_pocetna, p_oprema, p_mapa, p_admin], position="sidebar")
pg.run()
