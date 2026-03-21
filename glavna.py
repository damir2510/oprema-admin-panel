import streamlit as st

# 1. POSTAVKE STRANICE
st.set_page_config(page_title="BV Web App - Početna", layout="centered", page_icon="🏢")

# 2. DEFINISANJE STRANICA (Struktura navigacije)
# 'p_oprema' je u folderu pages, ostale su u root-u (glavnom folderu)
p_pocetna = st.Page("glavna.py", title="Početna", icon="🏠", default=True)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")

# Ove dve stranice se NEĆE videti u meniju levo jer ih ne ubacujemo u st.navigation listu
# Ali su definisane kako bi switch_page mogao da ih pronađe
p_mapa = st.Page("mapa_opreme.py", title="Mapa opreme")
p_admin = st.Page("oprema_admin.py", title="Admin Panel")

# 3. AKTIVACIJA NAVIGACIJE (Prikazujemo samo Početnu i Opremu)
pg = st.navigation([p_pocetna, p_oprema])
pg.run()

# --- SADRŽAJ POČETNE STRANE ---
st.title("👋 Dobrodošli u BV Web App")
st.markdown("---")

st.subheader("Izaberite sekciju kojoj želite da pristupite:")

# Prikazujemo samo karticu za Opremu (Radni sati su privremeno uklonjeni)
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.success("🔍 **Sektor Opreme**")
    st.write("Pregled instrumenata, statusa, baždarenja i mernih opsega.")
    if st.button("Uđi u evidenciju opreme", use_container_width=True):
        st.switch_page(p_oprema)

st.markdown("---")
st.write("💡 *Savet: Koristite meni sa leve strane za brzu navigaciju.*")

# Opcioni status sistema
with st.expander("📌 Aktuelne informacije"):
    st.write("- Modul za opremu je povezan sa Aiven SQL bazom.")
    st.write("- Admin panelu i mapi se pristupa direktno iz sekcije Oprema.")
