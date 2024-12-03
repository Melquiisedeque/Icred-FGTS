import requests
import os
import json
import time
from flask import Flask, request, jsonify

# Inicialização do aplicativo Flask
app = Flask(__name__)

TOKEN_FILE = "token.json"  # Nome do arquivo para salvar o token
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/DcB0aQaTyUe4/"


def generate_and_save_token():
    """Gera um novo token e salva em arquivo."""
    api_url = "https://api-hml.icred.app/authorization-server/oauth2/token"
    client_id = "sb-integration"  # Substitua pelo seu client_id
    client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"  # Substitua pelo seu client_secret

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
        with open(TOKEN_FILE, "w") as file:
            json.dump(token_data, file)
        return token_data["access_token"]
    else:
        raise Exception(f"Erro ao gerar o token: {response.status_code} - {response.text}")


def load_token():
    """Carrega o token existente ou gera um novo se necessário."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as file:
            token_data = json.load(file)
        if time.time() < token_data["generated_at"] + token_data["expires_in"]:
            return token_data["access_token"]
    return generate_and_save_token()


def send_to_webhook(data):
    """Envia os dados para o webhook."""
    response = requests.post(WEBHOOK_URL, json=data)
    if response.status_code == 200:
        print("Dados enviados com sucesso ao webhook.")
    else:
        print(f"Erro ao enviar ao webhook: {response.status_code} - {response.text}")


@app.route("/simulation", methods=["POST"])
def simulation():
    """Rota principal para processar a simulação."""
    try:
        content = request.json
        cpf = content.get("cpf")
        birthdate = content.get("birthdate")
        phone = content.get("phone")

        print(f"Dados recebidos: CPF={cpf}, Birthdate={birthdate}, Phone={phone}")

        token = load_token()
        print("Token carregado com sucesso.")

        simulation_url = "https://api-hml.icred.app/fgts/v1/max-simulation"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "personCode": cpf,
            "birthdate": birthdate,
            "numberOfInstallments": 12,
            "productIds": [20],
            "sellerPersonCode": cpf,
            "creditorId": -3,
            "phone": {
                "areaCode": phone[2:4],
                "number": phone[4:],
                "countryCode": phone[:2]
            }
        }

        for attempt in range(1, 11):
            response = requests.post(simulation_url, headers=headers, json=payload)
            if response.status_code == 200:
                simulation_data = response.json()
                print("Simulação criada com sucesso.")
                send_to_webhook(simulation_data)
                return jsonify(simulation_data)
            else:
                print(f"Tentativa {attempt} falhou: {response.status_code} - {response.text}")
                time.sleep(10)
        return jsonify({"error": "Não foi possível completar a simulação após 10 tentativas."}), 500
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
