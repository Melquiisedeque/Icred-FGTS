import os
import time
import requests
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

TOKEN_URL = "https://api-hml.icred.app/authorization-server/oauth2/token"
CLIENT_ID = "sb-integration"  # Substitua pelo valor correto
CLIENT_SECRET = "6698c059-3092-41d1-a218-5f03b5d1e37f"  # Substitua pelo valor correto
GRANT_TYPE = "client_credentials"
SCOPE = "default fgts"
WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/DcB0aQaTyUe4/"
TOKEN_FILE = "token.json"  # Arquivo para salvar o token

def generate_token():
    """Gera e retorna um novo token."""
    try:
        headers = {
            "Authorization": f"Basic {requests.auth._basic_auth_str(CLIENT_ID, CLIENT_SECRET)}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": GRANT_TYPE,
            "scope": SCOPE,
        }

        app.logger.info(f"Enviando requisição para gerar token...")
        app.logger.debug(f"Headers: {headers}")
        app.logger.debug(f"Payload: {data}")

        response = requests.post(TOKEN_URL, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            token_data["generated_at"] = time.time()  # Adiciona timestamp
            with open(TOKEN_FILE, "w") as token_file:
                token_file.write(token_data.get("access_token"))
            return token_data.get("access_token")
        else:
            app.logger.error(f"Erro ao gerar o token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        app.logger.error(f"Erro na requisição de token: {str(e)}")
        return None



def commit_and_push_to_github():
    """Faz commit e push automático para o GitHub."""
    try:
        # Adiciona mudanças no Git
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Atualizado token automaticamente"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        app.logger.info("Código atualizado no GitHub com sucesso.")
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Erro ao atualizar o GitHub: {str(e)}")


def regenerate_token_and_update():
    """Regenera o token, atualiza o código e realiza o push."""
    token = generate_token()
    if token:
        commit_and_push_to_github()
        app.logger.info("Token regenerado e código atualizado no GitHub.")
    else:
        app.logger.error("Falha ao regenerar o token.")


def simulate(cpf, birthdate, phone):
    """Executa a simulação e envia os dados ao Webhook."""
    token = generate_token()
    if not token:
        app.logger.error("Não foi possível gerar o token.")
        regenerate_token_and_update()
        return jsonify({"status": "error", "message": "Erro ao gerar o token. Tentando novamente..."}), 500

    simulation_url = "https://api-hml.icred.app/fgts/v1/max-simulation"
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
            "countryCode": "55"
        },
    }

    for attempt in range(10):
        try:
            response = requests.post(simulation_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                simulation_data = response.json()
                app.logger.info("Simulação realizada com sucesso.")
                send_to_webhook(simulation_data)  # Envia os dados para o Webhook
                return jsonify({"status": "success", "data": simulation_data})
            else:
                app.logger.error(f"Tentativa {attempt + 1}: Erro na simulação: {response.status_code} - {response.text}")
        except Exception as e:
            app.logger.error(f"Tentativa {attempt + 1}: Erro na simulação: {str(e)}")
        time.sleep(10)

    return jsonify({"status": "error", "message": "Simulação falhou após 10 tentativas"}), 500


@app.route("/simulation", methods=["POST"])
def simulation_endpoint():
    """Endpoint para receber dados de simulação."""
    try:
        data = request.json
        cpf = data.get("cpf")
        birthdate = data.get("birthdate")
        phone = data.get("phone")
        if not all([cpf, birthdate, phone]):
            return jsonify({"status": "error", "message": "Parâmetros inválidos"}), 400

        app.logger.info(f"Dados recebidos: CPF={cpf}, Data de nascimento={birthdate}, Telefone={phone}")
        return simulate(cpf, birthdate, phone)
    except Exception as e:
        app.logger.error(f"Erro: {str(e)}")
        return jsonify({"status": "error", "message": "Erro no processamento"}), 500


if __name__ == "__main__":
    app.logger.info("Inicializando o servidor Flask.")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
