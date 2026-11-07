# Trabalho 2 — Simulação de escalonamento de processos

**Disciplina:** Sistemas Operacionais — IFRS
**Dupla 3:** [Nome do integrante 1] e [Nome do integrante 2]
**Algoritmos implementados:** SRTF (Shortest Remaining Time First) e RR (Round Robin)

## Requisitos

- Python 3.7 ou superior
- Nenhuma biblioteca externa (usa apenas `json` e `sys`, da biblioteca padrão)

## Como executar

O programa lê um objeto JSON pela entrada padrão e escreve o resultado em JSON pela saída padrão:

```
python simulador.py < entradas/SRTF_EXP1.json > saidas/resultado_SRTF_EXP1.json
```

No **PowerShell** (Windows), o operador `<` não existe. Use uma destas formas:

```
Get-Content entradas\SRTF_EXP1.json | python simulador.py > saidas\resultado_SRTF_EXP1.json
python simulador.py entradas\SRTF_EXP1.json
```

A segunda forma (nome do arquivo como argumento) é uma alternativa equivalente. O programa não usa menus nem pede interação.

Para comparar os algoritmos, execute o programa uma vez para cada arquivo de entrada. Cada arquivo define o algoritmo no campo `algoritmo`.

## Formato da entrada

```json
{
  "algoritmo": "RR",
  "configuracao": { "quantum": 2 },
  "processos": [
    {"id": "P01", "chegada": 0, "cpu": 8},
    {"id": "P02", "chegada": 1, "cpu": 4}
  ]
}
```

- `algoritmo`: `"SRTF"` ou `"RR"`.
- `configuracao`: `{}` para SRTF; `{"quantum": n}` para RR, com `n` inteiro positivo. Parâmetros de outros algoritmos são ignorados.
- `processos`: lista não vazia; `id` string única (`OCIOSO` é reservado), `chegada` inteiro >= 0, `cpu` inteiro > 0. Campos como `peso` são ignorados.

A saída contém `algoritmo`, `linha_do_tempo`, `processos` (métricas ordenadas por ID) e `medias`.

## Entradas inválidas

Em caso de erro, o programa imprime apenas um JSON de erro e encerra com código 1, sem simulação parcial:

```json
{"erro": "O tempo de CPU deve ser um inteiro positivo."}
{"erro": "Algoritmo não implementado: FCFS."}
```

São validados: JSON válido, campos obrigatórios, tipos, valores (chegada >= 0, cpu > 0, IDs únicos e não vazios), algoritmo implementado e quantum do RR.

## Organização do código

O arquivo `simulador.py` é dividido em quatro partes:

| Parte | Funções / classes | Responsabilidade |
|---|---|---|
| Leitura e validação | `ler_entrada`, `validar` | Lê o JSON, valida os campos e ordena os processos por (chegada, ID) |
| Políticas | `simular_srtf`, `simular_rr` | Decidem qual processo usa a CPU em cada instante |
| Linha do tempo | `LinhaDoTempo` | Registra os intervalos, une trechos adjacentes do mesmo processo e registra `OCIOSO` |
| Métricas | `calcular_metricas` | Calcula turnaround, espera, resposta e as médias |

## Estruturas de dados

- **Lista de pendentes:** processos que ainda não chegaram, ordenados por chegada e ID. A cada instante, os processos com `chegada <= t` são retirados do início e admitidos.
- **Dicionário `restante`:** tempo de CPU que falta para cada processo (chave = ID).
- **SRTF — lista de prontos:** a escolha é feita com `min()` pela chave (restante, chegada, ID). O processo atual só é substituído se outro tiver restante estritamente menor. A simulação avança uma unidade por vez. Como, entre chegadas e conclusões, o restante do processo atual só diminui e o dos outros não muda, isso produz as mesmas decisões que reavaliar apenas nesses eventos.
- **RR — fila FIFO (lista):** retira-se o primeiro, executa-se `min(quantum, restante)`. Ao fim da fatia, as chegadas ocorridas durante a fatia ou exatamente no seu fim entram na fila **antes** da reinserção do processo interrompido.
- **Dicionários `primeira` e `conclusao`:** instante da primeira execução e da conclusão de cada processo, usados no cálculo das métricas.

## Métricas

- turnaround = conclusão − chegada
- espera = turnaround − tempo de CPU
- resposta = primeira execução − chegada

## Arquivos do trabalho

```
T02/
├── simulador.py
├── README.md
├── Relatorio_Trabalho2.pdf
├── entradas/
│   ├── SRTF_EXP1.json      RR_EXP1.json        (Experimento 1: conjunto comum)
│   ├── SRTF_EXP2.json      RR_EXP2.json        (Experimento 2: ociosidade, chegadas e empates)
│   └── SRTF_EXP3.json      RR_Q1_EXP3.json     RR_Q2_EXP3.json     RR_Q4_EXP3.json
│                                               (Experimento 3: preempção no SRTF e quanta 1, 2 e 4 no RR)
└── saidas/
    └── resultado_<nome da entrada>.json        (uma saída para cada entrada)
```
