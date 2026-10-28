import os
from pathlib import Path

# Umbrales de detección
UMBRAL_RAFAGA = 10           # consultas/minuto
UMBRAL_VOLUMEN = 100         # consultas/hora por usuario
UMBRAL_DNI_REPETIDO = 50     # ocurrencias del mismo DNI
STD_PERIODICO = 2.0          # segundos, desv. estándar de intervalos
MIN_CONSULTAS_PERIODICO = 20 # mínimo de consultas para evaluar periodicidad

# Horarios ilegítimos
HORA_INICIO_MADRUGADA = 0    # 00:00
HORA_FIN_MADRUGADA = 5       # antes de 05:00

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
GRAFICOS_DIR = OUTPUT_DIR / "graficos"
INFORMES_DIR = OUTPUT_DIR / "informes"
TEMPLATE_PATH = BASE_DIR / "plantilla_informe.docx"

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
