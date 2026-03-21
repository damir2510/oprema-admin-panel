import streamlit as st

# 1. KONFIGURACIJA
st.set_page_config(page_title="BV Web App", layout="centered", page_icon="🏢")

# 2. DEFINICIJA SADRŽAJA POČETNE STRANE
def prikazi_pocetnu():
    st.title("👋 Dobrodošli u BV Web App")
    st.markdown("---")
    st.subheader("Izaberite sekciju kojoj želite da pristupite:")
    
    col1, col2, col3 = st.columns(3)
    with col2:
        st.success("🔍 **Sektor Opreme**")
        st.write("Pregled instrumenata, statusa i baždarenja.")
        if st.button("Uđi u evidenciju opreme", use_container_width=True):
            st.switch_page(p_oprema)
    
    st.markdown("---")
    with st.expander("📌 Aktuelno"):
        st.write("- Sistem za opremu je povezan sa Aiven SQL bazom.")

# 3. DEFINISANJE STRANICA (Sklonjen 'radni_sati.py' jer pravi grešku)
p_pocetna = st.Page(prikazi_pocetnu, title="Početna", icon="🏠", default=True)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa opreme", icon="🗺️")
p_admin = st.Page("pages/oprema_admin.py", title="Admin Panel", icon="⚙️")

# 4. NAVIGACIJA (Samo one koje želiš u sidebaru)
pg = st.navigation({
    "Glavni meni": [p_pocetna, p_oprema]
})

# 5. POKRETANJE
pg.run()
