import streamlit as st

# Postavke stranice
st.set_page_config(page_title="BV Web App - Početna", layout="centered", page_icon="🏢")

# NASLOV I DOBRODOŠLICA
st.title("👋 Dobrodošli u BV Web App")
st.markdown("---")

st.subheader("Izaberite sekciju kojoj želite da pristupite:")

# KARTICE ZA NAVIGACIJU (Vizuelni meni na sredini)
col1, col2 = st.columns(2)

with col1:
    st.info("🕒 **Radni sati**")
    st.write("Evidencija i pregled terenskog rada.")
    # Napomena: Streamlit će sam dodati link u sidebar, 
    # ali možemo dodati i instrukciju:
    st.caption("Pronađite 'Radni sati' u meniju levo 👈")

with col2:
    st.success("🔍 **Oprema**")
    st.write("Pregled instrumenata, statusa i baždarenja.")
    st.caption("Pronađite 'Oprema' u meniju levo 👈")

st.markdown("---")
st.write("💡 *Savet: Koristite strelicu u gornjem levom uglu ako je meni sakriven.*")

# OPCIONO: Kratke vesti ili status sistema
with st.expander("📌 Aktuelno"):
    st.write("- Sistem za GPS praćenje lokacije je aktivan.")
    st.write("- Nova baza opreme je sinhronizovana.")
