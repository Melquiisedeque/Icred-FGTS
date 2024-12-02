import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
import base64
from threading import Thread
import logging

# Configuração de logging detalhado
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

TOKEN_FILE = "token.json"  # Arquivo para salvar o token
BOTCONVERSA_UPDATE_WEBHOOK = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/C587dNQFi2cS/"
NGROK_PORT = 5001  # Porta do servidor Flask


def get_ngrok_url():
    """Obtém o link público do ngrok."""
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        response.raise_for_status()
        data = response.json()
        ngrok_url = data["tunnels"][0]["public_url"]
        logging.info(f"Link do ngrok obtido: {ngrok_url}")
        return ngrok_url
    except Exception as e:
        logging.error(f"Erro ao obter o link do ngrok: {e}")
        return None


def update_botconversa_webhook(ngrok_url):
    """Atualiza o webhook do BotConversa com a parte dinâmica do ngrok."""
    headers = {"Content-Type": "application/json"}

    # Extrair somente a variável dinâmica do domínio ngrok
    ngrok_subdomain = ngrok_url.replace("https://", "").replace(".ngrok-free.app", "")

    payload = {
        "ngrok_subdomain": ngrok_subdomain  # Envia somente a parte dinâmica
    }

    try:
        response = requests.post(BOTCONVERSA_UPDATE_WEBHOOK, json=payload, headers=headers)
        if response.status_code == 200:
            logging.info("Webhook atualizado com sucesso no BotConversa!")
        else:
            logging.error(f"Erro ao atualizar o webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao enviar dados ao BotConversa: {e}")


@app.route('/simulation', methods=['POST'])
def simulation():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            return jsonify({"error": "Invalid content type. Expecting JSON."}), 400

        cpf = data.get('cpf')
        birthdate = data.get('birthdate')
        full_phone = data.get('fullPhone')
        webhook_url = data.get('webhook_url')

        if not cpf or not birthdate or not full_phone or not webhook_url:
            return jsonify({"error": "Missing required fields"}), 400

        logging.info(f"Dados recebidos: CPF={cpf}, Birthdate={birthdate}, Phone={full_phone}, Webhook={webhook_url}")

        def process_simulation():
            try:
                bearer_token = load_token()
                if not bearer_token:
                    logging.error("Erro na autenticação: Falha ao obter token.")
                    return
                simulation_result = perform_simulation(cpf, birthdate, full_phone, bearer_token)
                if "error" not in simulation_result:
                    send_to_webhook(simulation_result, webhook_url)
                else:
                    logging.error(f"Erro na simulação: {simulation_result['error']}")
            except Exception as e:
                logging.error(f"Erro ao processar simulação: {str(e)}")

        Thread(target=process_simulation).start()

        return jsonify({"message": "Request received. Processing simulation."}), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def generate_and_save_token():
    """Gera um novo token e salva em arquivo."""
    api_url = "https://api-hml.icred.app/authorization-server/oauth2/token"
    client_id = "sb-integration"
    client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"
    grant_type = "client_credentials"
    scope = "default fgts"

    auth_string = f"{client_id}:{client_secret}"
    auth_base64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_base64}",
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
        logging.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
        return None


def load_token():
    """Carrega o token e verifica validade."""
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
        logging.info("Token não encontrado ou inválido. Gerando um novo...")
        return generate_and_save_token()


def perform_simulation(cpf, birthdate, full_phone, bearer_token):
    """Realiza a simulação com os dados fornecidos."""
    api_url = "https://api-hml.icred.app/fgts/v1/max-simulation"

    if len(full_phone) == 13 and full_phone.startswith("55"):
        country_code = full_phone[:2]
        area_code = full_phone[2:4]
        phone_number = full_phone[4:]
    else:
        return {"error": "Telefone inválido. Verifique o formato do número enviado."}

    payload = {
        "personCode": cpf,
        "birthdate": birthdate,
        "numberOfInstallments": 12,
        "productIds": [20],
        "sellerPersonCode": cpf,
        "creditorId": -3,
        "phone": {
            "areaCode": area_code,
            "number": phone_number,
            "countryCode": country_code
        }
    }

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(api_url, json=payload, headers=headers)
    if response.status_code == 200:
        logging.info("Simulação criada com sucesso!")
        return response.json()
    else:
        logging.error(f"Erro ao realizar a simulação: {response.status_code} - {response.text}")
        return {"error": response.text}


def send_to_webhook(data, webhook_url):
    """Envia os resultados da simulação para o webhook configurado."""
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(webhook_url, json=data, headers=headers)
        if response.status_code == 200:
            logging.info(f"Dados enviados ao webhook com sucesso: {response.status_code}")
        else:
            logging.error(f"Erro ao enviar ao webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao enviar dados ao webhook: {e}")


if __name__ == "__main__":
    logging.info("Inicializando o servidor Flask e atualizando o webhook...")
    # Verifica se o ngrok está ativo
    ngrok_url = get_ngrok_url()
    if ngrok_url:
        logging.info(f"Link do ngrok: {ngrok_url}")
        update_botconversa_webhook(ngrok_url)
    else:
        logging.error("Não foi possível obter o link do ngrok.")
    app.run(port=NGROK_PORT)
