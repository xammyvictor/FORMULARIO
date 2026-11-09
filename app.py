import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import unicodedata
import json
import numpy as np

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
URL_GITHUB_GEO = "https://raw.githubusercontent.com/johndoe/pasto-comunas/main/comunas_pasto.geojson"
META_REGISTROS = 12000
USUARIOS_ADMIN = ["fabian", "xammy", "brayan"]
COMUNAS_PASTO_TOTAL = 12

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics - Pasto",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. FUNCIONES DE NORMALIZACIÓN ---
def normalizar(texto):
    """Limpia el texto de tildes, espacios y lo pasa a mayúsculas."""
    if not texto: return ""
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())

def normalizar_para_mapa(comuna):
    """Mapea nombres de entrada a la identificación oficial de las comunas de Pasto."""
    c = normalizar(comuna)
    mapping = {
        "CENTRO": "COMUNA 1",
        "COMUNA 1": "COMUNA 1",
        "ATAHUALPA": "COMUNA 2",
        "COMUNA 2": "COMUNA 2",
        "EL EJIDO": "COMUNA 3",
        "COMUNA 3": "COMUNA 3",
        "LORENZO": "COMUNA 4",
        "COMUNA 4": "COMUNA 4",
        "POTRERILLO": "COMUNA 5",
        "COMUNA 5": "COMUNA 5",
        "TAMASAGRA": "COMUNA 6",
        "COMUNA 6": "COMUNA 6",
        "PANDIACO": "COMUNA 7",
        "COMUNA 7": "COMUNA 7",
        "SAN PEDRO": "COMUNA 8",
        "COMUNA 8": "COMUNA 8",
        "MORASURCO": "COMUNA 9",
        "COMUNA 9": "COMUNA 9",
        "ARANDA": "COMUNA 10",
        "COMUNA 10": "COMUNA 10",
        "LA CAROLINA": "COMUNA 11",
        "COMUNA 11": "COMUNA 11",
        "SURORIENTAL": "COMUNA 12",
        "COMUNA 12": "COMUNA 12"
    }
    return mapping.get(c, c)

# --- 3. ESTILOS VISUALES ---
def apply_custom_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        :root {
            --pulse-pink: #E91E63;
            --pulse-dark: #0F172A;
            --pulse-slate: #64748B;
            --pulse-bg: #F8FAFC;
        }
        * { font-family: 'Plus Jakarta Sans', sans-serif; }
        .stApp { background-color: var(--pulse-bg); }
        
        .pulse-hero {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            color: white;
            padding: 40px;
            border-radius: 32px;
            margin-bottom: 35px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255,255,255,0.05);
        }
        .hero-label { font-size: 0.8rem; font-weight: 700; opacity: 0.6; letter-spacing: 0.1em; text-transform: uppercase; }
        .hero-value { font-size: 4rem; font-weight: 800; line-height: 1; margin: 10px 0; color: white !important; }
        .hero-perc { font-size: 2.5rem; font-weight: 800; color: var(--pulse-pink); }
        
        .pulse-progress-track {
            background: rgba(255, 255, 255, 0.1);
            height: 14px;
            border-radius: 20px;
            width: 100%;
            margin-top: 25px;
            overflow: hidden;
        }
        .pulse-progress-fill {
            background: linear-gradient(90deg, #E91E63 0%, #FF80AB 100%);
            height: 100%;
            border-radius: 20px;
            transition: width 1s ease;
        }

        .pulse-kpi-card {
            background: white;
            padding: 24px;
            border-radius: 24px;
            border: 1px solid #F1F5F9;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        }
        .kpi-label { color: var(--pulse-slate); font-size: 0.85rem; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
        .kpi-val { color: var(--pulse-dark); font-size: 2.4rem; font-weight: 800; line-height: 1; }

        .rank-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            background: white;
            border-radius: 18px;
            margin-bottom: 10px;
            border: 1px solid #F1F5F9;
        }
        .rank-num { width: 32px; height: 32px; background: #FCE4EC; color: var(--pulse-pink); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.8rem; margin-right: 12px; }
        .rank-name { font-weight: 700; color: #1E293B; }
        .rank-badge { background: #F8FAFC; color: #64748B; padding: 6px 14px; border-radius: 12px; font-weight: 700; border: 1px solid #E2E8F0; }

        .hotspot-pill {
            padding: 4px 12px;
            background: #FEF2F2;
            color: #B91C1C;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 4. CONEXIÓN A DATOS ---
@st.cache_resource
def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets: return None
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception: return None

def get_data():
    client = get_google_sheet_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open("Base_Datos_Ciudadanos_Pasto")
        df = pd.DataFrame(sh.sheet1.get_all_records())
        if not df.empty:
            df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'], errors='coerce')
            df.columns = [c.strip() for c in df.columns]
        return df
    except Exception: return pd.DataFrame()

def save_data(data_dict):
    client = get_google_sheet_client()
    if not client: return False
    try:
        sh = client.open("Base_Datos_Ciudadanos_Pasto")
        ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        user = st.session_state.get("user_name", "Anónimo")
        row = [
            ts, user, data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
            data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"], 
            data_dict["comuna"], data_dict.get("puesto", "")
        ]
        sh.sheet1.append_row(row)
        return True
    except Exception: return False

@st.cache_data(ttl=3600)
def get_pasto_geojson(url):
    """Descarga el GeoJSON de las comunas de Pasto."""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error cargando GeoJSON de Pasto: {e}")
    return None

# --- 5. LÓGICA DE AUTENTICACIÓN ---
def check_auth():
    if "logged_in" not in st.session_state: 
        st.session_state.logged_in = False
    if "user_name" not in st.session_state: 
        st.session_state.user_name = "Anónimo"
    if "is_guest" not in st.session_state: 
        st.session_state.is_guest = False
    
    params = st.query_params
    if "ref" in params and "ref_checked" not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.user_name = params["ref"]
        st.session_state.is_guest = True
        st.session_state.ref_checked = True

    if not st.session_state.logged_in:
        st.markdown("<div style='text-align:center; padding-top: 80px;'><h1>Pulse Analytics</h1><p>Gestión San Juan de Pasto</p></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.4, 1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Acceder al Panel"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234", "diveincalero": "1234"}
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.session_state.is_guest = False
                    st.rerun()
                else: st.error("Acceso Denegado")
        return False
    return True

# --- 6. VISTAS ---
def view_registro():
    st.title("🗳️ Nuevo Registro - Pasto")
    if "f_reset" not in st.session_state: st.session_state.f_reset = 0
    
    with st.form(key=f"form_pulse_{st.session_state.f_reset}"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo")
            ced = st.text_input("Cédula")
            tel = st.text_input("Teléfono")
        with c2:
            ocu = st.text_input("Ocupación")
            dir = st.text_input("Dirección")
            bar = st.text_input("Barrio")
        
        comuna = st.selectbox("Comuna", [
            "Comuna 1 (Centro)", "Comuna 2 (Atahualpa)", "Comuna 3 (El Ejido)", 
            "Comuna 4 (Lorenzo)", "Comuna 5 (Potrerillo)", "Comuna 6 (Tamasagra)", 
            "Comuna 7 (Pandiaco)", "Comuna 8 (San Pedro)", "Comuna 9 (Morasurco)", 
            "Comuna 10 (Aranda)", "Comuna 11 (La Carolina)", "Comuna 12 (Suroriental)"
        ])
        pue = st.text_input("Puesto de Votación (Opcional)")
        
        if st.form_submit_button("GUARDAR REGISTRO"):
            if nom and ced and tel:
                success = save_data({
                    "nombre": nom.upper(), "cedula": ced, "telefono": tel,
                    "ocupacion": ocu.upper(), "direccion": dir.upper(),
                    "barrio": bar.upper(), "comuna": comuna.upper(), "puesto": pue.upper()
                })
                if success:
                    st.success("¡Registro guardado exitosamente!")
                    st.session_state.f_reset += 1
                    time.sleep(1)
                    st.rerun()
                else: st.error("Fallo al guardar en la base de datos.")
            else: st.warning("Complete los campos obligatorios.")

def view_estadisticas():
    df = get_data()
    if df.empty:
        st.info("Cargando base de datos...")
        return

    st.title("Pulse Analytics | San Juan de Pasto")
    
    # --- HERO ---
    total = len(df)
    perc = min((total / META_REGISTROS) * 100, 100)
    st.markdown(f"""
        <div class="pulse-hero">
            <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                <div>
                    <p class="hero-label">Progreso de Gestión Global (Pasto)</p>
                    <h1 class="hero-value">{total:,}</h1>
                </div>
                <div style="text-align:right;">
                    <span class="hero-perc">{perc:.1f}%</span>
                    <p style="margin:0; opacity:0.6; font-size:0.8rem;">Meta: {META_REGISTROS:,}</p>
                </div>
            </div>
            <div class="pulse-progress-track"><div class="pulse-progress-fill" style="width: {perc}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)

    # --- KPIs ---
    hoy = datetime.now()
    df['F_S'] = df['Fecha Registro'].dt.date
    v_hoy = len(df[df['F_S'] == hoy.date()])
    v_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
    v_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])

    k1, k2, k3, k4 = st.columns(4)
    metricas = [("Hoy", v_hoy), ("Últ. 8 días", v_8d), ("Últ. 30 días", v_30d), ("Comunas Activas", df['Comuna'].nunique())]
    for col, (lab, val) in zip([k1, k2, k3, k4], metricas):
        col.markdown(f"""<div class="pulse-kpi-card"><div class="kpi-label">{lab}</div><div class="kpi-val">{val:,}</div></div>""", unsafe_allow_html=True)

    # --- MAPA DE CALOR E INTEGRACIÓN DE COMUNAS ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📍 Mapa de Calor y Comunas de Pasto")
    
    m_df = df.copy()
    m_df['ID_COMUNA'] = m_df['Comuna'].apply(normalizar_para_mapa).apply(normalizar)
    counts = m_df['ID_COMUNA'].value_counts().reset_index()
    counts.columns = ['ID_COMUNA', 'Registros']
    
    c_map_view, c_map_stats = st.columns([5, 1])
    
    with c_map_view:
        st.info("💡 Distribución de registros por comuna en San Juan de Pasto.")
        fig_bar = px.bar(counts, x='ID_COMUNA', y='Registros', color='Registros',
                         color_continuous_scale=[[0, '#FCE4EC'], [1, '#E91E63']],
                         title="Concentración de Registros por Comuna")
        fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

    with c_map_stats:
        st.write("**🔥 Ranking Comunas**")
        for _, row in counts.head(12).iterrows():
            st.markdown(f"""
                <div class="rank-item" style="padding:8px; margin-bottom:6px; border-radius:12px;">
                    <span style="font-weight:600; font-size:0.75rem;">{row['ID_COMUNA']}</span>
                    <span class="hotspot-pill" style="font-size:0.7rem; padding:2px 8px;">{row['Registros']}</span>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.metric("Comunas", f"{len(counts)}/12")

    # --- LEADERBOARD ---
    st.markdown("---")
    c_rank, c_trend = st.columns([1, 1.5])
    
    with c_rank:
        st.subheader("🏆 Leaderboard de Líderes")
        if 'Registrado Por' in df.columns:
            ranking = df['Registrado Por'].value_counts().reset_index()
            ranking.columns = ['Líder', 'Total']
            for i, row in ranking.head(8).iterrows():
                st.markdown(f"""
                    <div class="rank-item">
                        <div style="display:flex; align-items:center;">
                            <div class="rank-num">{i+1}</div>
                            <span class="rank-name">{row['Líder'].upper()}</span>
                        </div>
                        <span class="rank-badge">{row['Total']} regs</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Columna 'Registrado Por' no encontrada en la base de datos.")

    with c_trend:
        st.subheader("📈 Actividad Histórica")
        trend = df.groupby('F_S').size().reset_index(name='Ingresos')
        fig_trend = px.area(trend, x='F_S', y='Ingresos', color_discrete_sequence=['#E91E63'])
        fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=380, xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig_trend, use_container_width=True)

def view_busqueda():
    st.title("🔍 Explorador de Registros")
    df = get_data()
    if not df.empty:
        q = st.text_input("Buscar por nombre, cédula o comuna...").upper()
        if q:
            res = df[df.astype(str).apply(lambda x: q in x.str.upper().values, axis=1)]
            st.dataframe(res, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df.tail(100), use_container_width=True, hide_index=True)

# --- 7. EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    apply_custom_styles()
    
    if check_auth():
        usuario = st.session_state.user_name
        es_admin = usuario.lower() in USUARIOS_ADMIN and not st.session_state.get("is_guest", False)

        st.sidebar.markdown(f"""
            <div style='background:#F1F5F9; padding:20px; border-radius:18px; margin-bottom:20px;'>
                <p style='margin:0; font-size:0.75rem; font-weight:700; color:#64748B;'>SESIÓN ACTIVA</p>
                <p style='margin:0; font-size:1.1rem; font-weight:800; color:#0F172A;'>{usuario.upper()}</p>
            </div>
        """, unsafe_allow_html=True)
        
        opciones = ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"]
        opcion = st.sidebar.radio("MENÚ PRINCIPAL", opciones)
        
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

        if opcion == "📝 Registro": view_registro()
        elif opcion == "📊 Estadísticas": view_estadisticas()
        elif opcion == "🔍 Búsqueda": view_busqueda()
