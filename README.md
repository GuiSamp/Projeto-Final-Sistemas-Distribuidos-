# Plataforma Distribuída

Este projeto implementa um sistema distribuído com orquestrador, workers e cliente.

## Como rodar

1. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Inicie o Orquestrador:
   ```bash
   python -m orchestrator.main
   ```

3. Inicie um Worker:
   ```bash
   python -m worker.main
   ```

4. Envie uma tarefa com o Cliente:
   ```bash
   python -m client.main
   ```
