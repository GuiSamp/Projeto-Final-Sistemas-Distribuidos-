# client/main.py

# Importa as bibliotecas necessárias:
# socket: para comunicação de rede (TCP) com o orquestrador.
# json: para serializar (transformar em string) e desserializar (transformar de volta em objeto) os dados das tarefas.
# argparse: para criar uma interface de linha de comando amigável (ex: 'python -m client.main login ...').
# os: para interagir com o sistema operacional, especificamente para verificar se o arquivo de token existe.
import socket
import json
import argparse
import os

# Importa as configurações de host e porta do arquivo config.py.
# Isso centraliza as configurações, facilitando a manutenção.
from config import ORCHESTRATOR_CONNECT_HOST, CLIENT_PORT

# Define o nome do arquivo onde o token de autenticação será salvo localmente.
# Usar um arquivo oculto (começando com '.') é uma convenção comum.
TOKEN_FILE = ".api_token"

# Função para salvar o token de autenticação em um arquivo local.
def save_token(token):
    # Abre o arquivo em modo de escrita ('w'). Se o arquivo não existir, ele é criado.
    with open(TOKEN_FILE, "w") as f:
        # Escreve o token recebido no arquivo.
        f.write(token)

# Função para carregar o token de autenticação do arquivo local.
def load_token():
    # Verifica se o arquivo de token realmente existe no diretório.
    if os.path.exists(TOKEN_FILE):
        # Abre o arquivo em modo de leitura ('r').
        with open(TOKEN_FILE, "r") as f:
            # Lê o conteúdo do arquivo, remove espaços em branco extras (como quebras de linha) e o retorna.
            return f.read().strip()
    # Se o arquivo não existir, retorna None, indicando que o usuário não está logado.
    return None

# Função genérica para enviar qualquer tipo de requisição ao orquestrador.
def send_request(request):
    try:
        # Cria um socket TCP/IP.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Conecta-se ao endereço e porta do orquestrador definidos no config.py.
            s.connect((ORCHESTRATOR_CONNECT_HOST, CLIENT_PORT))
            # Converte o dicionário Python (request) para uma string JSON e a codifica para bytes antes de enviar.
            s.sendall(json.dumps(request).encode('utf-8'))
            # Espera por uma resposta do servidor (até 4096 bytes).
            response = s.recv(4096).decode('utf-8')
            # Converte a string JSON recebida de volta para um dicionário Python e a retorna.
            return json.loads(response)
    # Trata o erro caso o orquestrador não esteja rodando ou a conexão seja recusada.
    except ConnectionRefusedError:
        return {"error": "Não foi possível conectar ao orquestrador."}
    # Trata o erro caso a resposta do servidor não seja um JSON válido.
    except json.JSONDecodeError:
         return {"error": "Resposta inválida recebida do servidor."}

# Função que lida com o comando 'login'.
def handle_login(args):
    # Monta o dicionário da requisição com a ação e as credenciais fornecidas pelo usuário.
    request = {
        "action": "login",
        "username": args.username,
        "password": args.password
    }
    # Envia a requisição de login para o orquestrador.
    response = send_request(request)
    # Se a resposta contiver um "token", o login foi bem-sucedido.
    if "token" in response:
        # Salva o token recebido localmente para uso em futuras requisições.
        save_token(response["token"])
        print("Login realizado com sucesso. Token salvo.")
    else:
        # Caso contrário, exibe a mensagem de erro retornada pelo servidor.
        print(f"Erro no login: {response.get('error', 'desconhecido')}")

# Função que lida com o comando 'submit' para enviar uma nova tarefa.
def handle_submit(args):
    # Carrega o token salvo localmente.
    token = load_token()
    # Se não houver token, o usuário não está logado e não pode submeter tarefas.
    if not token:
        print("Você precisa fazer login primeiro. Use: client login <user> <pass>")
        return
    
    # Monta o dicionário da requisição, incluindo o token para autenticação
    # e os dados da tarefa (descrição e duração).
    request = {
        "action": "submit_task",
        "token": token,
        "data": {"description": args.description, "duration": args.duration}
    }
    # Envia a requisição para submeter a tarefa.
    response = send_request(request)
    # Se a resposta contiver um "task_id", a tarefa foi aceita pelo orquestrador.
    if "task_id" in response:
        print(f"Tarefa submetida com sucesso! ID da Tarefa: {response['task_id']}")
    else:
        # Caso contrário, exibe a mensagem de erro.
        print(f"Erro ao submeter tarefa: {response.get('error', 'desconhecido')}")
        
# Função que lida com o comando 'status' para verificar uma tarefa existente.
def handle_status(args):
    # Carrega o token para autenticar a requisição.
    token = load_token()
    if not token:
        print("Você precisa fazer login primeiro.")
        return
        
    # Monta a requisição para verificar o status, incluindo o token e o ID da tarefa.
    request = {
        "action": "task_status",
        "token": token,
        "task_id": args.task_id
    }
    # Envia a requisição.
    response = send_request(request)
    
    # Se o servidor retornar um erro, exibe-o.
    if "error" in response:
        print(f"Erro: {response['error']}")
    else:
        # Caso contrário, formata e exibe os detalhes da tarefa de forma legível.
        print("\n--- Status da Tarefa ---")
        for key, value in response.items():
            print(f"{key.capitalize():<20}: {value}")
        print("------------------------\n")

# Função principal que configura a interface de linha de comando.
def main():
    # Cria o parser principal.
    parser = argparse.ArgumentParser(description="Cliente para a plataforma de tarefas distribuídas.")
    # Cria subparsers para lidar com os diferentes comandos (login, submit, status).
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Configuração do comando 'login'.
    parser_login = subparsers.add_parser("login", help="Autentica o usuário e salva o token.")
    parser_login.add_argument("username", type=str, help="Nome do usuário.")
    parser_login.add_argument("password", type=str, help="Senha do usuário.")
    parser_login.set_defaults(func=handle_login) # Associa o comando 'login' à função handle_login.

    # Configuração do comando 'submit'.
    parser_submit = subparsers.add_parser("submit", help="Submete uma nova tarefa.")
    parser_submit.add_argument("description", type=str, help="Descrição da tarefa.")
    parser_submit.add_argument("-d", "--duration", type=int, default=5, help="Duração simulada da tarefa em segundos.")
    parser_submit.set_defaults(func=handle_submit) # Associa o comando 'submit' à função handle_submit.
    
    # Configuração do comando 'status'.
    parser_status = subparsers.add_parser("status", help="Verifica o status de uma tarefa.")
    parser_status.add_argument("task_id", type=str, help="O ID da tarefa a ser verificada.")
    parser_status.set_defaults(func=handle_status) # Associa o comando 'status' à função handle_status.

    # Analisa os argumentos fornecidos na linha de comando.
    args = parser.parse_args()
    # Chama a função que foi associada ao comando digitado pelo usuário (ex: handle_login).
    args.func(args)

# Bloco padrão em Python: o código aqui dentro só é executado quando o arquivo é rodado diretamente.
if __name__ == "__main__":
    main()