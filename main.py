import os
import time
import json  # Corrigido: Adicionado o módulo json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN_FILE = "token.json"
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/DcB0aQaTyUe4/"


def generate_token():
    """Função para gerar o token de autenticação."""
    api_url = "https://api-hml.icred.app/authorization-server/oauth2/token"
    client_id = "sb-integration"
    client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(client_id, client_secret)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "client_credentials",
        "scope": "default fgts",
    }

    response = requests.post(api_url, headers=headers, data=payload)
    if response.status_code == 200:
        token_data = response.json()
        token_data["generated_at"] = time.time()
        with open(TOKEN_FILE, "w") as token_file:
            json.dump(token_data, token_file, indent=4)
        return token_data["access_token"]
    else:
        raise Exception(f"Erro ao gerar o token: {response.status_code} - {response.text}")


def get_token():
    """Função para carregar ou gerar o token."""
    if not os.path.exists(TOKEN_FILE):
        return generate_token()

    with open(TOKEN_FILE, "r") as token_file:
        token_data = json.load(token_file)

    expires_in = token_data.get("expires_in", 0)
    generated_at = token_data.get("generated_at", 0)

    if time.time() > (generated_at + expires_in):
        return generate_token()
    return token_data["access_token"]


@app.route("/simulation", methods=["POST"])
def simulation():
    """Endpoint para receber dados e realizar a simulação."""
    try:
        data = request.json
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = data.get("phone")

        if not all([cpf, birthdate, phone]):
            return jsonify({"error": "Dados insuficientes para realizar a simulação."}), 400

        token = get_token()

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
            requests.post(WEBHOOK_URL, json=simulation_data)
            return jsonify({"message": "Simulação realizada com sucesso!", "simulation": simulation_data}), 200
        else:
            return jsonify({"error": f"Erro na simulação: {response.status_code}", "details": response.text}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
