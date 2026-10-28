# Skill: Detección Forense de Anomalías en Consumos

Este Skill describe los motores de detección implementados para auditar los consumos de servicios de identidad (RENIEC) e identificar comportamientos anómalos o de automatización.

## 1. Detección de Ráfagas (Bursts)
*   **Propósito:** Detectar picos rápidos de consultas que no pueden ser ejecutados de manera manual por un operador humano.
*   **Lógica:** Agrupar los registros por `(ruc, cod_usuario)` en ventanas rodantes de 60 segundos. Si en alguna de estas ventanas el conteo de consultas supera el umbral configurado (`UMBRAL_RAFAGA`, default 10), se considera una ráfaga.
*   **Mitigación de Ruido:** Para evitar alertas duplicadas sobre el mismo evento de ráfaga, se agrupan las detecciones por minuto y se selecciona únicamente el pico más representativo de cada intervalo.

## 2. Volumen Inusual por Hora
*   **Propósito:** Identificar periodos sostenidos de extracción masiva de información.
*   **Lógica:** Agrupar por `(ruc, hora_periodo)` redondeado a la hora exacta. Si el volumen en esa hora supera el umbral configurado (`UMBRAL_VOLUMEN`, default 100), se reporta el intervalo para la auditoría detallada.

## 3. Horarios Ilegítimos (Actividad Fuera de Jornada)
*   **Propósito:** Detectar accesos nocturnos o en días no laborables.
*   **Reglas de Clasificación:**
    *   **Madrugada:** Toda consulta realizada entre las `00:00:00` y las `04:59:59` del día.
    *   **Domingos:** Toda consulta realizada en el día de la semana correspondiente a domingo (day of week = 6).
*   **Etiquetado:** Cada fila detectada se etiqueta bajo los tipos `"MADRUGADA"`, `"DOMINGO"`, o `"MADRUGADA+DOMINGO"` según corresponda.

## 4. DNI Consultado Repetidamente
*   **Propósito:** Detectar focalización anómala o consultas repetitivas de datos de personas específicas.
*   **Lógica:** Agrupar por `(ruc, dni_consultado)`. Si un DNI ha sido consultado más de `UMBRAL_DNI` veces (default 50), se marca para lookup/investigación y se calcula su porcentaje relativo sobre la actividad total de la entidad.

## 5. Patrones Periódicos (Frecuencia Fija / Bots)
*   **Propósito:** Confirmar científicamente la presencia de bots o scripts clientes de integración que operan a intervalos fijos.
*   **Lógica:** Para cada `(ruc, cod_usuario)` con al menos 20 consultas, calcular la diferencia en segundos (intervalo) entre consultas consecutivas. Si la desviación estándar (`std`) de estos intervalos es menor a `2.0` segundos, se determina que el patrón es periódico y gobernado por un script automático.

## 6. Triangulación Sospechosa
*   **Propósito:** Evidenciar si la entidad está utilizando sus accesos RENIEC para consultar repetitivamente información de sus propios directivos, representantes o dueños.
*   **Lógica:** Cruzar la lista de DNIs repetidos investigados con los DNIs de directivos del RUC consultante (cargados mediante mock o API de SUNAT). Si hay coincidencia, se incrementa la severidad de la alerta.

## 7. Puntuación de Severidad (Severity Score)
Consolida un score general de 0 a 100 puntos en base a los tipos de anomalías detectadas:
*   Ráfagas presentes: **+25 puntos**
*   Volumen inusual por hora presente: **+25 puntos**
*   Patrones periódicos (bots) detectados: **+20 puntos**
*   Consultas en horarios ilegítimos: **+15 puntos**
*   DNIs repetidos por encima del umbral: **+15 puntos**
*   *Bonus de Triangulación:* Si se confirma coincidencia de DNI de directivos, se añade un incremento directo de **+30 puntos** (tope máximo general de 100).
