import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import qrcode
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import requests

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="📈",
    layout="wide"
)

# --- ESTILOS VISUALES PREMIUM (Pulse Style) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .stApp { background-color: #F8FAFC; }
    
    /* Contenedores de Tarjetas */
    .pulse-card {
        background: white;
        padding: 24px;
        border-radius: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        border: 1px solid #F1F5F9;
        margin-bottom: 24px;
    }
    
    /* Tarjetas KPI */
    .kpi-card {
        background: white;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #F1F5F9;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        text-align: left;
    }
    .kpi-label { color: #64748B; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-value { color: #0F172A; font-size: 2.2rem; font-weight: 800; margin: 8px 0; }
    
    /* Barra de Meta */
    .goal-section {
        background: #0F172A;
        color: white;
        padding: 35px;
        border-radius: 28px;
        margin-bottom: 35px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .goal-bar-bg { background: rgba(255,255,255,0.1); border-radius: 15px; height: 18px; width: 100%; margin: 20px 0; overflow: hidden; }
    .goal-bar-fill { 
        background: linear-gradient(90deg, #E91E63 0%, #FF4081 100%); 
        height: 100%; border-radius: 15px; transition: width 1.5s ease; 
    }
    
    /* Leaderboard */
    .leader-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid #F1F5F9;
    }
    .rank-circle { background: #FCE4EC; color: #E91E63; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.8rem; margin-right: 15px; }
    .leader-name { font-weight: 600; color: #1E293B; flex-grow: 1; }
    .leader-count { background: #F1F5F9; color: #475569; padding: 6px 12px; border-radius: 10px; font-weight: 700; font-size: 0.8rem; }

    /* Forms */
    .stButton>button { border-radius: 14px !important; background: #E91E63 !important; padding: 10px 24px !important; font-weight: 700 !important; border: none !important; color: white !important; width: 100%; }
    .stTextInput>div>div>input { border-radius: 12px !important; border: 1px solid #E2E8F0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- GOOGLE SHEETS API ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets: return None
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception: return None

def get_all_data():
    client = get_google_sheet_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        data = sh.sheet1.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'], errors='coerce')
        return df
    except Exception: return pd.DataFrame()

def save_to_drive(data_dict):
    client = get_google_sheet_client()
    if not client: return False
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        worksheet = sh.sheet1
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        usuario_actual = st.session_state.get("user_name", "Desconocido")
        row = [timestamp, usuario_actual, data_dict["nombre"], data_dict["cedula"], 
               data_dict["telefono"], data_dict["ocupacion"], data_dict["direccion"], 
               data_dict["barrio"], data_dict["ciudad"], data_dict.get("puesto", "")]
        worksheet.append_row(row)
        return True
    except Exception: return False

# --- SESIÓN ---
def check_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    try:
        params = st.query_params
        if "ref" in params and "query_checked" not in st.session_state:
            st.session_state.logged_in = True
            st.session_state.user_name = params["ref"]
            st.session_state.is_guest = True
            st.session_state.query_checked = True
    except: pass

    if not st.session_state.logged_in:
        st.markdown("<div style='text-align:center; padding-top: 50px;'><h1>Pulse Analytics</h1><p>Gestión Ciudadana Maria Irma</p></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Ingresar al Dashboard"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.session_state.is_guest = False
                    st.rerun()
                else: st.error("Acceso incorrecto")
        return False
    return True

if "form_reset_key" not in st.session_state:
    st.session_state.form_reset_key = 0

# --- LÓGICA DE NORMALIZACIÓN DE CIUDADES PARA EL MAPA ---
def normalizar_ciudad(ciudad):
    c = str(ciudad).upper().strip()
    # Mapeo exacto para que el GeoJSON pinte el color
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ",
        "GUACARI": "GUACARÍ",
        "DARIEN": "CALIMA",
        "CALIMA DARIEN": "CALIMA",
        "BUENAVENTURA": "BUENAVENTURA",
        "PALMIRA": "PALMIRA",
        "CARTAGO": "CARTAGO",
        "YUMBO": "YUMBO",
        "CAICEDONIA": "CAICEDONIA",
        "ROLDANILLO": "ROLDANILLO",
        "LA UNION": "LA UNIÓN",
        "SEVILLA": "SEVILLA",
        "ZARZAL": "ZARZAL"
    }
    return mapping.get(c, c)

# --- DASHBOARD ---
if check_session():
    usuario = st.session_state.user_name
    es_admin = usuario.lower() in ["fabian", "xammy", "brayan"] and not st.session_state.get("is_guest", False)

    st.sidebar.markdown(f"<div style='background:#FCE4EC; padding:15px; border-radius:15px; color:#E91E63; font-weight:800; text-align:center;'>PULSE | {usuario.upper()}</div>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    opcion = st.sidebar.radio("MENÚ", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    if opcion == "📝 Registro":
        st.title("🗳️ Registro de Ciudadano")
        with st.form(key=f"p_form_{st.session_state.form_reset_key}", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nombre Completo")
                ced = st.text_input("Cédula")
                tel = st.text_input("Teléfono")
            with col2:
                ocu = st.text_input("Ocupación")
                dire = st.text_input("Dirección")
                barr = st.text_input("Barrio")
            ciu = st.text_input("Ciudad / Municipio", value="BUGA")
            pue = st.text_input("Puesto de Votación (Opcional)")
            
            if st.form_submit_button("GUARDAR REGISTRO"):
                if nom and ced and tel:
                    if save_to_drive({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dire.upper(),"barrio":barr.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                        st.success("✅ ¡Registro completado!")
                        st.session_state.form_reset_key += 1
                        time.sleep(1)
                        st.rerun()
                else: st.warning("Por favor complete los datos obligatorios")

    elif opcion == "📊 Estadísticas":
        df = get_all_data()
        
        if not df.empty:
            st.title("Pulse Analytics | Valle del Cauca")
            
            # --- SECCIÓN 1: META DE CAMPAÑA ---
            total = len(df)
            perc = min((total / META_REGISTROS) * 100, 100)
            
            st.markdown(f"""
                <div class="goal-section">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <p style="margin:0; font-weight:700; opacity:0.6; font-size:0.8rem; letter-spacing:0.1em;">PROGRESO HACIA LA META</p>
                            <h1 style="color:white !important; margin:10px 0; font-size:3.5rem; font-weight:800;">{total:,}</h1>
                            <p style="margin:0; opacity:0.5;">Registros totales en base de datos</p>
                        </div>
                        <div style="text-align:right;">
                            <h2 style="color:#E91E63 !important; margin:0; font-size:2.5rem;">{perc:.1f}%</h2>
                            <p style="margin:0; opacity:0.5;">Meta: {META_REGISTROS:,}</p>
                        </div>
                    </div>
                    <div class="goal-bar-bg">
                        <div class="goal-bar-fill" style="width: {perc}%;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # --- SECCIÓN 2: KPIs ---
            hoy = datetime.now()
            df['F_S'] = df['Fecha Registro'].dt.date
            v_hoy = len(df[df['F_S'] == hoy.date()])
            v_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
            v_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])
            lideres_act = df['Registrado Por'].nunique()

            k1, k2, k3, k4 = st.columns(4)
            metrics = [("Nuevos Hoy", v_hoy), ("Últimos 8 Días", v_8d), ("Últimos 30 Días", v_30d), ("Líderes Activos", lideres_act)]
            
            for col, (label, val) in zip([k1, k2, k3, k4], metrics):
                col.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">{label}</div>
                        <div class="kpi-value">{val:,}</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- SECCIÓN 3: EL MAPA Y LEADERBOARD ---
            c_left, c_right = st.columns([1.5, 1])

            with c_left:
                st.subheader("📍 Mapa de Calor - Valle del Cauca")
                
                # Preparamos los datos del mapa con la normalización
                m_df = df.copy()
                m_df['Municipio_Map'] = m_df['Ciudad'].apply(normalizar_ciudad)
                map_data = m_df['Municipio_Map'].value_counts().reset_index()
                map_data.columns = ['Municipio', 'Registros']
                
                # Intentamos cargar el dibujo del mapa (GeoJSON)
                try:
                    # Este GeoJSON es específico de los municipios del Valle del Cauca
                    geojson_url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
                    response = requests.get(geojson_url)
                    geojson_data = response.json()
                    
                    fig = px.choropleth(
                        map_data,
                        geojson=geojson_data,
                        locations='Municipio',
                        featureidkey="properties.name",
                        color='Registros',
                        color_continuous_scale="RdPu",
                        template="plotly_white"
                    )
                    fig.update_geos(fitbounds="locations", visible=False)
                    fig.update_layout(
                        margin={"r":0,"t":0,"l":0,"b":0},
                        height=550,
                        coloraxis_showscale=False
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                except:
                    st.error("No se pudo cargar el dibujo del mapa. Mostrando gráfico alternativo:")
                    st.bar_chart(map_data.set_index('Municipio'))

            with c_right:
                st.subheader("🏆 Ranking de Líderes")
                rank = df['Registrado Por'].value_counts().reset_index()
                rank.columns = ['Líder', 'Total']
                
                for i, row in rank.head(10).iterrows():
                    st.markdown(f"""
                        <div class="leader-row">
                            <div class="rank-circle">{i+1}</div>
                            <div class="leader-name">{row['Líder'].upper()}</div>
                            <div class="leader-count">{row['Total']} registros</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                sel_lider = st.selectbox("🎯 Ver registros de un líder:", ["Seleccionar..."] + list(rank['Líder']))
                if sel_lider != "Seleccionar...":
                    detalle = df[df['Registrado Por'] == sel_lider][['Fecha Registro', 'Nombre', 'Ciudad']].tail(10)
                    st.dataframe(detalle, use_container_width=True, hide_index=True)

            # --- SECCIÓN 4: TENDENCIA ---
            st.markdown("---")
            st.subheader("📈 Tendencia Diaria de Ingresos")
            trend = df.groupby('F_S').size().reset_index(name='Ingresos')
            fig_trend = px.area(trend, x='F_S', y='Ingresos', color_discrete_sequence=['#E91E63'])
            fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                                   height=300, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_trend, use_container_width=True)

        else:
            st.info("No hay datos suficientes para generar el análisis.")

    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador Pulse")
        df = get_all_data()
        if not df.empty:
            search = st.text_input("Nombre, Cédula o Ciudad").upper()
            if search:
                res = df[df.astype(str).apply(lambda x: search in x.values, axis=1)]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(100), use_container_width=True)
