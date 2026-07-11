import os
import logging
from dagster import asset, Definitions, AssetExecutionContext, MetadataValue
import pandas as pd

from src.ingestion import run_ingestion
from src.transformation import run_transformation, PROCESSED_FILE_PATH
from src.training import run_training
from src.drift_monitoring import run_drift_monitoring

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asset(group_name="church_calendar_pipeline")
def raw_calendar_data(context: AssetExecutionContext) -> None:
    """
    Asset de Ingestão: Baixa os dados brutos da Church Calendar API e salva localmente como arquivos JSON.
    """
    context.log.info("Iniciando ingestão de dados da API...")
    run_ingestion(start_year=2023, end_year=2026)
    
    # Adicionar metadados à execução do Dagster
    raw_files = os.listdir("data/raw") if os.path.exists("data/raw") else []
    context.add_output_metadata(
        metadata={
            "num_files_ingested": len(raw_files),
            "raw_dir": MetadataValue.path("data/raw")
        }
    )

@asset(deps=[raw_calendar_data], group_name="church_calendar_pipeline")
def processed_calendar_data(context: AssetExecutionContext) -> pd.DataFrame:
    """
    Asset de Transformação e Qualidade: Lê os dados brutos, valida os schemas usando Pydantic,
    executa engenharia de features e salva um CSV limpo.
    """
    context.log.info("Iniciando transformação e validação de dados...")
    run_transformation()
    
    # Carregar o DataFrame resultante para expor metadados
    df = pd.read_csv(PROCESSED_FILE_PATH)
    
    # Estatísticas de cores litúrgicas para expor no Dagster
    color_distribution = df["colour"].value_counts().to_dict()
    
    context.add_output_metadata(
        metadata={
            "num_rows": len(df),
            "columns": list(df.columns),
            "color_distribution": str(color_distribution),
            "processed_file": MetadataValue.path(PROCESSED_FILE_PATH)
        }
    )
    return df

@asset(deps=[processed_calendar_data], group_name="church_calendar_pipeline")
def trained_model(context: AssetExecutionContext) -> None:
    """
    Asset de Machine Learning: Treina o classificador RandomForest,
    rastreia métricas e parâmetros no MLflow e salva o modelo localmente.
    """
    context.log.info("Iniciando treinamento do modelo e registro no MLflow...")
    # Treinar o modelo com hiperparâmetros padrão do pipeline
    run_training(n_estimators=120, max_depth=10)
    
    # Ler os metadados do modelo salvos localmente
    model_metadata_path = "models/liturgical_model/metadata.json"
    if os.path.exists(model_metadata_path):
        import json
        with open(model_metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            classes = meta.get("classes", [])
    else:
        classes = []

    context.add_output_metadata(
        metadata={
            "model_path": MetadataValue.path("models/liturgical_model/model.pkl"),
            "classes_predicted": len(classes),
            "mlflow_experiment": "church-calendar-color"
        }
    )

@asset(deps=[processed_calendar_data], group_name="church_calendar_pipeline")
def drift_report(context: AssetExecutionContext) -> None:
    """
    Asset de Monitoramento de Drift: Compara os dados de 2024 contra 2025/2026
    gerando um relatório Evidently em HTML.
    """
    context.log.info("Iniciando geração do relatório de Data Drift...")
    run_drift_monitoring()
    
    report_path = "data/reports/drift_report.html"
    context.add_output_metadata(
        metadata={
            "report_file": MetadataValue.path(report_path)
        }
    )

# Definições do Dagster que expõem os Assets
defs = Definitions(
    assets=[raw_calendar_data, processed_calendar_data, trained_model, drift_report],
)
