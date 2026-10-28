# Skill: Generación de Gráficos de Evidencia Técnica

Este Skill define las especificaciones estéticas, técnicas y de formato para las visualizaciones analíticas que sirven como pruebas forenses en los informes.

## 1. Configuración de Entorno e Renderizado
*   **Backend Headless:** Para evitar bloqueos o excepciones en entornos sin servidor o scripts de consola, usar el backend de no interfaz de matplotlib: `matplotlib.use("Agg")`.
*   **Estilo Visual:** Utilizar el tema de Seaborn `whitegrid` con la paleta de colores `muted` para una apariencia corporativa y clara.
*   **Resolución y Calidad:** Todos los gráficos deben ser guardados a una resolución mínima de **150 DPI** para garantizar legibilidad al ser impresos o incrustados en Word.

## 2. Gráficos Obligatorios (Siempre se Generan)
*   **G1 (Evolución de Volumen Diario - `consumo_diario.png`):** Gráfico de línea temporal (`plt.plot`) con marcadores que ilustran la tendencia general del volumen de consultas por día, debe incluir ina linea roja descontinuada que represente el promedio de volumen de consultas por día.
*   **G2 (Distribución por Hora - `consumo_por_hora.png`):** Histograma/Gráfico de barras (`sns.barplot`) de 24 columnas (0-23) para identificar la concentración de consultas en diferentes horas del día.
*   **G3 (Actividad por Día de la Semana - `consumo_dia_semana.png`):** Gráfico de barras ordenado de Lunes a Domingo para identificar si hay continuidad de operaciones los fines de semana.

## 3. Gráficos Condicionales (Según Reporte de Anomalías)
*   **G4 (Top 10 Usuarios - `distribucion_usuario.png`):** Generado si el conjunto de datos cuenta con más de 1 usuario único. Es un gráfico de barras horizontales (`sns.barplot` con `orient='h'`).
*   **G5 (Ráfagas por Hora - `rafagas_por_hora.png`):** Generado si se detectaron bursts. Gráfico de barras de 24 horas que muestra a qué horas del día ocurren las ráfagas rápidas de consultas.
*   **G6 (Dispersión de Volumen Horario Inusual - `scatter_volumen_tiempo.png`):** Generado si hay eventos de volumen por hora inusual. Gráfico de dispersión (`plt.scatter`) temporal indicando la media del volumen inusual detectado.
*   **G7 (Distribución de Frecuencia de DNIs Repetidos - `histograma_dni.png`):** Generado si hay DNIs repetidos por encima del umbral. Muestra una curva KDE de distribución de frecuencia de DNIs consultados reiteradas veces.
*   **G8 (Top 10 DNIs Más Consultados - `tabla_top10_dni.png`):** Generado si hay DNIs repetidos. Gráfico de barras horizontales de color rojo (`palette="Reds_r"`) con los 10 identificadores más consultados de forma intensiva.
*   **G9 (Desviación Estándar de Intervalos por Usuario - `patron_periodico.png`):** Generado si se identifican patrones de automatización periódicos. Muestra la desviación estándar de intervalos por operador e incluye una línea roja punteada indicando el umbral de bot (2.0 segundos).
*   **G10 (Mapa de Calor de Intensidad - `heatmap_hora_dia.png`):** Generado si se reporta actividad en horarios ilegítimos. Muestra una matriz bidimensional 24 horas x 7 días (`sns.heatmap`) usando la paleta `"YlOrRd"` para evidenciar visualmente picos nocturnos y de fin de semana.

## 4. Estética de las Figuras
*   **Títulos:** Siempre en negrita (`fontweight="bold"`) y con espaciado (`pad=15`).
*   **Dimensiones:**
    *   Gráficos horizontales o temporales amplios: `figsize=(14, 5)` (`FIGSIZE_WIDE`).
    *   Gráficos de dispersión y mapas de calor estructurados: `figsize=(10, 8)` (`FIGSIZE_SQUARE`).
*   **Manejo de Memoria:** Cerrar todas las figuras creadas con `plt.close()` después de guardar en disco para evitar fugas de memoria, especialmente en datasets grandes.
