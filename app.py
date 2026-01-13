import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import qrcode
from io import BytesIO
import re
import json
import requests

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
API_KEY = "" # El entorno proporciona la clave automáticamente

st.set_page_config(
    page_title="Formulario de Registro - IA Electoral",
    page_icon="🗳️",
    layout="centered"
)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #333333 !important; }
    h1, h2, h3 { color: #D81B60 !important; text-align: center; font-family: 'Helvetica'; }
    .stButton>button { 
        width: 100%; background-color: #E91E63 !important; color: white !important; 
        border-radius: 8px; font-weight: bold;
    }
    .stButton>button:hover { background-color: #C2185B !important; }
    [data-testid="stSidebar"] { background-color: #FCE4EC !important; }
    input:disabled { background-color: #f8f9fa !important; color: #495057 !important; border: 1px solid #dee2e6 !important; }
    .ia-badge {
        background-color: #E1F5FE; color: #01579B; padding: 5px 10px; 
        border-radius: 15px; font-size: 0.8em; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE IA Y BÚSQUEDA ---

def consultar_puesto_ia(cedula, barrio, ciudad):
    """
    Usa la API de Gemini con búsqueda en Google para encontrar el puesto de votación.
    """
    try:
        system_prompt = "Eres un asistente experto en el sistema electoral colombiano. Tu tarea es identificar el puesto de votación más probable para un ciudadano basado en su ubicación o cédula."
        user_query = f"¿Cuál es el puesto de votación asignado en Colombia para un ciudadano en el barrio {barrio}, ciudad {ciudad}? Si es posible, verifica si hay información pública para la cédula {cedula}. Responde únicamente con el NOMBRE DEL PUESTO Y LA DIRECCIÓN."
        
        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "tools": [{"google_search": {}}]
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"
        
        # Implementación de reintentos con backoff exponencial
        for delay in [1, 2, 4]:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                return text.strip() if text else "Puesto no determinado"
            time.sleep(delay)
            
        return "Consulta manual requerida"
    except Exception:
        return "Error en consulta de IA"

def validar_cedula_colombiana(cedula_str):
    if not cedula_str or not re.match(r'^\d+$', cedula_str): return False
    if len(cedula_str) < 6: return False
    
    # Algoritmo de pesos solicitado
    pesos = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
    numero_base = cedula_str[:-1]
    dv_ingresado = int(cedula_str[-1])
    suma = 0
    for i, digito in enumerate(reversed(numero_base)):
        if i < len(pesos): suma += int(digito) * pesos[i]
    residuo = suma % 11
    dv_calculado = 11 - residuo if residuo > 1 else residuo
    return dv_ingresado == dv_calculado

# --- CONEXIÓN A DRIVE ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Error de credenciales: {e}")
        return None

def save_and_learn(data_dict):
    """Guarda el registro y alimenta la base de datos de lugares automáticamente."""
    client = get_google_sheet_client()
    if not client: return False
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        
        # 1. Guardar en Hoja Principal
        ws_reg = sh.sheet1
        row = [
            pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            st.session_state.user_name,
            data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
            data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"],
            data_dict["ciudad"], data_dict["lugar_votacion"]
        ]
        ws_reg.append_row(row)
        
        # 2. Alimentar base de datos de Lugares_Votacion (para auto-crearla)
        try:
            ws_lugares = sh.worksheet("Lugares_Votacion")
        except gspread.WorksheetNotFound:
            ws_lugares = sh.add_worksheet(title="Lugares_Votacion", rows="100", cols="5")
            ws_lugares.append_row(["Barrio", "Ciudad", "Lugar_Votacion", "Ultima_Actualizacion"])
        
        # Guardar la relación para futuras búsquedas rápidas
        ws_lugares.append_row([data_dict["barrio"], data_dict["ciudad"], data_dict["lugar_votacion"], row[0]])
        
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- LÓGICA DE SESIÓN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = "invitado"

if not st.session_state.logged_in:
    st.title("🔐 Acceso")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            if p == "1234":
                st.session_state.logged_in = True
                st.session_state.user_name = u
                st.rerun()
    st.stop()

# --- FORMULARIO ---
st.title("🗳️ Maria Irma - Registro Inteligente")

# Estados del formulario
if "lugar_detectado" not in st.session_state: st.session_state.lugar_detectado = ""

with st.form("main_form"):
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre Completo").upper()
        cedula = st.text_input("Cédula (con DV)")
        telefono = st.text_input("Teléfono")
        ocupacion = st.text_input("Ocupación").upper()
    with col2:
        ciudad = st.text_input("Ciudad").upper()
        barrio = st.text_input("Barrio").upper()
        direccion = st.text_input("Dirección").upper()
        
    st.markdown("---")
    
    # Botón de búsqueda IA (dentro o fuera del form, lo pondremos aquí para procesar antes de guardar)
    buscar_puesto = st.form_submit_button("🔍 Validar y Buscar Puesto")
    
    if buscar_puesto:
        if not validar_cedula_colombiana(cedula):
            st.error("❌ Cédula inválida. Verifique el número y el dígito verificador.")
        elif not (barrio and ciudad):
            st.warning("⚠️ Necesito Ciudad y Barrio para localizar el puesto.")
        else:
            with st.spinner("🤖 Consultando puesto de votación con IA..."):
                puesto = consultar_puesto_ia(cedula, barrio, ciudad)
                st.session_state.lugar_detectado = puesto
                st.info(f"📍 **Puesto Sugerido:** {puesto}")

    # Campo de solo lectura para el resultado
    lugar_final = st.text_input("Lugar de Votación (Asignado por IA)", value=st.session_state.lugar_detectado, disabled=True)
    
    enviar = st.form_submit_button("✅ Guardar Registro")
    
    if enviar:
        if not st.session_state.lugar_detectado:
            st.error("Primero debe buscar el puesto de votación.")
        elif not nombre:
            st.error("Complete el nombre del ciudadano.")
        else:
            data = {
                "nombre": nombre, "cedula": cedula, "telefono": telefono,
                "ocupacion": ocupacion, "direccion": direccion, "barrio": barrio,
                "ciudad": ciudad, "lugar_votacion": st.session_state.lugar_detectado
            }
            if save_and_learn(data):
                st.success("¡Registro guardado y base de datos actualizada!")
                st.session_state.lugar_detectado = ""
                time.sleep(2)
                st.rerun()

st.sidebar.markdown(f"### 👤 {st.session_state.user_name.capitalize()}")
st.sidebar.info("Este sistema utiliza IA para suministrar el puesto de votación basándose en los datos ingresados y búsquedas en tiempo real.")
if st.sidebar.button("Salir"):
    st.session_state.logged_in = False
    st.rerun()
