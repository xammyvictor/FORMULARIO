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
    page_title="Maria Irma | Pulse Analytics",
    page_icon="📈",
    layout="wide"
)

# --- ESTILOS VISUALES PREMIUM (ESTILO LEADER PULSE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .stApp { background-color: #F9FAFB; }
    
    /* Contenedores Estilo Pulse */
    .pulse-container {
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
        transition: transform 0.2s;
    }
    .kpi-label { color: #64748B; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-value { color: #0F172A; font-size: 2rem; font-weight: 800; margin: 8px 0; }
    .kpi-trend { font-size: 0.75rem; font-weight: 600; padding: 4px 8px; border-radius: 8px; display: inline-block; }
    .trend-pos { background: #ECFDF5; color: #10B981; }
    
    /* Barra de Meta */
    .goal-card {
        background: #0F172A;
        color: white;
        padding: 32px;
        border-radius: 24px;
        margin-bottom: 32px;
    }
    .progress-track { background: rgba(255,255,255,0.1); border-radius: 12px; height: 16px; width: 100%; margin: 20px 0; overflow: hidden; }
    .progress-fill { 
        background: linear-gradient(90deg, #E91E63 0%, #F06292 100%); 
        height: 100%; border-radius: 12px; transition: width 1s ease; 
    }
    
    /* Leaderboard Pulse */
    .leader-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px;
        border-bottom: 1px solid #F1F5F9;
    }
    .leader-rank { background: #FCE4EC; color: #E91E63; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 0.8rem; font-weight: 800; margin-right: 12px; }
    .leader-info { flex-grow: 1; font-weight: 600; color: #334155; }
    .leader-badge { background: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 8px; font-weight: 700; font-size: 0.75rem; }

    /* Forms */
    .stButton>button { border-radius: 12px !important; background: #E91E63 !important; border: none !important; font-weight: 700 !important; }
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
        st.markdown("<div style='text-align:center; padding: 50px;'><h1>Pulse Analytics</h1><p>Inicie sesión para continuar</p></div>", unsafe_allow_html=True)
        with st.container():
            col_l, col_c, col_r = st.columns([1, 2, 1])
            with col_c:
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.button("Acceder al Panel"):
                    creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                    if u.lower() in creds and creds[u.lower()] == p:
                        st.session_state.logged_in = True
                        st.session_state.user_name = u.lower()
                        st.session_state.is_guest = False
                        st.rerun()
                    else: st.error("Acceso no autorizado")
        return False
    return True

if "form_reset_key" not in st.session_state:
    st.session_state.form_reset_key = 0

# --- DASHBOARD ---
if check_session():
    usuario = st.session_state.user_name
    USUARIOS_ADMIN = ["fabian", "xammy", "brayan"]
    es_admin = usuario.lower() in USUARIOS_ADMIN and not st.session_state.get("is_guest", False)

    # Sidebar
    st.sidebar.markdown(f"### ⚡ Pulse | {usuario.capitalize()}")
    st.sidebar.markdown("---")
    opcion = st.sidebar.radio("NAVEGACIÓN", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    if opcion == "📝 Registro":
        st.title("🗳️ Captura de Ciudadanos")
        with st.form(key=f"form_pulse_{st.session_state.form_reset_key}", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                nom = st.text_input("Nombre Completo")
                ced = st.text_input("Cédula")
                tel = st.text_input("Teléfono")
            with c2:
                ocu = st.text_input("Ocupación")
                dire = st.text_input("Dirección")
                barr = st.text_input("Barrio")
            ciu = st.text_input("Ciudad / Municipio", value="BUGA")
            pue = st.text_input("Puesto Votación (Opcional)")
            
            if st.form_submit_button("GUARDAR REGISTRO"):
                if nom and ced and tel:
                    if save_to_drive({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dire.upper(),"barrio":barr.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                        st.success("¡Registro guardado con éxito!")
                        st.session_state.form_reset_key += 1
                        time.sleep(1)
                        st.rerun()
                else: st.warning("Por favor llene los campos obligatorios.")

    elif opcion == "📊 Estadísticas":
        df = get_all_data()
        
        if not df.empty:
            st.title("Pulse Analytics | Real-Time Dashboard")
            
            # --- 1. META GLOBAL (STYLISH) ---
            total = len(df)
            perc = (total / META_REGISTROS) * 100
            
            st.markdown(f"""
                <div class="goal-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <p style="margin:0; font-weight: 700; opacity: 0.7; font-size: 0.8rem; letter-spacing: 0.1em;">META DE CAMPAÑA</p>
                            <h1 style="color: white !important; margin: 8px 0; font-size: 3rem; font-weight: 800;">{total:,}</h1>
                            <p style="margin:0; opacity: 0.6;">Registros totales recolectados</p>
                        </div>
                        <div style="text-align: right;">
                            <h2 style="color: #E91E63 !important; margin: 0; font-size: 2rem;">{perc:.1f}%</h2>
                            <p style="margin:0; opacity: 0.6;">de {META_REGISTROS:,} objetivo</p>
                        </div>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" style="width: {perc}%;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # --- 2. KPIs TEMPORALES (PULSE CARDS) ---
            hoy = datetime.now()
            df['F_S'] = df['Fecha Registro'].dt.date
            
            v_hoy = len(df[df['F_S'] == hoy.date()])
            v_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
            v_15d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=15))])
            v_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])

            k1, k2, k3, k4 = st.columns(4)
            data_kpi = [("Hoy", v_hoy), ("8 días", v_8d), ("15 días", v_15d), ("30 días", v_30d)]
            
            for col, (label, value) in zip([k1, k2, k3, k4], data_kpi):
                col.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">{label}</div>
                        <div class="kpi-value">{value:,}</div>
                        <div class="kpi-trend trend-pos">↑ Creciente</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 3. MAPA Y LIDERBOARD ---
            c_map, c_rank = st.columns([1.3, 1])

            with c_map:
                st.subheader("📍 Cobertura Territorial Valle")
                
                # NORMALIZACIÓN CRÍTICA PARA EL MAPA
                # Estos nombres deben coincidir con las propiedades del GeoJSON
                norm = {
                    "BUGA": "GUADALAJARA DE BUGA",
                    "CALI": "SANTIAGO DE CALI",
                    "JAMUNDI": "JAMUNDÍ",
                    "DARIEN": "CALIMA",
                    "GUACARI": "GUACARÍ",
                    "TULUA": "TULUÁ",
                    "CARTAGO": "CARTAGO",
                    "PALMIRA": "PALMIRA",
                    "YUMBO": "YUMBO"
                }
                
                m_df = df['Ciudad'].str.upper().str.strip().replace(norm).value_counts().reset_index()
                m_df.columns = ['Municipio', 'Cantidad']
                
                try:
                    # Usamos un GeoJSON confiable del Valle
                    geojson_url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
                    fig = px.choropleth(
                        m_df, geojson=geojson_url, locations='Municipio',
                        featureidkey="properties.name", color='Cantidad',
                        color_continuous_scale="RdPu",
                        template="plotly_white"
                    )
                    fig.update_geos(fitbounds="locations", visible=False)
                    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500, coloraxis_showscale=False)
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                except:
                    st.warning("Cargando visualización de mapa...")
                    st.bar_chart(m_df.set_index('Municipio'))

            with c_rank:
                st.subheader("🏆 Leaderboard")
                ranking = df['Registrado Por'].value_counts().reset_index()
                ranking.columns = ['Líder', 'Total']
                
                for i, row in ranking.head(10).iterrows():
                    st.markdown(f"""
                        <div class="leader-item">
                            <div style="display: flex; align-items: center;">
                                <div class="leader-rank">{i+1}</div>
                                <div class="leader-info">{row['Líder'].upper()}</div>
                            </div>
                            <div class="leader-badge">{row['Total']} registros</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                sel_lider = st.selectbox("Detalle por Líder:", ["-- Seleccione --"] + list(ranking['Líder']))
                if sel_lider != "-- Seleccione --":
                    st.dataframe(df[df['Registrado Por'] == sel_lider][['Nombre', 'Cédula', 'Ciudad']].tail(10), use_container_width=True)

            # --- 4. TENDENCIA ---
            st.markdown("---")
            st.subheader("📈 Actividad de Ingreso")
            trend = df.groupby('F_S').size().reset_index(name='Ingresos')
            fig_t = px.area(trend, x='F_S', y='Ingresos', color_discrete_sequence=['#E91E63'])
            fig_t.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                               xaxis_title=None, yaxis_title=None, height=300)
            st.plotly_chart(fig_t, use_container_width=True)

        else: st.info("Esperando datos para procesar estadísticas...")

    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador de Datos")
        df = get_all_data()
        if not df.empty:
            q = st.text_input("Buscar por Nombre, Cédula o Ciudad").upper()
            if q:
                res = df[df.astype(str).apply(lambda x: q in x.values, axis=1)]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(50), use_container_width=True)
