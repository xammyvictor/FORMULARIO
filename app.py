import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURACIÓN DE METAS ---
META_REGISTROS = 12000

# --- SISTEMA DE DISEÑO PULSE (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    :root {
        --pulse-pink: #E91E63;
        --pulse-dark: #0F172A;
        --pulse-slate: #64748B;
        --pulse-bg: #F8FAFC;
        --pulse-card-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
    }

    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: var(--pulse-bg); }

    /* Estilo del Hero (Progreso Global) */
    .pulse-hero {
        background: var(--pulse-dark);
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
        height: 16px;
        border-radius: 20px;
        width: 100%;
        margin-top: 25px;
        overflow: hidden;
    }
    .pulse-progress-fill {
        background: linear-gradient(90deg, #E91E63 0%, #FF80AB 100%);
        height: 100%;
        border-radius: 20px;
        transition: width 1.5s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Tarjetas KPI */
    .pulse-kpi-card {
        background: white;
        padding: 24px;
        border-radius: 24px;
        border: 1px solid #F1F5F9;
        box-shadow: var(--pulse-card-shadow);
    }
    .kpi-label { color: var(--pulse-slate); font-size: 0.85rem; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-val { color: var(--pulse-dark); font-size: 2.4rem; font-weight: 800; line-height: 1; }

    /* Listas de Ranking */
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
    .rank-name { font-weight: 700; color: #1E293B; font-size: 0.95rem; }
    .rank-badge { background: #FCE4EC; color: var(--pulse-pink); padding: 6px 14px; border-radius: 12px; font-weight: 700; font-size: 0.8rem; }
    
    /* Hotspot Pill */
    .hotspot-pill {
        padding: 4px 12px;
        background: #FCE4EC;
        color: #E91E63;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Sidebar y Botones */
    .stSidebar { background-color: white !important; border-right: 1px solid #E2E8F0; }
    .stButton>button { 
        border-radius: 14px !important; 
        background: var(--pulse-pink) !important; 
        font-weight: 700 !important; 
        color: white !important; 
        border: none !important; 
        width: 100%; 
        height: 3.2rem; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("No se encontraron las credenciales 'gcp_service_account' en st.secrets")
            return None
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

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
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
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
            data_dict["ciudad"], data_dict.get("puesto", "")
        ]
        sh.sheet1.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- NORMALIZACIÓN DE MUNICIPIOS PARA MAPA ---
def normalizar_para_mapa(muni):
    m = str(muni).upper().strip()
    # Mapeo exacto para coincidir con el GeoJSON de finiterank
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ",
        "GUACARI": "GUACARÍ",
        "DARIEN": "CALIMA",
        "CALIMA": "CALIMA",
        "ANDALUCIA": "ANDALUCÍA",
        "LA UNION": "LA UNIÓN",
        "LA VICTORIA": "LA VICTORIA",
        "RIOFRIO": "RIOFRÍO",
        "EL AGUILA": "EL ÁGUILA",
        "BOLIVAR": "BOLÍVAR",
        "ALCALA": "ALCALÁ"
    }
    return mapping.get(m, m)

# --- SISTEMA DE AUTENTICACIÓN ---
def check_auth():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.markdown("<div style='text-align:center; padding-top: 80px;'><h1>⚡ Pulse Analytics</h1><p>Gestión Territorial Maria Irma</p></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.4, 1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Acceder al Panel"):
                # Credenciales de ejemplo
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
        return False
    return True

# --- INICIO DE LA APLICACIÓN ---
if check_auth():
    usuario = st.session_state.user_name
    USUARIOS_ADMIN = ["fabian", "xammy", "brayan"]
    es_admin = usuario.lower() in USUARIOS_ADMIN

    # Sidebar
    st.sidebar.markdown(f"""
        <div style='background:#F1F5F9; padding:20px; border-radius:18px; margin-bottom:20px;'>
            <p style='margin:0; font-size:0.75rem; font-weight:700; color:#64748B;'>SESIÓN ACTIVA</p>
            <p style='margin:0; font-size:1.1rem; font-weight:800; color:#0F172A;'>{usuario.upper()}</p>
        </div>
    """, unsafe_allow_html=True)
    
    menu_opciones = ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"]
    opcion = st.sidebar.radio("MENÚ PRINCIPAL", menu_opciones)
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    # --- VISTA: REGISTRO ---
    if opcion == "📝 Registro":
        st.title("🗳️ Nuevo Registro de Ciudadano")
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
            
            c3, c4 = st.columns(2)
            with c3:
                ciu = st.text_input("Municipio", value="BUGA")
            with c4:
                pue = st.text_input("Puesto de Votación (Opcional)")
            
            submit = st.form_submit_button("GUARDAR EN BASE DE DATOS")
            
            if submit:
                if nom and ced and tel:
                    data = {
                        "nombre": nom.upper(), "cedula": ced, "telefono": tel,
                        "ocupacion": ocu.upper(), "direccion": dir.upper(),
                        "barrio": bar.upper(), "ciudad": ciu.upper(), "puesto": pue.upper()
                    }
                    if save_data(data):
                        st.success("¡Registro guardado correctamente!")
                        st.session_state.f_reset += 1
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Nombre, Cédula y Teléfono son obligatorios.")

    # --- VISTA: ESTADÍSTICAS ---
    elif opcion == "📊 Estadísticas":
        df = get_data()
        if not df.empty:
            st.title("Pulse Analytics | Valle del Cauca")
            
            # --- 1. HERO META ---
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

            # --- 2. KPIs ---
            k1, k2, k3, k4 = st.columns(4)
            hoy = datetime.now().date()
            v_hoy = len(df[df['Fecha Registro'].dt.date == hoy])
            v_municipios = df['Ciudad'].nunique()
            v_lideres = df['Registrado Por'].nunique()
            
            for col, (lab, val) in zip([k1, k2, k3, k4], [("Hoy", v_hoy), ("Municipios", v_municipios), ("Líderes", v_lideres), ("Total", total)]):
                col.markdown(f"""<div class="pulse-kpi-card"><div class="kpi-label">{lab}</div><div class="kpi-val">{val:,}</div></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 3. SECCIÓN MAPA REPARADA ---
            st.subheader("📍 Concentración Territorial (Mapa de Calor)")
            
            m_df = df.copy()
            m_df['Municipio_Map'] = m_df['Ciudad'].apply(normalizar_para_mapa)
            map_counts = m_df.groupby('Municipio_Map').size().reset_index(name='Registros')

            c_map_view, c_map_stats = st.columns([2, 1])

            with c_map_view:
                try:
                    # URL de GeoJSON del Valle del Cauca
                    url_geo = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
                    
                    fig = px.choropleth(
                        map_counts, 
                        geojson=url_geo, 
                        locations='Municipio_Map',
                        featureidkey="properties.name", # Llave correcta para este JSON
                        color='Registros',
                        color_continuous_scale=[[0, '#FCE4EC'], [0.5, '#F06292'], [1, '#E91E63']],
                        labels={'Registros': 'Total'},
                        template="plotly_white"
                    )
                    
                    fig.update_geos(fitbounds="locations", visible=False)
                    fig.update_layout(
                        margin={"r":0,"t":0,"l":0,"b":0}, 
                        height=500,
                        paper_bgcolor='rgba(0,0,0,0)',
                        coloraxis_colorbar=dict(title="Densidad")
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error al cargar dibujo territorial: {e}")
                    st.info("Mostrando tabla de apoyo:")
                    st.dataframe(map_counts)

            with c_map_stats:
                st.write("**🔥 Puntos Críticos**")
                hotspots = map_counts.sort_values('Registros', ascending=False).head(6)
                for _, row in hotspots.iterrows():
                    st.markdown(f"""
                        <div class="rank-item">
                            <span class="rank-name">{row['Municipio_Map']}</span>
                            <span class="hotspot-pill">{row['Registros']} regs</span>
                        </div>
                    """, unsafe_allow_html=True)

            # --- 4. RANKING LÍDERES ---
            st.markdown("---")
            st.subheader("🏆 Leaderboard de Registros")
            ranking = df['Registrado Por'].value_counts().reset_index()
            ranking.columns = ['Líder', 'Total']
            
            cols_rank = st.columns(2)
            for i, row in ranking.head(10).iterrows():
                target_col = cols_rank[0] if i < 5 else cols_rank[1]
                target_col.markdown(f"""
                    <div class="rank-item">
                        <span class="rank-name">{i+1}. {row['Líder'].upper()}</span>
                        <span class="rank-badge">{row['Total']} registros</span>
                    </div>
                """, unsafe_allow_html=True)

    # --- VISTA: BÚSQUEDA ---
    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador de Registros")
        df = get_data()
        if not df.empty:
            query = st.text_input("Buscar por Nombre, Cédula o Barrio...").upper()
            if query:
                mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)
                resultados = df[mask]
                st.write(f"Se encontraron {len(resultados)} resultados.")
                st.dataframe(resultados, use_container_width=True)
            else:
                st.write("Últimos 100 registros:")
                st.dataframe(df.tail(100), use_container_width=True)
