# SCIC — Sistema de Comunicação Interplanetária da Colônia

**Missão Aurora Siger | FIAP — Fase 6**

**Equipe:** Denis Urbano Cereto — RM 569187

## Objetivo

O SCIC é um protótipo em Python que organiza dados operacionais e de comunicação da colônia Aurora Siger, em Marte. O sistema:

- carrega, limpa e consulta uma base simulada de 12 módulos em 6 ciclos;
- calcula indicadores de comunicação e o erro absoluto e relativo entre a latência prevista e a observada;
- treina uma regressão linear para prever a latência e a avalia com MAE, MSE, RMSE e R² (com AIC e BIC na escolha do modelo);
- prioriza alertas críticos com um **heap** (fila de prioridade) implementado manualmente;
- faz buscas por prefixo com uma **trie** em módulos, códigos de sensores, alertas e comandos;
- relaciona o protótipo a dispositivos de entrada e saída, bases numéricas e eletricidade (P = V × I, Lei de Ohm);
- simula a recuperação da latência após uma tempestade de poeira com o método de Euler;
- gera gráficos e uma análise final de gerenciamento inteligente da comunicação.

## Arquivos da entrega

| Arquivo | Descrição |
|---|---|
| `codigo_fonte.py` | **Arquivo principal do sistema** (menu no terminal) |
| `dados_aurora_siger.csv` | Base de dados simulada (72 registros) |
| `relatorio_tecnico.md` | Relatório técnico completo |
| `README.md` | Este arquivo |
| `link_video.txt` | Link do vídeo de apresentação no YouTube (não listado) |
| `graficos_ou_imagens/` | Pasta opcional com os gráficos gerados pelo sistema (opção 11 do menu) |
| `arquivos_extras/gerar_dados.py` | Pasta opcional com o script auxiliar que recria a base simulada (não é necessário para executar o sistema) |

Estrutura do .zip:

```
DenisUrbanoCereto_SCIC.zip
├── codigo_fonte.py
├── dados_aurora_siger.csv
├── relatorio_tecnico.md
├── README.md
├── link_video.txt
├── graficos_ou_imagens/      (opcional)
└── arquivos_extras/          (opcional)
```

## Dependências

Python 3.10 ou superior e as bibliotecas abaixo, todas trabalhadas na fase:

| Biblioteca | Uso no projeto |
|---|---|
| `pandas` | Leitura do CSV, limpeza, agrupamentos e tabelas |
| `numpy` | Cálculos numéricos, simulação de Euler e tendência (polyfit) |
| `matplotlib` | Geração dos gráficos em PNG |
| `scikit-learn` | Regressão linear, divisão treino/validação/teste e métricas |

Instalação:

```bash
pip install pandas numpy matplotlib scikit-learn
```

Os demais módulos usados (`math`, `random`, `time`, `sys`, `unicodedata`, `pathlib`) fazem parte da biblioteca padrão do Python. O heap e a trie foram implementados do zero, sem bibliotecas prontas.

## Como executar

Abra um terminal **dentro da pasta do projeto** e execute:

```bash
# Windows
py codigo_fonte.py

# Linux / macOS
python3 codigo_fonte.py
```

Para ver **todas as funcionalidades em sequência**, com entradas de exemplo automáticas (útil para a correção e para o vídeo):

```bash
py codigo_fonte.py --demo
```

## Menu do sistema

| Opção | Funcionalidade |
|---|---|
| 1 | Visualizar dados da colônia (carga, limpeza e estatísticas) |
| 2 | Consultar registros por módulo, status ou ciclo |
| 3 | Cadastrar novo registro (simula a leitura de um sensor) |
| 4 | Indicadores de comunicação e operação |
| 5 | Erro absoluto, erro relativo e ponto flutuante |
| 6 | Modelo de previsão de latência e métricas (MAE, MSE, RMSE, R², AIC, BIC) |
| 7 | Analisar alertas de comunicação com heap |
| 8 | Busca por prefixo com trie |
| 9 | Dispositivos, bases numéricas e eletricidade |
| 10 | Simulação da recuperação da latência (método de Euler) |
| 11 | Gerar gráficos |
| 12 | Análise final e gerenciamento inteligente |
| 0 | Sair |

## Exemplos de execução

- **Opção 7 (heap):** os 9 alertas são inseridos com heapify-up, e o sistema mostra o heap nível a nível e atende os mais urgentes. O primeiro é o Suporte Médico (prioridade 93,0), seguido da Microrrede Solar e da Comunicação Interplanetária, ambas afetadas pela tempestade de poeira.
- **Opção 8 (trie):** no índice de módulos, o prefixo `com` retorna Comando Central, Combustível e Energia e Comunicação Interplanetária. No índice de códigos, `0xC0` retorna os sensores do setor de comunicação.
- **Opção 6 (modelo):** a regressão múltipla obtém RMSE de 3,64 ms no teste, contra 10,71 ms da regra atual do planejamento.

## Observações

- O sistema não altera o arquivo CSV. Registros cadastrados na opção 3 valem apenas para a sessão atual.
- Para recriar a base simulada do zero: `py arquivos_extras/gerar_dados.py` (a semente é fixa, então os dados são sempre os mesmos).
- Os tempos dos testes de desempenho (heap x lista e trie x lista) variam conforme o computador.
