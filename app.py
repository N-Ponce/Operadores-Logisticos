import streamlit as st
import pandas as pd

st.set_page_config(page_title='Guía Logística Ripley – Recomendador', page_icon='🚚', layout='centered')

PRIMARY = '#E6007E'
BLACK = '#000000'
WHITE = '#FFFFFF'

st.markdown(
    '<style>'+
    '.main .block-container { padding-top: 2rem; padding-bottom: 3rem; }'+
    '.ripley-title { font-weight: 800; font-size: 1.8rem; color: '+BLACK+'; margin-bottom: 0.2rem; }'+
    '.ripley-sub { color: #555; margin-bottom: 1.2rem; }'+
    '.pill { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 999px; background: '+PRIMARY+'15; color: '+PRIMARY+'; font-weight: 600; font-size: 0.85rem; margin-right: 0.4rem; }'+
    '.badge { border: 1px solid '+PRIMARY+'; color: '+PRIMARY+'; padding: 0.2rem 0.5rem; border-radius: 8px; font-size: 0.8rem; }'+
    '.section-title { margin-top: 1.2rem; font-size: 1.1rem; font-weight: 700; }'+
    '.ok { color: #0E8A16; font-weight: 700; }'+
    '.warn { color: #B00020; font-weight: 700; }'+
    '.muted { color: #666; }'+
    '</style>',
    unsafe_allow_html=True
)

# Data
FIRST_MILE = {
    'SP': {'lt_24990': 1000, 'ge_24990': 2690},
    'P1': {'flat': 4590},
    'P2': {'flat': 6690},
    'P3': {'flat': 7790},
    'M': {'flat': 8790},
    'G': {'flat': 12990},
    'SG': {'flat': 21490},
}

REVERSE = {
    'SP': 2800, 'P1': 2800, 'P2': 6000, 'P3': 11000, 'M': 20000, 'G': 23900, 'SG': 23900
}

CLASSES_INFO = {
    'SP': 'Super Pequeño (ej: smartphone)',
    'P1': 'Pequeño 1 (ej: bici infantil)',
    'P2': 'Pequeño 2 (ej: silla de escritorio)',
    'P3': 'Pequeño 3 (ej: set de 4 neumáticos)',
    'M': 'Mediano (ej: congeladora)',
    'G': 'Grande (ej: living)',
    'SG': 'Súper Grande (ej: sofá seccional)',
}

MODALITY_EXPLAIN = {
    'Operador Logístico': 'El seller maneja su stock y paga la primera milla. El cliente paga el despacho final.',
    'Crossdock': 'Ripley retira en la bodega del seller. El cliente paga el despacho final o $0 si retiro en tienda.',
    'Fulfillment': 'Ripley almacena y opera el inventario del seller (cofinanciado). El cliente paga el despacho final.',
}

def recomendar_modalidad(tiene_bodega: bool, voluminoso: bool, alta_rotacion: bool):
    if not tiene_bodega:
        return 'Fulfillment', 'Sin bodega propia: delega almacenamiento y despacho en Ripley.'
    if voluminoso:
        return 'Crossdock', 'Productos grandes/voluminosos: Ripley retira en tu bodega y puedes ofrecer retiro en tienda.'
    if alta_rotacion:
        return 'Fulfillment', 'Alta rotación: centraliza inventario en CD Ripley para despachos más rápidos.'
    return 'Operador Logístico', 'Tienes bodega y productos pequeños/medianos con rotación moderada: mantén control y paga solo primera milla.'

def calcular_primera_milla(clase: str, precio: float, modalidad: str):
    # Primera milla aplica en Operador Logístico y Crossdock (por orden de compra; se cobra el valor de la clase más alta).
    if modalidad == 'Fulfillment':
        return 0, 'No aplica (stock en CD Ripley).'
    if clase == 'SP':
        if precio < 24990:
            return FIRST_MILE['SP']['lt_24990'], 'SP < $24.990'
        else:
            return FIRST_MILE['SP']['ge_24990'], 'SP ≥ $24.990'
    else:
        return FIRST_MILE[clase]['flat'], f'{clase} tarifa fija'

def tabla_costos_modalidad(modalidad: str, clase: str, precio: float):
    pm_val, pm_nota = calcular_primera_milla(clase, precio, modalidad)
    rev_val = REVERSE[clase]
    data = {
        'Concepto': ['Primera milla', 'Logística inversa', 'Cliente: despacho final'],
        'Detalle': [pm_nota, f"{clase} ({CLASSES_INFO[clase]})", 'Matriz estándar por zona/tamaño/promos'],
        'Costo estimado': [
            '$0' if pm_val == 0 else f'${pm_val:,.0f}'.replace(',', '.'),
            f'${rev_val:,.0f}'.replace(',', '.'),
            'Variable (mismo cálculo en todas las modalidades)',
        ],
    }
    return pd.DataFrame(data)

st.markdown('<div class="ripley-title">Guía Logística Ripley – Recomendador para Sellers</div>', unsafe_allow_html=True)
st.markdown('<div class="ripley-sub">Responde 3 preguntas y obtén la modalidad recomendada, con costos clave para tu caso.</div>', unsafe_allow_html=True)

with st.expander('Cómo funciona', expanded=False):
    st.write('- Evaluamos **bodega propia**, **volumen del producto** y **rotación**.')
    st.write('- Mostramos **modalidad recomendada**, explicación y **costos** (primera milla, logística inversa, y nota sobre costo al cliente).')
    st.write('- La **primera milla** se cobra **por orden de compra**, aplicando el valor de la **clase logística más alta** dentro de la orden.')

col1, col2 = st.columns(2)
with col1:
    bodega = st.radio('¿Tienes bodega propia?', ['Sí', 'No'], index=0, horizontal=True)
    voluminoso = st.radio('¿Tus productos son grandes/voluminosos?', ['Sí', 'No'], index=1, horizontal=True)
with col2:
    rotacion = st.radio('¿Alta rotación y necesitas entregas rápidas?', ['Sí', 'No'], index=0, horizontal=True)
    clase = st.selectbox(
        'Selecciona la clase logística más alta de tu orden',
        list(CLASSES_INFO.keys()),
        format_func=lambda k: f"{k} – {CLASSES_INFO[k]}",
        index=2
    )

precio = st.number_input('Precio referencial del producto (CLP)', min_value=0, value=29990, step=1000)

if st.button('Ver recomendación'):
    tiene_bodega = (bodega == 'Sí')
    es_voluminoso = (voluminoso == 'Sí')
    alta_rot = (rotacion == 'Sí')

    modalidad, motivo = recomendar_modalidad(tiene_bodega, es_voluminoso, alta_rot)

    st.markdown('---')
    st.subheader(f'📦 Modalidad recomendada: **{modalidad}**')
    st.write(MODALITY_EXPLAIN[modalidad])
    st.markdown(f"<span class='badge'>Motivo</span> {motivo}", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>Costos para tu caso</div>", unsafe_allow_html=True)
    df = tabla_costos_modalidad(modalidad, clase, float(precio))
    st.dataframe(df, use_container_width=True)

    st.markdown("<div class='section-title'>Beneficios clave</div>", unsafe_allow_html=True)
    if modalidad == 'Operador Logístico':
        st.write('• Control total del inventario en tu bodega.\n• Pagas primera milla por OC y mantienes flexibilidad.\n• Ideal para productos pequeños/medianos y rotación moderada.')
    elif modalidad == 'Crossdock':
        st.write('• Ripley retira en tu bodega: menos fricción operacional.\n• Puedes ofrecer retiro en tienda (cliente sin costo de despacho).\n• Útil para órdenes grandes o productos voluminosos.')
    else:
        st.write('• Mayor conversión por velocidad de despacho.\n• Ripley opera almacenamiento, picking y packing.\n• Recomendado para alta rotación o si no tienes bodega.')

    with st.expander('Ver todas las modalidades'):
        comp = pd.DataFrame([
            {
                'Modalidad': 'Operador Logístico',
                'Quién paga qué': 'Seller paga primera milla; cliente paga despacho final; inversa por clase.',
                'Cuándo usarla': 'Pequeño/mediano + bodega propia.',
                'Valor': 'Control de stock y flexibilidad.'
            },
            {
                'Modalidad': 'Crossdock',
                'Quién paga qué': 'Seller paga primera milla; cliente despacho final o $0 si retiro en tienda; inversa por clase.',
                'Cuándo usarla': 'Órdenes grandes o voluminoso; retiro en bodega del seller.',
                'Valor': 'Menos tiempos de espera; opción retiro en tienda.'
            },
            {
                'Modalidad': 'Fulfillment',
                'Quién paga qué': 'Seller cofinancia operación en CD; cliente despacho final; inversa por clase.',
                'Cuándo usarla': 'Alta rotación o sin bodega.',
                'Valor': 'Mejor SLA, conversión y NPS.'
            },
        ])
        st.dataframe(comp, use_container_width=True)

st.markdown('---')
st.caption('Nota: El costo para el cliente (despacho final) se calcula con la matriz estándar por zona y tamaño. Es el mismo cálculo en todas las modalidades.')