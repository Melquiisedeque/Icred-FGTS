from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime, timedelta
import os
import logging
import time

app = Flask(__name__)

# Configuração do log
logging.basicConfig(level=logging.INFO)

# Caminho do arquivo token.json
TOKEN_FILE = "token.json"

# URL do webhook final
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/DcB0aQaTyUe4/"


def generate_and_save_token():
    """Gera um novo token e salva no arquivo."""
    logging.info("Gerando um novo token...")
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
        raise Exception("Não foi possível gerar o token.")


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
        logging.warning("Token não encontrado ou inválido. Gerando um novo...")
        return generate_and_save_token()


def send_to_webhook(data):
    """Envia os dados para o webhook."""
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        if response.status_code == 200:
            logging.info("Dados enviados com sucesso ao webhook.")
        else:
            logging.error(f"Erro ao enviar os dados ao webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao tentar enviar os dados ao webhook: {str(e)}")


@app.route("/simulation", methods=["POST"])
def simulation():
    """Endpoint principal para processar a simulação."""
    try:
        # Recebe os dados enviados
        data = request.json
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = data.get("phone")

        logging.info(f"Dados recebidos: CPF={cpf}, Data de Nascimento={birthdate}, Telefone={phone}")

        # Carrega ou gera o token
        token = load_token()

        # Envia a simulação
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

        response = requests.post(simulation_url, headers=headers, json=payload)
        if response.status_code == 200:
            simulation_data = response.json()
            logging.info("Simulação realizada com sucesso.")
            send_to_webhook(simulation_data)  # Envia os dados ao webhook
            return jsonify({"status": "success", "data": simulation_data})
        else:
            logging.error(f"Erro ao realizar a simulação: {response.status_code} - {response.text}")
            return jsonify({"status": "error", "message": "Erro ao realizar a simulação."}), 500

    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
