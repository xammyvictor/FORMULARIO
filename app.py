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
URL_GITHUB_GEO = "https://github.com/xammyvictor/FORMULARIO/blob/main/co_2018_MGN_MPIO_POLITICO.geojson"
META_REGISTROS = 12000
USUARIOS_ADMIN = ["fabian", "xammy", "brayan"]
MUNICIPIOS_VALLE_TOTAL = 42

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
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

def normalizar_para_mapa(muni):
    """Mapea nombres de entrada a la identificación oficial del DANE."""
    m = normalizar(muni)
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "JAMUNDI": "JAMUNDI",
        "TULUA": "TULUA",
        "GUACARI": "GUACARI",
        "DARIEN": "CALIMA",
        "CALIMA": "CALIMA",
        "LA UNION": "LA UNION",
        "RIOFRIO": "RIOFRIO",
        "ANDALUCIA": "ANDALUCIA",
        "YUMBO": "YUMBO",
        "PALMIRA": "PALMIRA",
        "DAGUA": "DAGUA",
        "CARTAGO": "CARTAGO",
        "EL CERRITO": "EL CERRITO",
        "BUGALAGRANDE": "BUGALAGRANDE",
        "CAICEDONIA": "CAICEDONIA",
        "FLORIDA": "FLORIDA",
        "GINEBRA": "GINEBRA",
        "PRADERA": "PRADERA",
        "RESTREPO": "RESTREPO",
        "ROLDANILLO": "ROLDANILLO",
        "SEVILLA": "SEVILLA",
        "SANTIAGO DE CALI": "CALI",
        "CALI": "CALI",
        "ZARZAL": "ZARZAL"
    }
    return mapping.get(m, m)

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
        sh = client.open("Base_Datos_Ciudadanos")
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
        sh = client.open("Base_Datos_Ciudadanos")
        ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        user = st.session_state.get("user_name", "Anónimo")
        row = [
            ts, user, data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
            data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"], 
            data_dict["ciudad"], data_dict.get("puesto", "")
        ]
        sh.sheet1.append_row(row)
        return True
    except Exception: return False

@st.cache_data(ttl=3600)
def get_valle_geojson(url):
    """Descarga el GeoJSON completo y filtra el Valle del Cauca en tiempo real."""
    raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    try:
        response = requests.get(raw_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            valle_features = []
            for feature in data["features"]:
                props = feature["properties"]
                if str(props.get("DPTO_CCDGO")) == "76":
                    m_name = normalizar(props.get("MPIO_CNMBR", ""))
                    feature["id"] = m_name
                    valle_features.append(feature)
            
            if valle_features:
                return {"type": "FeatureCollection", "features": valle_features}
    except Exception as e:
        st.error(f"Error cargando GeoJSON: {e}")
    return None

# --- 5. LÓGICA DE AUTENTICACIÓN ---
def check_auth():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    
    params = st.query_params
    if "ref" in params and "ref_checked" not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.user_name = params["ref"]
        st.session_state.is_guest = True
        st.session_state.ref_checked = True

    if not st.session_state.logged_in:
        st.markdown("<div style='text-align:center; padding-top: 80px;'><h1>Pulse Analytics</h1><p>Gestión Maria Irma</p></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.4, 1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Acceder al Panel"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234","diveincalero":1234}
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
    st.title("🗳️ Nuevo Registro")
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
        ciu = st.text_input("Municipio", value="BUGA")
        pue = st.text_input("Puesto (Opcional)")
        
        if st.form_submit_button("GUARDAR REGISTRO"):
            if nom and ced and tel:
                success = save_data({
                    "nombre": nom.upper(), "cedula": ced, "telefono": tel,
                    "ocupacion": ocu.upper(), "direccion": dir.upper(),
                    "barrio": bar.upper(), "ciudad": ciu.upper(), "puesto": pue.upper()
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

    st.title("Pulse Analytics | Valle del Cauca")
    
    # --- HERO ---
    total = len(df)
    perc = min((total / META_REGISTROS) * 100, 100)
    st.markdown(f"""
        <div class="pulse-hero">
            <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                <div>
                    <p class="hero-label">Progreso de Gestión Global</p>
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
    metricas = [("Hoy", v_hoy), ("Últ. 8 días", v_8d), ("Últ. 30 días", v_30d), ("Municipios", df['Ciudad'].nunique())]
    for col, (lab, val) in zip([k1, k2, k3, k4], metricas):
        col.markdown(f"""<div class="pulse-kpi-card"><div class="kpi-label">{lab}</div><div class="kpi-val">{val:,}</div></div>""", unsafe_allow_html=True)

    # --- MAPA MAXIMIZADO SIN LÍMITES ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📍 Visualización Territorial Completa")
    
    m_df = df.copy()
    m_df['ID_MPIO'] = m_df['Ciudad'].apply(normalizar_para_mapa).apply(normalizar)
    counts = m_df['ID_MPIO'].value_counts().reset_index()
    counts.columns = ['ID_MPIO', 'Registros']
    
    # Ajustamos proporciones para eliminar el efecto "encerrado" [5, 1]
    c_map_view, c_map_stats = st.columns([5, 1])
    
    with c_map_view:
        geojson_data = get_valle_geojson(URL_GITHUB_GEO)
        if geojson_data:
            all_features = geojson_data["features"]
            all_ids = [f["id"] for f in all_features]
            
            lats, lons, names = [], [], []
            for f in all_features:
                coords = f["geometry"]["coordinates"]
                if f["geometry"]["type"] == "Polygon":
                    coords_flat = np.array(coords[0])
                else: # MultiPolygon
                    coords_flat = np.array([c for sub in coords for c in sub[0]])
                
                lons.append(coords_flat[:, 0].mean())
                lats.append(coords_flat[:, 1].mean())
                names.append(f["id"])

            df_base = pd.DataFrame({"ID_MPIO": all_ids})
            map_data_full = df_base.merge(counts, on='ID_MPIO', how='left').fillna(0)
            
            fig = px.choropleth(
                map_data_full, 
                geojson=geojson_data, 
                locations='ID_MPIO',
                color='Registros',
                color_continuous_scale=[[0, 'white'], [0.0001, '#FCE4EC'], [1, '#E91E63']],
                labels={'Registros': 'Total'}
            )
            
            # Etiquetas más visibles
            fig.add_trace(go.Scattergeo(
                lat=lats,
                lon=lons,
                text=names,
                mode='text',
                textfont=dict(size=11, color="black", family="Plus Jakarta Sans", weight="bold"),
                hoverinfo='none',
                showlegend=False
            ))
            
            # Forzamos que el mapa use todo el canvas sin bordes internos
            fig.update_geos(
                fitbounds="locations",
                visible=False,
                projection_type="mercator"
            )
            
            fig.update_traces(
                marker_line_width=1.8,
                marker_line_color="black",
                selector=dict(type='choropleth')
            )
            
            # Altura al máximo y márgenes a cero absoluto
            fig.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0}, 
                height=1000,
                paper_bgcolor="white",
                plot_bgcolor="white",
                coloraxis_colorbar=dict(
                    title="REGISTROS", 
                    thickness=25, 
                    len=0.5, 
                    yanchor="middle", 
                    y=0.5,
                    xanchor="left",
                    x=0.02
                ),
                autosize=True
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.error("⚠️ No se pudo cargar el mapa.")
            st.dataframe(counts, use_container_width=True)

    with c_map_stats:
        st.write("**🔥 Ranking Municipal**")
        for _, row in counts.head(20).iterrows(): # Más municipios visibles
            st.markdown(f"""
                <div class="rank-item" style="padding:8px; margin-bottom:6px; border-radius:12px;">
                    <span style="font-weight:600; font-size:0.75rem;">{row['ID_MPIO']}</span>
                    <span class="hotspot-pill" style="font-size:0.7rem; padding:2px 8px;">{row['Registros']}</span>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.metric("Municipios", f"{len(counts)}/42")

    # --- LEADERBOARD ---
    st.markdown("---")
    c_rank, c_trend = st.columns([1, 1.5])
    
    with c_rank:
        st.subheader("🏆 Leaderboard de Líderes")
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
        q = st.text_input("Buscar por nombre, cédula o municipio...").upper()
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
