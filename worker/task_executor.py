# Importa o módulo 'time', que fornece funções relacionadas ao tempo.
# Neste caso, será usado para a função 'sleep', que pausa a execução do programa.
import time

# Define a função que simula a execução de uma tarefa.
# Ela recebe um dicionário 'task_data' com os detalhes da tarefa.
def execute_task(task_data):
    # Imprime uma mensagem no console indicando o início da tarefa, usando o 'id' da tarefa.
    print(f"Iniciando tarefa: {task_data['id']}...")
    
    # Pausa a execução da thread para simular um trabalho que leva tempo.
    # 'task_data.get('duration', 10)' busca o valor da chave 'duration' no dicionário.
    # Se a chave 'duration' não for encontrada, ele usa o valor padrão de 10 segundos.
    time.sleep(task_data.get('duration', 10))
    
    # Imprime uma mensagem indicando que a tarefa foi finalizada.
    print(f"Tarefa {task_data['id']} concluída.")
    
    # Retorna um dicionário simples para indicar o status de conclusão da tarefa.
    return {'status': 'completed'}