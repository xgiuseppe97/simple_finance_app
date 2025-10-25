import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import calendar

# -----------------------------
# CONFIG
# -----------------------------
DATA_FILE = "finanze.json"
PORTAFOGLI = ["Isybank", "Postepay", "Paypal", "Contanti"]
CATEGORIE = [
    "Stipendio", "Bonus", "Regali o entrate occasionali",  # Entrate
    "Affitto", "Canone di Amministrazione", "Bollette",
    "Mutuo", "Debito", "Assicurazioni",                    # Spese fisse
    "Spesa alimentare", "Trasporti", "Tempo libero",
    "Abbigliamento", "Cura personale",                     # Spese variabili
    "Salute", "Educazione / Formazione", "Investimenti",
    "Varie ed eventuali"                                   # Altro
]

st.set_page_config(page_title="💰 Gestionale Finanziario", layout="wide")
st.title("💰 Gestionale Personale Multi-Portafoglio")

# -----------------------------
# FUNZIONI
# -----------------------------
def load_data():
    try:
        df = pd.read_json(DATA_FILE)
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        return df
    except (FileNotFoundError, ValueError):
        return pd.DataFrame(columns=["Data", "Portafoglio", "Tipo", "Categoria", "Descrizione", "Importo"])

def save_data(df):
    df.to_json(DATA_FILE, orient="records", indent=2, date_format="iso")

def format_currency(value):
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def genera_report_pdf(df, mese, anno):
    df['AnnoMese'] = df['Data'].dt.to_period('M').dt.to_timestamp()
    df_mese = df[(df['Data'].dt.year == anno) & (df['Data'].dt.month == mese)]
    if df_mese.empty:
        return None

    # Calcoli principali
    saldi = {}
    for p in PORTAFOGLI:
        entrate = df_mese[(df_mese["Portafoglio"]==p) & (df_mese["Tipo"]=="Entrata")]["Importo"].sum()
        spese = df_mese[(df_mese["Portafoglio"]==p) & (df_mese["Tipo"]=="Uscita")]["Importo"].sum()
        saldi[p] = entrate - spese

    totale_entrate = df_mese[df_mese["Tipo"]=="Entrata"]["Importo"].sum()
    totale_spese = df_mese[df_mese["Tipo"]=="Uscita"]["Importo"].sum()
    risparmio_mese = totale_entrate - totale_spese

    # Crea PDF in memoria
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Titolo
    c.setFont("Helvetica-Bold", 16)
    c.drawString(3*cm, height-2*cm, f"Report Finanze Personali - {calendar.month_name[mese]} {anno}")

    # Saldi portafogli
    c.setFont("Helvetica", 12)
    y = height-3*cm
    c.drawString(3*cm, y, "💳 Saldi portafogli:")
    y -= 0.7*cm
    for p, saldo in saldi.items():
        c.drawString(4*cm, y, f"- {p}: {saldo:.2f} €")
        y -= 0.5*cm

    y -= 0.3*cm
    c.drawString(3*cm, y, f"💸 Entrate totali: {totale_entrate:.2f} €")
    y -= 0.5*cm
    c.drawString(3*cm, y, f"💰 Uscite totali: {totale_spese:.2f} €")
    y -= 0.5*cm
    c.drawString(3*cm, y, f"💵 Risparmio mese: {risparmio_mese:.2f} €")
    y -= 1*cm

    # ================================
    # Grafici a torta affiancati
    # ================================
    # 1) Spese per categoria
    spese_mese = df[(df["Tipo"] == "Uscita") & 
                    (df["AnnoMese"] == pd.Timestamp(year=anno, month=mese, day=1))]
    if not spese_mese.empty:
        spese_categoria = spese_mese.groupby("Categoria")["Importo"].sum().sort_values(ascending=False)
        fig1, ax1 = plt.subplots()
        ax1.pie(spese_categoria, labels=spese_categoria.index, autopct="%1.1f%%", startangle=90)
        ax1.set_title("Distribuzione spese")
        img_buffer1 = BytesIO()
        fig1.savefig(img_buffer1, format='PNG', bbox_inches='tight')
        img_buffer1.seek(0)
        img1 = ImageReader(img_buffer1)
        plt.close(fig1)
    else:
        img1 = None

    # 2) Stipendio vs spese
    entrate_stipendio = df[
        (df["Tipo"] == "Entrata") &
        (df["Categoria"] == "Stipendio") &
        (df["AnnoMese"] == pd.Timestamp(year=anno, month=mese, day=1))
    ]["Importo"].sum()
    if entrate_stipendio > 0:
        rimanente = max(entrate_stipendio - totale_spese, 0)
        dati_pie = [totale_spese, rimanente]
        etichette = ["Spese totali", "Stipendio rimanente"]
        fig2, ax2 = plt.subplots()
        ax2.pie(dati_pie, labels=etichette, autopct="%1.1f%%", startangle=90, colors=["#ff9999","#99ff99"])
        ax2.set_title("Stipendio vs Spese")
        img_buffer2 = BytesIO()
        fig2.savefig(img_buffer2, format='PNG', bbox_inches='tight')
        img_buffer2.seek(0)
        img2 = ImageReader(img_buffer2)
        plt.close(fig2)
    else:
        img2 = None

    # Inserimento grafici affiancati
    if img1:
        c.drawImage(img1, 3*cm, y-10*cm, width=8*cm, height=8*cm)
    if img2:
        c.drawImage(img2, 11*cm, y-10*cm, width=8*cm, height=8*cm)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# -----------------------------
# CARICA DATI
# -----------------------------
df = load_data()

# -----------------------------
# NAVIGAZIONE
# -----------------------------
sezione = st.sidebar.radio("📂 Sezioni", ["🏠 Dashboard", "🧾 Transazioni", "📈 Analisi"])

# -----------------------------
# DASHBOARD
# -----------------------------
if sezione == "🏠 Dashboard":
    st.header("📊 Panoramica generale")
    if df.empty:
        st.info("Ancora nessuna operazione registrata. Vai su **Transazioni** per aggiungerne una.")
    else:
        df["MeseAnno"] = df["Data"].dt.to_period("M")
        totale_entrate = df[df["Tipo"] == "Entrata"]["Importo"].sum()
        totale_uscite = df[df["Tipo"] == "Uscita"]["Importo"].sum()
        risparmio_totale = totale_entrate - totale_uscite
        mese_corrente = datetime.now().strftime("%Y-%m")
        df_mese = df[df["MeseAnno"] == mese_corrente]
        entrate_mese = df_mese[df_mese["Tipo"] == "Entrata"]["Importo"].sum()
        uscite_mese = df_mese[df_mese["Tipo"] == "Uscita"]["Importo"].sum()
        risparmio_mese = entrate_mese - uscite_mese

        col1, col2, col3 = st.columns(3)
        col1.metric("💸 Entrate totali", format_currency(totale_entrate))
        col2.metric("💰 Risparmio totale", format_currency(risparmio_totale))
        col3.metric("📆 Risparmio mese attuale", format_currency(risparmio_mese))

# -----------------------------
# INSERIMENTO / TRANSAZIONI
# -----------------------------
elif sezione == "🧾 Transazioni":
    st.header("➕ Aggiungi nuova operazione")
    col1, col2 = st.columns(2)
    with col1:
        descrizione = st.text_input("Descrizione", placeholder="Breve descrizione (es. Spesa supermercato)")
    with col2:
        importo = st.number_input("Importo (€)", min_value=0.0, step=0.5)

    col3, col4, col5 = st.columns(3)
    with col3:
        tipo = st.selectbox("Tipo", ["Entrata", "Uscita"])
    with col4:
        portafoglio = st.selectbox("Portafoglio", PORTAFOGLI)
    with col5:
        categoria = st.selectbox("Categoria", CATEGORIE)

    data_input = st.date_input("Data", datetime.now().date())
    data = pd.Timestamp(data_input)

    if st.button("💾 Aggiungi operazione"):
        if descrizione and importo > 0:
            new_row = pd.DataFrame({
                "Data": [data],
                "Portafoglio": [portafoglio],
                "Tipo": [tipo],
                "Categoria": [categoria],
                "Descrizione": [descrizione],
                "Importo": [importo]
            })
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success(f"{tipo} aggiunta con successo!")
        else:
            st.warning("Compila tutti i campi correttamente.")

    st.divider()
    st.header("📄 Storico operazioni")
    if df.empty:
        st.info("Nessuna operazione registrata.")
    else:
        st.dataframe(df.sort_values(by="Data", ascending=False), hide_index=True)

# -----------------------------
# ANALISI
# -----------------------------
elif sezione == "📈 Analisi":
    st.header("📊 Analisi mensile e andamento portafogli")
    if df.empty:
        st.info("Nessun dato disponibile per l’analisi.")
    else:
        df["AnnoMese"] = df["Data"].dt.to_period("M").dt.to_timestamp()
        mensile = df.groupby(["AnnoMese", "Tipo"])["Importo"].sum().unstack(fill_value=0)
        for col in ["Entrata", "Uscita"]:
            if col not in mensile.columns:
                mensile[col] = 0
        mensile["Risparmio"] = mensile["Entrata"] - mensile["Uscita"]
        mensile["Risparmio cumulativo"] = mensile["Risparmio"].cumsum()

        # Grafico risparmio cumulativo
        st.subheader("📈 Andamento risparmio cumulativo")
        st.line_chart(mensile["Risparmio cumulativo"])

        # Andamento portafogli
        st.subheader("💳 Andamento portafogli nel tempo")
        portafogli_mensili = df.groupby(["AnnoMese", "Portafoglio"])["Importo"].sum().unstack(fill_value=0)
        for p in PORTAFOGLI:
            if p not in portafogli_mensili.columns:
                portafogli_mensili[p] = 0
        portafogli_mensili = portafogli_mensili.cumsum()
        st.line_chart(portafogli_mensili)

        # Grafici a torta del mese selezionato
        st.subheader("🥧 Analisi spese e stipendio")
        mesi_disponibili = sorted(df["AnnoMese"].unique())
        mese_scelto = st.selectbox("Seleziona mese", mesi_disponibili)
        
        # Spese per categoria
        spese_mese = df[(df["Tipo"]=="Uscita") & (df["AnnoMese"]==pd.Timestamp(mese_scelto))]
        if not spese_mese.empty:
            spese_categoria = spese_mese.groupby("Categoria")["Importo"].sum().sort_values(ascending=False)
            fig, ax = plt.subplots()
            ax.pie(spese_categoria, labels=spese_categoria.index, autopct="%1.1f%%", startangle=90)
            ax.set_title(f"Distribuzione spese - {mese_scelto.strftime('%B %Y')}")
            st.pyplot(fig)
        
        # Stipendio vs spese
        entrate_stipendio = df[(df["Tipo"]=="Entrata") & (df["Categoria"]=="Stipendio") & (df["AnnoMese"]==pd.Timestamp(mese_scelto))]["Importo"].sum()
        spese_totali_mese = df[(df["Tipo"]=="Uscita") & (df["AnnoMese"]==pd.Timestamp(mese_scelto))]["Importo"].sum()
        if entrate_stipendio > 0:
            rimanente = max(entrate_stipendio - spese_totali_mese, 0)
            fig2, ax2 = plt.subplots()
            ax2.pie([spese_totali_mese, rimanente], labels=["Spese totali", "Stipendio rimanente"],
                    autopct="%1.1f%%", startangle=90, colors=["#ff9999","#99ff99"])
            ax2.set_title(f"Stipendio vs Spese - {mese_scelto.strftime('%B %Y')}")
            st.pyplot(fig2)
            st.write(f"**Totale stipendio:** {entrate_stipendio:.2f} €")
            st.write(f"**Totale spese:** {spese_totali_mese:.2f} €")
            st.write(f"**Risparmio mensile (stipendio - spese):** {rimanente:.2f} €")
        else:
            st.info("Nessuno stipendio registrato per questo mese.")

        st.divider()
        # Export CSV
        st.download_button("⬇️ Esporta CSV", df.to_csv(index=False).encode("utf-8"), "finanze.csv", "text/csv")

        # Export PDF
        mese_corrente = datetime.now().month
        anno_corrente = datetime.now().year
        pdf_buffer = genera_report_pdf(df, mese_corrente, anno_corrente)
        if pdf_buffer:
            st.download_button(
                "📄 Esporta report PDF",
                data=pdf_buffer,
                file_name=f"Report_Finanze_{calendar.month_name[mese_corrente]}_{anno_corrente}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("Nessuna operazione registrata per questo mese.")
