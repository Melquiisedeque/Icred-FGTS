import os
import time
import requests
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# URL do Webhook
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/DcB0aQaTyUe4/"

# Arquivo do token
TOKEN_FILE = "token.json"

# Função para enviar dados para o webhook
def enviar_webhook(data):
    headers = {"Content-Type": "application/json"}
    try:
        logging.info(f"Enviando dados para o webhook: {WEBHOOK_URL}")
        response = requests.post(WEBHOOK_URL, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            logging.info("Webhook enviado com sucesso!")
        else:
            logging.error(f"Erro ao enviar webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Erro ao enviar webhook: {str(e)}")

# Função para carregar o token de um arquivo
def carregar_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as file:
            return file.read().strip()
    return None

# Função para salvar o token em um arquivo
def salvar_token(token):
    with open(TOKEN_FILE, "w") as file:
        file.write(token)

# Função para gerar um novo token
def gerar_novo_token():
    logging.info("Gerando um novo token...")
    url = "https://api-hml.icred.app/authorization-server/oauth2/token"
    client_id = "sb-integration"
    client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"
    headers = {"Authorization": f"Basic {requests.auth._basic_auth_str(client_id, client_secret)}"}
    data = {"grant_type": "client_credentials", "scope": "default fgts"}
    response = requests.post(url, data=data, headers=headers)

    if response.status_code == 200:
        token_data = response.json()
        salvar_token(token_data["access_token"])
        logging.info("Token gerado com sucesso!")
        return token_data["access_token"]
    else:
        logging.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
        return None

# Função para validar o token
def validar_token(token):
    logging.info("Validando token...")
    # Simulação de validação (substituir com lógica real, se necessário)
    return token is not None

# Função para realizar a simulação
def realizar_simulacao(cpf, birthdate, phone):
    url = "https://api-hml.icred.app/fgts/v1/max-simulation"
    headers = {"Authorization": f"Bearer {carregar_token()}", "Content-Type": "application/json"}
    data = {"cpf": cpf, "birthdate": birthdate, "phone": phone}
    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        logging.info("Simulação realizada com sucesso!")
        return response.json()
    else:
        logging.error(f"Erro na simulação: {response.status_code} - {response.text}")
        return None

@app.route("/simulation", methods=["POST"])
def simulation():
    request_data = request.json
    cpf = request_data.get("cpf")
    birthdate = request_data.get("birthdate")
    phone = request_data.get("phone")

    logging.info(f"Dados recebidos: CPF={cpf}, Data de Nascimento={birthdate}, Telefone={phone}")

    token = carregar_token()
    if not validar_token(token):
        token = gerar_novo_token()
        if not token:
            logging.error("Erro: Não foi possível gerar o token.")
            return jsonify({"status": "error", "message": "Token inválido."}), 500

    for tentativa in range(10):
        simulacao = realizar_simulacao(cpf, birthdate, phone)
        if simulacao:
            enviar_webhook({"status": "success", "simulation": simulacao})
            return jsonify({"status": "success", "message": "Simulação realizada com sucesso."})
        time.sleep(10)
        logging.warning(f"Tentativa {tentativa + 1} falhou. Retentando...")

    logging.error("Erro: Não foi possível realizar a simulação após 10 tentativas.")
    return jsonify({"status": "error", "message": "Não foi possível realizar a simulação."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
