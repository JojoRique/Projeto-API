import pytest
from unittest.mock import patch, MagicMock
import requests
from src.ingestion import fetch_month_data

def test_fetch_month_data_success():
    """
    Testa se a função de busca retorna dados corretos em caso de sucesso da API.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"date": "2026-07-11", "season": "ordinary"}]
    
    with patch("requests.get", return_value=mock_response) as mock_get:
        data = fetch_month_data(2026, 7)
        assert len(data) == 1
        assert data[0]["date"] == "2026-07-11"
        assert data[0]["season"] == "ordinary"
        mock_get.assert_called_once_with(
            "http://calapi.inadiutorium.cz/api/v0/en/calendars/default/2026/7",
            timeout=15
        )

def test_fetch_month_data_retry_and_success():
    """
    Testa se a função faz retries em caso de falha de conexão e depois obtém sucesso.
    """
    mock_response_fail = MagicMock()
    mock_response_fail.raise_for_status.side_effect = requests.RequestException("Erro temporário")
    
    mock_response_ok = MagicMock()
    mock_response_ok.status_code = 200
    mock_response_ok.json.return_value = [{"date": "2026-07-11"}]
    
    # Simular uma falha seguida de sucesso
    with patch("requests.get", side_effect=[requests.RequestException("Timeout"), mock_response_ok]) as mock_get:
        with patch("time.sleep", return_value=None):  # Acelerar o backoff
            data = fetch_month_data(2026, 7, retries=2, backoff_factor=0.1)
            assert len(data) == 1
            assert mock_get.call_count == 2
