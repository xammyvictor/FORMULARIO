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
import requests

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Analytics Pulse",
    page_icon="📈",
    layout="wide"
)

# --- ESTILOS VISUALES PULSE (REPLICANDO leader-pulse-analytics.vercel.app) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .stApp { background-color: #F8FAFC; }
    
    /* Contenedor Principal de Dashboard */
    .dashboard-container {
        padding: 0px 20px;
    }
    
    /* Tarjetas KPI Premium */
    .pulse-kpi-card {
        background: white;
        padding: 24px;
        border-radius: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        border: 1px solid #F1F5F9;
        margin-bottom: 20px;
    }
    .pulse-kpi-label { color: #64748B; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
    .pulse-kpi-value { color: #0F172A; font-size: 2.2rem; font-weight: 800; line-height: 1; margin-bottom: 10px; }
    .pulse-kpi-trend { font-size: 0.8rem; font-weight: 600; display: flex; align-items: center; color: #10B981; }

    /* Hero / Goal Section */
    .hero-goal-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: white;
        padding: 40px;
        border-radius: 32px;
        margin-bottom: 40px;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
    }
    .goal-header { display: flex; justify-content: space-between; align-items: flex-end; }
    .goal-current { font-size: 3.5rem; font-weight: 800; margin: 10px 0; color: white !important; }
    .goal-target { font-size: 1.1rem; opacity: 0.6; font-weight: 500; }
    .goal-percentage { color: #E91E63; font-size: 2rem; font-weight: 800; }
    
    .progress-track-pulse { 
        background: rgba(255,255,255,0.1); 
        border-radius: 20px; 
        height: 16px; 
        width: 100%; 
        margin-top: 25px; 
        overflow: hidden; 
    }
    .progress-fill-pulse { 
        background: linear-gradient(90deg, #E91E63 0%, #FF4081 100%); 
        height: 100%; 
        border-radius: 20px; 
        transition: width 1.5s cubic-bezier(0.4, 0, 0.2, 1); 
    }

    /* Ranking Estilizado */
    .leader-item-pulse {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 18px;
        background: white;
        border-radius: 16px;
        margin-bottom: 10px;
        border: 1px solid #F1F5F9;
        transition: all 0.2s;
    }
    .leader-item-pulse:hover { border-color: #E91E63; transform: translateX(5px); }
    .leader-info-pulse { display: flex; align-items: center; gap: 15px; }
    .leader-avatar { background: #FCE4EC; color: #E91E63; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.9rem; }
    .leader-name-pulse { font-weight: 700; color: #334155; font-size: 0.95rem; }
    .leader-count-pulse { background: #F8FAFC; color: #64748B; padding: 6px 14px; border-radius: 12px; font-weight: 700; font-size: 0.85rem; border: 1px solid #E2E8F0; }

    /* Actividad / Chips */
    .active-chip {
        display: inline-block;
        padding: 8px 16px;
        background: #F1F5F9;
        color: #475569;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
        margin: 4px;
        border: 1px solid #E2E8F0;
    }

    /* Sidebar & Inputs */
    .stSidebar { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    .stButton>button { border-radius: 12px !important; background: #E91E63 !important; padding: 10px 24px !important; font-weight: 700 !important; border: none !important; }
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
        st.markdown("<div style='text-align:center; padding-top: 50px;'><h1>Pulse Analytics</h1><p>Sistema Maria Irma</p></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Acceder al Dashboard"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.session_state.is_guest = False
                    st.rerun()
                else: st.error("Usuario o contraseña incorrectos")
        return False
    return True

# --- NORMALIZACIÓN DE CIUDADES (CRÍTICO PARA EL MAPA) ---
def normalizar_ciudad_mapa(ciudad):
    c = str(ciudad).upper().strip()
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ",
        "GUACARI": "GUACARÍ",
        "DARIEN": "CALIMA",
        "BUENAVENTURA": "BUENAVENTURA",
        "PALMIRA": "PALMIRA",
        "CARTAGO": "CARTAGO",
        "YUMBO": "YUMBO",
        "LA UNION": "LA UNIÓN",
        "ANDALUCIA": "ANDALUCÍA",
        "BUGALAGRANDE": "BUGALAGRANDE",
        "CAICEDONIA": "CAICEDONIA",
        "CALIMA": "CALIMA",
        "CANELARIA": "CANDELARIA",
        "DAGUA": "DAGUA",
        "EL CERRITO": "EL CERRITO",
        "EL DOVIO": "EL DOVIO",
        "FLORIDA": "FLORIDA",
        "GINEBRA": "GINEBRA",
        "LA CUMBRE": "LA CUMBRE",
        "LA VICTORIA": "LA VICTORIA",
        "OBANDO": "OBANDO",
        "PRADERA": "PRADERA",
        "RESTREPO": "RESTREPO",
        "RIOFRIO": "RIOFRIO",
        "ROLDANILLO": "ROLDANILLO",
        "SAN PEDRO": "SAN PEDRO",
        "SEVILLA": "SEVILLA",
        "TORO": "TORO",
        "TRUJILLO": "TRUJILLO",
        "ULLOA": "ULLOA",
        "VERSALLES": "VERSALLES",
        "VIJES": "VIJES",
        "YOTOCO": "YOTOCO",
        "ZARZAL": "ZARZAL"
    }
    return mapping.get(c, c)

if "form_reset_key" not in st.session_state:
    st.session_state.form_reset_key = 0

# --- DASHBOARD PRINCIPAL ---
if check_session():
    usuario = st.session_state.user_name
    USUARIOS_ADMIN = ["fabian", "xammy", "brayan"]
    es_admin = usuario.lower() in USUARIOS_ADMIN and not st.session_state.get("is_guest", False)

    # Sidebar Moderno
    st.sidebar.markdown(f"<div style='background:#F1F5F9; padding:20px; border-radius:16px; margin-bottom:20px;'><p style='margin:0; font-size:0.7rem; font-weight:700; color:#64748B;'>SESIÓN ACTIVA</p><p style='margin:0; font-size:1.1rem; font-weight:800; color:#0F172A;'>{usuario.upper()}</p></div>", unsafe_allow_html=True)
    
    opcion = st.sidebar.radio("NAVEGACIÓN", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    # --- SECCIÓN: REGISTRO ---
    if opcion == "📝 Registro":
        st.title("🗳️ Captura de Datos")
        with st.form(key=f"form_pulse_{st.session_state.form_reset_key}", clear_on_submit=False):
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
            pue = st.text_input("Lugar de Votación (Opcional)")
            
            if st.form_submit_button("REGISTRAR CIUDADANO"):
                if nom and ced and tel:
                    if save_to_drive({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dire.upper(),"barrio":barr.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                        st.success("¡Registro guardado con éxito!")
                        st.session_state.form_reset_key += 1
                        time.sleep(1)
                        st.rerun()
                else: st.warning("Por favor complete los campos Nombre, Cédula y Teléfono.")

    # --- SECCIÓN: ESTADÍSTICAS ---
    elif opcion == "📊 Estadísticas":
        df = get_all_data()
        
        if not df.empty:
            st.markdown("<div class='dashboard-container'>", unsafe_allow_html=True)
            st.title("Pulse Analytics | Panel Estratégico")
            
            # --- 1. HERO GOAL (META) ---
            total = len(df)
            perc = min((total / META_REGISTROS) * 100, 100)
            
            st.markdown(f"""
                <div class="hero-goal-card">
                    <div class="goal-header">
                        <div>
                            <p style="margin:0; font-weight:700; opacity:0.6; font-size:0.85rem; letter-spacing:0.1em; text-transform:uppercase;">Meta de Gestión Ciudadana</p>
                            <h1 class="goal-current">{total:,}</h1>
                            <p style="margin:0; opacity:0.6; font-size:0.95rem;">Registros procesados en tiempo real</p>
                        </div>
                        <div style="text-align:right;">
                            <span class="goal-percentage">{perc:.1f}%</span>
                            <p class="goal-target">Objetivo: {META_REGISTROS:,}</p>
                        </div>
                    </div>
                    <div class="progress-track-pulse">
                        <div class="progress-fill-pulse" style="width: {perc}%;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # --- 2. KPIs (PULSE CARDS) ---
            hoy = datetime.now()
            df['F_S'] = df['Fecha Registro'].dt.date
            v_hoy = len(df[df['F_S'] == hoy.date()])
            v_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
            v_15d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=15))])
            v_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])

            k1, k2, k3, k4 = st.columns(4)
            data_kpis = [("Hoy", v_hoy), ("8 días", v_8d), ("15 días", v_15d), ("30 días", v_30d)]
            
            for col, (label, val) in zip([k1, k2, k3, k4], data_kpis):
                col.markdown(f"""
                    <div class="pulse-kpi-card">
                        <div class="pulse-kpi-label">{label}</div>
                        <div class="pulse-kpi-value">{val:,}</div>
                        <div class="pulse-kpi-trend">
                            <span style="margin-right:5px;">▲</span> Ritmo Activo
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 3. CONTENIDO PRINCIPAL: MAPA Y RANKING ---
            col_map, col_rank = st.columns([1.6, 1])

            with col_map:
                st.subheader("📍 Cobertura Territorial Valle")
                
                # Normalización y conteo para el mapa
                m_df = df.copy()
                m_df['Municipio_Map'] = m_df['Ciudad'].apply(normalizar_ciudad_mapa)
                map_data = m_df['Municipio_Map'].value_counts().reset_index()
                map_data.columns = ['Municipio', 'Registros']
                
                # Carga de GeoJSON del Valle del Cauca
                try:
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
                        height=600,
                        coloraxis_showscale=False,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                except:
                    st.error("Error al renderizar el mapa de dibujo. Mostrando resumen:")
                    st.dataframe(map_data, use_container_width=True)

            with col_rank:
                st.subheader("🏆 Leaderboard")
                ranking = df['Registrado Por'].value_counts().reset_index()
                ranking.columns = ['Líder', 'Total']
                
                for i, row in ranking.head(10).iterrows():
                    st.markdown(f"""
                        <div class="leader-item-pulse">
                            <div class="leader-info-pulse">
                                <div class="leader-avatar">{i+1}</div>
                                <span class="leader-name-pulse">{row['Líder'].upper()}</span>
                            </div>
                            <span class="leader-count-pulse">{row['Total']} regs</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                # Filtro interactivo de líder
                lider_sel = st.selectbox("🎯 Ver registros de líder:", ["Seleccionar líder..."] + list(ranking['Líder']))
                if lider_sel != "Seleccionar líder...":
                    sub = df[df['Registrado Por'] == lider_sel][['Fecha Registro', 'Nombre', 'Ciudad']].tail(15)
                    st.write(f"Últimos registros de **{lider_sel.upper()}**:")
                    st.dataframe(sub, use_container_width=True, hide_index=True)

            # --- 4. TENDENCIA Y LÍDERES ACTIVOS ---
            st.markdown("---")
            c_trend, c_chips = st.columns([2, 1])
            
            with c_trend:
                st.subheader("📈 Historial de Crecimiento")
                trend_data = df.groupby('F_S').size().reset_index(name='Ingresos')
                fig_trend = px.area(trend_data, x='F_S', y='Ingresos', color_discrete_sequence=['#E91E63'])
                fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                                       xaxis_title=None, yaxis_title=None, height=350)
                st.plotly_chart(fig_trend, use_container_width=True)
                
            with c_chips:
                st.subheader("👥 Equipo con Actividad")
                lideres_activos = sorted(df['Registrado Por'].unique())
                chips_html = ""
                for l in lideres_activos:
                    chips_html += f'<span class="active-chip">{l.upper()}</span>'
                st.markdown(f"<div style='margin-top:20px;'>{chips_html}</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.info("Sincronizando base de datos... Por favor espere.")

    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Búsqueda y Auditoría")
        df = get_all_data()
        if not df.empty:
            query = st.text_input("Buscar por Nombre, Cédula o Ciudad").upper()
            if query:
                res = df[df.astype(str).apply(lambda x: query in x.values, axis=1)]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(100), use_container_width=True)
