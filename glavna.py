import streamlit as st

# 1. OSNOVNA KONFIGURACIJA
st.set_page_config(page_title="BV Web App", layout="centered", page_icon="🏢")

# 2. SADRŽAJ POČETNE STRANE
st.title("👋 Dobrodošli u BV Web App")
st.markdown("---")

st.subheader("Izaberite sekciju kojoj želite da pristupite:")

col1, col2, col3 = st.columns(3)
with col2:
    st.success("🔍 **Sektor Opreme**")
    st.write("Pregled instrumenata, statusa i baždarenja.")
    # U klasičnom modu switch_page koristi samo ime fajla ako je u pages/
    if st.button("Uđi u evidenciju opreme", use_container_width=True):
        st.switch_page("pages/oprema.py")

st.markdown("---")
with st.expander("📌 Aktuelno"):
    st.write("- Sistem za opremu je povezan sa Aiven SQL bazom.")
