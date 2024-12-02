import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
import logging

app = Flask(__name__)

TOKEN_FILE = "token.json"  # Arquivo para salvar o token
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/C587dNQFi2cS/"  # Webhook final

logging.basicConfig(level=logging.INFO)

# Função para gerar e salvar o token
def generate_and_save_token():
    """Gera um novo token e salva em arquivo."""
    try:
        api_url = "https://api-hml.icred.app/authorization-server/oauth2/token"
        client_id = "sb-integration"
        client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"
        grant_type = "client_credentials"
        scope = "default fgts"

        headers = {
            "Authorization": f"Basic {requests.auth._basic_auth_str(client_id, client_secret)}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        payload = {
            "grant_type": grant_type,
            "scope": scope,
        }

        response = requests.post(api_url, headers=headers, data=payload)

        if response.status_code == 200:
            token_data = response.json()
            token_data["generated_at"] = datetime.now().isoformat()

            with open(TOKEN_FILE, "w") as token_file:
                json.dump(token_data, token_file, indent=4)

            logging.info("Token gerado e salvo com sucesso.")
            return token_data["access_token"]
        else:
            logging.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
            raise Exception(f"Erro ao gerar o token: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao gerar o token: {str(e)}")
        raise

# Função para carregar o token
def load_token():
    """Carrega o token do arquivo e verifica validade."""
    try:
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)

        generated_at = datetime.fromisoformat(token_data["generated_at"])
        expires_in = timedelta(seconds=token_data["expires_in"])

        if datetime.now() > generated_at + expires_in:
            logging.info("Token expirado. Gerando um novo...")
            return generate_and_save_token()

        return token_data["access_token"]
    except (FileNotFoundError, KeyError):
        logging.info("Token não encontrado. Gerando um novo...")
        return generate_and_save_token()

# Endpoint para simulação
@app.route('/simulation', methods=['POST'])
def simulation():
    try:
        data = request.json
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = data.get("phone")

        logging.info(f"Dados recebidos: CPF={cpf}, Birthdate={birthdate}, Phone={phone}")

        bearer_token = load_token()

        if not bearer_token:
            return jsonify({"error": "Erro ao carregar o token"}), 500

        api_url = "https://api-hml.icred.app/fgts/v1/max-simulation"

        payload = {
            "personCode": cpf,
            "birthdate": birthdate,
            "numberOfInstallments": 12,
            "productIds": [20],
            "sellerPersonCode": cpf,
            "creditorId": -3,
            "phone": {
                "areaCode": phone[:2],  # Extrair DDD
                "number": phone[2:],  # Extrair número sem DDD
                "countryCode": "55"
            },
        }

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(api_url, json=payload, headers=headers)

        if response.status_code == 200:
            simulation_data = response.json()
            logging.info("Simulação realizada com sucesso.")
            send_to_webhook(simulation_data)  # Envia os dados para o webhook
            return jsonify(simulation_data), 200
        else:
            logging.error(f"Erro ao realizar a simulação: {response.status_code} - {response.text}")
            return jsonify({"error": response.text}), response.status_code

    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Função para enviar os dados para o webhook final
def send_to_webhook(simulation_data):
    """Envia os dados da simulação para o webhook."""
    try:
        response = requests.post(WEBHOOK_URL, json=simulation_data)
        if response.status_code == 200:
            logging.info("Dados enviados com sucesso ao webhook.")
        else:
            logging.error(f"Erro ao enviar dados ao webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao enviar dados ao webhook: {str(e)}")

if __name__ == '__main__':
    logging.info("Inicializando o servidor Flask.")
    app.run(host='0.0.0.0', port=5001)
