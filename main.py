import os
import requests
from flask import Flask, request, jsonify
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Token File Path
TOKEN_FILE = "token.json"

# Webhook URL
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/ruhxOAwTgPFD/"


# Function to get or regenerate token
def get_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as token_file:
                token_data = json.load(token_file)
                token_expiry = datetime.fromisoformat(token_data["generated_at"]) + timedelta(
                    seconds=token_data["expires_in"])
                if datetime.now() < token_expiry:
                    return token_data["access_token"]
        except Exception as e:
            print(f"Erro ao carregar token: {e}")

    # Regenerate token
    return regenerate_token()


def regenerate_token():
    url = "https://api-hml.icred.app/authorization-server/oauth2/token"
    client_id = "sb-integration"
    client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"
    payload = {"grant_type": "client_credentials", "scope": "default fgts"}
    headers = {"Authorization": f"Basic {requests.auth._basic_auth_str(client_id, client_secret)}"}

    for attempt in range(10):  # Attempt to regenerate token up to 10 times
        response = requests.post(url, data=payload, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            token_data["generated_at"] = datetime.now().isoformat()
            with open(TOKEN_FILE, "w") as token_file:
                json.dump(token_data, token_file)
            return token_data["access_token"]
        else:
            print(f"Tentativa {attempt + 1} falhou: {response.text}")
    raise Exception("Não foi possível gerar o token após 10 tentativas.")


# Endpoint for simulation
@app.route("/simulation", methods=["POST"])
def simulation():
    data = request.json
    cpf = data.get("cpf")
    birthdate = data.get("birthdate")
    phone = data.get("phone")

    print(f"Dados recebidos: CPF={cpf}, Data de Nascimento={birthdate}, Telefone={phone}")

    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"personCode": cpf, "birthdate": birthdate,
                   "phone": {"areaCode": phone[:2], "number": phone[2:], "countryCode": "55"}}

        simulation_response = requests.post(
            "https://api-hml.icred.app/fgts/v1/simulations", headers=headers, json=payload
        )

        if simulation_response.status_code == 200:
            simulation_data = simulation_response.json()
            requests.post(WEBHOOK_URL, json=simulation_data)
            return jsonify({"status": "success", "data": simulation_data})
        else:
            return jsonify({"status": "error", "message": simulation_response.text}), 500
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
