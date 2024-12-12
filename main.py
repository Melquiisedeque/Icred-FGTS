import requests
from flask import Flask, request, jsonify
import logging
import json
import time

# Configurações
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/ruhxOAwTgPFD/"
TOKEN_FILE = "token.json"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Funções auxiliares
def generate_and_save_token():
    """Gera um novo token e salva no arquivo."""
    logging.info("Gerando um novo token...")
    url = "https://api-hml.icred.app/authorization-server/oauth2/token"
    client_id = "sb-integration"
    client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(client_id, client_secret)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials", "scope": "default fgts"}
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        token_data = response.json()
        with open(TOKEN_FILE, "w") as file:
            json.dump(token_data, file)
        logging.info("Token gerado e salvo com sucesso.")
        return token_data["access_token"]
    else:
        logging.error(f"Erro ao gerar token: {response.status_code} - {response.text}")
        return None


def load_token():
    """Carrega o token do arquivo."""
    try:
        with open(TOKEN_FILE, "r") as file:
            token_data = json.load(file)
            return token_data["access_token"]
    except (FileNotFoundError, KeyError):
        logging.info("Token não encontrado ou inválido. Gerando um novo token.")
        return generate_and_save_token()


def send_to_webhook(data):
    """Envia os dados da simulação para o webhook configurado."""
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        if response.status_code == 200:
            logging.info("Dados enviados ao webhook com sucesso.")
        else:
            logging.error(f"Erro ao enviar para o webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao conectar ao webhook: {str(e)}")


# Endpoint de Simulação
@app.route("/simulation", methods=["POST"])
def simulation():
    try:
        # Obtém os dados da requisição
        data = request.json
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = data.get("phone")

        logging.info(f"Dados recebidos: CPF={cpf}, Data de Nascimento={birthdate}, Telefone={phone}")

        # Valida o token
        token = load_token()
        if not token:
            return jsonify({"status": "error", "message": "Não foi possível gerar o token"}), 500

        # Faz a simulação
        simulation_url = "https://api-hml.icred.app/fgts/v1/simulation"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "cpf": cpf,
            "birthdate": birthdate,
            "phone": phone,
        }

        response = requests.post(simulation_url, json=payload, headers=headers)
        if response.status_code == 200:
            simulation_data = response.json()
            logging.info(f"Simulação realizada com sucesso: {simulation_data}")

            # Envia os dados para o Webhook
            send_to_webhook(simulation_data)
            return jsonify({"status": "success", "simulation": simulation_data}), 200
        else:
            logging.error(f"Erro na simulação: {response.status_code} - {response.text}")
            return jsonify({"status": "error", "message": "Erro ao realizar a simulação"}), 500
    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
