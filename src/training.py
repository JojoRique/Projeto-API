import os
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, ConfusionMatrixDisplay
import mlflow
import mlflow.sklearn
import pickle

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

PROCESSED_FILE_PATH = "data/processed/clean_calendar.csv"
MODEL_DIR = "models/liturgical_model"

# Mapeamentos fixos para codificação categórica
SEASON_MAP = {
    "ordinary": 0,
    "lent": 1,
    "advent": 2,
    "easter": 3,
    "christmas": 4
}

WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6
}

def preprocess_for_ml(df: pd.DataFrame):
    """
    Realiza pré-processamento, encoding de variáveis categóricas e separa features do target.
    """
    df_ml = df.copy()
    
    # Aplicar mapeamentos categóricos
    df_ml["season_code"] = df_ml["season"].map(SEASON_MAP).fillna(-1).astype(int)
    df_ml["weekday_code"] = df_ml["weekday"].map(WEEKDAY_MAP).fillna(-1).astype(int)
    
    # Features e Target
    features = ["season_code", "season_week", "weekday_code", "month", "day", "day_of_year", "is_sunday"]
    target = "colour"
    
    X = df_ml[features]
    y = df_ml[target]
    
    return X, y, df_ml[target].unique().tolist()

def run_training(n_estimators: int = 100, max_depth: int = 8):
    """
    Treina o modelo de Machine Learning, gera métricas e rastreia o experimento usando o MLflow.
    """
    if not os.path.exists(PROCESSED_FILE_PATH):
        logger.error(f"Arquivo transformado {PROCESSED_FILE_PATH} não encontrado. Execute a transformação primeiro.")
        return
        
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # 1. Carregar dados
    df = pd.read_csv(PROCESSED_FILE_PATH)
    
    # 2. Pré-processar
    X, y, classes = preprocess_for_ml(df)
    
    # Codificar o Target para valores numéricos para o modelo de treino
    # (Usar mapeamento do target para poder decodificar depois)
    unique_classes = sorted(list(set(y)))
    class_to_idx = {name: idx for idx, name in enumerate(unique_classes)}
    idx_to_class = {idx: name for idx, name in enumerate(unique_classes)}
    y_encoded = y.map(class_to_idx)
    
    # Salvar metadados do modelo
    metadata = {
        "season_map": SEASON_MAP,
        "weekday_map": WEEKDAY_MAP,
        "classes": unique_classes,
        "idx_to_class": idx_to_class,
        "class_to_idx": class_to_idx
    }
    with open(os.path.join(MODEL_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # Split treino / teste
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)
    
    # Configurar MLflow localmente
    mlflow.set_experiment("church-calendar-color")
    
    with mlflow.start_run():
        logger.info("Iniciando treinamento do RandomForestClassifier...")
        
        # Treinar o classificador
        clf = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
        clf.fit(X_train, y_train)
        
        # Predições
        y_pred = clf.predict(X_test)
        
        # Métricas
        acc = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="weighted")
        
        logger.info(f"Modelo treinado com sucesso! Acurácia no teste: {acc:.4f}, F1-score: {f1:.4f}")
        
        # Logar Parâmetros e Métricas no MLflow
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("max_depth", max_depth)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1_score", f1)
        
        # Gerar e Salvar Matriz de Confusão
        fig, ax = plt.subplots(figsize=(8, 6))
        cm = confusion_matrix(y_test, y_pred)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=[idx_to_class[i] for i in clf.classes_])
        disp.plot(cmap=plt.cm.Blues, ax=ax, xticks_rotation=45)
        plt.title("Matriz de Confusão — Cores Litúrgicas")
        plt.tight_layout()
        
        cm_path = os.path.join(MODEL_DIR, "confusion_matrix.png")
        plt.savefig(cm_path)
        plt.close()
        
        # Logar Matriz de Confusão e metadados no MLflow como artefatos
        mlflow.log_artifact(cm_path)
        mlflow.log_artifact(os.path.join(MODEL_DIR, "metadata.json"))
        
        # Logar o modelo Scikit-Learn
        mlflow.sklearn.log_model(clf, "model", registered_model_name="ChurchCalendarModel")
        
        # Salvar o modelo em arquivo binário local para o FastAPI
        with open(os.path.join(MODEL_DIR, "model.pkl"), "wb") as f:
            pickle.dump(clf, f)
            
        logger.info("Modelo e artefatos de treinamento salvos e registrados no MLflow.")

if __name__ == "__main__":
    logger.info("Executando treino do modelo...")
    run_training()
    logger.info("Treinamento finalizado!")
