import os
import json
import time
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

WEBHOOK_URL = "https://new-backend.botconversa.com.br/api/v1/webhooks-automation/catch/136922/ruhxOAwTgPFD/"
TOKEN_FILE = "token.json"  # Caminho para o arquivo que armazena o token


def generate_token():
    """Gera um novo token de acesso."""
    url = "https://api-hml.icred.app/authorization-server/oauth2/token"
    client_id = "sb-integration"
    client_secret = "6698c059-3092-41d1-a218-5f03b5d1e37f"
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(client_id, client_secret)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials", "scope": "default fgts"}

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        token_data["generated_at"] = datetime.now().isoformat()  # Salvar a data como string ISO 8601
        with open(TOKEN_FILE, "w") as file:
            json.dump(token_data, file)
        return token_data["access_token"]
    else:
        raise Exception(f"Erro ao gerar token: {response.status_code} - {response.text}")


def get_token():
    """Obtém o token de acesso, renovando se necessário."""
    if not os.path.exists(TOKEN_FILE):
        return generate_token()

    with open(TOKEN_FILE, "r") as file:
        token_data = json.load(file)

    expires_in = int(token_data.get("expires_in", 0))  # Garantir que 'expires_in' seja interpretado como inteiro
    generated_at = datetime.fromisoformat(token_data.get("generated_at"))  # Converter ISO 8601 para datetime
    time_elapsed = (datetime.now() - generated_at).total_seconds()  # Calcular segundos decorridos

    if time_elapsed >= expires_in:
        return generate_token()

    return token_data["access_token"]


def send_webhook(data):
    """Envia os dados da simulação para o webhook."""
    response = requests.post(WEBHOOK_URL, json=data, headers={"Content-Type": "application/json"})
    if response.status_code == 200:
        print("Dados enviados para o webhook com sucesso.")
    else:
        print(f"Erro ao enviar dados para o webhook: {response.status_code} - {response.text}")


@app.route("/simulation", methods=["POST"])
def simulation():
    try:
        input_data = request.json
        cpf = input_data.get("cpf")
        birthdate = input_data.get("birthdate")
        phone = input_data.get("phone")

        print(f"Dados recebidos: CPF={cpf}, Data de Nascimento={birthdate}, Telefone={phone}")

        token = get_token()

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"cpf": cpf, "birthdate": birthdate, "phone": phone}

        simulation_url = "https://api-hml.icred.app/fgts/v1/max-simulation"
        simulation_response = requests.post(simulation_url, json=payload, headers=headers)

        if simulation_response.status_code == 200:
            simulation_data = simulation_response.json()
            print("Simulação concluída com sucesso. Dados da simulação enviados para o webhook.")
            send_webhook(simulation_data)
            return jsonify({"status": "success", "simulation": simulation_data}), 200
        else:
            print(f"Erro ao realizar simulação: {simulation_response.status_code} - {simulation_response.text}")
            return jsonify({"status": "error", "message": "Erro ao realizar simulação"}), 500
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
