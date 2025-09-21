# orchestrator/lamport_clock.py

# Importa a biblioteca 'threading' para garantir que as operações no relógio
# sejam seguras em um ambiente com múltiplas threads (thread-safe).
import threading

# Define a classe que implementa o Relógio Lógico de Lamport.
# Este relógio é usado para estabelecer uma ordem causal parcial entre eventos em um sistema distribuído.
class LamportClock:
    # O construtor da classe.
    def __init__(self):
        # Inicializa o tempo lógico do relógio em 0.
        self.time = 0
        # Cria um "Lock" (cadeado) para evitar que múltiplas threads modifiquem
        # o valor do tempo ao mesmo tempo, o que poderia causar inconsistências.
        self._lock = threading.Lock()

    # Método para ser chamado quando um evento interno ocorre no processo (ex: criar uma tarefa).
    def increment(self):
        # O 'with self._lock:' garante que o bloco de código seguinte seja executado
        # por apenas uma thread de cada vez. O lock é liberado automaticamente no final.
        with self._lock:
            # A regra 1 do algoritmo de Lamport: incrementa o contador local.
            self.time += 1
            # Retorna o novo timestamp.
            return self.time

    # Método para ser chamado ao receber uma mensagem de outro processo que contém um timestamp.
    def update(self, received_time):
        with self._lock:
            # A regra 2 do algoritmo de Lamport: o tempo local é atualizado para ser o
            # máximo entre o seu valor atual e o timestamp recebido, e então incrementado.
            self.time = max(self.time, received_time) + 1
            # Retorna o novo timestamp atualizado.
            return self.time

    # Método para obter o valor atual do relógio de forma segura.
    def get_time(self):
        with self._lock:
            # Retorna o valor atual da variável 'time'.
            return self.time

    # Método para definir um novo valor para o relógio, usado pelo orquestrador de backup.
    def set_time(self, new_time):
        # Quando o backup assume ou sincroniza o estado, ele precisa ajustar seu relógio
        # para o valor mais recente conhecido no sistema para manter a consistência.
        with self._lock:
            self.time = new_time