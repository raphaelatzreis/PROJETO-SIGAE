# PROJETO-SIGAE
Sistema Integrado de Gestão e Atendimento de Emergência (SIGAE). Projeto de Estrutura de Dados Avançados com Árvore Rubro-Negra, Min-Heap e Tabela Hash.

Todas as operações do pronto-socorro (cadastrar, localizar, reclassificar, atender, listar e cancelar) passam pela camada de serviço, que mantém as três estruturas sincronizadas. A interface web só consome essa camada e mostra o estado das estruturas em tempo real.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

- Painel do operador: http://127.0.0.1:5000
- Telão da sala de espera: http://127.0.0.1:5000/painel
- Visualização das estruturas (fora do menu): http://127.0.0.1:5000/estruturas

### Testes

```bash
python -m unittest discover -s testes -t .
```

São 125 testes, cobrindo as três estruturas, os modelos e a camada de serviço.

## Estrutura do projeto

```
PROJETO-SIGAE/
├── app.py          # servidor Flask: rotas HTTP, que delegam ao ServicoAtendimento
├── estruturas/     # Árvore Rubro-Negra, Fila de Prioridade (Min-Heap) e Tabela Hash
├── servico/        # Paciente, Medico e ServicoAtendimento (regras de negócio e sincronização)
├── templates/      # páginas HTML (painel do operador e telão)
├── static/         # CSS e JavaScript da interface
└── testes/         # testes automatizados (unittest)
```

## Estruturas de dados

| Estrutura | Arquivo | Papel no sistema | Chave / critério |
|---|---|---|---|
| Árvore Rubro-Negra | `estruturas/arvore_rubro_negra.py` | Memória cronológica: lista os pacientes por ordem de chegada | `(horário, ID)` |
| Min-Heap de pacientes | `estruturas/fila_prioridade.py` | Fila de atendimento: define quem é chamado | nível de urgência → horário de chegada → ID |
| Min-Heap de médicos | `estruturas/fila_prioridade.py` | Escolhe o médico disponível | menos atendimentos concluídos → ordem de cadastro → ID |
| Tabela Hash | `estruturas/tabela_hash.py` | Localiza um paciente pelo ID | `ID % capacidade` |

### Árvore Rubro-Negra

- Inserção e remoção com rotações e recoloração, mantendo as propriedades rubro-negras (raiz preta, sem dois vermelhos seguidos, mesma altura negra em todos os caminhos).
- O empate de horário é resolvido pelo ID, então dois pacientes nunca têm a mesma chave.
- O percurso em ordem (`listar_em_ordem`) devolve os pacientes na ordem de chegada.
- `validar()` confere as propriedades da árvore e a ordenação das chaves.
- Complexidade: inserção, remoção e busca em O(log n); listagem em O(n).

Mais detalhes em [estruturas/README_arvore_rubro_negra.md](estruturas/README_arvore_rubro_negra.md).

### Fila de Prioridade (Min-Heap)

- Uma única classe, `FilaPrioridade`, recebe a regra de comparação no construtor. O serviço cria duas filas: uma com `paciente_vem_antes` e outra com `medico_vem_antes`.
- O heap é guardado em vetor, com um mapa de ID → posição. Com isso, reclassificar ou remover um paciente do meio da fila não exige busca linear.
- Operações: `inserir`, `remover_minimo`, `ver_proximo`, `alterar_prioridade`, `remover(id)`, `listar_ordenado` e `validar`.
- Complexidade: `ver_proximo` em O(1); inserir, remover e alterar prioridade em O(log n).

### Tabela Hash

- Função de dispersão `ID % capacidade`, com capacidade inicial 11.
- As colisões são tratadas por encadeamento separado: cada posição guarda uma lista de pares `[ID, paciente]`.
- Quando o fator de carga passa de 0,75, a tabela dobra de capacidade e redistribui todos os pacientes.
- A tabela contabiliza as colisões e permite inspecionar o conteúdo de um bucket (`inspecionar_bucket`).
- Complexidade: busca, inserção e remoção em O(1) no caso médio.

### Camada de serviço

`servico/servico_atendimento.py` concentra as regras de negócio e é o único ponto que altera as estruturas:

| Operação | Método | Estruturas usadas |
|---|---|---|
| Cadastrar paciente | `cadastrar_paciente` | Hash + Rubro-Negra + Heap de pacientes |
| Localizar paciente | `buscar_paciente` | Hash |
| Reclassificar urgência | `reclassificar_paciente` | Hash (localiza) + Heap de pacientes (reorganiza) |
| Atender | `chamar_proximo` | Heap de pacientes (mais urgente) + Heap de médicos (menos atendimentos); remove o paciente das três estruturas |
| Encerrar atendimento | `finalizar_atendimento` | Heap de médicos (o médico volta com +1 atendimento) |
| Listar por chegada | `listar_pacientes` | Rubro-Negra (percurso em ordem) |
| Cancelar | `cancelar_paciente` | Hash + Rubro-Negra + Heap de pacientes |
| Conferir consistência | `validar_integridade` | Todas |

Se qualquer etapa de uma operação falha, o serviço desfaz as etapas anteriores (rollback). Assim, um paciente nunca fica presente em uma estrutura e ausente em outra.

## Funcionalidades

**Painel do operador** (navegação lateral; vira barra inferior no celular)

| Seção | O que faz |
|---|---|
| Atendimento | Com o consultório **livre**: cartão do próximo paciente (sinais vitais, espera vs. tempo-alvo) e a lista dos próximos. Com paciente **chamado**: ID do paciente, médico responsável com o ID, prontuário do atendimento (dados da triagem, anamnese, exame físico, hipótese diagnóstica, conduta e desfecho) com salvamento automático, cronômetro, rechamar, encerrar e "encerrar e chamar próximo", com a fila ao lado |
| Fila | Tabela completa em duas ordens: **por prioridade** (Min-Heap) ou **por chegada** (percurso em ordem da Rubro-Negra). Tem filtro por nível, busca e reclassificação do nível de urgência (clique no selo). A chamada sempre segue a fila de prioridade |
| Nova triagem | Cadastro com classificação de risco (Protocolo de Manchester) e sinais vitais |
| Equipe médica | Cadastro de médicos, próximo médico a ser escalado e a ordem do Heap de médicos (atendimentos concluídos e situação) |
| Estruturas | Visualização ao vivo de tudo que está em memória (detalhes abaixo). Não aparece no menu, porque é uma tela técnica e não do operador: acesse por http://127.0.0.1:5000/estruturas |
| Histórico | Chamadas do turno com o médico responsável e a situação (em atendimento ou desfecho e duração da consulta); rechamada enquanto o atendimento está aberto |
| Ver paciente | Clique em qualquer paciente para abrir a ficha lateral (posição na fila, sinais vitais, remover) |

**Seção Estruturas**

- **Situação da integridade:** resultado de `validar_integridade()` e da validação da Rubro-Negra.
- **Testes ao vivo:** um botão para cada teste da defesa. O Teste A cadastra IDs que caem no mesmo bucket, localiza os dois e mostra o redimensionamento. O Teste B reclassifica pacientes e mostra quem passa a ocupar a raiz do Heap. O Teste C cadastra médicos com cargas diferentes e mostra qual é designado a cada chamada. O resultado aparece um passo por vez, com um indicador de progresso. Nos heaps, os nós que mudaram de posição aparecem primeiro no lugar antigo, com setas até o novo, e depois deslizam até lá. Para navegar, use os botões Anterior/Próximo, clique no número do passo ou use as setas ← e → do teclado. Cada teste roda num `ServicoAtendimento` separado, criado só para a demonstração, então não altera a fila real.
- **Atendimentos em andamento:** liga cada paciente ao médico que o atende e explica o critério das duas escolhas. Por exemplo, por que esse paciente foi chamado antes do seguinte e por que esse médico foi escalado.
- **Tabela Hash:** capacidade, quantidade, ocupação e total de colisões. Mostra os buckets (os com colisão ficam destacados) e tem uma busca por ID, que exibe o cálculo `ID % capacidade` e o bucket consultado.
- **Árvore Rubro-Negra:** desenho da árvore com as cores reais dos nós e a altura.
- **Heap de pacientes e Heap de médicos:** desenho de cada heap como árvore binária, na ordem do vetor.

**Regras gerais**

- Seletor de consultório no topo (fica salvo no navegador).
- Atalhos: `N` chama o próximo, `R` rechama o último, `Esc` fecha janelas.
- Cada consultório atende um paciente por vez: é preciso encerrar o atendimento (com desfecho) antes de chamar outro.
- Ao chamar ou rechamar, o painel mostra só o aviso visual: som e voz tocam **apenas no telão**.

**Telão (`/painel`)**

- Nome do paciente em destaque com o consultório, cor do nível e animação a cada chamada.
- Som de aviso (sintetizado, sem arquivos de áudio) seguido de chamada por voz em português, repetida duas vezes:
  *"Paciente Fulano, por favor, dirija-se ao Consultório 2."*
- Últimas chamadas, contagem de pacientes aguardando por nível e relógio.
- Os navegadores só liberam áudio depois de um clique, por isso o telão abre com o botão **Ativar som e voz**.
  Para TVs em modo quiosque, use `/painel?kiosk` com o navegador iniciado com autoplay liberado, ex.:
  `chrome --kiosk --autoplay-policy=no-user-gesture-required http://127.0.0.1:5000/painel?kiosk`

A voz usa a Web Speech API do navegador. Chrome e Edge já trazem vozes em pt-BR; em outros navegadores pode ser necessário instalar uma voz em português no sistema.

## API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/estado` | Estado completo: fila por prioridade e por chegada, médicos, histórico, estatísticas, resumo das estruturas e último evento |
| POST | `/api/pacientes` | Cadastra paciente (`nome`, `idade`, `sexo`, `nivel`, `queixa`, `sinais`, `observacoes`, `chegada`). `chegada` é opcional, no formato `HH:MM` de hoje; vazio usa a hora atual, e horário no futuro é recusado |
| GET | `/api/pacientes/<id>` | Localiza um paciente na fila pela Tabela Hash |
| PATCH | `/api/pacientes/<id>` | Reclassifica o nível de urgência (`nivel`) |
| DELETE | `/api/pacientes/<id>` | Cancela o paciente (remove das três estruturas) |
| POST | `/api/chamar` | Chama o paciente mais urgente com o médico disponível com menos atendimentos; `consultorio` define o destino |
| POST | `/api/rechamar` | Repete o aviso da última chamada, ou de uma específica com `seq` |
| PATCH | `/api/atendimentos/<seq>` | Salva o prontuário do atendimento em andamento (`prontuario`) |
| POST | `/api/atendimentos/<seq>/encerrar` | Encerra o atendimento e devolve o médico ao Heap; exige `prontuario.desfecho` (`alta`, `observacao`, `encaminhamento`, `internacao`, `nao_compareceu`) |
| POST | `/api/medicos` | Cadastra médico (`nome`) |
| GET | `/api/estruturas/hash/<id>` | Mostra como a Hash localiza o ID: índice calculado, conteúdo do bucket e situação do paciente |
| GET | `/api/demonstracao/<teste>` | Roda o teste ao vivo `a` (colisão), `b` (prioridade) ou `c` (balanceamento dos médicos) num serviço separado e devolve o passo a passo |
| POST | `/api/resetar` | Restaura os dados de teste |

Os IDs de paciente aceitam o formato `PAC-1049` ou o número puro `1049`.

## Equipe

<h3 align="center">Projeto acadêmico da disciplina de Estrutura de Dados Avançados<br>4º período · UNIVASSOURAS</h3>

<table align="center">
  <tr>
    <td align="center" width="20%">🔑<br><b>Ravi Carlos Diano da Costa e Dias da Fonseca</b><br><sub>Tabela Hash</sub></td>
    <td align="center" width="20%">🌳<br><b>Matheus Duarte Louredo da Costa</b><br><sub>Árvore Rubro-Negra</sub></td>
    <td align="center" width="20%">⛰️<br><b>Raphaela Tamara Zille dos Reis</b><br><sub>Fila de Prioridade (Min-Heap)</sub></td>
    <td align="center" width="20%">⚙️<br><b>Brenno Fernandes de Aragão</b><br><sub>Camada de serviço</sub></td>
    <td align="center" width="20%">🖥️<br><b>Marcos Gabriel Sales Pires</b><br><sub>Interface web e integração</sub></td>
  </tr>
</table>
