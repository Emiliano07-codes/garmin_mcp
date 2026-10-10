# Design System: Garmin Performance Lab (Pro Telemetry & Physiology)

## 1. Visual Theme & Atmosphere
- **Atmosphere:** Instrumentación biomédica de grado olímpico y telemetría de resistencia (estilo Coros Training Hub, Whoop 4.0 y TrainingPeaks).
- **Density:** Cockpit Dense (8/10) — visualización de alta densidad sin saturación ni ruido.
- **Variance:** Offset Asymmetric (6/10) — jerarquía visual clara: cockpit superior, navegación lateral fija, hero telemetría y gráficos analíticos.
- **Motion:** Fluid Micro-Physics (6/10) — transiciones suaves de 150-200ms (`cubic-bezier(0.16, 1, 0.3, 1)`), crosshairs sincronizados con aceleración de hardware.

## 2. Color Palette & Roles
- **Obsidian Core** (`#07090e`) — Fondo base principal (canvas).
- **Carbon Surface** (`#0e131f`) — Fondo de tarjetas, paneles y contenedores.
- **Carbon Elevated** (`#161d2e`) — Superficies elevadas, hover y badges secundarios.
- **Structural Border** (`rgba(255, 255, 255, 0.07)`) — Líneas divisorias estructurales de 1px.
- **Text Crisp** (`#f8fafc`) — Tipografía principal, títulos y números clave.
- **Text Muted** (`#94a3b8`) — Tipografía secundaria, unidades, etiquetas y leyendas.
- **Aerobic Cyan** (`#38bdf8`) — VO₂ Máx, potencia aeróbica y acento principal.
- **Mitochondrial Emerald** (`#10b981`) — Zona 2, estado Productivo y recuperación lograda.
- **Lactate Amber** (`#f59e0b`) — Zona umbral, ACWR elevado y fatiga.
- **Anaerobic Rose** (`#f43f5e`) — Alta intensidad anaeróbica y alertas de sobreesfuerzo.
- **Autonomic Violet** (`#a855f7`) — VFC, tono vagal parasimpático y fuerza.

## 3. Typography Rules
- **Display & Titles:** `Plus Jakarta Sans` / `Outfit` — weight 600-800, tracking -0.02em, escala controlada.
- **Body & Labels:** `Plus Jakarta Sans` — weight 400-500, leading 1.5.
- **Data & Telemetry Numbers:** `JetBrains Mono` / `Geist Mono` — tabular numbers (`font-variant-numeric: tabular-nums;`) para métricas, ritmos, frecuencias y tiempos.
- **Banned:** `Inter` en contextos genéricos, fuentes serif en interfaces de telemetría deportiva.

## 4. Component Stylings
- **Cockpit KPI Row:** 7 tarjetas en una sola línea continua, altura uniforme (98px), radio sutil (8px), borde izquierdo de acento (3px), tipografía tabular mono.
- **Sidebar Navigation:** Menú lateral fijo de ancho 250px, botones con padding táctil (10px 14px), estado activo con degradé sutil y borde izquierdo brillante.
- **Interactive Strava Volume Card:** Curva continua con relleno degradé vertical, nodos destacados en la semana seleccionada, selector de ventana de 12 semanas y controles temporales.
- **Telemetry Cards:** Desglose de zonas en barra segmentada continua (Z1 a Z5) con porcentajes y minutos exactos.
- **Firstbeat Load Balance:** Túneles óptimos con barra de progreso que indica si el entrenamiento está dentro, por debajo o por encima del target.
- **Modals:** Ventanas modales centradas con backdrop blur (`rgba(7, 9, 14, 0.85)`), semáforos de escala fisiológica continuos y gráficos históricos.

## 5. Layout Principles
- **Arquitectura de dos columnas:** Menú lateral fijo a la izquierda (250px) y canvas principal fluido a la derecha con ancho máximo de 1440px.
- **Grid auto-adaptativo:** Cockpit superior horizontal con scroll silencioso si la pantalla es menor a 1280px.
- **Espaciado rítmico:** Módulos de 8px (gaps de 12px, 16px, 20px).

## 6. Motion & Interaction
- Crosshair vertical en todos los gráficos temporales interactivos.
- Hover states con elevación sutil (`translateY(-2px)`) y realce de borde.
- Transición instantánea entre pestañas con recálculo automático del render de Chart.js (`resize`).

## 7. Anti-Patterns (Banned)
- Prohibido el uso de degradés de neón fucsia/violeta genéricos.
- Prohibido mezclar pasos diarios con el análisis de sueño.
- Prohibido el amontonamiento de textos o tarjetas desalineadas.
- Prohibido el formato de fecha anglosajón (siempre `DD/MM/AAAA`).
