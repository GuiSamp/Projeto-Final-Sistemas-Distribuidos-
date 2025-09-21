# orchestrator/load_balancer.py

# Importa as bibliotecas necessárias:
# threading: para o Lock, garantindo que a lista de workers não seja modificada e lida ao mesmo tempo.
# typing.List: para anotações de tipo, melhorando a legibilidade do código.
import threading
from typing import List

# Define a classe que implementa a política de balanceamento de carga Round Robin.
# Essa política distribui as tarefas sequencialmente entre os workers disponíveis, em um ciclo.
class RoundRobinLoadBalancer:
    # O construtor da classe.
    def __init__(self):
        # 'self.workers': uma lista que armazenará os IDs dos workers ativos.
        self.workers: List[str] = []
        # 'self.current_index': um ponteiro que aponta para o próximo worker a receber uma tarefa.
        self.current_index = 0
        # 'self.lock': um Lock para garantir que as operações na lista de workers sejam thread-safe.
        self.lock = threading.Lock()

    # Método para atualizar a lista de workers ativos.
    # É chamado periodicamente pelo orquestrador quando a lista de workers muda (alguém entra ou sai).
    def update_workers(self, workers: List[str]):
        # Adquire o lock para modificar a lista de workers com segurança.
        with self.lock:
            # Ordena a lista de workers. Isso garante uma ordem consistente, evitando que a
            # sequência de distribuição mude drasticamente se a lista for recebida em ordens diferentes.
            self.workers = sorted(workers)
            # Se o índice atual ficou inválido (ex: a lista de workers diminuiu),
            # ele é resetado para 0 para evitar um erro de "index out of bounds".
            if self.current_index >= len(self.workers):
                self.current_index = 0
    
    # Método principal que retorna o ID do próximo worker que deve receber uma tarefa.
    def get_next_worker(self) -> str | None:
        # Adquire o lock para ler a lista de workers e o índice com segurança.
        with self.lock:
            # Se não houver workers ativos na lista, retorna None.
            if not self.workers:
                return None
            
            # Checagem de segurança extra para o índice, caso a lista tenha sido esvaziada.
            if self.current_index >= len(self.workers):
                self.current_index = 0

            # Pega o ID do worker na posição atual do índice.
            worker = self.workers[self.current_index]
            
            # A mágica do Round Robin: avança o índice para a próxima posição.
            # O operador de módulo (%) faz com que o índice volte a 0 quando
            # atinge o final da lista, criando o efeito circular.
            self.current_index = (self.current_index + 1) % len(self.workers)
            
            # Retorna o ID do worker escolhido.
            return worker