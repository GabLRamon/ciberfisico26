# VigiaNet

Projeto final de Conectividade em Sistemas Ciberfísicos: monitoramento de disponibilidade de serviços de uma pequena empresa.

## Integrantes

- Leonardo Bueno de Castilho dos Santos
- João Victor Araújo Lourenço Domingues
- Gabriel Leite Ramon
- Gustavo Garcia

## Cenário e objetivo

Uma pequena empresa depende de uma página interna para receber pedidos. O responsável de TI precisa perceber rapidamente quando o serviço HTTP deixa de responder ou quando o nome do serviço não pode ser resolvido. O VigiaNet verifica esses dois sinais em intervalos regulares, registra resultados e publica um painel HTTP somente de leitura.

## Arquitetura

```text
Nó 1: monitor (Linux / Python)                    Nó 2: alvo (Linux / Python)
+-------------------------------------+            +---------------------------+
| DNS getaddrinfo("alvo")             |            | HTTP :8000 /health        |
| HTTP GET http://alvo:8000/health    |--- bridge ->| resposta JSON de saúde   |
| concorrência: ThreadPoolExecutor    |   TCP/IP   | ThreadingHTTPServer       |
| painel HTTP :8080 /status           |            +---------------------------+
+------------------+------------------+
                   |
                   +-- host: http://127.0.0.1:8080/status
                       publicação limitada ao loopback
```

O HTTP foi escolhido por ser padronizado, simples de inspecionar e adequado à checagem de disponibilidade. A biblioteca `urllib` usa TCP para a conexão HTTP. As verificações de DNS e HTTP ocorrem em paralelo com `ThreadPoolExecutor`; o painel aceita requisições simultâneas com `ThreadingHTTPServer`.

## Requisitos

- Windows com Docker Desktop e integração WSL2, ou Linux com Docker Engine e o plugin Compose.
- O Python 3.12 já vem na imagem Docker. A aplicação usa somente a biblioteca padrão do Python.

## Executar

No terminal, dentro desta pasta:

```bash
docker compose up --build -d
docker compose ps
```

Abra `http://127.0.0.1:8080/status`. O JSON deve mostrar verificações `dns` e `http` com `ok: true`. Recarregue a página para consultar o último ciclo concluído.

Para acompanhar registros:

```bash
docker compose logs -f monitor
```

Para encerrar:

```bash
docker compose down
```

## Evidências Linux e rede

Os contêineres são processos Linux em uma rede bridge do Docker. Execute os comandos abaixo e guarde capturas de tela legíveis para o relatório e o vídeo:

```bash
docker compose exec monitor sh -lc 'ip -br address; ip route'
docker compose exec monitor sh -lc 'getent hosts alvo; dig alvo'
docker compose exec monitor sh -lc 'ss -tn'
docker compose exec monitor sh -lc 'ping -c 2 alvo'
docker network inspect vigianet-demo
curl -s http://127.0.0.1:8080/status
```

O Dockerfile instala `iproute2`, `iputils-ping`, `dnsutils`, `procps` e `curl` na imagem. Se a configuração local do Docker bloquear o `ping`, use a resolução de nome e o HTTP como evidências de conectividade e registre a limitação.

### Falha provocada e recuperação

```bash
docker compose stop alvo
# Aguarde um novo ciclo do monitor.
curl -s http://127.0.0.1:8080/status
docker compose start alvo
# Aguarde um novo ciclo para observar a recuperação.
curl -s http://127.0.0.1:8080/status
```

Durante a parada, HTTP deve aparecer como falha e DNS pode continuar resolvendo. Após iniciar o alvo, HTTP deve voltar a `ok: true` no ciclo seguinte. Registre o horário, as duas respostas e a saída de `docker compose logs --tail=30 monitor`. Esta é a evidência de falha e recuperação a inserir no PDF; não use valores de exemplo como se fossem medições.

## Segurança e limites

- O alvo é fixado pelo Compose (`http://alvo:8000/health`); não há varredura de endereços.
- A porta HTTP do alvo não é publicada no host; o painel é publicado somente em `127.0.0.1`.
- Os contêineres executam como usuário sem privilégios. O painel não oferece operações de escrita.
- O protótipo não envia notificações externas, não autentica usuários no painel local e não substitui monitoramento de produção.
- Faça os testes somente neste ambiente local, conforme as regras da disciplina.


## Declaração de uso de IA generativa

Durante a preparação deste conteúdo, os autores utilizaram o assistente OpenAI Codex para apoiar o planejamento, a escrita e a revisão do código e do documento. Após esse apoio, os autores revisaram, executaram e editaram o conteúdo, compreendem o funcionamento da solução e assumem responsabilidade integral pelo que entregam.


## Referências

- Python Software Foundation. *socket — Low-level networking interface*. https://docs.python.org/3/library/socket.html
- Python Software Foundation. *urllib.request — Extensible library for opening URLs*. https://docs.python.org/3/library/urllib.request.html
- Python Software Foundation. *concurrent.futures — Launching parallel tasks*. https://docs.python.org/3/library/concurrent.futures.html
- Docker. *Networking overview*. https://docs.docker.com/engine/network/
- Docker. *Compose file reference*. https://docs.docker.com/reference/compose-file/
- PAULO, Luis Gonzaga de. *Projeto Final da Disciplina: PSI129A — Conectividade em Sistemas Ciberfísicos*. PUCPR, 2026.
