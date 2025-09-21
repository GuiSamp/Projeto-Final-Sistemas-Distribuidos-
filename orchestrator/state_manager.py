# orchestrator/state_manager.py

# --- Importações ---
import threading  # Necessário para o Lock, que garante a segurança em ambiente com múltiplas threads.
import time  # Usado para obter o timestamp atual para os heartbeats.
import json  # Usado para serializar/desserializar o estado do sistema para a sincronização com o backup.
from typing import Dict, List  # Para anotações de tipo, que melhoram a clareza do código.
from shared.models import Task  # Importa a classe Task para anotação de tipo.
from config import WORKER_TIMEOUT, logging  # Importa configurações e o logger.

# Esta classe centraliza e protege todo o estado compartilhado do orquestrador.
# Qualquer parte do orquestrador que precise ler ou modificar a lista de tarefas ou workers
# deve fazê-lo através desta classe, garantindo que as operações sejam atômicas e seguras.
class StateManager:
    # O construtor da classe.
    def __init__(self):
        # Dicionário que armazena todos os objetos de tarefa, usando o ID da tarefa como chave.
        self.tasks: Dict[str, Task] = {}
        # Lista que atua como uma fila (FIFO) para os IDs das tarefas pendentes.
        self.pending_tasks: List[str] = []
        # Dicionário que armazena o estado de cada worker ativo.
        self.workers: Dict[str, Dict] = {}  # Formato: { 'worker_id': {'addr': ('host', port), 'last_heartbeat': ts} }
        # O Lock (cadeado) é a peça central para garantir que apenas uma thread
        # modifique o estado de cada vez, evitando condições de corrida.
        self.lock = threading.Lock()

    # Adiciona uma nova tarefa ao estado.
    def add_task(self, task: Task):
        # 'with self.lock:' garante que as operações dentro deste bloco sejam atômicas.
        with self.lock:
            # Adiciona a tarefa ao dicionário principal.
            self.tasks[task.id] = task
            # Adiciona o ID da tarefa ao final da fila de pendentes.
            self.pending_tasks.append(task.id)
            logging.info(f"Nova tarefa adicionada à fila: {task.id}")

    # Pega a próxima tarefa da fila para ser processada.
    def get_next_task(self) -> Task | None:
        with self.lock:
            # Se a fila de tarefas pendentes estiver vazia, não há nada a fazer.
            if not self.pending_tasks:
                return None
            # Remove o primeiro ID da fila (comportamento de fila FIFO).
            task_id = self.pending_tasks.pop(0)
            # Busca o objeto Task completo no dicionário principal.
            task = self.tasks.get(task_id)
            if task:
                # Atualiza o status da tarefa para indicar que ela está sendo processada.
                task.status = "IN_PROGRESS"
            return task

    # Atualiza o timestamp do último heartbeat de um worker.
    def update_worker_heartbeat(self, worker_id: str, worker_addr):
        with self.lock:
            # Se for a primeira vez que vemos este worker, registra um log.
            if worker_id not in self.workers:
                logging.info(f"Novo worker registrado: {worker_id} em {worker_addr}")
            # Adiciona ou atualiza as informações do worker.
            self.workers[worker_id] = {
                'addr': worker_addr,
                'last_heartbeat': time.time() # Armazena o momento exato do último sinal de vida.
            }

    # Verifica quais workers estão inativos (mortos) e lida com suas tarefas.
    def check_dead_workers(self):
        with self.lock:
            now = time.time()
            # Cria uma lista de IDs de workers cujo último heartbeat foi há mais tempo que o TIMEOUT definido.
            dead_workers = [
                worker_id for worker_id, data in self.workers.items()
                if now - data['last_heartbeat'] > WORKER_TIMEOUT
            ]
            
            # Para cada worker inativo encontrado...
            for worker_id in dead_workers:
                logging.warning(f"Worker {worker_id} está inativo. Removendo e reatribuindo tarefas.")
                # Remove o worker da lista de ativos.
                del self.workers[worker_id]
                
                # Procura por todas as tarefas que estavam sendo executadas pelo worker que falhou.
                for task_id, task in self.tasks.items():
                    if task.assigned_worker == worker_id and task.status == "IN_PROGRESS":
                        # Reseta o status da tarefa para "PENDENTE".
                        task.status = "PENDING"
                        task.assigned_worker = None
                        # Coloca a tarefa de volta no início da fila para ser reatribuída rapidamente.
                        self.pending_tasks.insert(0, task_id)
                        logging.info(f"Tarefa {task_id} do worker {worker_id} devolvida à fila.")
            # Retorna a lista atualizada de workers ativos.
            return list(self.workers.keys())

    # Atualiza o status de uma tarefa (ex: para COMPLETED).
    def update_task_status(self, task_id, status, result=None):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = status
                self.tasks[task_id].result = result # Armazena o resultado da tarefa.
                logging.info(f"Status da tarefa {task_id} atualizado para {status}")

    # Obtém o status de uma tarefa específica.
    def get_task_status(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            # Retorna os dados da tarefa como um dicionário se ela existir.
            return task.__dict__ if task else None

    # Tira uma "foto" (snapshot) do estado atual do sistema para ser enviada ao backup.
    def get_state_snapshot(self):
        with self.lock:
            # Serializa as listas e dicionários para uma string JSON em formato de bytes (utf-8).
            return json.dumps({
                "tasks": {tid: t.__dict__ for tid, t in self.tasks.items()},
                "pending_tasks": self.pending_tasks,
                "workers": self.workers
            }).encode('utf-8')

    # Carrega um snapshot de estado recebido do orquestrador primário (usado pelo backup).
    def load_state_snapshot(self, snapshot_json, clock: 'LamportClock'):
        with self.lock:
            try:
                # Desserializa a string JSON de volta para objetos Python.
                state = json.loads(snapshot_json.decode('utf-8'))
                self.tasks = {tid: Task(**t_data) for tid, t_data in state["tasks"].items()}
                self.pending_tasks = state["pending_tasks"]
                self.workers = state["workers"]

                # Sincroniza o relógio de Lamport local com o estado recebido.
                # O relógio deve ser ajustado para o maior timestamp visto no sistema.
                max_ts = 0
                for task in self.tasks.values():
                    if task.lamport_ts > max_ts:
                        max_ts = task.lamport_ts
                clock.set_time(max_ts)

                logging.info("Estado global sincronizado com sucesso a partir do backup.")
            # Trata erros caso o snapshot esteja corrompido ou em formato inesperado.
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Erro ao carregar o snapshot do estado: {e}")