from flask import Flask, request, jsonify
import requests
import logging
import time
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO)

# Configuração da API
TOKEN_URL = "https://api-hml.icred.app/authorization-server/oauth2/token"
SIMULATION_URL = "https://api-hml.icred.app/fgts/v1/max-simulation"
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/DcB0aQaTyUe4/"
CLIENT_ID = "sb-integration"
CLIENT_SECRET = "6698c059-3092-41d1-a218-5f03b5d1e37f"
GRANT_TYPE = "client_credentials"
SCOPE = "default fgts"

# Inicializando o Flask
app = Flask(__name__)

# Variável global para armazenar o token
global_token = None

def get_token():
    """Gera um token de acesso usando as credenciais."""
    global global_token
    logging.info("Iniciando geração de token...")

    # Cabeçalhos e payload da requisição
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(CLIENT_ID, CLIENT_SECRET)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": GRANT_TYPE,
        "scope": SCOPE,
    }

    try:
        response = requests.post(TOKEN_URL, headers=headers, data=payload)

        if response.status_code == 200:
            global_token = response.json()["access_token"]
            logging.info("Token gerado com sucesso.")
            return global_token
        else:
            logging.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
            raise Exception("Não foi possível gerar o token.")

    except Exception as e:
        logging.error(f"Erro ao gerar o token: {e}")
        raise

def send_to_webhook(data):
    """Envia os dados para o webhook."""
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        if response.status_code == 200:
            logging.info("Dados enviados ao webhook com sucesso.")
        else:
            logging.error(f"Erro ao enviar ao webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao enviar ao webhook: {e}")

def perform_simulation(cpf, birthdate, phone):
    """Realiza a simulação."""
    logging.info("Iniciando a simulação...")
    headers = {
        "Authorization": f"Bearer {global_token}",
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

    try:
        response = requests.post(SIMULATION_URL, headers=headers, json=payload)

        if response.status_code == 200:
            logging.info("Simulação realizada com sucesso.")
            return response.json()
        else:
            logging.error(f"Erro ao realizar a simulação: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logging.error(f"Erro ao realizar a simulação: {e}")
        return None

@app.route("/simulation", methods=["POST"])
def simulation_route():
    """Rota principal para receber os dados e realizar a simulação."""
    data = request.json
    logging.info(f"Dados recebidos: CPF={data.get('cpf')}, Birthdate={data.get('birthdate')}, Phone={data.get('phone')}")

    # Tentativas para gerar token e realizar simulação
    for attempt in range(1, 11):
        try:
            if global_token is None:
                get_token()  # Gera o token caso não exista

            # Realiza a simulação
            simulation_result = perform_simulation(data["cpf"], data["birthdate"], data["phone"])
            if simulation_result:
                # Envia o resultado para o webhook
                send_to_webhook(simulation_result)
                return jsonify({"status": "success", "message": "Simulação realizada com sucesso!"}), 200
            else:
                logging.warning(f"Tentativa {attempt} falhou: Erro na simulação.")
        except Exception as e:
            logging.warning(f"Tentativa {attempt} falhou: {e}")

        time.sleep(10)  # Espera 10 segundos entre as tentativas

    return jsonify({"status": "error", "message": "Não foi possível realizar a simulação após 10 tentativas."}), 500

if __name__ == "__main__":
    # Executa o Flask
    logging.info("Inicializando o servidor Flask.")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
