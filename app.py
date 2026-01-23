import json

# 1. Nombre del archivo original (debe estar en la misma carpeta)
file_path = 'co_2018_MGN_MPIO_POLITICO.geojson'

print("⏳ Iniciando procesamiento del mapa... esto puede tardar unos segundos.")

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. Filtrar municipios del Valle del Cauca (Código 76)
    valle_features = []
    
    for feature in data['features']:
        props = feature['properties']
        # Convertimos a string y quitamos espacios para evitar errores de formato
        dpto_code = str(props.get('DPTO_CCDGO', '')).strip()
        
        if dpto_code == '76':
            # --- CORRECCIÓN CRÍTICA DE NOMBRES ---
            nombre_sucio = str(props.get('MPIO_CNMBR', '')).upper()
            
            # Si el nombre contiene CALI, lo estandarizamos a SANTIAGO DE CALI
            if "CALI" in nombre_sucio:
                props['MPIO_CNMBR'] = "SANTIAGO DE CALI"
            
            # Limpiamos el nombre para que no tenga espacios extra
            props['MPIO_CNMBR'] = " ".join(props['MPIO_CNMBR'].split())
            
            # Asignamos el ID para que Plotly lo encuentre fácilmente
            feature['id'] = props['MPIO_CNMBR']
            
            valle_features.append(feature)

    # 3. Crear el nuevo archivo optimizado
    valle_data = {
        "type": "FeatureCollection",
        "features": valle_features
    }

    # 4. Guardar el archivo corregido
    output_name = 'valle_del_cauca_fixed.geojson'
    with open(output_name, 'w', encoding='utf-8') as f:
        json.dump(valle_data, f, ensure_ascii=False)

    print(f"✅ ¡Éxito! Se ha creado '{output_name}'.")
    print(f"📦 El archivo se redujo de {len(data['features'])} a {len(valle_features)} municipios.")
    print("🚀 Ahora sube este archivo a tu repositorio de GitHub.")

except FileNotFoundError:
    print(f"❌ Error: No se encontró el archivo '{file_path}' en esta carpeta.")
except Exception as e:
    print(f"❌ Ocurrió un error inesperado: {e}")
