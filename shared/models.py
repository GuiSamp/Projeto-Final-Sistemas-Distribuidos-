# shared/models.py

# --- Importações ---
# dataclasses: um decorador e funções para criar classes que armazenam dados de forma concisa.
# field: usado para fornecer valores padrão para campos de dataclass, especialmente para tipos mutáveis como dicionários.
from dataclasses import dataclass, field
# typing: para anotações de tipo, que ajudam a tornar o código mais legível e a detectar erros.
from typing import Dict, Any

# O decorador @dataclass automaticamente gera métodos especiais para a classe,
# como __init__(), __repr__(), __eq__(), etc. Isso simplifica a criação de classes
# cujo principal objetivo é armazenar dados.
@dataclass
class Task:
    """
    Representa uma única unidade de trabalho (tarefa) no sistema.
    Esta classe é usada para transportar informações sobre uma tarefa entre o cliente,
    o orquestrador e os workers.
    """
    
    # Atributos da tarefa:
    
    # O identificador único da tarefa (geralmente um UUID).
    id: str
    
    # O identificador do cliente que submeteu a tarefa.
    client_id: str
    
    # O estado atual da tarefa. O valor padrão é "PENDING" quando uma tarefa é criada.
    # Estados possíveis: PENDING, IN_PROGRESS, COMPLETED, FAILED
    status: str = "PENDING"
    
    # Um dicionário para armazenar os dados específicos da tarefa (o "payload").
    # Ex: a descrição, parâmetros de execução, duração, etc.
    # 'field(default_factory=dict)' garante que cada nova instância de Task
    # receba um dicionário novo e vazio, evitando que todas compartilhem o mesmo.
    data: Dict[str, Any] = field(default_factory=dict)
    
    # O timestamp do Relógio de Lamport, atribuído pelo orquestrador no momento da criação.
    # Usado para manter uma ordem causal dos eventos no sistema distribuído.
    lamport_ts: int = 0
    
    # O ID do worker que está atualmente executando a tarefa.
    # É 'None' se a tarefa estiver pendente ou se tiver falhado antes da atribuição.
    assigned_worker: str = None
    
    # Armazena o resultado da tarefa após sua conclusão.
    # Pode ser qualquer tipo de dado ('Any').
    result: Any = None