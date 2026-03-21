import streamlit as st

# 1. DEFINISANJE STRANICA (Struktura menija)
# Napomena: Fajlovi moraju postojati na navedenim putanjama
p_pocetna = st.Page("glavna.py", title="Početna", icon="🏠", default=True)
p_radni_sati = st.Page("pages/radni_sati.py", title="Radni sati", icon="🕒")
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")

# Ove dve strane se NEĆE videti u glavnom meniju levo dok ne uđemo u "Opremu"
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa opreme", icon="🗺️")
p_admin = st.Page("pages/oprema_admin.py", title="Admin Panel", icon="⚙️")

# 2. NAVIGACIJA (Prikazujemo samo osnovne 3 strane)
pg = st.navigation([p_pocetna, p_radni_sati, p_oprema])

# 3. POKRETANJE NAVIGACIJE
pg.run()

# --- SADRŽAJ POČETNE STRANE (Isti kao tvoj, samo bez set_page_config jer ga navigacija kontroliše) ---
st.title("👋 Dobrodošli u BV Web App")
st.markdown("---")

st.subheader("Izaberite sekciju kojoj želite da pristupite:")

col1, col2 = st.columns(2)

with col1:
    st.info("🕒 **Radni sati**")
    st.write("Evidencija i pregled terenskog rada.")
    if st.button("Idi na Radne sate"):
        st.switch_page(p_radni_sati)

with col2:
    st.success("🔍 **Oprema**")
    st.write("Pregled instrumenata, statusa i baždarenja.")
    if st.button("Idi na Opremu"):
        st.switch_page(p_oprema)

st.markdown("---")
with st.expander("📌 Aktuelno"):
    st.write("- Sistem za GPS praćenje lokacije je aktivan.")
    st.write("- Nova baza opreme je sinhronizovana.")
