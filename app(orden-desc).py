import streamlit as st
import pandas as pd

# ---------- Configuración ----------
st.set_page_config(page_title="Guía Logística Ripley – Orden de Recomendación", page_icon="🚚", layout="centered")
PRIMARY = "#E6007E"; BLACK = "#000000"

st.markdown(
    f"""
    <style>
    .main .block-container {{ padding-top: 2rem; padding-bottom: 3rem; }}
    .ripley-title {{ font-weight: 800; font-size: 1.8rem; color: {BLACK}; margin-bottom: 0.2rem; }}
    .ripley-sub {{ color: #555; margin-bottom: 1.2rem; }}
    .badge {{ border: 1px solid {PRIMARY}; color: {PRIMARY}; padding: 0.2rem 0.5rem; border-radius: 8px; font-size: 0.8rem; }}
    .section-title {{ margin-top: 1.2rem; font-size: 1.1rem; font-weight: 700; }}
    .ordinal {{ font-weight: 800; color: {PRIMARY}; margin-right: .35rem; }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Datos ----------
FIRST_MILE = {
    "SP": {"lt_24990": 1000, "ge_24990": 2690},
    "P1": {"flat": 4590},
    "P2": {"flat": 6690},
    "P3": {"flat": 7790},
    "M": {"flat": 8790},
    "G": {"flat": 12990},
    "SG": {"flat": 21490},
}
REVERSE = {
    "SP": 2800, "P1": 2800, "P2": 6000, "P3": 11000,
    "M": 20000, "G": 23900, "SG": 23900
}
CLASSES_INFO = {
    "SP": "Super Pequeño (ej: smartphone)",
    "P1": "Pequeño 1 (ej: bici infantil)",
    "P2": "Pequeño 2 (ej: silla de escritorio)",
    "P3": "Pequeño 3 (ej: set de 4 neumáticos)",
    "M": "Mediano (ej: congeladora)",
    "G": "Grande (ej: living)",
    "SG": "Súper Grande (ej: sofá seccional)",
}
MODALITY_EXPLAIN = {
    "Operador Logístico": "El seller maneja su stock y paga la primera milla. El cliente paga el despacho final.",
    "Crossdock": "Ripley retira en la bodega del seller. Cliente paga despacho final o $0 si retiro en tienda.",
    "Fulfillment": "Ripley almacena y opera inventario (cofinanciado). Cliente paga despacho final.",
    "Flota Propia": "Transporte especializado/aliado (p. ej. Envíame) para cargas voluminosas o rutas especiales.",
}
BENEFICIOS = {
    "Operador Logístico": [
        "Control total del inventario en tu bodega.",
        "Pagas primera milla por OC y mantienes flexibilidad.",
        "Ideal para productos pequeños/medianos y rotación moderada."
    ],
    "Crossdock": [
        "Ripley retira en tu bodega: menos fricción operacional.",
        "Puedes ofrecer retiro en tienda (cliente sin costo de despacho).",
        "Útil para órdenes grandes o productos voluminosos."
    ],
    "Fulfillment": [
        "Mayor conversión por velocidad de despacho.",
        "Ripley opera almacenamiento, picking y packing.",
        "Recomendado para alta rotación o si no tienes bodega."
    ],
    "Flota Propia": [
        "Mejor manejo de cargas muy voluminosas o especiales.",
        "Coordinación directa con operador de transporte aliado.",
        "Útil cuando necesitas ventanas horarias o manipulación específica."
    ],
}

# ---------- Utilidades de costos ----------
def calcular_primera_milla(clase: str, precio: float, modalidad: str):
    if modalidad == "Fulfillment":
        return 0, "No aplica (stock en CD Ripley)."
    if modalidad == "Flota Propia":
        return None, "Caso a caso (tarifa acordada con operador aliado)."
    if clase == "SP":
        if precio < 24990:
            return FIRST_MILE["SP"]["lt_24990"], "SP < $24.990"
        else:
            return FIRST_MILE["SP"]["ge_24990"], "SP ≥ $24.990"
    return FIRST_MILE[clase]["flat"], f"{clase} tarifa fija"

def tabla_costos_modalidad(modalidad: str, clase: str, precio: float):
    pm_val, pm_nota = calcular_primera_milla(clase, precio, modalidad)
    rev_val = REVERSE[clase]
    pm_str = "Variable (caso a caso)" if pm_val is None else ("$0" if pm_val == 0 else f"${pm_val:,.0f}".replace(",", "."))
    return pd.DataFrame({
        "Concepto": ["Primera milla", "Logística inversa", "Cliente: despacho final"],
        "Detalle": [pm_nota, f"{clase} ({CLASSES_INFO[clase]})", "Matriz estándar por zona/tamaño/promos"],
        "Costo estimado": [pm_str, f"${rev_val:,.0f}".replace(",", "."), "Variable (misma lógica en todas las modalidades)"]
    })

# ---------- Heurística para ORDEN (no mostramos puntajes) ----------
def ordenar_modalidades(tiene_bodega: bool, voluminoso: bool, alta_rot: bool):
    # Partimos de una lista base
    mods = ["Operador Logístico", "Crossdock", "Fulfillment", "Flota Propia"]
    # Reglas simples y transparentes para posicionar:
    orden = []
    # 1) Sin bodega -> Fulfillment primero
    if not tiene_bodega:
        orden.append("Fulfillment")
    # 2) Con bodega y voluminoso -> Crossdock primero
    if tiene_bodega and voluminoso:
        orden.append("Crossdock")
    # 3) Con bodega y no voluminoso -> Operador Logístico primero
    if tiene_bodega and not voluminoso:
        orden.append("Operador Logístico")
    # 4) Alta rotación empuja Fulfillment hacia arriba si no está primero
    if alta_rot and "Fulfillment" not in orden:
        orden.append("Fulfillment")
    # 5) Flota Propia usualmente al final, salvo muy voluminoso (ya se prioriza Crossdock)
    if "Flota Propia" not in orden:
        orden.append("Flota Propia")
    # Completar con las que falten respetando el orden base
    for m in mods:
        if m not in orden:
            orden.append(m)
    # Devolver sin duplicados manteniendo el orden
    seen = set(); result = []
    for m in orden:
        if m not in seen:
            result.append(m); seen.add(m)
    # Asegurar 4 elementos
    return result[:4]

# ---------- UI ----------
st.markdown('<div class="ripley-title">Guía Logística Ripley – Orden de Recomendación</div>', unsafe_allow_html=True)
st.markdown('<div class="ripley-sub">Mostramos todas las opciones (Primero → Cuarto) según tu caso. Luego revisa costos y beneficios para decidir.</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    bodega = st.radio("¿Tienes bodega propia?", ["Sí", "No"], index=0, horizontal=True)
    voluminoso = st.radio("¿Tus productos son grandes/voluminosos?", ["Sí", "No"], index=1, horizontal=True)
with col2:
    rotacion = st.radio("¿Alta rotación y necesitas entregas rápidas?", ["Sí", "No"], index=0, horizontal=True)
    clase = st.selectbox(
        "Selecciona la clase logística más alta de tu orden",
        list(CLASSES_INFO.keys()),
        format_func=lambda k: f"{k} – {CLASSES_INFO[k]}",
        index=2
    )

precio = st.number_input("Precio referencial del producto (CLP)", min_value=0, value=29990, step=1000)

if st.button("Mostrar opciones en orden"):
    tiene_bodega = (bodega == "Sí")
    es_voluminoso = (voluminoso == "Sí")
    alta_rot = (rotacion == "Sí")

    orden = ordenar_modalidades(tiene_bodega, es_voluminoso, alta_rot)
    ordinales = ["Primero", "Segundo", "Tercero", "Cuarto"]

    st.markdown("---")
    st.subheader("📋 Orden recomendado (según tus respuestas)")

    for idx, modalidad in enumerate(orden):
        st.markdown(f"### <span class='ordinal'>{ordinales[idx]}:</span> {modalidad}", unsafe_allow_html=True)
        st.write(MODALITY_EXPLAIN[modalidad])
        st.markdown("<div class='section-title'>Costos estimados</div>", unsafe_allow_html=True)
        st.dataframe(tabla_costos_modalidad(modalidad, clase, float(precio)), use_container_width=True)
        st.markdown("<div class='section-title'>Beneficios clave</div>", unsafe_allow_html=True)
        for b in BENEFICIOS[modalidad]:
            st.write(f"• {b}")
        st.markdown("---")

st.caption("Nota: El costo para el cliente (despacho final) se calcula con la matriz estándar por zona y tamaño. Es el mismo cálculo en todas las modalidades.")
