# Skill: Investigación Forense de DNIs Repetidos

Este Skill establece los procedimientos para la identificación e investigación de titulares de DNIs detectados bajo comportamiento de consultas repetitivas de forma atípica.

## 1. Flujo de Consulta e Integración de APIs
*   **API Principal:** API de SUNAT para consultar y resolver el nombre del ciudadano titular del DNI.
*   **Entradas:** DataFrame de DNIs repetidos y el RUC principal de la empresa investigada.
*   **Parámetros:** Utilizar el timeout configurado en `config.py` (`API_TIMEOUT_SECONDS`, default 5s) para evitar bloqueos en el hilo de ejecución principal.

## 2. Buenas Prácticas de Scraping y Acceso a Redes
*   **Políticas de Robots:** Respetar los términos de robots.txt de los portales gubernamentales. Identificar el agente de la petición si es posible.
*   **Frecuencia (Delay):** Pausa de cortesía obligatoria (`time.sleep(0.5)`) entre llamadas de DNI para evitar el bloqueo temporal de la IP de la auditoría o la sobrecarga de los servidores de SUNAT.
*   **Caché en Memoria:** Mantener un diccionario `_dni_cache` local. Si un DNI ya fue investigado previamente durante el mismo procesamiento, se debe retornar directamente el resultado cacheado, reduciendo llamadas de red innecesarias.

## 3. Manejo de Errores y Robustez
*   **Excepciones de Conexión:** Si el servidor de SUNAT está caído, la petición tiene timeout, o la respuesta no es exitosa, atrapar los errores (`requests.RequestException`) y continuar con el siguiente DNI.
*   **Fallo de Resolución (Flag Manual):** Si un DNI no puede ser resuelto en línea, asignar:
    *   `fuente = "MANUAL_FLAG"`
    *   `requiere_manual = True`
    *   `nombre_completo = None`
    *   Esto alertará visualmente al analista en el informe final marcando la celda del DNI correspondiente con un fondo amarillo destacado.

## 4. Detección de Directivos y Triangulación
*   **Mock/Búsqueda de Directivos:** Comparar el DNI consultado con la base de datos de representantes legales, dueños o directores asociados al RUC consultante.
*   **Resultado Positivo:** Si el DNI pertenece a un directivo de la misma empresa investigada, marcar `es_directivo_ruc = True` y agregar la nota respectiva. Esto activa el análisis de triangulación en el motor de detección de anomalías.
