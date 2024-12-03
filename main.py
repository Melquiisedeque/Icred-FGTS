import requests
from flask import Flask, request, jsonify
import logging
import json

# Configurar o logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações da API e do webhook
TOKEN_URL = "https://api-hml.icred.app/authorization-server/oauth2/token"
CLIENT_ID = "sb-integration"
CLIENT_SECRET = "6698c059-3092-41d1-a218-5f03b5d1e37f"
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/DcB0aQaTyUe4/"

# Inicializar o Flask
app = Flask(__name__)

# Função para gerar token
def generate_token():
    logger.info("Gerando novo token...")
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(CLIENT_ID, CLIENT_SECRET)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "client_credentials",
        "scope": "default fgts",
    }
    response = requests.post(TOKEN_URL, headers=headers, data=payload)
    if response.status_code == 200:
        token_data = response.json()
        logger.info("Token gerado com sucesso!")
        return token_data["access_token"]
    else:
        logger.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
        raise Exception(f"Erro ao gerar o token: {response.status_code} - {response.text}")

# Endpoint de simulação
@app.route('/simulation', methods=['POST'])
def simulation():
    try:
        # Receber dados do Bot Conversa
        data = request.get_json()
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = str(data.get("phone"))  # Converter para string

        logger.info(f"Dados recebidos: CPF={cpf}, Data de Nascimento={birthdate}, Telefone={phone}")

        # Gerar token
        token = generate_token()

        # Simulação
        simulation_url = "https://api-hml.icred.app/fgts/v1/max-simulation"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
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

        logger.info("Enviando requisição de simulação...")
        response = requests.post(simulation_url, headers=headers, json=payload)

        if response.status_code == 200:
            simulation_data = response.json()
            logger.info("Simulação realizada com sucesso!")
            # Enviar os dados ao webhook
            send_to_webhook(simulation_data)
            return jsonify(simulation_data)
        else:
            logger.error(f"Erro ao realizar a simulação: {response.status_code} - {response.text}")
            return jsonify({"error": "Erro ao realizar a simulação", "details": response.text}), 500

    except Exception as e:
        logger.error(f"Erro: {e}")
        return jsonify({"error": str(e)}), 500

# Função para enviar dados ao webhook
def send_to_webhook(data):
    try:
        logger.info("Enviando resultado ao webhook...")
        response = requests.post(WEBHOOK_URL, json=data, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            logger.info("Dados enviados ao webhook com sucesso!")
        else:
            logger.error(f"Erro ao enviar os dados ao webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Erro ao enviar ao webhook: {e}")

# Iniciar o servidor Flask
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
