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

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Analytics Pulse",
    page_icon="📈",
    layout="wide"
)

# --- ESTILOS VISUALES (Pulse Premium Style) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .stApp { background-color: #F8FAFC; }
    
    /* Contenedores de Tarjetas KPI */
    .pulse-card {
        background: white;
        padding: 24px;
        border-radius: 20px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.02);
        border: 1px solid #F1F5F9;
        margin-bottom: 20px;
    }
    
    .pulse-label { color: #64748B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
    .pulse-value { color: #0F172A; font-size: 1.75rem; font-weight: 800; line-height: 1; }
    .pulse-trend { font-size: 0.8rem; font-weight: 600; margin-top: 10px; display: flex; align-items: center; }
    .trend-up { color: #10B981; }
    
    /* Barra de Meta */
    .goal-box {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: white;
        padding: 30px;
        border-radius: 24px;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }
    
    .goal-progress-bg { background: rgba(255,255,255,0.1); border-radius: 10px; height: 14px; width: 100%; margin: 15px 0; }
    .goal-progress-fill { 
        background: linear-gradient(90deg, #E91E63 0%, #FF4081 100%); 
        height: 14px; border-radius: 10px; transition: width 1s ease-in-out; 
    }
    
    /* Ranking Table Custom */
    .leader-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid #F1F5F9;
    }
    .leader-name { font-weight: 600; color: #334155; }
    .leader-count { background: #FCE4EC; color: #E91E63; padding: 4px 12px; border-radius: 12px; font-weight: 700; font-size: 0.85rem; }

    /* Ajustes Streamlit */
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 800 !important; }
    .stSidebar { background-color: #FFFFFF !important; }
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
        st.markdown("<h1 style='text-align:center;'>Pulse Login</h1>", unsafe_allow_html=True)
        with st.container():
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Acceder al Dashboard"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.session_state.is_guest = False
                    st.rerun()
                else: st.error("Credenciales Inválidas")
        return False
    return True

if "form_reset_key" not in st.session_state:
    st.session_state.form_reset_key = 0

# --- DASHBOARD ---
if check_session():
    usuario = st.session_state.user_name
    USUARIOS_ADMIN = ["fabian", "xammy", "brayan"]
    es_admin = usuario.lower() in USUARIOS_ADMIN and not st.session_state.get("is_guest", False)

    st.sidebar.markdown(f"<div style='padding: 10px; border-radius: 12px; background: #FCE4EC; color: #E91E63; font-weight: 800; text-align: center;'>{usuario.upper()}</div>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    opcion = st.sidebar.radio("MENÚ PULSE", ["📝 Registro", "🔍 Búsqueda", "📊 Estadísticas"] if es_admin else ["📝 Registro"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    if opcion == "📝 Registro":
        st.title("🗳️ Registro Ciudadano")
        with st.form(key=f"p_reg_{st.session_state.form_reset_key}"):
            c1, c2 = st.columns(2)
            with c1:
                nom = st.text_input("Nombre Completo")
                ced = st.text_input("Número de Cédula")
                tel = st.text_input("Teléfono de Contacto")
            with c2:
                ocu = st.text_input("Ocupación / Oficio")
                dire = st.text_input("Dirección de Residencia")
                barr = st.text_input("Barrio")
            ciu = st.text_input("Municipio", value="BUGA")
            pue = st.text_input("Lugar de Votación (Opcional)")
            
            if st.form_submit_button("REGISTRAR AHORA"):
                if nom and ced and tel:
                    if save_to_drive({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dire.upper(),"barrio":barr.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                        st.success("¡Excelente! Registro capturado.")
                        st.session_state.form_reset_key += 1
                        time.sleep(1)
                        st.rerun()
                else: st.warning("Por favor complete los campos requeridos.")

    elif opcion == "📊 Estadísticas":
        df = get_all_data()
        
        if not df.empty:
            st.title("Pulse Analytics | Gestión Maria Irma")
            
            # --- 1. SECCIÓN DE META ---
            total_actual = len(df)
            porcentaje = (total_actual / META_REGISTROS) * 100
            
            st.markdown(f"""
                <div class="goal-box">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <p style="margin: 0; opacity: 0.8; font-size: 0.9rem; font-weight: 600;">ESTADO DE LA META GLOBAL</p>
                            <h2 style="color: white !important; margin: 5px 0 0 0; font-size: 2.5rem;">{total_actual:,} <span style="font-size: 1rem; opacity: 0.6;">registros</span></h2>
                        </div>
                        <div style="text-align: right;">
                            <h3 style="color: #E91E63 !important; margin: 0; font-size: 1.8rem;">{porcentaje:.1f}%</h3>
                            <p style="margin: 0; opacity: 0.8; font-size: 0.8rem;">de {META_REGISTROS:,}</p>
                        </div>
                    </div>
                    <div class="goal-progress-bg">
                        <div class="goal-progress-fill" style="width: {porcentaje}%;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # --- 2. KPIs TEMPORALES ---
            hoy = datetime.now()
            df['Fecha_Solo'] = df['Fecha Registro'].dt.date
            m_hoy = len(df[df['Fecha_Solo'] == hoy.date()])
            m_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
            m_15d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=15))])
            m_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])

            k1, k2, k3, k4 = st.columns(4)
            labels = ["Hoy", "Últimos 8 Días", "Últimos 15 Días", "Últimos 30 Días"]
            vals = [m_hoy, m_8d, m_15d, m_30d]
            
            for col, label, val in zip([k1, k2, k3, k4], labels, vals):
                col.markdown(f"""
                    <div class="pulse-card">
                        <div class="pulse-label">{label}</div>
                        <div class="pulse-value">{val:,}</div>
                        <div class="pulse-trend trend-up">▲ Actividad positiva</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 3. SECCIÓN MIXTA: MAPA Y RANKING ---
            c_left, c_right = st.columns([1.2, 1])

            with c_left:
                st.subheader("🗺️ Distribución Valle del Cauca")
                
                # Mapeo de nombres para asegurar que el GeoJSON funcione
                normalization = {
                    "BUGA": "GUADALAJARA DE BUGA",
                    "CALI": "SANTIAGO DE CALI",
                    "JAMUNDI": "JAMUNDÍ",
                    "DARIEN": "CALIMA",
                    "CALIMA DARIEN": "CALIMA",
                    "GUACARI": "GUACARÍ",
                    "TULUA": "TULUÁ"
                }
                
                muni_counts = df['Ciudad'].str.upper().str.strip().replace(normalization).value_counts().reset_index()
                muni_counts.columns = ['Municipio', 'Registros']
                
                try:
                    geojson_url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
                    fig_map = px.choropleth(
                        muni_counts, geojson=geojson_url, locations='Municipio',
                        featureidkey="properties.name", color='Registros',
                        color_continuous_scale="RdPu",
                        template="plotly_white"
                    )
                    fig_map.update_geos(fitbounds="locations", visible=False)
                    fig_map.update_layout(margin={"r":0,"t":10,"l":0,"b":0}, height=500,
                                         coloraxis_showscale=False)
                    st.plotly_chart(fig_map, use_container_width=True, config={'displayModeBar': False})
                except:
                    st.error("Error cargando el dibujo del mapa. Verifica conexión.")

            with c_right:
                st.subheader("🏆 TOP Líderes")
                rank_df = df['Registrado Por'].value_counts().reset_index()
                rank_df.columns = ['Líder', 'Registros']
                
                # Ranking visual estilo lista
                for _, row in rank_df.head(8).iterrows():
                    st.markdown(f"""
                        <div class="leader-row">
                            <span class="leader-name">{row['Líder'].upper()}</span>
                            <span class="leader-count">{row['Registros']} rec.</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                # Explorador de líder
                lider_sel = st.selectbox("Explorar registros de:", ["Seleccionar líder..."] + list(rank_df['Líder']))
                if lider_sel != "Seleccionar líder...":
                    sub = df[df['Registrado Por'] == lider_sel][['Fecha Registro', 'Nombre', 'Ciudad']]
                    st.dataframe(sub, use_container_width=True, hide_index=True)

            # --- 4. TENDENCIA ---
            st.markdown("---")
            st.subheader("📈 Tendencia de Crecimiento")
            trend_data = df.groupby('Fecha_Solo').size().reset_index(name='Nuevos')
            fig_trend = px.area(trend_data, x='Fecha_Solo', y='Nuevos', 
                               color_discrete_sequence=['#E91E63'])
            fig_trend.update_traces(fillcolor="rgba(233, 30, 99, 0.1)")
            fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                   xaxis_title=None, yaxis_title=None, height=300)
            st.plotly_chart(fig_trend, use_container_width=True)

        else:
            st.info("Iniciando sistema... No hay datos suficientes aún.")

    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador de Registros")
        df = get_all_data()
        if not df.empty:
            search = st.text_input("Ingrese Nombre, Cédula o Líder para filtrar:").upper()
            if search:
                filtered = df[df.astype(str).apply(lambda x: search in x.values, axis=1)]
                st.dataframe(filtered, use_container_width=True)
            else:
                st.dataframe(df.tail(100), use_container_width=True)
