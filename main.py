import os
import requests
import json  # Certifique-se de que esta linha esteja presente
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN_FILE = "token.json"

# Função para gerar e salvar o token
def generate_and_save_token():
    api_url = "https://api-hml.icred.app/authorization-server/oauth2/token"
    client_id = "sb-integration"
    client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"
    grant_type = "client_credentials"
    scope = "default fgts"

    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(client_id, client_secret)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {"grant_type": grant_type, "scope": scope}

    response = requests.post(api_url, headers=headers, data=payload)
    if response.status_code == 200:
        token_data = response.json()
        token_data["generated_at"] = datetime.now().isoformat()

        with open(TOKEN_FILE, "w") as token_file:
            json.dump(token_data, token_file, indent=4)

        logging.info("Token gerado e salvo com sucesso.")
        return token_data["access_token"]
    else:
        raise Exception(f"Erro ao gerar o token: {response.status_code} - {response.text}")


# Função para carregar o token
def load_token():
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
        logging.info("Arquivo de token não encontrado. Gerando um novo...")
        return generate_and_save_token()


@app.route("/simulation", methods=["POST"])
def simulation():
    try:
        data = request.json
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = data.get("phone")

        if not all([cpf, birthdate, phone]):
            return jsonify({"error": "Faltam dados obrigatórios"}), 400

        logging.info(f"Dados recebidos: CPF={cpf}, Birthdate={birthdate}, Phone={phone}")

        token = load_token()

        # Fazer a simulação
        api_url = "https://api-hml.icred.app/fgts/v1/max-simulation"
        payload = {
            "personCode": cpf,
            "birthdate": birthdate,
            "numberOfInstallments": 12,
            "productIds": [20],
            "sellerPersonCode": cpf,
            "creditorId": -3,
            "phone": {"areaCode": phone[:2], "number": phone[2:], "countryCode": "55"},
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(api_url, json=payload, headers=headers)
        if response.status_code == 200:
            simulation_data = response.json()
            logging.info("Simulação criada com sucesso.")

            # Retorna os dados diretamente ao BotConversa
            return jsonify(simulation_data)
        else:
            logging.error(f"Erro ao realizar a simulação: {response.status_code} - {response.text}")
            return jsonify({"error": "Erro na simulação", "details": response.json()}), response.status_code

    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
