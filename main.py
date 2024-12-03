from flask import Flask, request, jsonify
import requests
import time
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TOKEN_URL = "https://api-hml.icred.app/authorization-server/oauth2/token"
SIMULATION_URL = "https://api-hml.icred.app/fgts/v1/max-simulation"
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/DcB0aQaTyUe4/"

CLIENT_ID = "sb-integration"
CLIENT_SECRET = "6698c059-3092-41d1-a218-5f03b5d1e37f"
SCOPE = "default fgts"
GRANT_TYPE = "client_credentials"

# Token global para reutilização
global_token = None

# Função para obter ou atualizar o token
def get_token():
    global global_token
    if global_token is None:
        response = requests.post(
            TOKEN_URL,
            headers={
                "Authorization": f"Basic {requests.auth._basic_auth_str(CLIENT_ID, CLIENT_SECRET)}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": GRANT_TYPE, "scope": SCOPE},
        )
        if response.status_code == 200:
            global_token = response.json()["access_token"]
            logging.info("Token gerado com sucesso.")
        else:
            logging.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
            raise Exception("Não foi possível gerar o token.")
    return global_token

# Função para processar a simulação
def process_simulation(cpf, birthdate, phone):
    token = get_token()
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

    logging.info("Enviando requisição de simulação...")
    response = requests.post(SIMULATION_URL, json=payload, headers=headers)

    if response.status_code == 200:
        simulation_data = response.json()
        logging.info(f"Simulação realizada com sucesso: {simulation_data}")
        return simulation_data
    else:
        logging.error(f"Erro ao realizar a simulação: {response.status_code} - {response.text}")
        raise Exception("Erro ao realizar a simulação.")

# Rota para receber os dados
@app.route("/simulation", methods=["POST"])
def simulation():
    try:
        data = request.json
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = data.get("phone")

        if not all([cpf, birthdate, phone]):
            return jsonify({"status": "error", "message": "Dados incompletos"}), 400

        logging.info(f"Dados recebidos: CPF={cpf}, Birthdate={birthdate}, Phone={phone}")

        # Tentar obter a simulação por até 10 tentativas
        for attempt in range(10):
            try:
                simulation_data = process_simulation(cpf, birthdate, phone)
                return jsonify(simulation_data), 200
            except Exception as e:
                logging.warning(f"Tentativa {attempt + 1} falhou: {e}")
                time.sleep(10)  # Aguardar 10 segundos antes de tentar novamente

        return jsonify({"status": "error", "message": "Simulação falhou após várias tentativas"}), 500

    except Exception as e:
        logging.error(f"Erro: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
