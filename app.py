# --- DASHBOARD ---
if check_auth():

    usuario = st.session_state.user_name
    es_admin = usuario.lower() in ["fabian", "xammy", "brayan"]

    st.sidebar.markdown(
        f"<b>Usuario:</b><br>{usuario.upper()}",
        unsafe_allow_html=True
    )

    opcion = st.sidebar.radio(
        "MENÚ",
        ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"]
    )

    if st.sidebar.button("Salir"):
        st.session_state.clear()
        st.rerun()

    # =========================
    # REGISTRO
    # =========================
    if opcion == "📝 Registro":

        st.title("🗳️ Nuevo Registro")

        with st.form(key=f"form_{st.session_state.f_reset}"):
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
                    if save_data({
                        "nombre": nom.upper(),
                        "cedula": ced,
                        "telefono": tel,
                        "ocupacion": ocu.upper(),
                        "direccion": dir.upper(),
                        "barrio": bar.upper(),
                        "ciudad": ciu.upper(),
                        "puesto": pue.upper()
                    }):
                        st.success("Registro guardado")
                        st.session_state.f_reset += 1
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Complete Nombre, Cédula y Teléfono")

    # =========================
    # ESTADÍSTICAS
    # =========================
    elif opcion == "📊 Estadísticas":

        st.title("📊 Pulse Analytics")

        df = get_data()
        if df.empty:
            st.info("No hay datos para mostrar.")
        else:
            df["Municipio_Map"] = df["Ciudad"].apply(normalizar_para_mapa)
            map_data = df["Municipio_Map"].value_counts().reset_index()
            map_data.columns = ["Municipio", "Registros"]

            geojson_url = (
                "https://raw.githubusercontent.com/"
                "caticoa3/colombia_mapa/master/"
                "co_2018_MGN_MPIO_POLITICO.geojson"
            )
            geojson_data = requests.get(geojson_url).json()

            fig = px.choropleth(
                map_data,
                geojson=geojson_data,
                locations="Municipio",
                featureidkey="properties.NOM_MPIO",
                color="Registros",
                color_continuous_scale="YlOrRd",
                template="plotly_white"
            )

            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(height=600)

            st.plotly_chart(fig, use_container_width=True)

    # =========================
    # BÚSQUEDA
    # =========================
    elif opcion == "🔍 Búsqueda":

        st.title("🔍 Explorador de Registros")

        df = get_data()
        if df.empty:
            st.info("No hay datos para mostrar.")
        else:
            q = st.text_input("Buscar...").upper()
            if q:
                res = df[df.astype(str).apply(
                    lambda x: x.str.upper().str.contains(q, na=False),
                    axis=1
                )]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(100), use_container_width=True)
