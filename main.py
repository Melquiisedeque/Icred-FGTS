import requests
import json
import time
import logging
from flask import Flask, request, jsonify

# Configurações
TOKEN_URL = "https://api-hml.icred.app/authorization-server/oauth2/token"
CLIENT_ID = "sb-integration"  # Substitua pelo seu CLIENT_ID
CLIENT_SECRET = "6698c059-3092-41d1-a218-5f03b5d1e37f"  # Substitua pelo seu CLIENT_SECRET
GRANT_TYPE = "client_credentials"
SCOPE = "default fgts"
TOKEN_FILE = "token.json"

# Configuração do Flask
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def generate_and_save_token():
    """Gera um novo token e salva em token.json."""
    try:
        headers = {
            "Authorization": f"Basic {requests.auth._basic_auth_str(CLIENT_ID, CLIENT_SECRET)}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {
            "grant_type": GRANT_TYPE,
            "scope": SCOPE,
        }

        app.logger.info("Enviando requisição para gerar o token...")
        response = requests.post(TOKEN_URL, headers=headers, data=payload)

        if response.status_code == 200:
            token_data = response.json()
            token_data["generated_at"] = time.time()  # Timestamp de geração do token
            with open(TOKEN_FILE, "w") as token_file:
                json.dump(token_data, token_file, indent=4)
            app.logger.info("Token gerado e salvo com sucesso!")
            return token_data["access_token"]
        else:
            app.logger.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        app.logger.error(f"Erro ao gerar o token: {str(e)}")
        return None

def load_token():
    """Carrega o token de token.json e verifica validade."""
    try:
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)

        # Verificar validade do token
        expires_in = token_data.get("expires_in", 0)
        generated_at = token_data.get("generated_at", 0)

        if time.time() < generated_at + expires_in:
            app.logger.info("Token carregado do arquivo.")
            return token_data.get("access_token")
        else:
            app.logger.info("Token expirado. Gerando um novo token...")
            return generate_and_save_token()
    except FileNotFoundError:
        app.logger.info("Arquivo token.json não encontrado. Gerando um novo token...")
        return generate_and_save_token()
    except Exception as e:
        app.logger.error(f"Erro ao carregar o token: {str(e)}")
        return generate_and_save_token()

@app.route('/simulation', methods=['POST'])
def simulation():
    """Endpoint para processar a simulação."""
    try:
        # Receber dados do BotConversa
        data = request.get_json()
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = data.get("phone")

        app.logger.info(f"Dados recebidos: CPF={cpf}, Birthdate={birthdate}, Phone={phone}")

        # Obter token
        token = load_token()
        if not token:
            return jsonify({"error": "Não foi possível gerar o token."}), 500

        # Simulação (exemplo)
        simulation_result = {
            "cpf": cpf,
            "birthdate": birthdate,
            "phone": phone,
            "simulation_status": "success",
        }

        # Retornar resultado
        return jsonify(simulation_result), 200
    except Exception as e:
        app.logger.error(f"Erro na simulação: {str(e)}")
        return jsonify({"error": "Erro ao processar a simulação."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int("5001"), debug=True)
