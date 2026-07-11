import os
import logging
import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

PROCESSED_FILE_PATH = "data/processed/clean_calendar.csv"
REPORT_DIR = "data/reports"
REPORT_FILE_PATH = os.path.join(REPORT_DIR, "drift_report.html")

def run_drift_monitoring():
    """
    Compara dados de referência (2024) com dados atuais (2025/2026) para detectar Data Drift usando Evidently.
    """
    if not os.path.exists(PROCESSED_FILE_PATH):
        logger.error(f"Arquivo de dados processados {PROCESSED_FILE_PATH} não encontrado. Execute a transformação primeiro.")
        return
        
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    # 1. Carregar dados
    df = pd.read_csv(PROCESSED_FILE_PATH)
    
    # Separar os conjuntos para análise de drift
    # Dados de 2024 servirão como nossa referência (baseline / treino original)
    # Dados de 2025/2026 serão os dados atuais (produção)
    reference_data = df[df["year"] == 2024].copy()
    current_data = df[df["year"] >= 2025].copy()
    
    if reference_data.empty:
        logger.warning("Conjunto de dados de referência (2024) está vazio. Usando os primeiros 40% do dataset como referência.")
        # Fallback se não houver dados de 2024
        split_idx = int(len(df) * 0.4)
        reference_data = df.iloc[:split_idx].copy()
        current_data = df.iloc[split_idx:].copy()
        
    if current_data.empty:
        logger.error("Sem dados atuais suficientes (2025/2026) para comparar data drift.")
        return
        
    logger.info(f"Monitoramento de Drift: Referência = {len(reference_data)} linhas, Atual = {len(current_data)} linhas.")
    
    # Colunas de interesse para monitoramento de drift
    features_to_monitor = ["season", "season_week", "weekday", "month", "day", "colour"]
    
    # 2. Configurar o relatório do Evidently
    # DataDriftPreset calcula estatísticas de drift para todas as colunas
    drift_report = Report(metrics=[DataDriftPreset()])
    
    logger.info("Calculando métricas de Data Drift...")
    drift_report.run(
        reference_data=reference_data[features_to_monitor],
        current_data=current_data[features_to_monitor]
    )
    
    # 3. Salvar relatório em HTML
    drift_report.save_html(REPORT_FILE_PATH)
    logger.info(f"Relatório de Data Drift salvo com sucesso em {REPORT_FILE_PATH}")

if __name__ == "__main__":
    logger.info("Executando monitoramento de Data Drift...")
    run_drift_monitoring()
    logger.info("Monitoramento de Data Drift finalizado!")
