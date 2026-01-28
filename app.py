import streamlit as st
import pandas as pd
import datetime
import numpy as np

def apply_custom_styles():
    """
    Inyecta el CSS del sistema de diseño Pulse Analytics con mejoras para móviles.
    """
    st.markdown("""
    <style>
        /* Variables del Sistema */
        :root {
            --pulse-pink: #E91E63;
            --pulse-dark: #0F172A;
            --pulse-slate: #64748B;
            --pulse-bg: #F8FAFC;
        }

        /* Estilo Base de Tarjetas KPI */
        .pulse-kpi-card {
            background: white;
            padding: 24px;
            border-radius: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid #F1F5F9;
            margin-bottom: 1rem;
            transition: transform 0.2s;
        }

        .pulse-kpi-label {
            color: var(--pulse-slate);
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 4px;
        }

        .pulse-kpi-value {
            color: var(--pulse-dark);
            font-size: 1.875rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .pulse-trend {
            display: flex;
            align-items: center;
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 8px;
        }

        .trend-up { color: #10B981; }
        .trend-down { color: #EF4444; }

        /* Estilos para Lista de Barrios */
        .barrio-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: #F8FAFC;
            border-radius: 12px;
            margin-bottom: 8px;
        }

        .badge-pct {
            background: var(--pulse-pink);
            color: white;
            padding: 2px 8px;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: bold;
        }

        /* --- RESPONSIVIDAD MÓVIL --- */
        @media (max-width: 768px) {
            .pulse-kpi-card {
                padding: 16px;
                margin-bottom: 0.75rem;
            }
            
            .pulse-kpi-value {
                font-size: 1.5rem;
            }

            /* Forzar que los elementos táctiles sean accesibles */
            .stButton > button {
                min-height: 44px;
                width: 100%;
            }

            /* Ajuste de fuentes generales */
            p, span, div {
                font-size: 16px !important; 
            }
            
            .main .block-container {
                padding-left: 0.5rem;
                padding-right: 0.5rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def get_neighborhood_stats(df):
    """Calcula estadísticas de barrios para la nueva sección."""
    # Top 5 general
    top_5_barrios = df['Barrio'].value_counts().head(5)
    
    # Top 3 por municipio (solo si municipio > 50 registros)
    city_counts = df['Ciudad'].value_counts()
    eligible_cities = city_counts[city_counts > 50].index.tolist()
    
    city_barrio_breakdown = {}
    for city in eligible_cities:
        city_df = df[df['Ciudad'] == city]
        top_3 = city_df['Barrio'].value_counts().head(3)
        city_barrio_breakdown[city] = {
            'total': len(city_df),
            'top': top_3.to_dict()
        }
        
    return top_5_barrios, city_barrio_breakdown

def view_estadisticas(df):
    """
    Refactorización de la vista de estadísticas optimizada para móviles.
    """
    apply_custom_styles()
    
    # Asegurar que la fecha sea tipo date para comparaciones
    if not pd.api.types.is_datetime64_any_dtype(df['Fecha Registro']):
        df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'])
    
    df_dates = df['Fecha Registro'].dt.date
    
    # --- 1. SECCIÓN HERO Y PROGRESO ---
    st.title("📊 Estadísticas de Campaña")
    total_registros = len(df)
    objetivo = 12000
    progreso = min(total_registros / objetivo, 1.0)
    
    st.markdown(f"""
        <div style="background: white; padding: 20px; border-radius: 24px; margin-bottom: 20px; border: 1px solid #F1F5F9;">
            <p style="color: #64748B; font-weight: 500; margin-bottom: 10px;">Meta Departamental: {total_registros:,} / {objetivo:,} registros</p>
            <div style="background: #F1F5F9; border-radius: 10px; height: 12px; width: 100%;">
                <div style="background: var(--pulse-pink); width: {progreso*100}%; height: 100%; border-radius: 10px;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- 2. CUADRÍCULA DE KPI ADAPTABLE ---
    hoy = datetime.date.today()
    hace_8_dias = hoy - datetime.timedelta(days=8)
    hace_30_dias = hoy - datetime.timedelta(days=30)
    
    reg_hoy = len(df[df_dates == hoy])
    reg_8d = len(df[df_dates >= hace_8_dias])
    reg_30d = len(df[df_dates >= hace_30_dias])
    total_municipios = df['Ciudad'].nunique()

    kpi_cols = st.columns([1, 1, 1, 1])
    kpis = [
        {"icon": "📈", "label": "Registros Hoy", "val": reg_hoy, "trend": "+12%", "up": True},
        {"icon": "🗓️", "label": "Últimos 8 Días", "val": reg_8d, "trend": "+5%", "up": True},
        {"icon": "📊", "label": "Últimos 30 Días", "val": reg_30d, "trend": "-2%", "up": False},
        {"icon": "📍", "label": "Municipios", "val": total_municipios, "trend": "Firme", "up": True}
    ]

    for i, col in enumerate(kpi_cols):
        with col:
            trend_class = "trend-up" if kpis[i]["up"] else "trend-down"
            trend_icon = "↑" if kpis[i]["up"] else "↓"
            st.markdown(f"""
                <div class="pulse-kpi-card">
                    <div style="font-size: 1.5rem; margin-bottom: 8px;">{kpis[i]['icon']}</div>
                    <div class="pulse-kpi-label">{kpis[i]['label']}</div>
                    <div class="pulse-kpi-value">{kpis[i]['val']:,}</div>
                    <div class="pulse-trend {trend_class}">
                        {trend_icon} {kpis[i]['trend']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # --- 3. ANÁLISIS POR BARRIOS ---
    top_5_b, city_b = get_neighborhood_stats(df)
    
    with st.expander("🏘️ Análisis por Barrios", expanded=False):
        st.subheader("Top 5 Barrios")
        b_cols = st.columns(5)
        for idx, (barrio, count) in enumerate(top_5_b.items()):
            with b_cols[idx]:
                st.markdown(f"""
                    <div style="background: #FDF2F8; padding: 10px; border-radius: 12px; text-align: center; border: 1px solid #FCE7F3;">
                        <div style="font-size: 0.65rem; color: var(--pulse-pink); font-weight: bold;">{barrio}</div>
                        <div style="font-size: 1.1rem; font-weight: 700;">{count:,}</div>
                    </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        if city_b:
            for city, data in city_b.items():
                with st.expander(f"📍 {city}", expanded=False):
                    for barrio, b_count in data['top'].items():
                        b_pct = (b_count / data['total']) * 100
                        st.markdown(f"""
                            <div class="barrio-item">
                                <span style="font-weight: 600;">{barrio}</span>
                                <span class="badge-pct">{b_pct:.1f}%</span>
                            </div>
                        """, unsafe_allow_html=True)

    # --- 4. MAPA (Simulado/Mantenido) ---
    st.subheader("Cobertura Territorial")
    c_map_view, c_map_stats = st.columns([5, 1])
    with c_map_view:
        st.info("Visualización de Mapa Territorial Activa")
    with c_map_stats:
        st.markdown("### Top 3")
        top_cities = df['Ciudad'].value_counts().head(3)
        for city, count in top_cities.items():
            st.metric(city, count)

    # --- 5. TENDENCIAS Y LÍDERES ---
    st.divider()
    t_cols = st.columns([2, 1])
    with t_cols[0]:
        st.subheader("Tendencia")
        st.line_chart(df.groupby(df_dates).size())
    with t_cols[1]:
        st.subheader("Líderes")
        leaderboard = df['Registrado Por'].value_counts().head(5)
        st.dataframe(leaderboard, use_container_width=True)

# --- INICIO DE LA APLICACIÓN (Punto de entrada) ---
if __name__ == "__main__":
    st.set_page_config(page_title="Pulse Analytics", layout="wide")
    
    # Generar datos de prueba si no existen
    np.random.seed(42)
    ciudades = ['Cali', 'Palmira', 'Buenaventura', 'Buga', 'Tuluá']
    barrios = ['Centro', 'El Prado', 'San Antonio', 'Santa Rita', 'Pance', 'Ciudad Jardín']
    registradores = ['Ana P.', 'Carlos M.', 'Lucía R.', 'Juan K.']
    
    try:
        # Intentamos cargar datos o usamos mock
        if 'df_social' not in st.session_state:
            dates = [datetime.date.today() - datetime.timedelta(days=x) for x in range(40)]
            data = {
                'Fecha Registro': np.random.choice(dates, 1000),
                'Ciudad': np.random.choice(ciudades, 1000),
                'Barrio': np.random.choice(barrios, 1000),
                'Registrado Por': np.random.choice(registradores, 1000)
            }
            st.session_state.df_social = pd.DataFrame(data)
        
        view_estadisticas(st.session_state.df_social)
    except Exception as e:
        st.error(f"Error al cargar la vista: {e}")
