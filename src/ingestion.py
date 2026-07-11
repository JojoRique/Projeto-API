import os
import time
import json
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

RAW_DATA_DIR = "data/raw"

def fetch_month_data(year: int, month: int, retries: int = 3, backoff_factor: float = 1.5) -> list:
    """
    Busca dados de um mês específico da Church Calendar API com retries e backoff.
    """
    url = f"http://calapi.inadiutorium.cz/api/v0/en/calendars/default/{year}/{month}"
    
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Buscando dados de {year}/{month:02d} (Tentativa {attempt}/{retries})...")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            else:
                logger.warning(f"Resposta inesperada para {year}/{month:02d}. Esperado lista, obtido {type(data)}.")
                return []
        except requests.RequestException as e:
            logger.error(f"Erro na requisição para {year}/{month:02d}: {e}")
            if attempt == retries:
                raise
            time.sleep(backoff_factor ** attempt)
    return []

def download_month(year: int, month: int) -> None:
    """
    Baixa os dados de um único mês e salva no formato json raw.
    """
    file_path = os.path.join(RAW_DATA_DIR, f"{year}_{month:02d}.json")
    
    # Se o arquivo já existe e é de um ano passado (imutável), pulamos
    if os.path.exists(file_path) and year < 2026:
        logger.info(f"Dados de {year}/{month:02d} já existem localmente. Pulando.")
        return
        
    try:
        data = fetch_month_data(year, month)
        if data:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Dados salvos com sucesso em {file_path}")
    except Exception as e:
        logger.error(f"Falha ao processar {year}/{month:02d}: {e}")

def run_ingestion(start_year: int = 2023, end_year: int = 2026, max_workers: int = 6):
    """
    Executa a ingestão concorrente de dados históricos da API e salva na pasta raw local.
    """
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    # Gerar a lista de tarefas (ano, mês)
    tasks = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            tasks.append((year, month))
            
    logger.info(f"Iniciando download concorrente de {len(tasks)} meses utilizando {max_workers} threads...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_month, y, m): (y, m) for y, m in tasks}
        for future in as_completed(futures):
            y, m = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Erro na execução da thread para {y}/{m:02d}: {e}")

if __name__ == "__main__":
    logger.info("Iniciando ingestão manual de dados...")
    run_ingestion()
    logger.info("Ingestão concluída!")

