import time
import requests
import logging
from dataclasses import dataclass
from config import SUNAT_API_URL, API_TIMEOUT_SECONDS

logger = logging.getLogger("reniec_anomalias")

@dataclass
class DNIInfo:
    dni: str
    nombre_completo: str | None
    fuente: str                  # "SUNAT_API", "MANUAL_FLAG", "MOCK_DB"
    es_directivo_ruc: bool       # True si coincide con directivos del RUC
    requiere_manual: bool
    notas: str

# Cache en memoria para evitar repetir consultas en la misma ejecución
_dni_cache = {}

# Variables globales para control de fallas en red
_api_disabled = False
_failed_connection_count = 0

# Mock de directivos por RUC para pruebas y demostración de triangulación sospechosa
# En un entorno productivo, esto se obtendría consultando el RUC en SUNAT
MOCK_DIRECTIVOS_POR_RUC = {
    "20123456789": ["44444444", "00000001", "12345678"],
    "20999999999": ["99999999"]
}

def investigate_single_dni(dni: str, ruc: str = None) -> DNIInfo:
    """
    Investiga un DNI específico consultando APIs públicas.
    Aplica caché en memoria y reintento.
    """
    global _api_disabled, _failed_connection_count
    
    if dni in _dni_cache:
        # Actualizar es_directivo_ruc para este RUC si es necesario
        cached_info = _dni_cache[dni]
        es_dir = False
        if ruc and ruc in MOCK_DIRECTIVOS_POR_RUC:
            es_dir = dni in MOCK_DIRECTIVOS_POR_RUC[ruc]
        cached_info.es_directivo_ruc = es_dir
        return cached_info

    logger.info(f"Investigando DNI: {dni}...")

    nombre_completo = None
    fuente = "MANUAL_FLAG"
    requiere_manual = True
    notas = "No se pudo obtener información de APIs públicas."

    if not _api_disabled:
        # Respetar tasa de solicitudes (delay)
        time.sleep(0.5)

        # 1. Intentar consulta a la API de SUNAT
        url = SUNAT_API_URL.format(dni=dni)
        try:
            response = requests.get(url, timeout=API_TIMEOUT_SECONDS)
            if response.status_code == 200:
                data = response.json()
                # Asumimos estructura estándar: {"nombre": "JUAN PEREZ", ...} o similar
                # Se adaptan posibles respuestas de APIs de prueba
                if isinstance(data, dict):
                    nombre_completo = data.get("nombre") or data.get("nombre_completo") or data.get("razon_social")
                    if nombre_completo:
                        fuente = "SUNAT_API"
                        requiere_manual = False
                        notas = "Obtenido exitosamente de API SUNAT."
                        _failed_connection_count = 0  # resetear contador al tener éxito
            else:
                logger.warning(f"API SUNAT retornó código de estado {response.status_code} para DNI {dni}")
        except requests.RequestException as e:
            logger.warning(f"Error de conexión al consultar API SUNAT para DNI {dni}: {str(e)}")
            _failed_connection_count += 1
            if _failed_connection_count >= 3:
                logger.warning("Se detectaron fallos de conexión consecutivos. Deshabilitando consultas a API externa para agilizar procesamiento offline.")
                _api_disabled = True
    else:
        notas = "Consulta a API externa omitida por fallas de conexión previas."

    # 2. Stub/Comentario de Scraping alternativo (por razones legales y éticas se mantiene como demostración)
    """
    # Ejemplo de scraping de respaldo respetando robots.txt
    try:
        # url_reniec = f"https://www.ejemplo-reniec.gob.pe/consultas/{dni}"
        # res = requests.get(url_reniec, headers={'User-Agent': 'BotAuditoriaRENIEC/1.0'}, timeout=5)
        # ... parsear html con BeautifulSoup ...
        pass
    except Exception:
        pass
    """

    # 3. Determinar si es directivo del RUC consultante
    es_directivo = False
    if ruc and ruc in MOCK_DIRECTIVOS_POR_RUC:
        es_directivo = dni in MOCK_DIRECTIVOS_POR_RUC[ruc]
        if es_directivo:
            notas += " COINCIDENCIA: Es directivo/representante legal de la empresa investigada."

    info = DNIInfo(
        dni=dni,
        nombre_completo=nombre_completo,
        fuente=fuente,
        es_directivo_ruc=es_directivo,
        requiere_manual=requiere_manual,
        notas=notas
    )

    # Almacenar en caché
    _dni_cache[dni] = info
    return info

def investigate_dnis(repeated_dni_df, ruc_principal: str = None) -> list[DNIInfo]:
    """
    Investiga todos los DNIs detectados en el dataframe de DNIs repetidos.
    """
    infos = []
    if repeated_dni_df.empty:
        return infos

    # Tomar la columna dni_consultado
    dnis_a_investigar = repeated_dni_df["dni_consultado"].unique().tolist()
    
    logger.info(f"Iniciando investigación de {len(dnis_a_investigar)} DNI(s) repetidos...")
    for dni in dnis_a_investigar:
        info = investigate_single_dni(dni, ruc_principal)
        infos.append(info)
        
    return infos
