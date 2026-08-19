import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import io
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y ESTILOS CRM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CRM & Funnel RFM Classifier | Marketing Director Suite",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 18px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        text-align: center;
    }
    .metric-value { font-size: 26px; font-weight: 700; color: #1e293b; }
    .metric-label { font-size: 13px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
    .strategy-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #2563eb;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
</style>
""", unsafe_allowed_html=True)

# -----------------------------------------------------------------------------
# LÓGICA DE METODOLOGÍA RFM
# -----------------------------------------------------------------------------
def process_rfm(df, reference_date=None):
    df = df.copy()
    df['UltimaCompra'] = pd.to_datetime(df['UltimaCompra'], errors='coerce')
    df['Compras'] = pd.to_numeric(df['Compras'], errors='coerce').fillna(1)
    df['ValorTotal'] = pd.to_numeric(df['ValorTotal'], errors='coerce').fillna(0)
    
    if reference_date is None:
        reference_date = df['UltimaCompra'].max() + dt.timedelta(days=1)
    else:
        reference_date = pd.to_datetime(reference_date)
        
    df['Recency_Days'] = (reference_date - df['UltimaCompra']).dt.days
    
    # Cálculo de Quintiles 1 a 5
    try:
        df['R_Score'] = pd.qcut(df['Recency_Days'], q=5, labels=[5, 4, 3, 2, 1], duplicates='drop').astype(int)
    except Exception:
        df['R_Score'] = pd.cut(df['Recency_Days'], bins=5, labels=[5, 4, 3, 2, 1]).astype(int)

    try:
        df['F_Score'] = pd.qcut(df['Compras'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    except Exception:
        df['F_Score'] = pd.cut(df['Compras'], bins=5, labels=[1, 2, 3, 4, 5]).astype(int)

    try:
        df['M_Score'] = pd.qcut(df['ValorTotal'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    except Exception:
        df['M_Score'] = pd.cut(df['ValorTotal'], bins=5, labels=[1, 2, 3, 4, 5]).astype(int)

    df['RFM_Score'] = df['R_Score'].astype(str) + df['F_Score'].astype(str) + df['M_Score'].astype(str)
    
    # Mapeo Estratégico de Segmentos
    def segment_mapping(row):
        r, f, m = row['R_Score'], row['F_Score'], row['M_Score']
        if r >= 4 and f >= 4 and m >= 4:
            return 'Campeones (VIP)'
        elif r >= 3 and f >= 3 and m >= 3:
            return 'Leales y Frecuentes'
        elif r >= 4 and f <= 2:
            return 'Nuevos Prometedores'
        elif r == 3 and f <= 2:
            return 'En Desarrollo / Necesitan Atención'
        elif r <= 2 and f >= 4 and m >= 4:
            return 'En Riesgo Alto (VIPs Aislados)'
        elif r <= 2 and f >= 3:
            return 'No Los Podemos Perder'
        elif r <= 2 and f <= 2 and m >= 4:
            return 'Alto Valor Dormidos'
        elif r == 2 and f <= 2:
            return 'A Punto de Dormir'
        elif r == 1 and f <= 2 and m <= 2:
            return 'Perdidos / Inactivos'
        else:
            return 'En Transición / Otros'

    df['Segmento_RFM'] = df.apply(segment_mapping, axis=1)
    return df

STRATEGY_MAP = {
    'Campeones (VIP)': {
        'objetivo': 'Fidelización avanzada, Advocacy y Cross-Selling VIP de Equipos/Consultoría.',
        'canal_principal': 'WhatsApp Directo (Asesor VIP) + Email Personalizado',
        'accion': 'Enviar primicias de catálogo, invitaciones a demos exclusivas y diagnósticos técnicos prioritarios sin costo.'
    },
    'Leales y Frecuentes': {
        'objetivo': 'Aumentar el Ticket Promedio (Up-selling) y recurrencia de consumibles.',
        'canal_principal': 'Email Marketing + WhatsApp Automatizado',
        'accion': 'Planes de suscripción periódica de consumibles y mantenimientos preventivos programados con descuento.'
    },
    'Nuevos Prometedores': {
        'objetivo': 'Onboarding exitoso y aceleración del segundo pedido.',
        'canal_principal': 'Email Onboarding Sequence + SMS',
        'accion': 'Secuencia educativa sobre uso de equipos adquiridos y bono de bienvenida para repuestos/mantenimiento.'
    },
    'En Riesgo Alto (VIPs Aislados)': {
        'objetivo': 'Reactivación urgente de clientes de gran volumen histórico.',
        'canal_principal': 'WhatsApp Directo (Llamada de Director Comercial)',
        'accion': 'Auditoría de satisfacción personalizada, revisión de estado de equipos y ofertas de retención exclusivas.'
    },
    'Perdidos / Inactivos': {
        'objetivo': 'Campaña masiva de bajo costo o depuración de base de datos.',
        'canal_principal': 'Pauta Digital (Custom Audience Meta/Google) + Email Masivo',
        'accion': 'Campaña agresiva de liquidación de insumos o depuración para optimizar ROI de CRM.'
    }
}

def to_excel_single(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Clientes_RFM')
    return output.getvalue()

def to_excel_multi_segments(df_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for name, data in df_dict.items():
            clean_name = name[:30].replace('/', '-').replace('\\', '-')
            data.to_excel(writer, index=False, sheet_name=clean_name)
    return output.getvalue()

# -----------------------------------------------------------------------------
# INTERFAZ LATERAL (BARRA DE CONTROL)
# -----------------------------------------------------------------------------
st.sidebar.title("CRM RFM Classifier")
st.sidebar.caption("Director de Marketing & Funnel Suite")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("Sube tu archivo CSV de clientes", type=["csv"])
use_sample = st.sidebar.checkbox("Usar datos de demostración", value=(uploaded_file is None))

if uploaded_file is not None:
    raw_df = pd.read_csv(uploaded_file)
elif use_sample:
    # Simulación de datos B2B / B2C
    np.random.seed(42)
    n = 200
    dates = [dt.date(2025,1,1) + dt.timedelta(days=int(np.random.randint(0, 500))) for _ in range(n)]
    raw_df = pd.DataFrame({
        'ClienteID': [f'CLI-{1000+i}' for i in range(n)],
        'Nombre': [f'Cliente {i+1}' for i in range(n)],
        'Tipo': np.random.choice(['Empresa', 'Persona'], n, p=[0.6, 0.4]),
        'Ciudad': np.random.choice(['Medellín', 'Bogotá', 'Cali', 'Barranquilla', 'Bucaramanga', 'Pereira', 'Manizales', 'Cartagena'], n),
        'UltimaCompra': [d.strftime('%Y-%m-%d') for d in dates],
        'Compras': np.random.geometric(p=0.25, size=n),
        'ValorTotal': np.round(np.random.exponential(scale=3500000, size=n) + 150000, -3),
        'Categoria': np.random.choice(['Equipos', 'Mantenimiento', 'Consumibles', 'Consultoría'], n),
        'Canal': np.random.choice(['WhatsApp', 'Email', 'SMS', 'Pauta Digital', 'Directo'], n)
    })

rfm_df = process_rfm(raw_df)

# Filtros
selected_types = st.sidebar.multiselect("Tipo de Cliente", options=rfm_df['Tipo'].unique(), default=rfm_df['Tipo'].unique())
selected_cities = st.sidebar.multiselect("Ciudad", options=rfm_df['Ciudad'].unique(), default=rfm_df['Ciudad'].unique())

filtered_df = rfm_df[(rfm_df['Tipo'].isin(selected_types)) & (rfm_df['Ciudad'].isin(selected_cities))]

# -----------------------------------------------------------------------------
# DASHBOARD PRINCIPAL
# -----------------------------------------------------------------------------
st.title("🎯 Clasificador RFM & Panel de Estrategia CRM")
st.markdown("Automatización de clasificación de clientes e integración con campañas de WhatsApp, SMS, Email y Pauta Digital.")

# KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Clientes", f"{len(filtered_df):,}")
k2.metric("Facturación Total", f"${filtered_df['ValorTotal'].sum()/1e6:,.1f}M")
k3.metric("Ticket Promedio", f"${filtered_df['ValorTotal'].mean():,.0f}")
k4.metric("Clientes VIP", f"{len(filtered_df[filtered_df['Segmento_RFM']=='Campeones (VIP)'])}")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📈 Distribución y Gráficos", "📋 Playbook CRM", "📥 Descargas Excel"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        fig_bar = px.bar(filtered_df['Segmento_RFM'].value_counts().reset_index(), x='count', y='Segmento_RFM', orientation='h', title="Clientes por Segmento RFM")
        st.plotly_chart(fig_bar, use_container_width=True)
    with c2:
        fig_pie = px.pie(filtered_df, names='Segmento_RFM', values='ValorTotal', title="Participación en Facturación ($)")
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("Plan de Acción Táctico por Segmento")
    seg_choice = st.selectbox("Selecciona un Segmento:", list(STRATEGY_MAP.keys()))
    info = STRATEGY_MAP.get(seg_choice, {'objetivo': 'General', 'canal_principal': 'Email', 'accion': 'Mantener contacto.'})
    st.info(f"**Objetivo:** {info['objetivo']}\n\n**Canal Principal:** {info['canal_principal']}\n\n**Acción Comercial:** {info['accion']}")
    st.dataframe(filtered_df[filtered_df['Segmento_RFM'] == seg_choice], use_container_width=True)

with tab3:
    st.subheader("Descarga de Datos Segmentados")
    excel_multi = to_excel_multi_segments({seg: filtered_df[filtered_df['Segmento_RFM'] == seg] for seg in filtered_df['Segmento_RFM'].unique()})
    st.download_button(
        label="📚 Descargar Excel Multipestaña (Todos los Segmentos)",
        data=excel_multi,
        file_name="Segmentos_RFM_Clientes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
