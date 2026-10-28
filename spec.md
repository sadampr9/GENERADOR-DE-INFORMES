# spec.md — Especificación Técnica: Sistema de Detección de Anomalías en Consumos RENIEC

**Versión**: 1.0  
**Fecha**: 2026-06-02  
**Estado**: Borrador  

---

## 1. Descripción general del proyecto

Sistema Python de análisis forense de consumos de servicios RENIEC. Procesa archivos Excel con registros de uso (5 000 – 50 000+ filas), detecta comportamientos anómalos o patrones de bots por parte de empresas suscriptoras, genera gráficos profesionales con matplotlib y produce un informe Word formal usando python-docx sobre una plantilla existente.

El informe resultante está dirigido a dos audiencias:

- **Auditoría interna / jefatura**: evidencia técnica detallada.
- **Empresa infractora**: notificación formal con respaldo gráfico.

---

## 2. Servicios RENIEC soportados

| ID | Nombre completo |
|----|-----------------|
| 1  | CONSULTAS EN LINEA VIA LINEA DEDICADA *(valor por defecto)* |
| 2  | CONSULTAS EN LINEA VIA INTERNET |
| 3  | VERIFICACION BIOMETRICA DE LA IDENTIDAD DE LAS PERSONAS |
| 4  | WEB SERVICE DE DATOS |
| 5  | WEB SERVICES BIOMETRICO DACTILAR |
| 6  | WEB SERVICE BIOMETRICO FACIAL |

---

## 3. Estructura del repositorio

```
reniec_anomalias/
├── main.py                    # Punto de entrada / orquestador
├── config.py                  # Umbrales, rutas y constantes globales
├── requirements.txt
├── plantilla_informe.docx     # Plantilla Word proporcionada por el usuario
│
├── .agent/                    # Reglas de negocio y lineamientos para agentes de IA
│   └── skills/
│       ├── carga_datos/
│       │   └── SKILL.md       # Ingesta, aliases y parseo de fechas peruano
│       ├── detectar_anomalias/
│       │   └── SKILL.md       # Reglas de motores de anomalía y score
│       ├── generar_graficos/
│       │   └── SKILL.md       # Estética, backend headless y condiciones G1-G10
│       ├── investigar_dni/
│       │   └── SKILL.md       # Tasa de llamadas, caché e investigación manual
│       └── construir_reporte/
│           └── SKILL.md       # Formato Justificado, fechas locales, tono forense
│
├── modules/
│   ├── __init__.py
│   ├── data_loader.py         # Carga y normalización del Excel
│   ├── anomaly_detector.py    # Lógica de detección de anomalías
│   ├── dni_investigator.py    # Investigación automática/manual de DNIs
│   ├── chart_generator.py     # Generación de todos los gráficos
│   └── report_builder.py      # Construcción del informe Word
│
└── output/
    ├── graficos/              # PNG de alta resolución generados
    └── informes/              # Documentos Word finales
```

---

## 4. Requisitos funcionales

### 4.1 Entrada de datos

#### 4.1.1 Formato de archivo

- Tipo: `.xlsx` / `.xls` / `.csv` / `.txt` 
- Hoja: única (se toma siempre la primera hoja)
- Filas: 5 000 – 50 000+
- Encoding esperado: UTF-8 o latin-1 (pandas lo detecta automáticamente)

#### 4.1.2 Columnas reconocidas

El módulo `data_loader` normaliza los nombres de columna a un esquema canónico interno independientemente de cómo vengan en el archivo.

| Nombre canónico interno | Aliases aceptados en el Excel |
|------------------------|-------------------------------|
| `ruc` | `RUC_EMPRESA`, `NU_RUC` |
| `empresa` | `EMPRESA`, `DE_RAZON_SOCIAL` |
| `cod_usuario` | `CODIGO_USUARIO`, `NU_DOC_USUARIO` |
| `nombre_usuario` | `NOMBRES_USUARIO`, `DE_USUARIO` |
| `fecha_consulta` | `FEC_CONSULTA`, `FE_CONSULTA` |
| `dni_consultado` | `DNI_CONSULTADO`, `NU_DNI_CONSULTADO` |
| `respuesta` | `RESPUESTA` |
| `servicio` | `SERVICIO`, `NOMBRE_SERVICIO` |
| `ip_usuario` | `DE_IP_USUARIO` |

Columnas no reconocidas se conservan sin modificación.

#### 4.1.3 Columnas críticas (obligatorias)

- `fecha_consulta` — fecha y hora de cada consulta; se parsea con `pd.to_datetime` con inferencia de formato.
- `dni_consultado` — DNI objetivo de la consulta; se trata siempre como string (padding a 8 dígitos).

#### 4.1.4 Columnas opcionales relevantes

- `respuesta` — valores `HIT` / `NO_HIT`; obligatoria para análisis biométrico (servicios 5 y 6).
- `ip_usuario` — presente solo en algunos exports; se usa si existe.
- `servicio` — si la columna no existe en el archivo, se toma del argumento CLI `--servicio`.

#### 4.1.5 Argumento de línea de comandos

```
python main.py [ruta/al/archivo.xlsx] [--servicio "NOMBRE_SERVICIO"] [--ruc "20XXXXXXXXX"] [--simulate]
```

| Argumento | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `archivo` | posicional (opcional) | `datos_simulados.xlsx` | Ruta al Excel. Opcional si se especifica `--simulate`. |
| `--servicio` | opcional | `"CONSULTAS EN LINEA VIA LINEA DEDICADA"` | Nombre del servicio si no está en el Excel |
| `--ruc` | opcional | `None` | Filtrar análisis a un RUC específico |
| `--output` | opcional | `output/` | Carpeta raíz de salida |
| `--umbral-rafaga` | opcional | `10` | Consultas/minuto para ráfaga |
| `--umbral-volumen` | opcional | `100` | Consultas/hora para volumen inusual |
| `--umbral-dni` | opcional | `50` | Repeticiones de DNI para marcarlo |
| `--simulate` | opcional (flag) | `False` | Genera un archivo Excel simulado con patrones anómalos y ejecuta el flujo completo de prueba |

---

### 4.2 Módulo `data_loader.py`

**Responsabilidades:**

1. Leer el Excel con `openpyxl` (engine).
2. Renombrar columnas al esquema canónico interno.
3. Parsear `fecha_consulta` a `datetime64[ns]`.
4. Asignar el servicio: columna del Excel > argumento CLI > valor por defecto.
5. Convertir `dni_consultado` a string, rellenar con ceros a la izquierda hasta 8 caracteres.
6. Eliminar filas con `fecha_consulta` nula (log de advertencia).
7. Ordenar el DataFrame por `fecha_consulta` ascendente.
8. Retornar `(df: pd.DataFrame, metadata: dict)` con metadatos del archivo (nombre, total filas, rango de fechas, servicio, RUCs únicos).

**Firma pública:**

```python
def load_excel(filepath: str, servicio_default: str = "CONSULTAS EN LINEA VIA LINEA DEDICADA") -> tuple[pd.DataFrame, dict]:
    ...
```

---

### 4.3 Módulo `anomaly_detector.py`

Recibe el DataFrame normalizado y retorna un objeto `AnomalyReport` con todos los hallazgos.

#### 4.3.1 Detecciones implementadas

**A. Ráfagas de consultas**

- Agrupar por `(ruc, cod_usuario)` en ventanas rodantes de 60 segundos.
- Marcar si en alguna ventana el conteo supera `UMBRAL_RAFAGA` (default 10).
- Registrar: RUC, usuario, timestamp inicio de ráfaga, cantidad de consultas.

```python
def detect_bursts(df: pd.DataFrame, threshold: int = 10) -> pd.DataFrame:
    # Retorna DataFrame con columnas: ruc, cod_usuario, window_start, count
```

**B. Volumen inusual por hora**

- Agrupar por `(ruc, hora)`.
- Marcar si supera `UMBRAL_VOLUMEN` (default 100) consultas/hora.

```python
def detect_high_volume(df: pd.DataFrame, threshold: int = 100) -> pd.DataFrame:
```

**C. Horarios ilegítimos**

- Hora entre 00:00–04:59 → `MADRUGADA`
- Domingo → `DOMINGO`
- Retornar filas con flag de tipo de anomalía horaria.

```python
def detect_illegal_hours(df: pd.DataFrame) -> pd.DataFrame:
```

**D. DNI repetido**

- Agrupar por `(ruc, dni_consultado)`.
- Marcar DNIs consultados más de `UMBRAL_DNI` veces (default 50).

```python
def detect_repeated_dni(df: pd.DataFrame, threshold: int = 50) -> pd.DataFrame:
    # Retorna DataFrame: ruc, dni_consultado, count, porcentaje_del_total
```

**E. Patrones periódicos (posible automatización)**

- Para cada `(ruc, cod_usuario)`, calcular intervalos entre consultas consecutivas.
- Si la desviación estándar de los intervalos (en segundos) es < 2.0 y hay ≥ 20 consultas → marcar como automatizado.

```python
def detect_periodic_patterns(df: pd.DataFrame, std_threshold: float = 2.0, min_count: int = 20) -> pd.DataFrame:
```

**F. Triangulación sospechosa**

- Cruzar DNIs repetidos con la lista de directivos/propietarios del RUC investigado (ver módulo `dni_investigator`).
- Si el DNI consultado frecuentemente coincide con un directivo del mismo RUC → flag `TRIANGULACION`.

```python
def detect_triangulation(df: pd.DataFrame, dni_info: dict) -> list[dict]:
```

#### 4.3.2 Objeto de retorno

```python
@dataclass
class AnomalyReport:
    bursts: pd.DataFrame
    high_volume: pd.DataFrame
    illegal_hours: pd.DataFrame
    repeated_dni: pd.DataFrame
    periodic: pd.DataFrame
    triangulation: list[dict]
    severity_score: int          # 0-100, calculado por ponderación
    summary_text: str            # Párrafo resumen generado automáticamente
```

---

### 4.4 Módulo `dni_investigator.py`

Investiga DNIs que aparecen más de `UMBRAL_DNI` veces.

#### 4.4.1 Estrategia de investigación (en orden de prioridad)

1. **Consulta SUNAT API pública** (`https://api.sunat.cloud/v1/persona/getPersona/{dni}` u equivalente disponible públicamente). Retorna nombre completo si está disponible.
2. **Consulta APIs públicas de RENIEC** (si existe endpoint abierto en el momento de ejecución).
3. **Flag manual**: si ninguna fuente automática responde en < 5 segundos (timeout), marcar el DNI como `REQUIERE_INVESTIGACION_MANUAL` en el reporte con el DNI resaltado en rojo en el Word.

#### 4.4.2 Salida por cada DNI investigado

```python
@dataclass
class DNIInfo:
    dni: str
    nombre_completo: str | None
    fuente: str                  # "SUNAT_API", "MANUAL_FLAG"
    es_directivo_ruc: bool       # True si coincide con directivos del RUC
    requiere_manual: bool
    notas: str
```

#### 4.4.3 Consideraciones

- Respetar `robots.txt` y `terms of service` de cada fuente.
- Implementar `time.sleep(0.5)` entre requests para no saturar servicios externos.
- Cachear resultados en memoria durante la ejecución para no repetir consultas.
- El scraping web queda como stub comentado; activarlo requiere revisión legal previa.

---

### 4.5 Módulo `chart_generator.py`

Genera los gráficos PNG y los guarda en `output/graficos/`.

#### 4.5.1 Configuración de estilo

```python
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style="whitegrid", palette="muted")
FIGSIZE_WIDE = (14, 5)
FIGSIZE_SQUARE = (10, 8)
DPI = 150
```

#### 4.5.2 Gráficos obligatorios

| ID | Nombre archivo | Descripción | Siempre generado |
|----|---------------|-------------|-----------------|
| G1 | `consumo_diario.png` | Línea de consultas por fecha | ✅ Sí |
| G2 | `consumo_por_hora.png` | Heatmap o barplot por hora del día | ✅ Sí |

#### 4.5.3 Gráficos condicionales (se generan solo si el patrón fue detectado)

| ID | Nombre archivo | Condición de activación |
|----|---------------|------------------------|
| G3 | `consumo_dia_semana.png` | Siempre (complementario) |
| G4 | `distribucion_usuario.png` | Si hay >1 usuario único |
| G5 | `rafagas_por_hora.png` | Si `bursts` no está vacío |
| G6 | `scatter_volumen_tiempo.png` | Si `high_volume` no está vacío |
| G7 | `histograma_dni.png` | Si `repeated_dni` no está vacío |
| G8 | `tabla_top10_dni.png` | Si hay DNIs repetidos |
| G9 | `patron_periodico.png` | Si `periodic` no está vacío |
| G10 | `heatmap_hora_dia.png` | Si hay actividad en madrugada o domingos |

#### 4.5.4 Firma pública

```python
def generate_all(df: pd.DataFrame, report: AnomalyReport, output_dir: str) -> dict[str, str]:
    # Retorna dict {chart_id: filepath}
```

---

### 4.6 Módulo `report_builder.py`

Construye el documento Word final usando `python-docx` sobre la plantilla `plantilla_informe.docx`, alineándose con los modelos de referencia (`MINISTERIO DE EDUCACION-AGOSTO-LD.docx`, `PAGOS DIGITALES PERUANOS S.A-JULIO-LD.docx` y `BANCO DE LA NACION-JULIO-LD.docx`).

#### 4.6.1 Información General (Página 1)

1. **Cantidad de usuarios del Servicio**: Se consulta el archivo `USUARIOS POR ENTIDAD.xlsx` para la Entidad y el Servicio analizados, obteniendo y registrando la cantidad total de usuarios asignados al servicio (ej. `30 usuarios`).
2. **Usuario evaluado**: Se identifica dinámicamente al usuario con mayor volumen total de consultas consumidas en el periodo evaluado y se formatea como `Nombre Completo (DNI: XXXXXXXX)`.

#### 4.6.2 Integración con `REVISION SEMANAL DE CONSUMOS` (Imagen 1 y Métricas 2025+)

1. **Gráfico Histórico (Imagen 1)**: Para la primera técnica (4.2.1), el sistema explora la carpeta `C:\Users\sperezr\Documents\Proyectos - Proyectos\REVISION SEMANAL DE CONSUMOS\output\graficos` buscando el gráfico diario multi-anual de la empresa (periodo 2025-2026).
2. **Valores de VNP, VID e IP%**: El Volumen diario Promedio (VNP) registrado en la Tabla 1 de la primera página y en la redacción de 4.2.1 se calcula en base a la línea temporal histórica 2025-2026 obtenida de `REVISION SEMANAL DE CONSUMOS`. El Incremento Porcentual se obtiene como `IP% = ((VID - VNP) / VNP) * 100`.

#### 4.6.2 Estructura y Formato de Subsecciones (4.2.X)

1. **Alineación de Encabezados**: Los títulos de subsección (`4.2.1`, `4.2.2`, `4.2.3`, etc.) se formatean sin sangría izquierda (`left_indent = 0`, `first_line_indent = 0`), alineados al margen izquierdo a la misma altura que `4.2`.
2. **Paginación Fija**: Se inserta un salto de página antes de cada subsección (a partir de 4.2.2) para garantizar que **cada técnica con su imagen entra limpiamente en una sola página**.
3. **Párrafos de Hallazgo**: Texto redactado en alineación **Justificada** (`WD_ALIGN_PARAGRAPH.JUSTIFY`), concluyendo explícitamente con la indicación `(ver imagen X).`.
4. **Imágenes y Etiquetas**: La imagen PNG se inserta centrada con ancho controlado (~14.5 cm), seguida inmediatamente por una etiqueta centrada `(Imagen X)`.

#### 4.6.3 Conclusiones y Recomendaciones

1. **Conclusiones**: Se incluyen exactamente **3 conclusiones justificadas y extensas** en la sección `4.3. Conclusiones:`:
   - **Evidencia Incontestable de Automatización**: Resumen del total de ráfagas y velocidad máxima en consultas/segundo.
   - **Concentración Extrema del Consumo**: Análisis del porcentaje de consultas concentradas en los usuarios principales.
   - **Reincidencia Anómala en Documentos de Identidad**: Impacto por consultas repetitivas de DNIs específicos.
2. **Recomendaciones**: Se incluye exactamente **1 recomendación justificada y detallada** en la sección `4.4. Recomendaciones:` exigiendo el bloqueo preventivo inmediato de credenciales y la remisión de un informe forense interno en un plazo no mayor a cinco (5) días hábiles.

---

## 5. Módulo `config.py`

Centraliza todos los valores configurables:

```python
# Umbrales de detección
UMBRAL_RAFAGA = 10           # consultas/minuto
UMBRAL_VOLUMEN = 100         # consultas/hora
UMBRAL_DNI_REPETIDO = 50     # ocurrencias del mismo DNI
STD_PERIODICO = 2.0          # segundos, desv. estándar de intervalos
MIN_CONSULTAS_PERIODICO = 20 # mínimo de consultas para evaluar periodicidad

# Horarios ilegítimos
HORA_INICIO_MADRUGADA = 0    # 00:00
HORA_FIN_MADRUGADA = 5       # antes de 05:00

# Rutas
OUTPUT_DIR = "output/"
GRAFICOS_DIR = "output/graficos/"
INFORMES_DIR = "output/informes/"
TEMPLATE_PATH = "plantilla_informe.docx"

# APIs externas
SUNAT_API_URL = "https://api.sunat.cloud/v1/persona/getPersona/{dni}"
API_TIMEOUT_SECONDS = 5

# Descripciones para el informe (sección 5)
CHART_DESCRIPTIONS = {
    "G1": "Evolución del volumen de consultas día a día. Permite identificar picos anómalos y cambios abruptos en el patrón de uso.",
    "G2": "Distribución de consultas por hora del día. Revela actividad en horarios no laborales o concentración inusual en franjas horarias específicas.",
    "G3": "Actividad por día de la semana. Identifica uso excesivo en fines de semana o días festivos.",
    "G4": "Volumen por usuario/código. Detecta si uno o pocos usuarios concentran la mayoría del tráfico.",
    "G5": "Frecuencia de ráfagas por hora. Visualiza los períodos donde se superó el umbral de consultas por minuto.",
    "G6": "Dispersión de volumen a lo largo del tiempo. Permite apreciar la sostenibilidad del ritmo de consultas.",
    "G7": "Histograma de frecuencia por DNI consultado. Un DNI con barra muy alta indica consulta sistemática o triangulación.",
    "G8": "Top 10 DNIs más consultados. Tabla visual para identificar rápidamente los sujetos bajo escrutinio masivo.",
    "G9": "Distribución de intervalos entre consultas. Intervalos muy regulares (baja desviación estándar) sugieren automatización.",
    "G10": "Mapa de calor hora × día de semana. Concentraciones en celdas de madrugada o fin de semana son señal de alerta.",
}
```

---

## 6. Módulo `main.py` — Orquestador

```python
# Pseudocódigo del flujo principal
def main():
    args = parse_args()
    
    # 1. Carga y normalización
    df, metadata = load_excel(args.archivo, args.servicio)
    
    # 2. Detección de anomalías
    report = run_all_detections(df, args)
    
    # 3. Investigación de DNIs
    dni_infos = investigate_dnis(report.repeated_dni, metadata["ruc_principal"])
    
    # 4. Generación de gráficos
    charts = generate_all(df, report, GRAFICOS_DIR)
    
    # 5. Construcción del informe
    output_path = build_report(df, metadata, report, charts, dni_infos, TEMPLATE_PATH, INFORMES_DIR)
    
    print(f"✅ Informe generado: {output_path}")
    print(f"✅ Gráficos guardados en: {GRAFICOS_DIR}")
```

---

## 7. Requisitos no funcionales

### 7.1 Rendimiento

- Tiempo máximo de procesamiento para 50 000 filas: **< 60 segundos** en hardware estándar (i5, 8 GB RAM).
- Uso de `pandas` vectorizado; evitar loops Python explícitos sobre DataFrames.
- Para ventanas rodantes de ráfagas, usar `pd.Grouper` + `rolling` en lugar de iterrows.

### 7.2 Robustez

- Manejo de columnas faltantes: si una columna opcional no existe, omitir el análisis que la requiere y loggear advertencia.
- Manejo de fechas mal formateadas: registrar en log y omitir la fila.
- Manejo de archivos Excel corruptos: capturar excepción y mostrar mensaje claro al usuario.
- Timeout de 5 segundos en todas las llamadas a APIs externas.

### 7.3 Logging

- Usar el módulo `logging` estándar de Python.
- Nivel `INFO` por defecto; nivel `DEBUG` con flag `--verbose`.
- Formato: `[YYYY-MM-DD HH:MM:SS] [LEVEL] mensaje`
- Guardar log en `output/log_{timestamp}.txt`.

### 7.4 Portabilidad

- Python 3.10+.
- Sin dependencias de sistema operativo específico.
- Todas las rutas manejadas con `pathlib.Path`.

---

## 8. Dependencias (`requirements.txt`)

```
pandas>=2.0
openpyxl>=3.1
matplotlib>=3.7
seaborn>=0.13
python-docx>=1.1
requests>=2.31
```

---

## 9. Instalación y uso rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Uso básico (servicio por defecto)
python main.py datos/consumo_empresa_X.xlsx

# Especificando servicio
python main.py datos/consumo.xlsx --servicio "WEB SERVICE BIOMETRICO FACIAL"

# Filtrar por RUC y modo verbose
python main.py datos/consumo.xlsx --ruc 20123456789 --verbose
```

---

## 10. Flujo de datos de extremo a extremo

```
Excel (.xlsx)
     │
     ▼
[data_loader.py]
  Normalización de columnas, parseo de fechas, asignación de servicio
     │
     ▼
[anomaly_detector.py]
  Ráfagas │ Volumen │ Horarios │ DNI repetido │ Periódico │ Triangulación
     │
     ├──────────────────────┐
     ▼                      ▼
[dni_investigator.py]   [chart_generator.py]
  Lookup SUNAT/RENIEC     G1–G10 según patrones detectados
  → DNIInfo[]             → PNG en output/graficos/
     │                      │
     └──────────┬───────────┘
                ▼
        [report_builder.py]
          Plantilla Word + placeholders + imágenes
                │
                ▼
     output/informes/{NOMBREDELAENTIDAD}-{MES}-{SERVICIOABREVIADO}.docx
```

---

## 11. Decisiones de diseño y justificaciones

| Decisión | Justificación |
|----------|--------------|
| Módulos separados en vez de script monolítico | Facilita pruebas unitarias, mantenimiento y reutilización independiente de cada fase |
| Normalización de columnas en `data_loader` | Los alias de columnas varían por servicio; centralizar la lógica evita condicionales dispersos |
| `config.py` con todos los umbrales | Permite ajustar la sensibilidad sin modificar lógica de negocio |
| Gráficos condicionales | Evita páginas vacías o gráficos sin datos en el informe |
| Timeout en APIs externas | Impide que una API lenta bloquee todo el proceso |
| Flag `REQUIERE_INVESTIGACION_MANUAL` | Garantiza que los DNIs no resueltos automáticamente sean atendidos sin perder el hallazgo |
| Copia de plantilla antes de modificar | Preserva el original para ejecuciones futuras |
| Habilidades de Agente en `.agent/skills/` | Asegura la coherencia, tono técnico y cumplimiento de reglas operativas/legales ante futuras modificaciones de agentes de IA |

---

## 12. Casos de prueba mínimos

| Test | Descripción | Resultado esperado |
|------|-------------|-------------------|
| TC-01 | Excel sin columna `SERVICIO` + argumento `--servicio` | Servicio asignado correctamente |
| TC-02 | Excel sin columna `SERVICIO` sin argumento CLI | Servicio = "CONSULTAS EN LINEA VIA LINEA DEDICADA" |
| TC-03 | 15 consultas en 1 minuto desde mismo RUC | Detectado como ráfaga |
| TC-04 | DNI consultado 80 veces | Aparece en `repeated_dni`; se intenta lookup |
| TC-05 | Consultas a las 02:30 | Detectadas como horario ilegítimo `MADRUGADA` |
| TC-06 | Intervalos de 0.5 s exactos, 30 consultas | Detectado como patrón periódico |
| TC-07 | API SUNAT no responde | DNI marcado `REQUIERE_INVESTIGACION_MANUAL` sin crash |
| TC-08 | Excel con 50 000 filas | Ejecución completa < 60 s |
| TC-09 | Plantilla sin placeholder `{{EMPRESA}}` | Warning en log; resto del informe generado |
| TC-10 | Solo anomalías de horario (sin ráfagas) | Gráficos G5, G6, G9 no generados; informe coherente |

---

*Fin del documento de especificación.*
