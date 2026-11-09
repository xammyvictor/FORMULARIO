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
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
META_REGISTROS = 6000
USUARIOS_ADMIN = ["fabian", "xammy", "brayan"]

st.set_page_config(
    page_title="Pulse Analytics - Pasto",
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
        "CENTRO": "COMUNA 1", "COMUNA 1": "COMUNA 1",
        "ATAHUALPA": "COMUNA 2", "COMUNA 2": "COMUNA 2",
        "EL EJIDO": "COMUNA 3", "COMUNA 3": "COMUNA 3",
        "LORENZO": "COMUNA 4", "COMUNA 4": "COMUNA 4",
        "POTRERILLO": "COMUNA 5", "COMUNA 5": "COMUNA 5",
        "TAMASAGRA": "COMUNA 6", "COMUNA 6": "COMUNA 6",
        "PANDIACO": "COMUNA 7", "COMUNA 7": "COMUNA 7",
        "SAN PEDRO": "COMUNA 8", "COMUNA 8": "COMUNA 8",
        "MORASURCO": "COMUNA 9", "COMUNA 9": "COMUNA 9",
        "ARANDA": "COMUNA 10", "COMUNA 10": "COMUNA 10",
        "LA CAROLINA": "COMUNA 11", "COMUNA 11": "COMUNA 11",
        "SURORIENTAL": "COMUNA 12", "COMUNA 12": "COMUNA 12"
    }
    return mapping.get(c, c)

# Coordenadas aproximadas de referencia central para las comunas urbanas de Pasto
COORDS_COMUNAS = {
    "COMUNA 1": [1.2140, -77.2820],
    "COMUNA 2": [1.2230, -77.2780],
    "COMUNA 3": [1.2100, -77.2890],
    "COMUNA 4": [1.1990, -77.2850],
    "COMUNA 5": [1.1910, -77.2770],
    "COMUNA 6": [1.2180, -77.2980],
    "COMUNA 7": [1.2070, -77.2910],
    "COMUNA 8": [1.2200, -77.2730],
    "COMUNA 9": [1.2300, -77.2700],
    "COMUNA 10": [1.2200, -77.2650],
    "COMUNA 11": [1.2000, -77.2700],
    "COMUNA 12": [1.1850, -77.2800]
}

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

# --- 4. CONEXIÓN A DATOS CON CACHÉ ---
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

@st.cache_data(ttl=60) # Caché de 1 minuto para evitar llamadas lentas constantes a Google Sheets
def get_data():
    client = get_google_sheet_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        df = pd.DataFrame(sh.sheet1.get_all_records())
        if not df.empty:
            df.columns = [c.strip() for c in df.columns]
            if 'Fecha Registro' in df.columns:
                df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'], errors='coerce')
        return df
    except Exception as e:
        return pd.DataFrame()

def save_data(data_dict):
    client = get_google_sheet_client()
    if not client: return False
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        user = st.session_state.get("user_name", "Anónimo")
        row = [
            ts, user, data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
            data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"], 
            data_dict["comuna"], data_dict.get("novedades", "")
        ]
        sh.sheet1.append_row(row)
        st.cache_data.clear() # Limpiar caché para reflejar el nuevo registro de inmediato
        return True
    except Exception: return False

# --- 5. LÓGICA DE AUTENTICACIÓN ---
def check_auth():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if "user_name" not in st.session_state: st.session_state.user_name = "Anónimo"
    if "is_guest" not in st.session_state: st.session_state.is_guest = False
    
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
            ocu = st.text_input("Ocupación")
        with c2:
            dir = st.text_input("Dirección")
            bar = st.text_input("Barrio")
            comuna = st.selectbox("Comuna", [
                "Comuna 1", "Comuna 2", "Comuna 3", "Comuna 4", "Comuna 5", "Comuna 6", 
                "Comuna 7", "Comuna 8", "Comuna 9", "Comuna 10", "Comuna 11", "Comuna 12"
            ])
            nov = st.selectbox("Novedades", ["", "Cedula no existe", "Cedula no vota", "Ciudadano repetido"])
        
        if st.form_submit_button("GUARDAR REGISTRO"):
            if nom and ced and tel:
                success = save_data({
                    "nombre": nom.upper(), "cedula": ced, "telefono": tel,
                    "ocupacion": ocu.upper(), "direccion": dir.upper(),
                    "barrio": bar.upper(), "comuna": comuna.upper(), "novedades": nov
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
        st.warning("⚠️ La base de datos está vacía o no se pudo conectar con Google Sheets.")
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
    if 'Fecha Registro' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Fecha Registro']):
        df['F_S'] = df['Fecha Registro'].dt.date
        v_hoy = len(df[df['F_S'] == hoy.date()])
        v_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
        v_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])
    else:
        v_hoy, v_8d, v_30d = 0, 0, 0

    col_comuna_name = 'comuna' if 'comuna' in df.columns else ('Comuna' if 'Comuna' in df.columns else None)
    num_comunas = df[col_comuna_name].nunique() if col_comuna_name else 0

    k1, k2, k3, k4 = st.columns(4)
    metricas = [("Hoy", v_hoy), ("Últ. 8 días", v_8d), ("Últ. 30 días", v_30d), ("Comunas Activas", num_comunas)]
    for col, (lab, val) in zip([k1, k2, k3, k4], metricas):
        col.markdown(f"""<div class="pulse-kpi-card"><div class="kpi-label">{lab}</div><div class="kpi-val">{val:,}</div></div>""", unsafe_allow_html=True)

    # --- MAPA DE CALOR OPTIMIZADO ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📍 Mapa de Calor - Comunas de Pasto")
    
    c_map_view, c_map_stats = st.columns([5, 1])
    
    with c_map_view:
        # Cargar mapa ligero optimizado
        pasto_coords = [1.2136, -77.2811]
        m = folium.Map(location=pasto_coords, zoom_start=13, tiles="OpenStreetMap", prefer_canvas=True)

        if col_comuna_name and not df.empty:
            m_df = df.copy()
            m_df['ID_COMUNA'] = m_df[col_comuna_name].apply(normalizar_para_mapa).apply(normalizar)
            conteo_comunas = m_df['ID_COMUNA'].value_counts()
            
            heat_data = []
            for comuna, count in conteo_comunas.items():
                if comuna in COORDS_COMUNAS:
                    lat, lon = COORDS_COMUNAS[comuna]
                    # Agrupamos la intensidad para renderizado fluido sin congelar la app
                    heat_data.append([lat, lon, float(count)])

            if heat_data:
                HeatMap(heat_data, radius=30, blur=20, max_zoom=18, min_opacity=0.4).add_to(m)

            for comuna, count in conteo_comunas.items():
                if comuna in COORDS_COMUNAS:
                    lat, lon = COORDS_COMUNAS[comuna]
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=6,
                        popup=f"<b>{comuna}</b><br>Registros: {count}",
                        color="#E91E63",
                        fill=True,
                        fill_color="#E91E63",
                        fill_opacity=0.8
                    ).add_to(m)

        st_folium(m, width="100%", height=450, returned_objects=[])

    with c_map_stats:
        st.write("**🔥 Ranking Comunas**")
        if col_comuna_name:
            counts_df = df[col_comuna_name].value_counts().reset_index()
            counts_df.columns = ['Comuna', 'Registros']
            for _, row in counts_df.head(12).iterrows():
                st.markdown(f"""
                    <div class="rank-item" style="padding:8px; margin-bottom:6px; border-radius:12px;">
                        <span style="font-weight:600; font-size:0.75rem;">{str(row['Comuna']).upper()}</span>
                        <span class="hotspot-pill" style="font-size:0.7rem; padding:2px 8px;">{row['Registros']}</span>
                    </div>
                """, unsafe_allow_html=True)
        st.markdown("---")
        st.metric("Comunas", f"{num_comunas}/12")

    # --- LEADERBOARD & TENDENCIA ---
    st.markdown("---")
    c_rank, c_trend = st.columns([1, 1.5])
    
    with c_rank:
        st.subheader("🏆 Leaderboard de Líderes")
        col_lider = 'Registrado Por' if 'Registrado Por' in df.columns else ('Usuario' if 'Usuario' in df.columns else None)
        if col_lider:
            ranking = df[col_lider].value_counts().reset_index()
            ranking.columns = ['Líder', 'Total']
            for i, row in ranking.head(8).iterrows():
                st.markdown(f"""
                    <div class="rank-item">
                        <div style="display:flex; align-items:center;">
                            <div class="rank-num">{i+1}</div>
                            <span class="rank-name">{str(row['Líder']).upper()}</span>
                        </div>
                        <span class="rank-badge">{row['Total']} regs</span>
                    </div>
                """, unsafe_allow_html=True)

    with c_trend:
        st.subheader("📈 Actividad Histórica")
        if 'F_S' in df.columns and not df['F_S'].isna().all():
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
