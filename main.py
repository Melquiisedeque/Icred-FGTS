import requests
import json
import logging
from datetime import datetime, timedelta
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN_FILE = "token.json"
MAX_RETRIES = 10
API_URL = "https://api-hml.icred.app/authorization-server/oauth2/token"
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/ruhxOAwTgPFD/"

CLIENT_ID = "sb-integration"
CLIENT_SECRET = "6698c059-3092-41d1-a218-5f03b5d1e37f"
GRANT_TYPE = "client_credentials"
SCOPE = "default fgts"

# Função para carregar o token
def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as file:
            token_data = json.load(file)
            expires_in = timedelta(seconds=token_data.get("expires_in", 0))
            generated_at = datetime.fromisoformat(token_data.get("generated_at"))
            if datetime.now() < generated_at + expires_in:
                return token_data["access_token"]
            else:
                logger.info("Token expirado. Gerando um novo...")
                return generate_token()
    else:
        return generate_token()

# Função para gerar um novo token
def generate_token():
    payload = {
        "grant_type": GRANT_TYPE,
        "scope": SCOPE
    }
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(CLIENT_ID, CLIENT_SECRET)}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Tentativa {attempt} de gerar token...")
            response = requests.post(API_URL, data=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                token_data = response.json()
                token_data["generated_at"] = datetime.now().isoformat()
                with open(TOKEN_FILE, "w") as file:
                    json.dump(token_data, file, indent=4)
                logger.info("Token gerado com sucesso.")
                return token_data["access_token"]
            else:
                logger.error(f"Erro ao gerar token: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Falha na tentativa {attempt}: {str(e)}")
        
    logger.error("Não foi possível gerar o token após 10 tentativas.")
    return None

# Função para enviar dados ao webhook
def send_to_webhook(data):
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        if response.status_code == 200:
            logger.info("Dados enviados com sucesso ao webhook.")
        else:
            logger.error(f"Erro ao enviar dados ao webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Falha ao enviar dados ao webhook: {str(e)}")

# Rota principal para simulação
def main_simulation(cpf, birthdate, phone):
    token = load_token()
    if not token:
        logger.error("Não foi possível gerar um token válido.")
        return
    
    payload = {
        "personCode": cpf,
        "birthdate": birthdate,
        "numberOfInstallments": 12,
        "productIds": [20],
        "sellerPersonCode": cpf,
        "creditorId": -3,
        "phone": {
            "areaCode": phone[:2],
            "number": phone[2:],
            "countryCode": "55"
        }
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        logger.info("Enviando requisição de simulação...")
        response = requests.post(
            "https://api-hml.icred.app/fgts/v1/max-simulation",
            json=payload,
            headers=headers,
            timeout=20
        )
        if response.status_code == 200:
            result = response.json()
            logger.info("Simulação concluída com sucesso.")
            send_to_webhook(result)
        else:
            logger.error(f"Erro na simulação: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Erro inesperado durante a simulação: {str(e)}")

if __name__ == "__main__":
    cpf = "04901788558"
    birthdate = "1997-10-24"
    phone = "5579998877665"
    main_simulation(cpf, birthdate, phone)
