# orchestrator/main.py

# --- Importações de Bibliotecas Padrão ---
import socket  # Para comunicação de rede (TCP, UDP, Multicast)
import threading  # Para executar tarefas concorrentes (ex: ouvir clientes e workers ao mesmo tempo)
import json  # Para serializar e desserializar dados (converter dict para string e vice-versa)
import time  # Para pausas (sleep) e timestamps
import hashlib  # Para gerar tokens de autenticação seguros (hash)
import uuid  # Para gerar IDs únicos para as tarefas
import sys  # Para acessar argumentos da linha de comando (ex: --backup)
import struct  # Para empacotar dados para a configuração de multicast

# --- Importações do Projeto ---
from config import * # Importa todas as configurações do arquivo config.py
from orchestrator.lamport_clock import LamportClock  # Importa o relógio lógico
from orchestrator.state_manager import StateManager  # Importa o gerenciador de estado
from orchestrator.load_balancer import RoundRobinLoadBalancer  # Importa o balanceador de carga
from shared.models import Task  # Importa o modelo de dados para uma Tarefa

# A classe principal que representa o "cérebro" do sistema.
class Orchestrator:
    # O construtor é chamado quando um novo Orquestrador é criado.
    def __init__(self, is_backup=False):
        # Instancia os componentes principais que o Orquestrador vai gerenciar.
        self.state_manager = StateManager()
        self.lamport_clock = LamportClock()
        self.load_balancer = RoundRobinLoadBalancer()
        
        # Define o papel (role) do orquestrador com base no argumento da linha de comando.
        self.role = "BACKUP" if is_backup else "PRIMARY"
        
        # Guarda o timestamp do último "sinal de vida" recebido do primário (relevante para o backup).
        self.last_primary_heartbeat = time.time()
        logging.info(f"Orquestrador iniciando no modo: {self.role}")

        # Inicia os serviços correspondentes ao seu papel.
        if self.role == "PRIMARY":
            self.start_primary_services()
        else:
            self.start_backup_services()

    # Inicia todas as threads necessárias para um orquestrador PRIMÁRIO funcionar.
    def start_primary_services(self):
        self.role = "PRIMARY"
        # Cada função principal roda em sua própria thread para não bloquear as outras.
        # 'daemon=True' faz com que as threads terminem quando o programa principal for encerrado.
        threading.Thread(target=self.listen_for_clients, daemon=True, name="ClientListener").start()
        threading.Thread(target=self.listen_for_workers, daemon=True, name="WorkerListener").start()
        threading.Thread(target=self.distribute_tasks, daemon=True, name="TaskDistributor").start()
        threading.Thread(target=self.monitor_workers, daemon=True, name="WorkerMonitor").start()
        threading.Thread(target=self.sync_state_to_backup, daemon=True, name="StateSyncer").start()
        logging.info("Serviços do Orquestrador Primário iniciados.")

    # Inicia os serviços para um orquestrador de BACKUP (que são bem mais simples).
    def start_backup_services(self):
        self.role = "BACKUP"
        # O backup só precisa de uma thread: a que ouve por atualizações do primário.
        threading.Thread(target=self.listen_for_sync, daemon=True, name="BackupListener").start()

    # Thread que ouve por conexões de clientes (TCP).
    def listen_for_clients(self):
        # Cria um socket TCP.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Associa o socket ao endereço e porta definidos em 'config.py'.
            s.bind((ORCHESTRATOR_HOST, CLIENT_PORT))
            # Coloca o socket em modo de escuta.
            s.listen()
            logging.info(f"Ouvindo clientes em {ORCHESTRATOR_HOST}:{CLIENT_PORT}")
            # Loop infinito para aceitar novas conexões.
            while True:
                conn, addr = s.accept()
                # Para cada cliente que se conecta, uma nova thread é criada para lidar com ele.
                # Isso permite que o orquestrador atenda múltiplos clientes simultaneamente.
                threading.Thread(target=self.handle_client, args=(conn, addr), name=f"Client-{addr[0]}").start()

    # Função que processa a requisição de um único cliente.
    def handle_client(self, conn, addr):
        try:
            with conn:
                # Recebe os dados enviados pelo cliente.
                request_data = conn.recv(4096).decode('utf-8')
                if not request_data: return
                
                # Converte a string JSON para um dicionário Python.
                request = json.loads(request_data)
                
                # --- Lógica de Autenticação ---
                # Se a requisição não tem um token, ela só pode ser de login.
                if "token" not in request:
                    if request.get("action") == "login":
                        self.handle_login(conn, request)
                    else:
                        # Se não for login e não tiver token, é um acesso não autorizado.
                        conn.sendall(json.dumps({"error": "Autenticação necessária"}).encode())
                    return
                
                # Se tem um token, verifica se ele é válido.
                if not self.verify_token(request["token"]):
                    conn.sendall(json.dumps({"error": "Token inválido ou expirado"}).encode())
                    return
                
                # --- Roteamento de Ações Autenticadas ---
                # Se o token é válido, verifica qual ação o cliente quer realizar.
                action = request.get("action")
                if action == "submit_task":
                    self.handle_submit_task(conn, request)
                elif action == "task_status":
                    self.handle_task_status(conn, request)
        # Trata erros comuns de rede e JSON para evitar que o orquestrador quebre.
        except (json.JSONDecodeError, ConnectionResetError, BrokenPipeError) as e:
            logging.error(f"Erro ao lidar com cliente {addr}: {e}")

    # Lida com a tentativa de login de um usuário.
    def handle_login(self, conn, request):
        username = request.get("username")
        password = request.get("password")
        # Verifica se o usuário e senha correspondem ao que está em 'config.py'.
        if USERS.get(username) == password:
            # Se forem válidos, gera um token simples usando SHA256 (hash).
            token = hashlib.sha256(f"{username}{SECRET_KEY}".encode()).hexdigest()
            # Envia o token de volta para o cliente.
            conn.sendall(json.dumps({"token": token}).encode())
            logging.info(f"Usuário '{username}' autenticado com sucesso.")
        else:
            # Se as credenciais estiverem erradas, envia uma mensagem de erro.
            conn.sendall(json.dumps({"error": "Credenciais inválidas"}).encode())
            logging.warning(f"Falha de autenticação para o usuário '{username}'.")
    
    # Verifica se um token recebido é válido.
    def verify_token(self, token):
        # Para cada usuário conhecido, gera o token esperado e compara com o recebido.
        for user in USERS.keys():
            expected_token = hashlib.sha256(f"{user}{SECRET_KEY}".encode()).hexdigest()
            if token == expected_token:
                return True # Se encontrar um correspondente, o token é válido.
        return False # Se percorrer todos e não encontrar, é inválido.
    
    # Lida com o envio de uma nova tarefa.
    def handle_submit_task(self, conn, request):
        # Identifica o cliente pelo token.
        client_id = self.get_user_from_token(request["token"])
        # Cria uma nova instância da classe Task.
        task = Task(
            id=str(uuid.uuid4()), # Gera um ID único universal.
            client_id=client_id,
            data=request.get("data", {}), # Pega os dados da tarefa da requisição.
            lamport_ts=self.lamport_clock.increment() # Atribui um timestamp de Lamport.
        )
        # Adiciona a nova tarefa ao gerenciador de estado.
        self.state_manager.add_task(task)
        # Responde ao cliente confirmando o recebimento e enviando o ID da tarefa.
        conn.sendall(json.dumps({"status": "Tarefa recebida", "task_id": task.id}).encode())

    # Descobre a qual usuário um token pertence.
    def get_user_from_token(self, token):
        for user in USERS.keys():
            # Gera o token esperado para cada usuário e compara.
            expected_token = hashlib.sha256(f"{user}{SECRET_KEY}".encode()).hexdigest()
            if token == expected_token:
                return user
        return "unknown"

    # Lida com a consulta de status de uma tarefa.
    def handle_task_status(self, conn, request):
        task_id = request.get("task_id")
        # Pede ao gerenciador de estado os detalhes da tarefa.
        status = self.state_manager.get_task_status(task_id)
        if status:
            # Se a tarefa for encontrada, envia os detalhes de volta.
            conn.sendall(json.dumps(status).encode())
        else:
            # Se não, envia um erro.
            conn.sendall(json.dumps({"error": "Tarefa não encontrada"}).encode())

    # Thread que ouve por mensagens dos workers (UDP).
    def listen_for_workers(self):
        # Cria um socket UDP, que é mais leve que TCP e ideal para mensagens curtas como heartbeats.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((ORCHESTRATOR_HOST, WORKER_PORT))
            logging.info(f"Ouvindo workers em {ORCHESTRATOR_HOST}:{WORKER_PORT} (UDP)")
            while True:
                # Espera por uma mensagem UDP.
                data, addr = s.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                msg_type = message.get("type")
                
                # Se a mensagem for um heartbeat, atualiza o status do worker.
                if msg_type == "heartbeat":
                    worker_id = message["worker_id"]
                    self.state_manager.update_worker_heartbeat(worker_id, addr)
                # Se for uma notificação de conclusão, atualiza o status da tarefa.
                elif msg_type == "task_complete":
                    self.state_manager.update_task_status(
                        message["task_id"], "COMPLETED", message["result"]
                    )

    # Thread que monitora a saúde dos workers.
    def monitor_workers(self):
        # Loop infinito que roda periodicamente.
        while True:
            # Dorme por um tempo definido em 'config.py'.
            time.sleep(WORKER_TIMEOUT)
            # Pede ao gerenciador de estado para verificar e remover workers "mortos".
            active_workers = self.state_manager.check_dead_workers()
            # Atualiza o balanceador de carga com a nova lista de workers ativos.
            self.load_balancer.update_workers(active_workers)

    # Thread que distribui tarefas da fila para os workers.
    def distribute_tasks(self):
        while True:
            # Pega a próxima tarefa da fila do gerenciador de estado.
            task = self.state_manager.get_next_task()
            if not task:
                time.sleep(1) # Se a fila estiver vazia, espera um pouco.
                continue
            
            # Pede ao balanceador de carga para escolher o próximo worker.
            worker_id = self.load_balancer.get_next_worker()
            if not worker_id:
                # Se não há workers disponíveis, devolve a tarefa para o início da fila.
                logging.warning("Nenhum worker disponível. Devolvendo tarefa à fila.")
                self.state_manager.add_task(task)
                time.sleep(2)
                continue

            try:
                # Envia a tarefa para o worker escolhido via TCP.
                worker_addr_info = self.state_manager.workers[worker_id]['addr']
                # O worker_id contém o host e a porta de escuta da tarefa.
                task_addr = (worker_addr_info[0], int(worker_id.split('_')[-1]))
                
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(task_addr)
                    # Marca no objeto da tarefa qual worker foi designado.
                    task.assigned_worker = worker_id
                    s.sendall(json.dumps(task.__dict__).encode('utf-8'))
                logging.info(f"Tarefa {task.id} enviada para {worker_id} em {task_addr}")

            # Se a conexão com o worker falhar, a tarefa é devolvida à fila.
            except (KeyError, ConnectionRefusedError) as e:
                logging.error(f"Falha ao enviar tarefa {task.id} para {worker_id}: {e}. Reenfileirando.")
                task.assigned_worker = None
                self.state_manager.add_task(task)

    # Função utilitária para criar um socket UDP configurado para Multicast.
    def create_multicast_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        # TTL (Time To Live) define quantos "saltos" na rede o pacote pode dar. 2 é comum para redes locais.
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        return sock

    # Thread do PRIMÁRIO que envia seu estado para o backup via Multicast.
    def sync_state_to_backup(self):
        multicast_sock = self.create_multicast_socket()
        while self.role == "PRIMARY":
            # Pega um "snapshot" (uma cópia instantânea) do estado atual.
            state_snapshot = self.state_manager.get_state_snapshot()
            
            # Envia duas mensagens distintas para o grupo multicast:
            
            # Mensagem Tipo 1: O snapshot completo do estado.
            # Um byte `\x01` é adicionado no início para identificar o tipo da mensagem.
            message = b'\x01' + state_snapshot
            multicast_sock.sendto(message, (MULTICAST_GROUP, MULTICAST_PORT))
            
            # Mensagem Tipo 2: Um heartbeat "estou vivo" do primário.
            # Um byte `\x02` identifica esta mensagem.
            heartbeat_msg = b'\x02' + json.dumps({"ts": time.time()}).encode()
            multicast_sock.sendto(heartbeat_msg, (MULTICAST_GROUP, MULTICAST_PORT))

            time.sleep(SYNC_INTERVAL)

    # Thread do BACKUP que ouve as mensagens de sincronização do primário.
    def listen_for_sync(self):
        # Cria e configura um socket para receber pacotes multicast.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', MULTICAST_PORT))
        
        # Diz ao sistema operacional para se juntar ao grupo multicast.
        mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        logging.info("Backup ouvindo por sincronização de estado e heartbeats do primário.")
        
        while self.role == "BACKUP":
            # Verifica se o primário está "morto" (não envia heartbeat há muito tempo).
            if time.time() - self.last_primary_heartbeat > PRIMARY_TIMEOUT:
                logging.warning("Heartbeat do primário não detectado. Iniciando failover!")
                self.promote_to_primary() # Inicia o processo de failover.
                break # Sai do loop de escuta do backup.

            # Define um timeout no socket para não ficar bloqueado para sempre.
            sock.settimeout(PRIMARY_TIMEOUT)
            try:
                # Espera por uma mensagem multicast.
                data, _ = sock.recvfrom(65535)
                # Extrai o primeiro byte para saber o tipo da mensagem.
                msg_type = data[0:1]
                content = data[1:]

                if msg_type == b'\x01': # Se for um snapshot do estado...
                    self.state_manager.load_state_snapshot(content, self.lamport_clock)
                elif msg_type == b'\x02': # Se for um heartbeat do primário...
                    self.last_primary_heartbeat = time.time() # Atualiza o timestamp.

            except socket.timeout:
                # Se o timeout ocorrer, o loop continua e a verificação no início do 'while'
                # vai eventualmente detectar a falha do primário.
                logging.warning("Socket timeout esperando por pacotes do primário.")
                continue

    # Função que transforma o backup em primário.
    def promote_to_primary(self):
        logging.info("PROMOVENDO A PRIMÁRIO!")
        self.role = "PRIMARY"
        # Inicia todos os serviços que um orquestrador primário precisa ter.
        self.start_primary_services()

# Ponto de entrada do script.
if __name__ == "__main__":
    # Verifica se o argumento '--backup' foi passado na linha de comando.
    is_backup = "--backup" in sys.argv
    # Cria a instância do Orquestrador com o papel correto.
    orch = Orchestrator(is_backup=is_backup)
    # Loop infinito para manter a thread principal viva, permitindo que as threads
    # daemon (serviços) continuem rodando em segundo plano.
    while True:
        time.sleep(60)