import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Gestione Bivacco", page_icon="⛺", layout="wide")

# PASSWORD PER ACCEDERE AL SITO (Generale per tutti)
PASSWORD_EVENTO = "fazzolettone2024" 

# PASSWORD PER AREA STAFF (Solo capi)
PASSWORD_STAFF = "capi123"

# STRUTTURA GRUPPI
# Ho aggiunto la categoria per gli esterni alla fine
GRUPPI = {
    "Reparto (11-16 anni)": ["Marco Rossi", "Giulia Bianchi", "Luca Verdi"],
    "Branco (8-11 anni)": ["Sofia Neri", "Matteo Gialli"],
    "Noviziato (16-17 anni)": ["Andrea Blu", "Chiara Viola"],
    "Amici & Ex Scout ⚜️": ["Nessun riferimento (Partecipo da solo/a)"] 
}

POSTI_LETTO_TOTALI = 20

# --- 2. SISTEMA DI LOGIN (PROTEZIONE SITO) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.password_input == PASSWORD_EVENTO:
        st.session_state.authenticated = True
    else:
        st.error("Password errata. Riprova.")

if not st.session_state.authenticated:
    st.title("🔒 Area Riservata Bivacco")
    st.text_input("Inserisci la password dell'evento per entrare:", type="password", key="password_input", on_change=check_password)
    st.stop() # Ferma il codice qui se non loggato

# --- 3. CONNESSIONE GOOGLE SHEETS ---
@st.cache_resource
def connect_to_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(st.secrets["private_url"]).sheet1
    return sheet

try:
    sheet = connect_to_sheet()
except Exception as e:
    st.error("Errore tecnico di connessione. Contatta lo staff.")
    st.stop()

# --- 4. FUNZIONI UTILI ---
def get_data():
    return pd.DataFrame(sheet.get_all_records())

# --- 5. INTERFACCIA PRINCIPALE (Visibile solo se loggati) ---
menu = st.sidebar.radio("Menu", ["📝 Prenotazione", "🔐 Area Staff"])

if menu == "📝 Prenotazione":
    st.title("⛺ Prenotazione Bivacco")
    
    # Calcolo posti
    df = get_data()
    if not df.empty and "Sistemazione" in df.columns:
        occupati = len(df[df["Sistemazione"] == "Letto"])
    else:
        occupati = 0
    rimasti = POSTI_LETTO_TOTALI - occupati

    # Contatori
    col1, col2 = st.columns(2)
    col1.metric("Posti Letto Totali", POSTI_LETTO_TOTALI)
    col2.metric("Disponibili ora", rimasti)
    st.markdown("---")

    with st.form("prenotazione"):
        st.subheader("I tuoi dati")
        
        # Selezione Intelligente
        gruppo = st.selectbox("A quale gruppo appartieni o sei collegato?", list(GRUPPI.keys()))
        
        # Se sono Amici/Ex Scout, mostriamo solo l'opzione unica, altrimenti la lista ragazzi
        lista_nomi = GRUPPI[gruppo]
        ragazzo = st.selectbox("Riferimento (Ragazzo/a o Se Stessi)", lista_nomi)
        
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome e Cognome Prenotato")
        tel = c2.text_input("Telefono")
        
        c3, c4 = st.columns(2)
        arrivo = c3.radio("Giorno Arrivo", ["Sabato", "Domenica"], horizontal=True)
        
        # Logica Letti
        opts = ["Tenda (illimitati)"]
        if rimasti > 0:
            opts.insert(0, "Letto")
        else:
            st.warning("⚠️ I letti sono finiti! Puoi prenotare solo in tenda.")
            
        sistemazione = c4.radio("Sistemazione", opts)
        
        if st.form_submit_button("Conferma Prenotazione"):
            if not nome or not tel:
                st.error("Inserisci Nome e Telefono!")
            else:
                row = [
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    gruppo,
                    ragazzo, # Sarà "Nessun riferimento" per gli amici
                    nome,
                    tel,
                    arrivo,
                    "Letto" if "Letto" in sistemazione else "Tenda",
                    "NO"
                ]
                sheet.append_row(row)
                st.success("Prenotazione Salvata con successo!")
                st.balloons()
                st.rerun()

elif menu == "🔐 Area Staff":
    st.title("Admin & Presenze")
    pwd = st.sidebar.text_input("Password Staff", type="password")
    
    if pwd == PASSWORD_STAFF:
        st.info("Gestione presenze attiva.")
        
        df = get_data()
        if not df.empty:
            # Filtro per vedere meglio
            filtro = st.selectbox("Filtra visualizzazione", ["Tutti"] + list(GRUPPI.keys()))
            
            df_view = df if filtro == "Tutti" else df[df["Gruppo"] == filtro]

            edited_df = st.data_editor(
                df_view,
                column_config={
                    "Presente": st.column_config.CheckboxColumn("Presente?", default=False)
                },
                disabled=["Data", "Nome Prenotato"],
                hide_index=True,
                num_rows="dynamic"
            )
            
            if st.button("💾 SALVA SU EXCEL"):
                # Attenzione: qui ricarichiamo tutto il dataset originale 
                # e aggiorniamo solo le righe visualizzate se necessario, 
                # ma per semplicità sovrascriviamo con la vista corrente se non filtrata,
                # o gestiamo la logica complessa.
                # PER SEMPLICITÀ (Visto il livello base):
                # Se si usa il filtro, il salvataggio potrebbe essere parziale.
                # Consiglio per ora: Salvare solo quando si visualizza "Tutti".
                
                if filtro != "Tutti":
                    st.warning("⚠️ Per salvare le modifiche, seleziona 'Tutti' nel filtro sopra, verifica i dati e poi salva.")
                else:
                    lista_dati = [edited_df.columns.values.tolist()] + edited_df.values.tolist()
                    sheet.clear()
                    sheet.update(lista_dati)
                    st.success("Database aggiornato!")
    else:
        st.warning("Inserisci password staff per vedere i dati.")
