import os
import requests
import json
from flask import Flask, request, jsonify
from time import sleep

app = Flask(__name__)

# Caminho para salvar o token
token_file = "token.json"

# Configurações da API
token_url = "https://api-hml.icred.app/authorization-server/oauth2/token"
client_id = "sb-integration"
client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"
scope = "default fgts"


def generate_token():
    """Gera um novo token de acesso."""
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(client_id, client_secret)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "client_credentials",
        "scope": scope,
    }
    response = requests.post(token_url, headers=headers, data=payload)
    if response.status_code == 200:
        token_data = response.json()
        token_data["generated_at"] = "2024-12-12"  # Data atual simulada
        with open(token_file, "w") as f:
            json.dump(token_data, f, indent=4)
        return token_data["access_token"]
    else:
        raise Exception(f"Erro ao gerar token: {response.status_code} - {response.text}")


def get_valid_token():
    """Obtém um token válido, gerando um novo se necessário."""
    for attempt in range(10):
        try:
            if os.path.exists(token_file):
                with open(token_file, "r") as f:
                    token_data = json.load(f)
                    return token_data["access_token"]
            else:
                return generate_token()
        except Exception as e:
            app.logger.error(f"Tentativa {attempt + 1} falhou: {e}")
            sleep(10)  # Aguarda 10 segundos antes de tentar novamente
    raise Exception("Falha ao obter um token válido após 10 tentativas.")


@app.route("/simulation", methods=["POST"])
def simulation():
    """Rota para realizar a simulação."""
    try:
        data = request.json
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = data.get("phone")

        app.logger.info(f"Dados recebidos: CPF={cpf}, Data de Nascimento={birthdate}, Telefone={phone}")

        token = get_valid_token()
        app.logger.info("Token válido confirmado.")

        # Aqui viria a lógica de realizar a simulação usando o token
        return jsonify({"status": "success", "message": "Simulação realizada com sucesso."}), 200

    except Exception as e:
        app.logger.error(f"Erro: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
