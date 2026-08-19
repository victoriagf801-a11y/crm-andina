import io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTÉTICA CRM ENTERPRISE
# ==============================================================================
st.set_page_config(
    page_title="ANDINA | Customer Intelligence & RFM Engine",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Tarjetas de métricas */
    .metric-container {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    }
    .metric-label { font-size: 0.82rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-val { font-size: 1.65rem; font-weight: 700; color: #0F172A; margin: 4px 0; }
    .metric-sub { font-size: 0.78rem; color: #10B981; font-weight: 500; }
    
    /* Playbook Card */
    .playbook-card {
        background: #F8FAFC;
        border-left: 4px solid #3B82F6;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        margin: 10px 0;
    }
    .channel-badge {
        display: inline-block;
        background: #EEF2FF;
        color: #4F46E5;
        border: 1px solid #C7D2FE;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-right: 6px;
        margin-top: 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. FRAMEWORK RFM & PLAYBOOKS DE MARKETING DIGITAL
# ==============================================================================
PLAYBOOKS = {
    "Campeones": {
        "color": "#10B981",
        "desc": "Compraron recientemente, compran seguido y generan el mayor volumen de facturación.",
        "canales": [
            "WhatsApp VIP / Key Account",
            "Email 1-a-1",
            "Pauta Lookalike (1%)",
        ],
        "accion": "Venta cruzada de contratos anuales de consultoría y mantenimiento preventivo. Early access a nuevos equipos.",
    },
    "Clientes Leales": {
        "color": "#3B82F6",
        "desc": "Compradores constantes con alto valor acumulado. Receptivos a la marca.",
        "canales": [
            "Email Marketing Segmentado",
            "WhatsApp Automatizado",
            "Pauta Retargeting",
        ],
        "accion": "Suscripción recurrente a consumibles con beneficios exclusivos y programas de referidos B2B.",
    },
    "Prometedores": {
        "color": "#8B5CF6",
        "desc": "Clientes recientes con buena respuesta pero bajo número de compras históricas.",
        "canales": [
            "Email Secuencia Nurturing",
            "WhatsApp Onboarding",
            "Pauta Conversión",
        ],
        "accion": "Garantizar adopción del equipo adquirido, ofrecer paquete de consumibles de bienvenida con descuento temporal.",
    },
    "Necesitan Atención": {
        "color": "#F59E0B",
        "desc": "Frecuencia y valor promedio, pero su recencia empieza a enfriarse.",
        "canales": [
            "Email Reactivación",
            "SMS Recordatorio",
            "Pauta Remarketing Dinámico",
        ],
        "accion": "Ofrecer chequeo de diagnóstico gratuito para equipos o recordatorio de reposición de insumos críticos.",
    },
    "En Riesgo": {
        "color": "#EF4444",
        "desc": "Eran grandes compradores o cuentas clave, pero no han interactuado recientemente.",
        "canales": [
            "Llamada Ejecutiva + WhatsApp Directo",
            "Email Especial de Retención",
        ],
        "accion": "Contacto personalizado de Gerencia de Servicio / Ventas con ofertas agresivas de renovación y soporte.",
    },
    "Dormidos / Perdidos": {
        "color": "#64748B",
        "desc": "Bajo ticket, baja frecuencia y sin actividad comercial en largo tiempo.",
        "canales": [
            "Email Win-Back Automatizado",
            "SMS Promocional Flash",
            "Exclusión de Pauta",
        ],
        "accion": "Depuración del CRM para no quemar entregabilidad o 1 campaña final con descuento de liquidación.",
    },
}


# ==============================================================================
# 3. MOTOR DE CÁLCULO RFM ROBUSTO
# ==============================================================================
def process_rfm(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df.columns = df.columns.str.strip()

    # Tipado y limpieza
    df["UltimaCompra"] = pd.to_datetime(df["UltimaCompra"], errors="coerce")
    df["Compras"] = pd.to_numeric(df["Compras"], errors="coerce").fillna(0)
    df["ValorTotal"] = (
        pd.to_numeric(df["ValorTotal"], errors="coerce").fillna(0)
    )

    # Recencia en días
    hoy = pd.Timestamp.now().normalize()
    df["Recencia_Dias"] = (
        (hoy - df["UltimaCompra"]).dt.days.fillna(9999).astype(int)
    )

    # Quintiles estadísticos usando ranking para manejar fronteras idénticas sin empates
    df["R_Score"] = pd.qcut(
        df["Recencia_Dias"].rank(method="first", ascending=True),
        5,
        labels=[5, 4, 3, 2, 1],
    ).astype(int)
    df["F_Score"] = pd.qcut(
        df["Compras"].rank(method="first", ascending=True),
        5,
        labels=[1, 2, 3, 4, 5],
    ).astype(int)
    df["M_Score"] = pd.qcut(
        df["ValorTotal"].rank(method="first", ascending=True),
        5,
        labels=[1, 2, 3, 4, 5],
    ).astype(int)

    df["RFM_Cell"] = (
        df["R_Score"].astype(str)
        + df["F_Score"].astype(str)
        + df["M_Score"].astype(str)
    )
    df["FM_Score"] = ((df["F_Score"] + df["M_Score"]) / 2.0).round(2)

    # Matriz Moderna de Segmentación (R vs FM)
    def assign_segment(row):
        r = row["R_Score"]
        fm = row["FM_Score"]
        if r >= 4 and fm >= 4:
            return "Campeones"
        elif r >= 3 and fm >= 3:
            return "Clientes Leales"
        elif r >= 4 and fm < 3:
            return "Prometedores"
        elif r in [2, 3] and (2.0 <= fm < 3.5):
            return "Necesitan Atención"
        elif r <= 2 and fm >= 3.0:
            return "En Riesgo"
        else:
            return "Dormidos / Perdidos"

    df["Segmento"] = df.apply(assign_segment, axis=1)
    return df


def to_excel_download(df_to_export: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_to_export.to_excel(writer, index=False, sheet_name="Segmento_RFM")
    return output.getvalue()


# ==============================================================================
# 4. SIDEBAR - INGESTA DE DATOS Y FILTROS
# ==============================================================================
with st.sidebar:
    st.image(
        "https://cdn-icons-png.flaticon.com/512/9167/9167015.png", width=48
    )
    st.title("ANDINA CRM")
    st.caption("Sistema de Segmentación RFM y Funnels")
    st.divider()

    uploaded_file = st.file_uploader(
        "Cargar Base de Clientes (.CSV)",
        type=["csv"],
        help="El archivo debe contener: ClienteID, Nombre, Tipo, Ciudad, UltimaCompra, Compras, ValorTotal, Categoria, Canal",
    )

    url_default = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRyGkmN0BzJUz4ILVZvL3zeg6-PVXRbdwgV5epmI4QfhnrFj4HfzUgoEUV07ZanEgV-ArFCX18g312v/pub?output=csv"
    use_cloud_data = st.checkbox("Cargar dataset en vivo de ANDINA", value=True)

# Carga de Datos
df_raw = None
if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
elif use_cloud_data:
    try:
        df_raw = pd.read_csv(url_default)
    except Exception:
        st.sidebar.error("Error al cargar la URL. Sube el archivo CSV manual.")

# ==============================================================================
# 5. DASHBOARD PRINCIPAL
# ==============================================================================
if df_raw is not None:
    df = process_rfm(df_raw)

    # Filtros de Operación en Sidebar
    with st.sidebar:
        st.subheader("🎯 Filtros Estratégicos")
        ciudades_disp = ["Todas"] + sorted(
            df["Ciudad"].dropna().unique().tolist()
        )
        ciudad_sel = st.selectbox("Filtrar por Ciudad", ciudades_disp)

        tipos_disp = ["Todos"] + sorted(df["Tipo"].dropna().unique().tolist())
        tipo_sel = st.selectbox("Tipo de Cliente", tipos_disp)

        if ciudad_sel != "Todas":
            df = df[df["Ciudad"] == ciudad_sel]
        if tipo_sel != "Todos":
            df = df[df["Tipo"] == tipo_sel]

    # Header
    st.title("⚡ Segmentación de Clientes RFM & Activación")
    st.markdown(
        f"Base procesada: **{len(df):,} clientes** | Facturación acumulada: **${df['ValorTotal'].sum():,.0f}**"
    )

    # KPIs de Alto Nivel
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(
            f"""
        <div class="metric-container">
            <div class="metric-label">Total Clientes</div>
            <div class="metric-val">{len(df):,}</div>
            <div class="metric-sub">Activos en Base</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with kpi2:
        st.markdown(
            f"""
        <div class="metric-container">
            <div class="metric-label">Ticket Promedio (AOV)</div>
            <div class="metric-val">${(df['ValorTotal'].sum() / max(df['Compras'].sum(), 1)):,.0f}</div>
            <div class="metric-sub">Por Transacción</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with kpi3:
        st.markdown(
            f"""
        <div class="metric-container">
            <div class="metric-label">Recencia Mediana</div>
            <div class="metric-val">{int(df['Recencia_Dias'].median())} días</div>
            <div class="metric-sub">Ventana de compra</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with kpi4:
        champs_rev = df[df["Segmento"] == "Campeones"]["ValorTotal"].sum()
        pct_champs = (
            (champs_rev / df["ValorTotal"].sum() * 100)
            if df["ValorTotal"].sum() > 0
            else 0
        )
        st.markdown(
            f"""
        <div class="metric-container">
            <div class="metric-label">Ingresos Campeones</div>
            <div class="metric-val">{pct_champs:.1f}%</div>
            <div class="metric-sub">Concentración de Facturación</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # ==============================================================================
    # 6. VISUALIZACIÓN ANALÍTICA TIPO CRM
    # ==============================================================================
    tab_overview, tab_matrix, tab_exports, tab_playbooks = st.tabs([
        "📊 Distribución de Segmentos",
        "🎯 Matriz 2D (R vs FM)",
        "📥 Descargas Excel por Segmento",
        "🚀 Playbooks de Campañas",
    ])

    with tab_overview:
        c_left, c_right = st.columns([1, 1])

        # Agrupación de métricas por segmento
        seg_summary = (
            df.groupby("Segmento")
            .agg(
                Clientes=("ClienteID", "count"),
                Ingresos=("ValorTotal", "sum"),
                ComprasPromedio=("Compras", "mean"),
                RecenciaPromedio=("Recencia_Dias", "mean"),
            )
            .reset_index()
        )

        color_map = {k: v["color"] for k, v in PLAYBOOKS.items()}

        with c_left:
            fig_pie = px.pie(
                seg_summary,
                values="Clientes",
                names="Segmento",
                title="<b>Volumen de Clientes por Segmento</b>",
                color="Segmento",
                color_discrete_map=color_map,
                hole=0.45,
            )
            fig_pie.update_traces(
                textposition="inside", textinfo="percent+label"
            )
            fig_pie.update_layout(
                margin=dict(t=40, b=0, l=0, r=0), height=380, showlegend=False
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_right:
            fig_bar = px.bar(
                seg_summary,
                x="Segmento",
                y="Ingresos",
                color="Segmento",
                color_discrete_map=color_map,
                title="<b>Aporte en Facturación por Segmento ($)</b>",
                text_auto=".2s",
            )
            fig_bar.update_layout(
                margin=dict(t=40, b=0, l=0, r=0),
                height=380,
                showlegend=False,
                xaxis_title="",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("📋 Resumen Ejecutivo de Rendimiento")
        st.dataframe(
            seg_summary.style.format({
                "Clientes": "{:,.0f}",
                "Ingresos": "${:,.0f}",
                "ComprasPromedio": "{:,.1f}",
                "RecenciaPromedio": "{:,.0f} días",
            }),
            use_container_width=True,
        )

    with tab_matrix:
        st.markdown(
            "#### Matriz de Comportamiento: Recencia vs. Frecuencia/Monetario"
        )
        st.caption(
            "Cada punto representa un cliente. Permite identificar clústeres desaprovechados y clientes en fuga."
        )

        fig_scatter = px.scatter(
            df,
            x="Recencia_Dias",
            y="ValorTotal",
            size="Compras",
            color="Segmento",
            color_discrete_map=color_map,
            hover_name="Nombre",
            hover_data=["Ciudad", "Tipo", "Categoria", "Canal", "RFM_Cell"],
            log_y=True,
            title="Distribución Scatter: Días sin compra vs. Valor Total Facturado (Escala Log)",
        )
        fig_scatter.update_layout(height=480, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_scatter, use_container_width=True)

    with tab_exports:
        st.subheader("📥 Exportación Segmentada para Plataformas de Pauta y CRM")
        st.markdown(
            "Descarga el archivo Excel individual listo para subir a listas de **Mailchimp/Klaviyo, audiencias personalizadas de Meta Ads o secuencias de WhatsApp Business**."
        )

        cols_download = st.columns(3)
        segmentos_disponibles = list(PLAYBOOKS.keys())

        for idx, seg_name in enumerate(segmentos_disponibles):
            df_seg = df[df["Segmento"] == seg_name]
            col_idx = idx % 3
            with cols_download[col_idx]:
                st.markdown(f"**{seg_name}** (`{len(df_seg)} clientes`)")
                excel_bytes = to_excel_download(df_seg)
                st.download_button(
                    label=f"⬇️ Descargar {seg_name}.xlsx",
                    data=excel_bytes,
                    file_name=f"ANDINA_RFM_{seg_name.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"btn_{seg_name}",
                )
                st.markdown("<br>", unsafe_allow_html=True)

        st.divider()
        st.markdown("##### Exportar Base Completa con Scores RFM")
        excel_all = to_excel_download(df)
        st.download_button(
            label="⬇️ Descargar Base Completa con Scores y Segmentación (.xlsx)",
            data=excel_all,
            file_name="ANDINA_RFM_Base_Total.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_all",
        )

    with tab_playbooks:
        st.subheader("🚀 Estrategias de Activación Digital por Segmento")
        for seg_name, pbook in PLAYBOOKS.items():
            cant = len(df[df["Segmento"] == seg_name])
            fact = df[df["Segmento"] == seg_name]["ValorTotal"].sum()

            st.markdown(
                f"""
            <div class="playbook-card" style="border-left-color: {pbook['color']};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h4 style="margin:0; color:{pbook['color']};">{seg_name} ({cant} Clientes - ${fact:,.0f})</h4>
                </div>
                <p style="margin: 6px 0; color: #475569; font-size: 0.9rem;">{pbook['desc']}</p>
                <div style="margin-top: 8px;">
                    <strong>Canales Recomendados:</strong><br>
                    {''.join([f'<span class="channel-badge">{c}</span>' for c in pbook['canales']])}
                </div>
                <div style="margin-top: 10px; font-size: 0.88rem; color: #1E293B;">
                    <strong>🎯 Acción Táctica de Marketing:</strong> {pbook['accion']}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

else:
    st.info("👋 Sube un archivo CSV en el panel lateral para iniciar el análisis.")
