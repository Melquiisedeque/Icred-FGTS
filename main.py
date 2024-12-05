import os
import requests
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO)

# Arquivo para salvar o token
TOKEN_FILE = "token.json"

def test_token_validity(token):
    """Testa se o token atual é válido."""
    api_url = "https://api-hml.icred.app/authorization-server/oauth2/token-info"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            logging.info("Token válido confirmado.")
            return True
        else:
            logging.warning(f"Token inválido. Código de status: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Erro ao testar o token: {str(e)}")
        return False

def generate_and_save_token():
    """Gera um novo token e salva no arquivo."""
    logging.info("Gerando um novo token...")
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

    try:
        response = requests.post(api_url, headers=headers, data=payload)
        logging.info(f"Requisição de token enviada. Código de status: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            token_data["generated_at"] = datetime.now().isoformat()
            with open(TOKEN_FILE, "w") as token_file:
                json.dump(token_data, token_file, indent=4)
            logging.info("Novo token gerado e salvo.")
            return token_data["access_token"]
        else:
            logging.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Erro ao tentar gerar o token: {str(e)}")
        return None

def load_or_generate_token():
    """Carrega o token do arquivo ou gera um novo."""
    try:
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)
            token = token_data.get("access_token")
            if test_token_validity(token):
                return token
        logging.info("Token expirado ou inválido. Tentando gerar um novo token...")
    except FileNotFoundError:
        logging.info("Arquivo de token não encontrado. Tentando gerar um novo token...")

    # Tentativa múltipla de gerar um novo token
    for attempt in range(10):
        logging.info(f"Tentativa {attempt + 1} para gerar o token.")
        token = generate_and_save_token()
        if token and test_token_validity(token):
            return token
        logging.warning(f"Tentativa {attempt + 1} falhou.")
        time.sleep(5)  # Aguarda 5 segundos entre as tentativas
    logging.error("Falha ao gerar um token válido após 10 tentativas.")
    return None

@app.route("/simulation", methods=["POST"])
def simulation():
    """Rota para iniciar a simulação."""
    try:
        data = request.get_json()
        cpf = data["cpf"]
        birthdate = data["birthdate"]
        phone = data["phone"]

        logging.info(f"Dados recebidos: CPF={cpf}, Data de Nascimento={birthdate}, Telefone={phone}")

        token = load_or_generate_token()
        if not token:
            return jsonify({"status": "error", "message": "Não foi possível gerar um token válido."}), 500

        # Aqui você inicia a lógica da simulação usando o token
        simulation_data = {
            "cpf": cpf,
            "birthdate": birthdate,
            "phone": phone
        }
        logging.info(f"Iniciando simulação com os dados: {simulation_data}")

        # Lógica simulada de sucesso
        return jsonify({"status": "success", "simulation": simulation_data}), 200

    except KeyError as e:
        logging.error(f"Erro: Faltando chave no corpo da requisição: {str(e)}")
        return jsonify({"status": "error", "message": f"Chave ausente: {str(e)}"}), 400
    except Exception as e:
        logging.error(f"Erro na simulação: {str(e)}")
        return jsonify({"status": "error", "message": "Erro interno no servidor."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
