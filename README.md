# PROJETO-SIGAE
Sistema Integrado de Gestão e Atendimento de Emergência (SIGAE) - Projeto de Estrutura de Dados Avançados com Árvore Rubro-Negra, Min-Heap e Tabela Hash.

## Como rodar

```bash
pip install -r requirements.txt
python main.py
```

- Painel do operador: http://127.0.0.1:5000
- Telão da sala de espera: http://127.0.0.1:5000/painel

## Funcionalidades

**Painel do operador** (navegação lateral; vira barra inferior no celular)

| Seção | O que faz |
|---|---|
| Atendimento | Indicadores (na fila, críticos, acima do tempo-alvo, espera média, atendidos), cartão do próximo paciente com sinais vitais e barra de espera vs. tempo-alvo, última chamada com botão de rechamar, próximos 5 da fila e distribuição por nível |
| Fila | Tabela completa por prioridade, filtro por nível, busca e botão de chamar qualquer paciente |
| Nova triagem | Cadastro com classificação de risco (Protocolo de Manchester) e sinais vitais |
| Histórico | Chamadas do turno, com rechamada individual |
| Ver paciente | Clique em qualquer paciente para abrir a ficha lateral (posição na fila, sinais vitais, chamar ou remover) |

- Seletor de consultório no topo (fica salvo no navegador).
- Atalhos: `N` chama o próximo, `R` rechama o último, `Esc` fecha janelas.
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
| GET | `/api/estado` | Estado completo (fila ordenada, histórico, estatísticas, último evento) |
| POST | `/api/pacientes` | Cadastra paciente (`nome`, `idade`, `sexo`, `nivel`, `queixa`, `sinais`, `observacoes`) |
| GET | `/api/pacientes/<id>` | Dados de um paciente na fila |
| DELETE | `/api/pacientes/<id>` | Remove paciente da fila |
| POST | `/api/chamar` | Chama o próximo, ou um paciente específico com `id`; `consultorio` define o destino |
| POST | `/api/rechamar` | Repete o aviso da última chamada, ou de uma específica com `seq` |
| POST | `/api/resetar` | Restaura os dados de teste |
