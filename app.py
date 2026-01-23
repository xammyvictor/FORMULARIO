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
    page_title="Maria Irma | Analytics",
    page_icon="📈",
    layout="wide"
)

# --- ESTILOS VISUALES (Leader Pulse Style) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp { background-color: #F8FAFC; }
    
    /* Tarjetas de Métricas */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #E2E8F0;
        text-align: center;
    }
    .metric-title { color: #64748B; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }
    .metric-value { color: #1E293B; font-size: 1.5rem; font-weight: 700; }
    
    /* Barra de Progreso */
    .progress-container {
        background-color: #E2E8F0;
        border-radius: 20px;
        height: 12px;
        width: 100%;
        margin: 10px 0;
    }
    .progress-bar {
        background: linear-gradient(90deg, #E91E63 0%, #C2185B 100%);
        height: 12px;
        border-radius: 20px;
    }
    
    /* Leader Cards */
    .leader-tag {
        background-color: #FCE4EC;
        color: #C2185B;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
        margin: 4px;
        border: 1px solid #F8BBD0;
    }

    h1, h2, h3 { color: #0F172A !important; font-weight: 700 !important; }
    .stSidebar { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# --- GOOGLE SHEETS API ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets:
            return None
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
    
    # Referido por URL
    try:
        params = st.query_params
        if "ref" in params and "query_checked" not in st.session_state:
            st.session_state.logged_in = True
            st.session_state.user_name = params["ref"]
            st.session_state.is_guest = True
            st.session_state.query_checked = True
    except: pass

    if not st.session_state.logged_in:
        st.title("🔐 Acceso Analytics")
        with st.container():
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Iniciar Sesión"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.session_state.is_guest = False
                    st.rerun()
                else: st.error("Acceso Denegado")
        return False
    return True

if "form_reset_key" not in st.session_state:
    st.session_state.form_reset_key = 0

# --- DASHBOARD ---
if check_session():
    usuario = st.session_state.user_name
    USUARIOS_ADMIN = ["fabian", "xammy", "brayan"]
    es_admin = usuario.lower() in USUARIOS_ADMIN and not st.session_state.get("is_guest", False)

    # Sidebar Moderno
    st.sidebar.markdown(f"### ⚡ **{usuario.capitalize()}**")
    st.sidebar.markdown("---")
    opcion = st.sidebar.radio("Navegación", ["📝 Registro", "🔍 Búsqueda", "📊 Estadísticas"] if es_admin else ["📝 Registro"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    if opcion == "📝 Registro":
        st.title("🗳️ Nuevo Registro")
        with st.form(key=f"reg_form_{st.session_state.form_reset_key}"):
            c1, c2 = st.columns(2)
            with c1:
                nom = st.text_input("Nombre")
                ced = st.text_input("Cédula")
                tel = st.text_input("Teléfono")
            with c2:
                ocu = st.text_input("Ocupación")
                dire = st.text_input("Dirección")
                barr = st.text_input("Barrio")
            ciu = st.text_input("Ciudad", value="BUGA")
            pue = st.text_input("Puesto (Opcional)")
            
            if st.form_submit_button("✅ Guardar Registro"):
                if nom and ced and tel:
                    if save_to_drive({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dire.upper(),"barrio":barr.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                        st.success("¡Registro Exitoso!")
                        st.session_state.form_reset_key += 1
                        time.sleep(1.5)
                        st.rerun()
                else: st.warning("Nombre, Cédula y Teléfono son obligatorios")

    elif opcion == "📊 Estadísticas":
        df = get_all_data()
        
        if not df.empty:
            st.title("📊 Análisis de Gestión en Tiempo Real")
            
            # --- 1. PROGRESO Y KPIs ---
            total_actual = len(df)
            progreso = min(total_actual / META_REGISTROS, 1.0)
            
            st.markdown(f"""
                <div style="background-color: white; padding: 25px; border-radius: 15px; border: 1px solid #E2E8F0; margin-bottom: 25px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span style="font-weight: 700; color: #1E293B;">PROGRESO HACIA LA META</span>
                        <span style="font-weight: 700; color: #E91E63; font-size: 1.2rem;">{total_actual:,} / {META_REGISTROS:,}</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {progreso*100}%;"></div>
                    </div>
                    <p style="color: #64748B; font-size: 0.85rem; margin-top: 10px;">Equivale al {progreso*100:.1f}% del objetivo general.</p>
                </div>
            """, unsafe_allow_html=True)

            # Cálculo de tiempos
            hoy = datetime.now()
            df['Fecha_Solo'] = df['Fecha Registro'].dt.date
            
            m_hoy = len(df[df['Fecha_Solo'] == hoy.date()])
            m_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
            m_15d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=15))])
            m_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])

            k1, k2, k3, k4 = st.columns(4)
            for col, title, val in zip([k1, k2, k3, k4], 
                                     ["Hoy", "Últimos 8 Días", "Últimos 15 Días", "Últimos 30 Días"],
                                     [m_hoy, m_8d, m_15d, m_30d]):
                col.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">{title}</div>
                        <div class="metric-value">{val:,}</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 2. RANKING Y MAPA ---
            col_rank, col_mapa = st.columns([1, 1.2])

            with col_rank:
                st.subheader("🏆 Ranking de Líderes")
                rank_df = df['Registrado Por'].value_counts().reset_index()
                rank_df.columns = ['Líder', 'Registros']
                
                # Gráfico de barras moderno
                fig_rank = px.bar(rank_df.head(10), x='Registros', y='Líder', orientation='h',
                                 color='Registros', color_continuous_scale='RdPu',
                                 text_auto=True)
                fig_rank.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', 
                                      paper_bgcolor='rgba(0,0,0,0)', height=400,
                                      yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_rank, use_container_width=True, config={'displayModeBar': False})

                # Selector Interactivo
                st.markdown("---")
                lider_sel = st.selectbox("🎯 Filtrar por Líder:", ["Ver Todos"] + list(rank_df['Líder']))
                if lider_sel != "Ver Todos":
                    subset = df[df['Registrado Por'] == lider_sel][['Fecha Registro', 'Nombre', 'Ciudad']]
                    st.write(f"Detalle de **{lider_sel.upper()}**")
                    st.dataframe(subset, use_container_width=True, hide_index=True)

            with col_mapa:
                st.subheader("🗺️ Cobertura Valle del Cauca")
                muni_df = df['Ciudad'].str.upper().value_counts().reset_index()
                muni_df.columns = ['Municipio', 'Cantidad']
                
                # Mapa Coroplético "Dibujo" (GeoJSON)
                try:
                    geojson_url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
                    fig_valle = px.choropleth(
                        muni_df, geojson=geojson_url, locations='Municipio', 
                        featureidkey="properties.name", color='Cantidad',
                        color_continuous_scale="RdPu",
                        labels={'Cantidad':'Registros'}
                    )
                    fig_valle.update_geos(fitbounds="locations", visible=False)
                    fig_valle.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500, paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_valle, use_container_width=True)
                except:
                    st.warning("No se pudo cargar el mapa. Mostrando resumen:")
                    st.table(muni_df)

            # --- 3. LÍDERES ACTIVOS ---
            st.markdown("---")
            st.subheader("👥 Líderes con Actividad Reciente")
            activos = sorted(df['Registrado Por'].unique())
            
            # Mostrar como etiquetas
            html_lideres = ""
            for l in activos:
                html_lideres += f'<span class="leader-tag">{l.upper()}</span>'
            st.markdown(f'<div>{html_lideres}</div>', unsafe_allow_html=True)
            
            # Tendencia Diaria (Área)
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📈 Tendencia de Ingresos")
            trend = df.groupby('Fecha_Solo').size().reset_index(name='Registros')
            fig_trend = px.area(trend, x='Fecha_Solo', y='Registros', 
                               color_discrete_sequence=['#E91E63'])
            fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                   xaxis_title=None, yaxis_title="Nuevos Registros")
            st.plotly_chart(fig_trend, use_container_width=True)

        else:
            st.info("No hay datos suficientes para generar estadísticas.")

    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador de Datos")
        df = get_all_data()
        if not df.empty:
            q = st.text_input("Buscar por Nombre, Cédula o Líder").upper()
            if q:
                res = df[df.astype(str).apply(lambda x: q in x.values, axis=1)]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(50), use_container_width=True)
