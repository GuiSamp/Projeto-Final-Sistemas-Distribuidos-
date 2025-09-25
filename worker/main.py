# worker/main.py

# --- Importações de Bibliotecas Padrão ---
import socket  # Para comunicação de rede (TCP para receber tarefas, UDP para enviar status).
import threading  # Para rodar o envio de heartbeats em segundo plano.
import json  # Para serializar/desserializar as mensagens trocadas com o orquestrador.
import time  # Usado para simular o tempo de execução de uma tarefa.
import sys  # Para ler argumentos da linha de comando (host e porta do worker).

# --- Importações do Projeto ---
# Importa todas as variáveis de configuração (endereços, portas, timeouts, logger).
# O asterisco (*) importa tudo, mas foi corrigido para importar apenas o necessário nos passos anteriores.
from config import ORCHESTRATOR_HOST, WORKER_PORT, HEARTBEAT_INTERVAL, logging

# Função que simula a execução de uma tarefa.
def execute_task(task_data):
    logging.info(f"Iniciando execução da tarefa: {task_data['id']}")
    # Simula um trabalho pesado "dormindo" por um tempo.
    # A duração é pega dos dados da tarefa, com um padrão de 5 segundos se não for especificada.
    duration = task_data.get('data', {}).get('duration', 5)
    time.sleep(duration)
    # Cria um dicionário com o resultado da tarefa.
    result = {"message": f"Tarefa {task_data['id']} concluída com sucesso"}
    logging.info(f"Tarefa {task_data['id']} finalizada.")
    # Retorna o resultado.
    return result

# Função que roda em uma thread separada para enviar "sinais de vida" (heartbeats) ao orquestrador.
def send_heartbeat(worker_id):
    # Define o endereço do orquestrador para onde os heartbeats serão enviados.
    orchestrator_addr = (ORCHESTRATOR_HOST, WORKER_PORT)
    # Cria um socket UDP (mais leve que TCP, ideal para mensagens curtas e repetitivas).
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Loop infinito para enviar heartbeats continuamente.
        while True:
            try:
                # Monta a mensagem do heartbeat em formato JSON.
                message = json.dumps({"type": "heartbeat", "worker_id": worker_id})
                # Envia a mensagem para o orquestrador.
                s.sendto(message.encode('utf-8'), orchestrator_addr)
            except Exception as e:
                # Loga um erro se o envio falhar, mas não quebra o loop.
                logging.error(f"Erro ao enviar heartbeat: {e}")
            # Espera pelo intervalo definido em 'config.py' antes de enviar o próximo.
            time.sleep(HEARTBEAT_INTERVAL)

# Função para notificar o orquestrador que uma tarefa foi concluída.
def notify_task_completion(task_id, result):
    # Define o endereço do orquestrador.
    orchestrator_addr = (ORCHESTRATOR_HOST, WORKER_PORT)
    # Usa um socket UDP para enviar uma notificação "dispare e esqueça".
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Monta a mensagem de conclusão com o ID da tarefa e seu resultado.
        message = json.dumps({
            "type": "task_complete",
            "task_id": task_id,
            "result": result
        })
        # Envia a notificação.
        s.sendto(message.encode('utf-8'), orchestrator_addr)
        logging.info(f"Notificação de conclusão da tarefa {task_id} enviada.")


# Função principal do worker que ouve por novas tarefas do orquestrador.
def listen_for_tasks(host, port):
    # Cria um socket TCP para receber as tarefas (TCP é confiável para dados importantes).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Associa o socket ao endereço e porta especificados na inicialização.
        s.bind((host, port))
        # Coloca o socket em modo de escuta por conexões.
        s.listen()
        logging.info(f"Ouvindo por tarefas em {host}:{port}")
        # Loop infinito para aceitar conexões de tarefas.
        while True:
            # Aceita uma nova conexão (esta chamada é bloqueante).
            conn, addr = s.accept()
            with conn:
                # Recebe os dados da tarefa.
                data = conn.recv(4096).decode('utf-8')
                if not data:
                    continue
                
                # Converte os dados JSON em um dicionário Python.
                task_data = json.loads(data)
                # Chama a função para executar a tarefa.
                result = execute_task(task_data)
                
                # Após a conclusão, notifica o orquestrador.
                notify_task_completion(task_data['id'], result)


# Ponto de entrada do script.
if __name__ == "__main__":
    # Verifica se os argumentos da linha de comando (host e porta) foram fornecidos.
    if len(sys.argv) != 3:
        print("Uso: python -m worker.main <host> <port>")
        sys.exit(1)
        
    # Pega o host e a porta dos argumentos.
    host = sys.argv[1]
    port = int(sys.argv[2])
    # Cria um ID único para este worker.
    worker_id = f"{host}_{port}"
    
    # Cria e inicia uma nova thread para a função 'send_heartbeat'.
    # Isso é crucial para que o worker possa enviar heartbeats E ouvir por tarefas ao mesmo tempo.
    # 'daemon=True' garante que esta thread será encerrada quando o programa principal terminar.
    threading.Thread(target=send_heartbeat, args=(worker_id,), daemon=True, name=f"Heartbeat-{worker_id}").start()
    
    # Chama a função de escuta de tarefas, que rodará na thread principal do programa.
    listen_for_tasks(host, port)