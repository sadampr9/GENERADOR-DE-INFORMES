# Skill: Construcción de Reporte de Auditoría Forense

Este Skill define las reglas de negocio, tono, estructura y formato para la redacción e inserción de hallazgos dinámicos en el informe Word generado para la entidad bajo análisis, adaptado al modelo oficial (`MINISTERIO DE EDUCACION-AGOSTO-LD.docx`, `PAGOS DIGITALES PERUANOS S.A-JULIO-LD.docx` y `BANCO DE LA NACION-JULIO-LD.docx`).

## 1. Tono y Vocabulario Técnico
* **Objetividad:** Toda anomalía debe presentarse como un "comportamiento atípico" o "patrón que diverge de la jornada operativa regular".
* **Terminología:**
    * No usar: "sospechoso", "ilegal", "delito", "robo de datos".
    * Usar: "anómalo", "desviación del estándar", "patrón consistente con extracción automatizada (scripts)", "exposición potencial de datos".

## 2. Reglas de Formato y Estructura del Documento (Word)

### 2.1 Información General (Página 1 - Modelo MINISTERIO DE EDUCACION-AGOSTO-LD.docx)
* **Cantidad de usuarios del Servicio:** Se interactúa con el archivo `USUARIOS POR ENTIDAD.xlsx` (filtrando por la Entidad y el Servicio analizado) para contar y colocar la cantidad total de usuarios registrados/asignados al servicio (ej. `30 usuarios`).
* **Usuario evaluado:** Se identifica el usuario que más consume (aquel que registra el mayor volumen total de consultas en el periodo evaluado) y se coloca su Nombre Completo y DNI (ej. `Segundo Kenny Rodríguez Gil (DNI: 42260520)`).

### 2.2 Integración de Imagen 1 e Histórico (2025+)
* **Fuente del Gráfico 1:** La Imagen 1 (histórico 2025-2026 de consumos diarios) debe ser tomada del proyecto `C:\Users\sperezr\Documents\Proyectos - Proyectos\REVISION SEMANAL DE CONSUMOS\output\graficos`.
* **Métricas en Tabla 1:** Los valores de Volumen diario Promedio (VNP), Volumen Inusual Detectado (VID) e Incremento Porcentual (IP%) registrados en la Tabla 1 de la primera página y en la subsección 4.2.1 provienen del análisis histórico 2025-2026.

### 2.3 Alineación y Paginación de Subsecciones (4.2.X)
* **Alineación de Títulos:** Los títulos de las subsecciones (`4.2.1`, `4.2.2`, `4.2.3`, etc.) deben estar alineados a la izquierda sin sangría (`left_indent = 0`, `first_line_indent = 0`), al mismo nivel que `4.2`.
* **Formato de 1 Página por Técnica:** A partir de `4.2.2`, se debe insertar un salto de página antes de cada subsección para garantizar que la técnica, su texto descriptivo, el gráfico y su etiqueta entren en una sola página.
* **Párrafo Justificado y Referencia a la Imagen:** Todos los párrafos explicativos deben tener alineación **Justificada** (`WD_ALIGN_PARAGRAPH.JUSTIFY`) y terminar explícitamente con `(ver imagen X).`.
* **Imágenes y Etiquetas:** Cada gráfico debe ser insertado centrado horizontalmente (ancho ~14.5 cm), seguido inmediatamente por la etiqueta centrada `(Imagen X)`.

### 2.4 Especificación de Redacción Dinámica por Subsección (4.2.2 a 4.2.10)

Cada subsección debe calcular de forma automatizada y presentar métricas exactas extraídas del dataset evaluado, siguiendo el estilo de redacción fluido e institucional de los informes oficiales:

* **4.2.1 Análisis del Consumo por Usuario (Enero – Mes 2026) [Imagen 1]:** Presenta la tendencia histórica 2025-2026, indicando la fecha del pico histórico, el volumen inusual detectado (VID), el promedio diario registrado (VNP) y el incremento porcentual (IP%).
* **4.2.2 Distribución de Consultas por Hora del Día [Imagen 2]:** Identifica la hora del día con mayor concentración acumulada, especificando el volumen exacto de esa franja horaria y analizando la actividad en horas no operativas (posteriores a las 17:00 h).
* **4.2.3 Actividad de Consultas por Día de la Semana [Imagen 3]:** Evalúa la continuidad operativa durante los fines de semana, indicando el total exacto de consultas realizadas los días domingo y sustentando la ejecución de servicios desatendidos.
* **4.2.4 Distribución por Usuario/Código [Imagen 4]:** Identifica los principales usuarios operadores, detallando el volumen exacto de consultas consumidas por el usuario líder y su porcentaje relativo respecto al total institucional.
* **4.2.5 Frecuencia de Ráfagas por Hora del Día [Imagen 5]:** Cuantifica el total de ráfagas en ventanas de 60 segundos, destacando la ráfaga más intensa con su fecha/hora, número de consultas y su velocidad equivalente en consultas por segundo.
* **4.2.6 Dispersión de Volumen Horario Inusual [Imagen 6] — (Subsección de Énfasis Crítico):**
  * Debe indicar la **fecha y horario exactos** que registraron el mayor volumen de consultas por hora (ej. *Jueves 20 de agosto de 2026 a las 10:00 h*).
  * Debe calcular y exponer el **volumen total de consultas** alcanzado en esa sola hora (ej. *6,570 consultas*).
  * Debe calcular el **porcentaje relativo** que dicho pico concentró respecto al total global de consultas del periodo evaluado (ej. *1.43%*).
  * Debe detallar la equivalencia en **consultas por minuto** (ej. *109.50 consultas/minuto*) y consultas por segundo (ej. *~1.83 consultas/segundo*) sostenidas durante los 60 minutos ininterrumpidos.
  * Debe concluir justificando la naturaleza de extracción masiva desatendida mediante software o scripts clientes (terminando en `(ver imagen X).`).
* **4.2.7 Distribución de Frecuencia de DNIs Repetidos [Imagen 7]:** Reporta la cantidad de DNIs únicos que superaron el umbral de repetición y su distribución KDE de reconsultas.
* **4.2.8 Top 10 DNIs Más Consultados por los Usuarios [Imagen 8]:** Presenta el ranking de los 10 DNIs más consultados del dataset, identificando el DNI en el puesto 1 con su volumen exacto y el usuario operador responsable.
* **4.2.9 Análisis de Intervalos entre Consultas [Imagen 9]:** Detalla el número de usuarios que presentaron una desviación estándar de intervalos menor a 2.0 segundos, confirmando el uso de procesos automatizados (*bots*).
* **4.2.10 Mapa de Calor de Consumo (Hora × Día) [Imagen 10]:** Examina las concentraciones en horas de la madrugada (00:00 - 04:59 h) y domingos mediante la matriz bidimensional de intensidad.

### 2.5 Conclusiones y Recomendaciones
* **3 Conclusiones Justificadas:** Se deben incluir exactamente tres conclusiones sustanciales (Evidencia Incontestable de Automatización, Concentración Extrema del Consumo y Reincidencia Anómala en Documentos de Identidad).
* **1 Recomendación Justificada:** Se debe incluir una recomendación detallada sobre el bloqueo preventivo inmediato de credenciales y la exigencia de un informe forense interno en 5 días hábiles.

## 3. Checklist de Validación Final (Antes de guardar el documento)
1. ¿Se consultó `USUARIOS POR ENTIDAD.xlsx` para obtener la 'Cantidad de usuarios del Servicio'?
2. ¿Se identificó correctamente al 'Usuario evaluado' (el usuario que más consume)?
3. ¿La Tabla 1 (Resumen) contiene los datos de VNP (2025+), VID e IP% reales?
4. ¿La Imagen 1 se extrajo de `REVISION SEMANAL DE CONSUMOS`?
5. ¿Las subsecciones 4.2.X están alineadas a la izquierda sin sangría?
6. ¿Cada subsección (4.2.2, 4.2.3, etc.) y su gráfico caben en una sola página?
7. ¿La subsección 4.2.6 incluye la fecha/hora pico, volumen en esa hora, % del total del periodo y consultas/minuto?
8. ¿Los párrafos terminan en `(ver imagen X).` y tienen debajo la etiqueta `(Imagen X)`?
9. ¿Existen exactamente 3 conclusiones y 1 recomendación justificadas y detalladas?
