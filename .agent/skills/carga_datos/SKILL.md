# Skill: Carga y Normalización de Datos

Este Skill define las directrices y criterios técnicos para la ingesta, limpieza y normalización de los registros de consulta (RENIEC) provenientes de diversas fuentes.

## 1. Soporte de Formatos y Lectura
*   **Extensiones aceptadas:** `.xlsx`, `.xls`, `.csv`, `.txt`, `.tsv`.
*   **Hoja de cálculo:** Se procesa únicamente la primera pestaña en archivos Excel.
*   **Codificación (Encoding):** 
    *   Para CSV/TXT, intentar primero codificación `utf-8`.
    *   Si falla por caracteres especiales, decodificar usando `latin-1`.
    *   Para archivos delimitados por texto plano, usar detección automática del separador (`sep=None` con el motor `python` en pandas).

## 2. Esquema Canónico y Normalización de Columnas
Para garantizar el funcionamiento de los algoritmos de detección, las columnas del archivo origen deben renombrarse según el siguiente mapeo canónico:

| Campo Interno | Aliases de Columna Origen |
| :--- | :--- |
| `ruc` | `RUC`, `ruc`, `RUC_EMPRESA`, `NU_RUC` |
| `empresa` | `empresa`, `EMPRESA`, `DE_RAZON_SOCIAL` |
| `cod_usuario` | `cod_usuario`, `CODIGO_USUARIO`, `NU_DOC_USUARIO` |
| `nombre_usuario` | `nombre_usuario`, `NOMBRES_USUARIO`, `DE_USUARIO` |
| `fecha_consulta` | `fecha_consulta`, `FEC_CONSULTA`, `FE_CONSULTA` |
| `dni_consultado` | `dni_consultado`, `DNI_CONSULTADO`, `NU_DNI_CONSULTADO` |
| `respuesta` | `respuesta`, `RESPUESTA` |
| `servicio` | `servicio`, `SERVICIO`, `NOMBRE_SERVICIO` |
| `ip_usuario` | `ip_usuario`, `DE_IP_USUARIO` |

## 3. Limpieza de Fechas e Identificadores (Reglas Críticas)
*   **Formato de Fecha:** El campo `fecha_consulta` debe parsearse con `dayfirst=True` para interpretar correctamente el orden de días y meses en el estándar local (`DD/MM/AAAA HH:MM:SS`), evitando pérdidas de registros y conversión masiva a valores nulos (`NaT`).
*   **Filtrado de Nulos:** Descartar filas que contengan fecha de consulta vacía o que no puedan convertirse a fecha válida, registrando una advertencia en el log del sistema.
*   **Normalización de DNI:** El campo `dni_consultado` debe ser tratado como cadena de texto limpia de decimales (en caso de exportaciones flotantes), aplicando relleno con ceros a la izquierda (`zfill(8)`) para asegurar que siempre posea una longitud exacta de 8 caracteres.

## 4. Inferencia de Metadatos
En caso de que el archivo de entrada carezca de las columnas `ruc` o `empresa`, el cargador debe inferir la identidad de la entidad a partir del nombre del archivo en mayúsculas:
*   Si contiene `"INTERBANK"`: RUC `20100053455` y Empresa `BANCO INTERNACIONAL DEL PERU S.A. INTERBANK`.
*   Si contiene `"JNE"`: RUC `20131370603` y Empresa `JURADO NACIONAL DE ELECCIONES`.
*   Si contiene `"SUNEDU"`: RUC `20600044975` y Empresa `SUPERINTENDENCIA NACIONAL DE EDUCACION SUPERIOR UNIVERSITARIA`.
*   Otros casos por defecto: RUC `SIN_RUC` y Empresa `EMPRESA NO ESPECIFICADA`.

## 5. Ordenamiento y Salida
El conjunto de datos final debe devolverse ordenado cronológicamente (`fecha_consulta` ascendente), acompañado de un diccionario de metadatos con el rango de fechas evaluado, total de filas válidas, RUC principal y nombre del servicio.
