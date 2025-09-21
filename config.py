# config.py

import logging

# --- Configurações de Rede ---
ORCHESTRATOR_HOST = 'localhost'
# Porta para comunicação com Clientes (TCP)
CLIENT_PORT = 50051
# Porta para comunicação com Workers (receber heartbeats e enviar tarefas)
WORKER_PORT = 50052
# Porta para enviar tarefas aos Workers (TCP)
TASK_PORT = 60000

# --- Configurações do Orquestrador de Backup e Failover ---
# Grupo multicast para sincronização de estado e heartbeats do primário
MULTICAST_GROUP = '224.1.1.1'
MULTICAST_PORT = 5007
# Tempo em segundos sem um heartbeat do primário para o backup assumir
PRIMARY_TIMEOUT = 5.0 # 5 segundos
# Intervalo em que o primário envia seu estado e heartbeat
SYNC_INTERVAL = 2.0 # 2 segundos

# --- Configurações dos Workers ---
# Lista de workers conhecidos. Na prática, isso poderia ser dinâmico.
WORKERS_ADDRESSES = [
    ('localhost', 60001),
    ('localhost', 60002),
    ('localhost', 60003),
]
# Intervalo em segundos que os workers enviam heartbeats
HEARTBEAT_INTERVAL = 2.0
# Tempo em segundos sem um heartbeat para considerar um worker inativo/morto
WORKER_TIMEOUT = 5.0

# --- Configurações de Segurança ---
# Usuários e senhas para autenticação básica
USERS = {
    "user1": "pass1",
    "user2": "pass2"
}
# Chave "secreta" para gerar tokens simples. Em um sistema real, use algo mais robusto.
SECRET_KEY = "sua-chave-super-secreta"

# --- Configurações de Logging ---
LOGGING_FORMAT = '%(asctime)s - %(levelname)s - %(threadName)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)