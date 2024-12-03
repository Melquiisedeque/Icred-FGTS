from flask import Flask, request, jsonify
import requests
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
            return generate_and_save_token()
        return token_data["access_token"]
    except (FileNotFoundError, KeyError):
        return generate_and_save_token()


# Rota principal para simulação
@app.route("/simulation", methods=["POST"])
def simulation():
    try:
        data = request.json
        cpf = data["cpf"]
        birthdate = data["birthdate"]
        phone = data["phone"]
        webhook = data["webhook"]

        logging.info(f"Dados recebidos: CPF={cpf}, Birthdate={birthdate}, Phone={phone}")

        # Carregar token
        token = load_token()

        # Configurar requisição de simulação
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

        # Fazer a requisição de simulação
        response = requests.post(simulation_url, headers=headers, json=payload)
        if response.status_code == 200:
            simulation_result = response.json()
            logging.info(f"Simulação realizada com sucesso: {simulation_result}")

            # Enviar dados ao webhook
            webhook_payload = {
                "status": "success",
                "cpf": cpf,
                "result": simulation_result
            }
            webhook_response = requests.post(webhook, json=webhook_payload)
            if webhook_response.status_code == 200:
                logging.info("Dados enviados ao webhook com sucesso.")
                return jsonify({"status": "success", "message": "Simulação realizada e enviada ao webhook."}), 200
            else:
                logging.error(f"Erro ao enviar dados ao webhook: {webhook_response.status_code} - {webhook_response.text}")
                return jsonify({"status": "error", "message": "Erro ao enviar dados ao webhook."}), 500
        else:
            logging.error(f"Erro ao realizar a simulação: {response.status_code} - {response.text}")
            return jsonify({"status": "error", "message": "Erro ao realizar a simulação.", "details": response.text}), 500
    except Exception as e:
        logging.error(f"Erro: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    logging.info("Inicializando o servidor Flask.")
    app.run(host="0.0.0.0", port=5001)
