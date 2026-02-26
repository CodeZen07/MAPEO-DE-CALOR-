import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =============================================
# CONFIGURACIÓN DE LA APP
# =============================================
st.set_page_config(
    page_title="PuntoRojo - Gestión de Pérdidas EDE Este",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================
# DATOS SINTÉTICOS DE DEMOSTRACIÓN
# =============================================
def generar_datos_demo():
    """
    Genera dataset sintético con ubicaciones reales del Sector Este de RD
    Corredor: Máximo Gómez (DN) - Santo Domingo Este - San Pedro de Macorís
    """
    datos_demo = {
        'ID_Trafo': [
            'TF-GAZ-001', 'TF-GAZ-002', 'TF-LUP-001', 'TF-LUP-002', 'TF-LUP-003',
            'TF-SIS-001', 'TF-SIS-002', 'TF-ISL-001', 'TF-ISL-002', 'TF-BCH-001',
            'TF-BCH-002', 'TF-SPM-001', 'TF-SPM-002', 'TF-SPM-003', 'TF-SDE-001',
            'TF-SDE-002', 'TF-SDE-003', 'TF-GAZ-003', 'TF-LUP-004', 'TF-SPM-004'
        ],
        'Sector': [
            'Gazcue', 'Gazcue', 'Ensanche Luperón', 'Ensanche Luperón', 'Ensanche Luperón',
            'San Isidro', 'San Isidro', 'San Isidro Labrador', 'San Isidro Labrador', 
            'Boca Chica', 'Boca Chica', 'San Pedro de Macorís', 'San Pedro de Macorís', 
            'San Pedro de Macorís', 'Santo Domingo Este', 'Santo Domingo Este', 
            'Santo Domingo Este', 'Gazcue', 'Ensanche Luperón', 'San Pedro de Macorís'
        ],
        'Latitud': [
            18.4709, 18.4735, 18.4921, 18.4978, 18.5012,
            18.4532, 18.4598, 18.4423, 18.4389, 18.4512,
            18.4478, 18.4531, 18.4598, 18.4478, 18.4856,
            18.4923, 18.4789, 18.4698, 18.4956, 18.4612
        ],
        'Longitud': [
            -69.9312, -69.9289, -69.9123, -69.9089, -69.9056,
            -69.7123, -69.7089, -69.7234, -69.7298, -69.6123,
            -69.6089, -69.2978, -69.2912, -69.3012, -69.8456,
            -69.8389, -69.8523, -69.9267, -69.9112, -69.2889
        ],
        'Capacidad_kVA': [
            150, 225, 300, 150, 225, 300, 150, 225, 150, 300,
            225, 300, 150, 225, 300, 150, 225, 150, 300, 225
        ],
        'kWh_Entregado': [
            125000, 180000, 245000, 98000, 165000, 278000, 112000, 189000, 95000, 265000,
            198000, 312000, 145000, 203000, 289000, 134000, 176000, 108000, 256000, 198000
        ],
        'kWh_Facturado': [
            52500, 81000, 98000, 44100, 66000, 97240, 50400, 85140, 42750, 111300,
            89100, 124800, 63250, 91350, 130950, 60300, 79200, 48600, 102400, 89100
        ]
    }
    
    df = pd.DataFrame(datos_demo)
    
    # Calcular pérdidas y métricas
    df['kWh_Perdido'] = df['kWh_Entregado'] - df['kWh_Facturado']
    df['Perdida_%'] = (df['kWh_Perdido'] / df['kWh_Entregado']) * 100
    df['Perdida_Monetaria_RD$'] = df['kWh_Perdido'] * 12.5  # Tarifa promedio RD$
    df['Carga_%'] = (df['kWh_Entregado'] / (df['Capacidad_kVA'] * 730 * 0.8)) * 100
    
    return df

# =============================================
# FUNCIÓN DE CARGA Y VALIDACIÓN DE DATOS
# =============================================
def cargar_y_validar_datos(archivo):
    """
    Carga archivo Excel o CSV y valida columnas requeridas
    """
    try:
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo)
        elif archivo.name.endswith('.xlsx'):
            df = pd.read_excel(archivo, engine='openpyxl')
        else:
            st.error("❌ Formato no soportado. Use CSV o XLSX")
            return None
        
        # Columnas requeridas (flexibles con mayúsculas/minúsculas)
        columnas_requeridas = {
            'id_trafo': ['ID_Trafo', 'id_trafo', 'ID_TRAFO', 'Trafo_ID', 'trafo_id'],
            'sector': ['Sector', 'sector', 'SECTOR', 'Zona', 'zona'],
            'latitud': ['Latitud', 'latitud', 'LATITUD', 'Lat', 'lat'],
            'longitud': ['Longitud', 'longitud', 'LONGITUD', 'Lon', 'lon', 'Long', 'long'],
            'capacidad_kva': ['Capacidad_kVA', 'capacidad_kva', 'CAPACIDAD_KVA', 'kVA', 'kva'],
            'kwh_entregado': ['kWh_Entregado', 'kwh_entregado', 'KWH_ENTREGADO', 'Entregado', 'entregado'],
            'kwh_facturado': ['kWh_Facturado', 'kwh_facturado', 'KWH_FACTURADO', 'Facturado', 'facturado']
        }
        
        # Mapeo de columnas
        mapa_columnas = {}
        for col_std, variantes in columnas_requeridas.items():
            encontrada = False
            for variante in variantes:
                if variante in df.columns:
                    mapa_columnas[variante] = col_std
                    encontrada = True
                    break
            if not encontrada:
                st.error(f"❌ No se encontró la columna: {col_std.upper()}. Variantes buscadas: {', '.join(variantes)}")
                return None
        
        # Renombrar columnas
        df.rename(columns=mapa_columnas, inplace=True)
        
        # Calcular métricas
        df['kwh_perdido'] = df['kwh_entregado'] - df['kwh_facturado']
        df['perdida_%'] = (df['kwh_perdido'] / df['kwh_entregado']) * 100
        df['perdida_monetaria_rd$'] = df['kwh_perdido'] * 12.5
        df['carga_%'] = (df['kwh_entregado'] / (df['capacidad_kva'] * 730 * 0.8)) * 100
        
        # Normalizar nombres de columnas para consistencia
        df.columns = [
            'ID_Trafo', 'Sector', 'Latitud', 'Longitud', 'Capacidad_kVA', 
            'kWh_Entregado', 'kWh_Facturado', 'kWh_Perdido', 'Perdida_%', 
            'Perdida_Monetaria_RD$', 'Carga_%'
        ]
        
        st.success(f"✅ Archivo cargado: {len(df)} transformadores procesados")
        return df
        
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {str(e)}")
        return None

# =============================================
# ALGORITMO DE PRIORIZACIÓN
# =============================================
def calcular_prioridades(df):
    """
    Calcula prioridad de intervención basada en múltiples factores
    """
    df_prioridad = df.copy()
    
    # Score de prioridad (0-100)
    df_prioridad['Score_Volumen'] = (df_prioridad['kWh_Perdido'] / df_prioridad['kWh_Perdido'].max()) * 40
    df_prioridad['Score_Porcentaje'] = (df_prioridad['Perdida_%'] / 100) * 30
    df_prioridad['Score_Sobrecarga'] = df_prioridad['Carga_%'].apply(lambda x: 30 if x > 100 else (x/100)*15)
    
    df_prioridad['Prioridad_Score'] = (
        df_prioridad['Score_Volumen'] + 
        df_prioridad['Score_Porcentaje'] + 
        df_prioridad['Score_Sobrecarga']
    )
    
    # Categorizar prioridad
    def categorizar_prioridad(row):
        score = row['Prioridad_Score']
        perdida = row['Perdida_%']
        sector = row['Sector']
        carga = row['Carga_%']
        
        # Lógica especializada por sector y condiciones
        if sector in ['Ensanche Luperón', 'San Isidro'] and perdida > 50:
            return 'CRÍTICA - Operativo Urgente'
        elif carga > 100 and perdida > 40:
            return 'CRÍTICA - Cambio Transformador'
        elif score > 70:
            return 'ALTA'
        elif score > 40:
            return 'MEDIA'
        else:
            return 'BAJA'
    
    df_prioridad['Categoria_Prioridad'] = df_prioridad.apply(categorizar_prioridad, axis=1)
    
    # Generar sugerencias
    def generar_sugerencia(row):
        sector = row['Sector']
        perdida = row['Perdida_%']
        carga = row['Carga_%']
        
        sugerencias = []
        
        if sector in ['Ensanche Luperón', 'San Isidro'] and perdida > 50:
            sugerencias.append("🔴 OPERATIVO DE NORMALIZACIÓN: Blindaje de red y regularización de conexiones directas")
        
        if carga > 100:
            sugerencias.append(f"⚡ CAMBIO DE TRANSFORMADOR: Sobrecarga del {carga:.0f}% - Capacidad insuficiente")
        
        if perdida > 60:
            sugerencias.append("🔍 INSPECCIÓN TÉCNICA: Posible fraude masivo o falla en medición")
        elif perdida > 40:
            sugerencias.append("📋 AUDITORÍA DE RED: Revisar conexiones no autorizadas")
        
        if perdida > 30 and carga < 70:
            sugerencias.append("🔧 MANTENIMIENTO PREVENTIVO: Revisar estado de conductores y empalmes")
        
        return ' | '.join(sugerencias) if sugerencias else 'Monitoreo regular'
    
    df_prioridad['Sugerencia_Intervencion'] = df_prioridad.apply(generar_sugerencia, axis=1)
    
    return df_prioridad.sort_values('Prioridad_Score', ascending=False)

# =============================================
# GENERACIÓN DE MAPA INTERACTIVO
# =============================================
def crear_mapa_calor(df):
    """
    Crea mapa de calor con marcadores categorizados por pérdida
    """
    # Centro del mapa: Corredor Este RD
    mapa = folium.Map(
        location=[18.48, -69.65],
        zoom_start=11,
        tiles='OpenStreetMap'
    )
    
    # Agregar capa de calor
    heat_data = [[row['Latitud'], row['Longitud'], row['kWh_Perdido']] 
                 for idx, row in df.iterrows()]
    HeatMap(heat_data, radius=15, blur=25, max_zoom=13, gradient={
        0.0: 'green', 0.3: 'yellow', 0.5: 'orange', 0.7: 'red', 1.0: 'darkred'
    }).add_to(mapa)
    
    # Agregar marcadores con categorización por color
    for idx, row in df.iterrows():
        perdida = row['Perdida_%']
        
        # Determinar color y tamaño
        if perdida > 50:
            color = 'red'
            radius = 12
            icono = '🔴'
        elif perdida > 30:
            color = 'orange'
            radius = 10
            icono = '🟠'
        else:
            color = 'green'
            radius = 8
            icono = '🟢'
        
        # Crear popup con información detallada
        popup_html = f"""
        <div style="font-family: Arial; width: 250px;">
            <h4 style="margin:0; color:{color};">{icono} {row['ID_Trafo']}</h4>
            <hr style="margin:5px 0;">
            <b>Sector:</b> {row['Sector']}<br>
            <b>Pérdida:</b> {perdida:.1f}%<br>
            <b>Energía Perdida:</b> {row['kWh_Perdido']:,.0f} kWh<br>
            <b>Impacto Monetario:</b> RD$ {row['Perdida_Monetaria_RD$']:,.2f}<br>
            <b>Capacidad:</b> {row['Capacidad_kVA']} kVA<br>
            <b>Carga:</b> {row['Carga_%']:.0f}%
        </div>
        """
        
        folium.CircleMarker(
            location=[row['Latitud'], row['Longitud']],
            radius=radius,
            popup=folium.Popup(popup_html, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(mapa)
    
    # Agregar leyenda
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 180px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
        <p style="margin:0;"><b>Nivel de Pérdida</b></p>
        <p style="margin:5px 0;"><span style="color:red;">🔴</span> > 50% - CRÍTICO</p>
        <p style="margin:5px 0;"><span style="color:orange;">🟠</span> 30-50% - ALTO</p>
        <p style="margin:5px 0;"><span style="color:green;">🟢</span> < 30% - NORMAL</p>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legend_html))
    
    return mapa

# =============================================
# INTERFAZ PRINCIPAL
# =============================================
st.title("🔴 PuntoRojo - Sistema de Gestión de Pérdidas Energéticas")
st.markdown("### EDE Este - Corredor DN → SDE → San Pedro de Macorís")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/250x80/FF0000/FFFFFF?text=EDE+ESTE", use_container_width=True)
    st.markdown("## ⚙️ Configuración")
    
    modo = st.radio(
        "Modo de Operación:",
        ["📊 Modo Demostración", "📁 Cargar Datos Reales"],
        help="Use el modo demo para ver el funcionamiento o cargue su archivo"
    )
    
    st.markdown("---")
    
    if modo == "📁 Cargar Datos Reales":
        st.markdown("### 📤 Subir Archivo")
        archivo = st.file_uploader(
            "Seleccione archivo Excel (.xlsx) o CSV",
            type=['xlsx', 'csv'],
            help="El archivo debe contener: ID_Trafo, Sector, Latitud, Longitud, Capacidad_kVA, kWh_Entregado, kWh_Facturado"
        )
        
        if archivo:
            df = cargar_y_validar_datos(archivo)
        else:
            df = None
            st.info("⬆️ Suba un archivo para comenzar el análisis")
    else:
        st.success("✅ Usando datos de demostración")
        df = generar_datos_demo()
        
        with st.expander("ℹ️ Sobre los Datos Demo"):
            st.markdown("""
            Los datos de demostración incluyen **20 transformadores** en:
            - Gazcue (DN)
            - Ensanche Luperón
            - San Isidro
            - San Isidro Labrador
            - Boca Chica
            - San Pedro de Macorís
            - Santo Domingo Este
            
            Representan escenarios reales de pérdida energética en el Sector Este.
            """)

# Contenido principal
if df is not None and len(df) > 0:
    
    # Calcular prioridades
    df_priorizado = calcular_prioridades(df)
    
    # Métricas globales
    st.markdown("## 📈 Indicadores Generales")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_entregado = df['kWh_Entregado'].sum()
        st.metric(
            "Energía Entregada",
            f"{total_entregado/1e6:.2f} MWh",
            help="Total de energía distribuida"
        )
    
    with col2:
        total_facturado = df['kWh_Facturado'].sum()
        st.metric(
            "Energía Facturada",
            f"{total_facturado/1e6:.2f} MWh",
            help="Total de energía cobrada"
        )
    
    with col3:
        perdida_total = df['kWh_Perdido'].sum()
        perdida_pct = (perdida_total / total_entregado) * 100
        st.metric(
            "Pérdida Total",
            f"{perdida_pct:.1f}%",
            f"-{perdida_total/1e6:.2f} MWh",
            delta_color="inverse"
        )
    
    with col4:
        impacto_monetario = df['Perdida_Monetaria_RD$'].sum()
        st.metric(
            "Impacto Monetario",
            f"RD$ {impacto_monetario/1e6:.2f}M",
            help="Pérdida estimada en pesos dominicanos"
        )
    
    st.markdown("---")
    
    # Panel de priorización
    st.markdown("## 🎯 Panel de Priorización de Intervenciones")
    
    tab1, tab2, tab3 = st.tabs(["🗺️ Mapa de Calor", "📊 Análisis por Sector", "📋 Lista Priorizada"])
    
    with tab1:
        st.markdown("### Visualización Geoespacial de Pérdidas")
        
        # Crear y mostrar mapa
        mapa = crear_mapa_calor(df_priorizado)
        st_folium(mapa, width=1400, height=600)
        
        st.info("""
        **Cómo interpretar el mapa:**
        - Las zonas **rojas intensas** en el mapa de calor indican alta concentración de pérdidas
        - Los marcadores **🔴 rojos** representan transformadores con >50% de pérdida (CRÍTICO)
        - Los marcadores **🟠 naranjas** indican pérdidas entre 30-50% (ATENCIÓN)
        - Los marcadores **🟢 verdes** muestran operación normal (<30% pérdida)
        - Haga clic en cualquier marcador para ver detalles específicos
        """)
    
    with tab2:
        st.markdown("### Análisis Comparativo por Sector")
        
        # Agrupar por sector
        df_sector = df_priorizado.groupby('Sector').agg({
            'kWh_Perdido': 'sum',
            'Perdida_%': 'mean',
            'Perdida_Monetaria_RD$': 'sum',
            'ID_Trafo': 'count'
        }).reset_index()
        df_sector.columns = ['Sector', 'kWh_Perdido_Total', 'Perdida_%_Promedio', 'Impacto_Monetario', 'Num_Transformadores']
        df_sector = df_sector.sort_values('kWh_Perdido_Total', ascending=False)
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Gráfico de barras: Pérdida por sector
            fig1 = px.bar(
                df_sector,
                x='Sector',
                y='kWh_Perdido_Total',
                title='Energía Perdida por Sector (kWh)',
                color='Perdida_%_Promedio',
                color_continuous_scale='RdYlGn_r',
                labels={'kWh_Perdido_Total': 'kWh Perdidos', 'Perdida_%_Promedio': '% Pérdida Promedio'}
            )
            fig1.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col_g2:
            # Gráfico circular: Distribución de impacto monetario
            fig2 = px.pie(
                df_sector,
                values='Impacto_Monetario',
                names='Sector',
                title='Distribución de Impacto Monetario por Sector',
                hole=0.4
            )
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True)
        
        # Tabla resumen por sector
        st.markdown("#### 📊 Resumen Detallado por Sector")
        df_sector_display = df_sector.copy()
        df_sector_display['kWh_Perdido_Total'] = df_sector_display['kWh_Perdido_Total'].apply(lambda x: f"{x:,.0f}")
        df_sector_display['Perdida_%_Promedio'] = df_sector_display['Perdida_%_Promedio'].apply(lambda x: f"{x:.1f}%")
        df_sector_display['Impacto_Monetario'] = df_sector_display['Impacto_Monetario'].apply(lambda x: f"RD$ {x:,.2f}")
        
        st.dataframe(df_sector_display, use_container_width=True, hide_index=True)
    
    with tab3:
        st.markdown("### Lista de Transformadores Priorizados")
        
        # Filtros
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            filtro_prioridad = st.multiselect(
                "Filtrar por Prioridad:",
                options=df_priorizado['Categoria_Prioridad'].unique(),
                default=df_priorizado['Categoria_Prioridad'].unique()
            )
        
        with col_f2:
            filtro_sector = st.multiselect(
                "Filtrar por Sector:",
                options=df_priorizado['Sector'].unique(),
                default=df_priorizado['Sector'].unique()
            )
        
        with col_f3:
            min_perdida = st.slider(
                "Pérdida Mínima (%):",
                0, 100, 30
            )
        
        # Aplicar filtros
        df_filtrado = df_priorizado[
            (df_priorizado['Categoria_Prioridad'].isin(filtro_prioridad)) &
            (df_priorizado['Sector'].isin(filtro_sector)) &
            (df_priorizado['Perdida_%'] >= min_perdida)
        ]
        
        st.markdown(f"**Transformadores encontrados:** {len(df_filtrado)}")
        
        # Mostrar tabla priorizada
        for idx, row in df_filtrado.head(20).iterrows():
            with st.expander(f"🔸 {row['ID_Trafo']} - {row['Sector']} | Prioridad: {row['Categoria_Prioridad']} (Score: {row['Prioridad_Score']:.0f})"):
                col_d1, col_d2 = st.columns([1, 2])
                
                with col_d1:
                    st.markdown(f"""
                    **Datos Técnicos:**
                    - Capacidad: {row['Capacidad_kVA']} kVA
                    - Carga: {row['Carga_%']:.0f}%
                    - Entregado: {row['kWh_Entregado']:,.0f} kWh
                    - Facturado: {row['kWh_Facturado']:,.0f} kWh
                    """)
                    
                    st.markdown(f"""
                    **Pérdidas:**
                    - Porcentaje: **{row['Perdida_%']:.1f}%**
                    - Volumen: {row['kWh_Perdido']:,.0f} kWh
                    - Impacto: RD$ {row['Perdida_Monetaria_RD$']:,.2f}
                    """)
                
                with col_d2:
                    st.markdown("**🎯 Plan de Intervención Sugerido:**")
                    st.warning(row['Sugerencia_Intervencion'])
                    
                    # Indicador visual de prioridad
                    if 'CRÍTICA' in row['Categoria_Prioridad']:
                        st.error("⚠️ **ACCIÓN INMEDIATA REQUERIDA**")
                    elif row['Categoria_Prioridad'] == 'ALTA':
                        st.warning("⚡ **INTERVENCIÓN PRIORITARIA**")
                    else:
                        st.info("📋 Programar revisión")
    
    # Sección de exportación
    st.markdown("---")
    st.markdown("## 📥 Exportar Resultados")
    
    col_e1, col_e2, col_e3 = st.columns(3)
    
    with col_e1:
        csv_completo = df_priorizado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Descargar Análisis Completo (CSV)",
            data=csv_completo,
            file_name=f"analisis_completo_puntorojo_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col_e2:
        # Top 10 críticos
        df_top10 = df_priorizado.head(10)
        csv_top10 = df_top10.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🔴 Top 10 Transformadores Críticos (CSV)",
            data=csv_top10,
            file_name=f"top10_criticos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col_e3:
        # Resumen por sector
        csv_sector = df_sector.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📍 Resumen por Sector (CSV)",
            data=csv_sector,
            file_name=f"resumen_sectores_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

else:
    # Estado inicial sin datos
    st.info("""
    ### 👋 Bienvenido a PuntoRojo
    
    **Para comenzar:**
    1. Seleccione el "Modo Demostración" en el panel lateral para ver datos de ejemplo
    2. O cargue su propio archivo Excel/CSV con datos de transformadores
    
    **Columnas requeridas en el archivo:**
    - `ID_Trafo` - Identificador del transformador
    - `Sector` - Nombre del sector o zona
    - `Latitud` - Coordenada geográfica
    - `Longitud` - Coordenada geográfica
    - `Capacidad_kVA` - Capacidad del transformador en kVA
    - `kWh_Entregado` - Energía distribuida
    - `kWh_Facturado` - Energía cobrada
    """)
    
    st.markdown("---")
    st.markdown("### 🎯 Capacidades del Sistema")
    
    col_cap1, col_cap2, col_cap3 = st.columns(3)
    
    with col_cap1:
        st.markdown("""
        **🗺️ Visualización Avanzada**
        - Mapa de calor geoespacial
        - Marcadores categorizados por severidad
        - Popups informativos detallados
        """)
    
    with col_cap2:
        st.markdown("""
        **🎯 Priorización Inteligente**
        - Algoritmo multi-factor
        - Sugerencias automáticas
        - Identificación de sectores críticos
        """)
    
    with col_cap3:
        st.markdown("""
        **📊 Análisis Profundo**
        - Métricas por sector
        - Impacto monetario
        - Exportación de resultados
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85em;'>
    <p><strong>PuntoRojo v1.0</strong> - Sistema de Gestión de Pérdidas Energéticas</p>
    <p>EDE Este | República Dominicana | {}</p>
    <p><em>Objetivo: Reducir pérdidas del 58% actual hacia niveles sostenibles</em></p>
</div>
""".format(datetime.now().strftime("%Y")), unsafe_allow_html=True)
