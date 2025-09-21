# Plataforma Distribuída de Processamento Colaborativo de Tarefas

![Status](https://img.shields.io/badge/status-concluído-green)

Este projeto, desenvolvido para a disciplina de Sistemas Distribuídos, implementa uma plataforma de orquestração de tarefas que simula um sistema real de processamento colaborativo. A plataforma permite a submissão de trabalhos por clientes, que são distribuídos para múltiplos nós de processamento (workers), com acompanhamento de estado e recuperação em caso de falhas.

## Visão Geral do Projeto

O objetivo principal é aplicar conceitos centrais de sistemas distribuídos, como:

* **Balanceamento de Carga:** Distribuir o trabalho de forma equitativa entre os nós de processamento.
* **Tolerância a Falhas:** Garantir que o sistema continue operacional mesmo com a queda de um ou mais componentes (workers ou o orquestrador principal).
* **Replicação e Consistência de Estado:** Manter um orquestrador de backup sincronizado para assumir o controle em caso de falha (failover).
* **Comunicação entre Processos:** Utilizar diferentes protocolos de comunicação (TCP para tarefas, UDP para heartbeats e UDP Multicast para sincronização).
* **Ordenação de Eventos:** Empregar Relógios Lógicos de Lamport para manter uma ordem causal dos eventos no sistema.
* **Autenticação:** Controlar o acesso à submissão de tarefas através de um sistema simples de autenticação por token.

## Arquitetura do Sistema

O sistema é dividido em quatro componentes principais:

### 1. Orquestrador (Primário e Backup)
* **Responsabilidades:** Receber tarefas de clientes autenticados, distribuir para os workers usando uma política de balanceamento, monitorar a saúde dos workers via heartbeats e sincronizar seu estado com o backup. Em caso de falha de um worker, ele reatribui a tarefa para outro nó.
* **Failover:** O nó de Backup monitora o Primário e assume seu papel automaticamente em caso de falha.

### 2. Workers (Nós de Processamento)
* **Responsabilidades:** Executar as tarefas que recebem do orquestrador, reportar seu status periodicamente via heartbeat e notificar a conclusão do trabalho.

### 3. Clientes
* **Responsabilidades:** Autenticar-se no sistema, submeter novas tarefas para processamento e consultar o status de tarefas previamente submetidas.

## Recursos Implementados

- [✔] **Tolerância a Falhas:** Failover automático para o backup e redistribuição de tarefas em caso de queda de um worker.
- [✔] **Balanceamento de Carga:** Política *Round Robin* para distribuição de tarefas.
- [✔] **Sincronização de Estado:** O orquestrador primário sincroniza o estado global (fila de tarefas, workers ativos) com o backup via UDP Multicast.
- [✔] **Heartbeats:** Workers e o orquestrador primário enviam "sinais de vida" para monitoramento.
- [✔] **Autenticação e Segurança:** Sistema de login com usuário/senha que gera um token para autorizar operações.
- [✔] **Relógios de Lamport:** Timestamp para ordenação de eventos de submissão de tarefas.
- [✔] **Cliente via Linha de Comando (CLI):** Interface para interagir com o sistema (`login`, `submit`, `status`).

## Tecnologias Utilizadas

* **Linguagem:** Python 3
* **Bibliotecas:** Apenas bibliotecas padrão do Python (`socket`, `threading`, `json`, `argparse`, `logging`, `hashlib`, `uuid`).

## Pré-requisitos

* Python 3.8 ou superior.

## Como Executar

Para rodar o sistema, você precisará de **6 terminais** abertos na pasta raiz do projeto (`plataforma_distribuida`).

### Passo 1: Iniciar o Orquestrador Primário
**No Terminal 1**, inicie o coordenador principal.
```bash
python -m orchestrator.main
```

### Passo 2: Iniciar o Orquestrador de Backup
**No Terminal 2**, inicie o nó de backup que ficará monitorando o primário.
```bash
python -m orchestrator.main --backup
```

### Passo 3: Iniciar os Workers
Inicie cada worker em seu próprio terminal (o projeto exige um mínimo de 3).

**No Terminal 3:**
```bash
python -m worker.main localhost 60001
```

**No Terminal 4:**
```bash
python -m worker.main localhost 60002
```

**No Terminal 5:**
```bash
python -m worker.main localhost 60003
```

### Passo 4: Usar o Cliente
**No Terminal 6**, interaja com o sistema.

Faça Login (use as credenciais de config.py):
```bash
python -m client.main login user1 pass1
```

Submeta uma Tarefa (o -d simula a duração em segundos):
```bash
python -m client.main submit "Processar relatório financeiro" -d 15
```

Verifique o Status (substitua pelo ID da sua tarefa):
```bash
python -m client.main status <ID_DA_TAREFA_AQUI>
```

## Testando a Tolerância a Falhas

### Cenário 1: Falha de um Worker
1. Submeta uma tarefa de longa duração (ex: 20 segundos).
2. Observe no terminal do Orquestrador Primário qual worker recebeu a tarefa.
3. Vá ao terminal desse worker e pressione Ctrl + C para encerrá-lo.
4. Observe o Orquestrador: ele detectará a falha (worker para de enviar heartbeats) e reatribuirá a tarefa não concluída para outro worker ativo.

### Cenário 2: Failover do Orquestrador
1. Com o sistema todo em execução, vá ao terminal do Orquestrador Primário (Terminal 1) e pressione Ctrl + C.
2. Observe o terminal do Orquestrador de Backup (Terminal 2). Após o tempo de timeout, ele detectará a ausência do primário e assumirá o papel principal.
3. O sistema continuará funcionando. Você pode submeter novas tarefas pelo cliente, que serão gerenciadas pelo novo primário.

```
