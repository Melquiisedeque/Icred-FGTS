import requests
from flask import Flask, request, jsonify
import time
import logging
import os

# Configuração do log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credenciais
CLIENT_ID = "sb-integration"  # Substitua por suas credenciais
CLIENT_SECRET = "6698c059-3092-41d1-a218-5f03b5d1e37f"
TOKEN_URL = "https://api-hml.icred.app/authorization-server/oauth2/token"
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/DcB0aQaTyUe4/"
MAX_ATTEMPTS = 10  # Máximo de tentativas para token e simulação

app = Flask(__name__)
TOKEN = None  # Variável global para armazenar o token

def generate_token():
    """Gera um novo token usando as credenciais fornecidas."""
    global TOKEN
    logger.info("Tentando gerar um novo token...")
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(CLIENT_ID, CLIENT_SECRET)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}
    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        if response.status_code == 200:
            TOKEN = response.json().get("access_token")
            logger.info("Token gerado com sucesso.")
            return TOKEN
        else:
            logger.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        logger.error(f"Erro na requisição de token: {e}")
        return None

def ensure_token():
    """Garante que o token esteja válido."""
    if not TOKEN:
        return generate_token()
    return TOKEN

def send_webhook(data):
    """Envia os dados da simulação para o webhook."""
    logger.info("Enviando dados para o webhook...")
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        if response.status_code == 200:
            logger.info("Dados enviados com sucesso ao webhook.")
        else:
            logger.error(f"Erro ao enviar para o webhook: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        logger.error(f"Erro ao enviar dados ao webhook: {e}")

@app.route("/simulation", methods=["POST"])
def simulation():
    """Rota principal para processar a simulação."""
    global TOKEN
    cpf = request.json.get("cpf")
    birthdate = request.json.get("birthdate")
    phone = request.json.get("phone")

    if not cpf or not birthdate or not phone:
        return jsonify({"error": "Dados incompletos. CPF, birthdate e phone são obrigatórios."}), 400

    logger.info(f"Dados recebidos: CPF={cpf}, Birthdate={birthdate}, Phone={phone}")

    # Garantir que o token está disponível
    for attempt in range(1, MAX_ATTEMPTS + 1):
        TOKEN = ensure_token()
        if not TOKEN:
            logger.warning(f"Tentativa {attempt} falhou: Não foi possível gerar o token.")
            time.sleep(10)  # Aguardar antes de tentar novamente
            continue

        # Fazer a simulação
        headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
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
                "countryCode": "55",
            },
        }
        try:
            response = requests.post("https://api-hml.icred.app/fgts/v1/max-simulation", headers=headers, json=payload)
            if response.status_code == 200:
                sim_data = response.json()
                logger.info("Simulação realizada com sucesso.")
                send_webhook(sim_data)  # Envia o resultado da simulação ao webhook
                return jsonify({"status": "success", "data": sim_data}), 200
            else:
                logger.error(f"Erro ao realizar a simulação: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logger.error(f"Erro ao realizar a simulação: {e}")

        logger.warning(f"Tentativa {attempt} falhou para a simulação. Retentando em 10 segundos.")
        time.sleep(10)

    # Todas as tentativas falharam
    logger.error("Todas as tentativas de gerar o token ou realizar a simulação falharam.")
    return jsonify({"status": "error", "message": "Não foi possível processar a simulação."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
