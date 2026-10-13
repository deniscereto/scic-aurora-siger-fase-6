# Relatório Técnico — SCIC: Sistema de Comunicação Interplanetária da Colônia

**Missão Aurora Siger | FIAP — Fase 6**

**Equipe:** Denis Urbano Cereto — RM 569187

---

## 1. Contexto da solução

A colônia Aurora Siger, em Marte, depende de dois níveis de comunicação:

1. **Enlace interplanetário com a Terra**, limitado pela velocidade da luz. Considerando a distância entre os planetas, o atraso de ida varia de **3,0 min** (54,6 milhões de km) a **22,3 min** (401 milhões de km). Uma pergunta e sua resposta podem levar **até 44,6 minutos**.
2. **Rede interna da colônia**, que liga os módulos (habitação, agricultura, suporte médico, energia etc.) a um hub central, com latências de dezenas de milissegundos.

Como a Terra não consegue responder em tempo real, a colônia precisa analisar seus próprios dados e decidir localmente. O **SCIC** é um protótipo em Python que organiza os dados operacionais e de comunicação, mede a confiabilidade das previsões de latência, prevê a latência com um modelo simples, prioriza alertas com **heap**, permite buscas rápidas com **trie** e gera uma análise final de apoio à decisão.

### 1.1 Organização do protótipo

| Arquivo | Função |
|---|---|
| `codigo_fonte.py` | Arquivo principal: menu no terminal com 12 funcionalidades e modo `--demo` |
| `dados_aurora_siger.csv` | Base simulada com 72 registros |
| `arquivos_extras/gerar_dados.py` | Script auxiliar que documenta e recria a base simulada (semente fixa) |
| `graficos_ou_imagens/` | 6 gráficos gerados pelo sistema |

O fluxo segue a sugestão da atividade: **coletar dados simulados → organizar arquivos → calcular indicadores → avaliar modelo → priorizar e consultar → gerar relatório**.

---

## 2. Descrição dos dados

A base `dados_aurora_siger.csv` contém **72 registros**: 12 módulos monitorados em 6 ciclos de coleta, um a cada 5 sols, entre 05/09/2026 e 30/09/2026.

| Campo | Descrição |
|---|---|
| `id_registro`, `ciclo`, `data_registro` | Identificação e momento da leitura |
| `modulo`, `tipo_modulo`, `essencial` | Módulo, categoria e se é essencial à sobrevivência |
| `codigo_sensor` | Identificador hexadecimal do sensor (ex.: `0xC011`) |
| `distancia_hub_km` | Distância do módulo até o hub de rede |
| `carga_trafego_mbps` | Tráfego de dados no ciclo |
| `qualidade_sinal_pct` | Qualidade do sinal do enlace (0 a 100%) |
| `tensao_v`, `corrente_a` | Medições elétricas da alimentação do módulo |
| `latencia_prevista_ms` | Latência estimada pela regra do planejamento |
| `latencia_observada_ms` | Latência medida pelos sensores |
| `status` | `ativo`, `manutenção` ou `alerta` |
| `nivel_criticidade` | Importância do módulo, de 1 a 5 |
| `mensagem_alerta` | Resumo da ocorrência |

**Eventos simulados** para tornar a análise realista: latência alta no enlace médico (ciclo 2), manutenção programada na agricultura (ciclo 3), **tempestade de poeira** que degradou o sinal de três módulos (ciclo 4), sobrecarga de tráfego no enlace com a Terra e queda de tensão no controle ambiental (ciclo 5), falha de disco no armazenamento de dados e rover fora da cobertura (ciclo 6). Resultado: **62 registros ativos, 9 alertas e 1 em manutenção**.

**Organização e limpeza (Pandas):** os dados são lidos com `pd.read_csv` para um DataFrame. A base tem **dois valores ausentes** propositais (uma leitura de qualidade de sinal e uma de corrente), preenchidos com a **mediana do próprio módulo**, que representa melhor aquele equipamento do que a média geral da colônia. Em seguida o sistema cria as colunas derivadas `potencia_w`, `erro_absoluto_ms`, `erro_relativo` e `classificacao_erro`. Os alertas usam dicionários e listas; as buscas usam objetos `Trie`.

---

## 3. Indicadores de comunicação

| Indicador | Resultado |
|---|---|
| Latência média da rede interna | **46,05 ms** |
| Disponibilidade geral (registros ativos) | **86,1%** |
| Taxa geral de alertas | **12,5%** |
| Módulo com maior latência média | Rover de Exploração (97,1 ms) |
| Ciclo mais crítico | Ciclo 4: 3 alertas (25% dos módulos) e menor qualidade média de sinal (81,2%) |
| Uso máximo da microrrede | 77,2% da capacidade (ciclo 6) |

O ciclo 4 concentra os efeitos da tempestade de poeira: a qualidade média do sinal cai de cerca de 88% para 81,2% e a latência média sobe. No ciclo 6 a latência média chega ao maior valor da série (50,07 ms) por causa da falha de disco e do afastamento do rover.

---

## 4. Análise numérica: erro absoluto e erro relativo

- **Erro absoluto** = |latência observada − latência prevista|, em ms.
- **Erro relativo** = erro absoluto / |latência observada|, em %.

**Critério adotado:** até 10% é **aceitável**; de 10% a 25% exige **atenção**; acima de 25% é **preocupante** e gera alerta.

### 4.1 Resultados

| Módulo | Prevista (ms) | Observada (ms) | Erro abs. médio (ms) | Erro rel. médio | Classificação |
|---|---|---|---|---|---|
| Rover de Exploração | 72,5 | 97,10 | 24,60 | 23,9% | atenção |
| Microrrede Solar | 39,5 | 51,74 | 12,24 | 22,6% | atenção |
| Suporte Médico | 22,4 | 28,94 | 6,54 | 19,9% | atenção |
| Agricultura Hidropônica | 30,5 | 37,85 | 7,35 | 19,3% | atenção |
| Controle Ambiental | 23,6 | 29,24 | 5,64 | 19,0% | atenção |
| Comunicação Interplanetária | 49,7 | 61,68 | 11,98 | 18,2% | atenção |
| Combustível e Energia | 35,0 | 42,76 | 7,76 | 18,0% | atenção |
| Habitação Beta | 32,0 | 38,05 | 6,05 | 15,4% | atenção |
| Laboratório de Geologia | 45,8 | 54,18 | 8,38 | 15,4% | atenção |
| Armazenamento de Dados | 36,2 | 44,20 | 8,43 | 13,4% | atenção |
| Comando Central | 28,7 | 33,10 | 4,54 | 12,8% | atenção |
| Habitação Alfa | 30,8 | 33,79 | 2,99 | 8,5% | aceitável |

**Principal descoberta:** a regra do planejamento **subestima sistematicamente** a latência. Em média a latência real ficou **+8,83 ms** acima do previsto, e **97%** dos registros ficaram acima da previsão. A causa é que a regra ignora a qualidade do sinal. Isso motivou o modelo da seção 6.

**Por que o erro relativo é necessário:** o mesmo erro de 5 ms representa **17,3%** no Suporte Médico (latência ~28,9 ms), mas só **5,1%** no Rover (latência ~97,1 ms). O erro absoluto isolado esconde que o enlace médico, mais rápido e mais crítico, é o mais sensível.

**Registros preocupantes (> 25%):** 8 registros, todos ligados a eventos reais. O maior é a falha de disco do Armazenamento de Dados (52,3%), seguida da latência no enlace médico (46,3%), do rover fora da cobertura (42,5%) e dos módulos atingidos pela tempestade (31% a 40%).

### 4.2 Ponto flutuante e precisão numérica

- `0.1 + 0.2` resulta em `0.30000000000000004` e a comparação com `0.3` dá `False`. `math.isclose` resolve o problema.
- Somar 0,1 dez vezes em um laço resulta em `0.9999999999999999`: o erro de arredondamento se acumula a cada operação.
- A latência 55,19 ms guardada em `float32` vira 55,18999862..., uma diferença de **1,37 × 10⁻⁶ ms**.
- Arredondar a previsão para inteiro muda o erro relativo médio de **17,1980%** para **17,1314%** (0,07 ponto percentual).

**Interpretação:** erros de representação (~10⁻¹⁵) são desprezíveis perto dos erros físicos, que são de vários ms. Mesmo assim, o sistema nunca compara floats com `==`: ele usa faixas de tolerância (10% e 25%) e só arredonda na exibição, não nos cálculos intermediários.

### 4.3 Quando o erro é aceitável ou preocupante

Em **módulos essenciais** (suporte médico, controle ambiental, comunicação), um erro de 10% a 25% já justifica investigação, porque atrasos afetam diretamente a segurança da tripulação. Em módulos não essenciais, como o laboratório, a mesma faixa pode ser tolerada por mais tempo. Acima de 25%, o erro indica um evento anormal e vira alerta em qualquer módulo.

---

## 5. Simulação numérica: recuperação da latência (método de Euler)

Para estimar quanto tempo o enlace interplanetário leva para se recuperar depois da tempestade, a latência foi modelada como uma variável que volta ao normal a uma taxa constante:

$$\frac{dL}{dt} = -k\,(L - L_{base}), \quad k = 0{,}35\ \text{h}^{-1}$$

Os valores vêm da própria base: o pico na tempestade é **73,42 ms** e a latência normal (mediana dos ciclos ativos) é **57,08 ms**. O método de Euler aplica, a cada passo, $L_{n+1} = L_n + h \cdot f(L_n)$. Como esse modelo tem solução exata, foi possível medir o erro do próprio método:

| Passo h | Erro absoluto máximo em relação à solução exata |
|---|---|
| 2,0 h | 3,211 ms |
| 0,5 h | 0,567 ms |

Reduzir o passo em 4 vezes reduziu o erro em cerca de 5,7 vezes, o que confirma que passos menores dão mais precisão em troca de mais cálculos. A simulação indica que a latência volta a menos de 10% acima do normal em **cerca de 3 horas**. Essa informação ajuda a decidir entre ativar o enlace reserva ou apenas aguardar (gráfico `06_simulacao_euler.png`).

---

## 6. Modelo simples de previsão e avaliação de performance

**Problema:** prever a latência interna (`latencia_observada_ms`) a partir de três variáveis medidas pelos sensores: distância até o hub, carga de tráfego e qualidade do sinal. É um problema de **regressão**, então foram usadas as métricas MAE, MSE, RMSE e R².

**Divisão dos dados** (`train_test_split`, `random_state=42`): **42 registros de treino, 15 de validação e 15 de teste**. O treino ajusta os coeficientes, a validação escolhe entre os candidatos e o teste é usado uma única vez, para a avaliação final.

### 6.1 Escolha do modelo (validação)

| Candidato | RMSE validação | R² validação | AIC (treino) | BIC (treino) |
|---|---|---|---|---|
| Regressão linear simples (só distância) | 11,737 | 0,556 | 184,96 | 188,43 |
| **Regressão linear múltipla (3 variáveis)** | **8,592** | **0,762** | **93,29** | **100,25** |

A regressão múltipla venceu em todos os critérios. O AIC e o BIC penalizam o número de parâmetros e, mesmo assim, a regressão múltipla teve valores muito menores. Isso mostra que as duas variáveis extras melhoram o ajuste de verdade, e não apenas tornam o modelo mais complexo.

### 6.2 Avaliação final (teste)

| Método | MAE (ms) | MSE (ms²) | RMSE (ms) | R² |
|---|---|---|---|---|
| Baseline (prever sempre a média) | 14,965 | 392,103 | 19,802 | −0,001 |
| Regra atual do planejamento | 7,282 | 114,699 | 10,710 | 0,707 |
| **Regressão múltipla** | **3,168** | **13,275** | **3,644** | **0,966** |

**Equação obtida:**

latência (ms) = 58,519 + 9,543 × distância_km + 0,357 × carga_Mbps − 0,522 × qualidade_sinal_%

Cada ponto percentual a menos de qualidade de sinal acrescenta cerca de 0,52 ms de latência. Esse é justamente o efeito que a regra do planejamento ignorava.

### 6.3 Interpretação das métricas

- **MAE = 3,17 ms:** em média, a previsão erra cerca de 3 ms para mais ou para menos.
- **MSE = 13,28 ms²:** eleva os erros ao quadrado e por isso penaliza mais os erros grandes; a unidade (ms²) dificulta a leitura direta.
- **RMSE = 3,64 ms:** volta para a unidade da latência. Funciona como a "incerteza típica" da previsão.
- **R² = 0,966:** o modelo explica 96,6% da variação da latência no conjunto de teste.
- **RMSE / MAE = 1,15:** os erros são parecidos entre si. Uma razão bem maior indicaria poucos registros com erros muito grandes.
- O modelo reduz o RMSE em **81,6%** em relação ao baseline e em **66,0%** em relação à regra atual.

**Por que um único número não basta:** o RMSE na validação foi 8,59 ms, mas no teste foi 3,64 ms. Os três maiores erros do teste aconteceram em registros de operação normal, ou seja, **o conjunto de teste não sorteou nenhum dos eventos extremos** (tempestade, falha de disco). Por isso o R² de 0,966 é otimista: um R² alto não significa modelo perfeito. O modelo não conhece eventos como falhas de disco, que não aparecem nas variáveis de entrada. Com só 15 registros de teste, a métrica pode variar bastante conforme o sorteio. A conclusão correta é que o modelo é **muito melhor que a regra atual em operação normal**, mas eventos anormais continuam precisando do sistema de alertas.

---

## 7. Priorização de alertas com heap

### 7.1 Representação dos alertas

Cada registro com status `alerta` vira um **dicionário** com prioridade, tempo de espera, id do registro, ciclo, módulo, código do sensor, mensagem e uma lista de **motivos** que explicam a pontuação. Os motivos deixam a decisão transparente para o operador.

### 7.2 Critério de prioridade

| Critério | Pontos |
|---|---|
| Criticidade do módulo (1 a 5) | × 10 (até 50) |
| Módulo essencial | +15 |
| Latência acima do previsto (excesso %) | × 0,5 (até 20) |
| Risco operacional: sinal < 60% ou queda de tensão > 10% | +10 |
| Tempo desde o registro | +2 por ciclo de espera |

O último critério funciona como **envelhecimento** (*aging*): um alerta antigo ainda não resolvido ganha prioridade com o tempo e não fica esquecido no fundo da fila.

### 7.3 Como o heap organiza os alertas

A classe `FilaPrioridadeAlertas` implementa manualmente um **max-heap** sobre uma lista Python. Para o nó na posição *i*, o pai está em `(i−1)//2` e os filhos em `2i+1` e `2i+2`. A regra é que todo pai tem prioridade maior ou igual à dos filhos, então o alerta mais urgente fica sempre na posição 0.

- **Inserção + heapify-up:** o alerta entra no fim da lista e troca de lugar com o pai enquanto for mais urgente que ele.
- **Extração + heapify-down:** o topo é removido, o último elemento ocupa seu lugar e desce, trocando com o filho mais urgente, até a regra voltar a valer.
- **Desempate:** com prioridades iguais, vence o alerta que espera há mais tempo.

Estado do heap após inserir os 9 alertas da base:

```
Nível 0: [0] 93.0 Suporte Médico
Nível 1: [1] 89.0 Microrrede Solar | [2] 89.0 Comunicação Interplanetária
Nível 2: [3] 88.0 Suporte Médico | [4] 54.0 Rover | [5] 86.7 Comunicação | [6] 86.4 Controle Ambiental
Nível 3: [7] 75.0 Armazenamento de Dados | [8] 40.0 Rover
```

Só o topo é garantidamente o maior; os outros níveis ficam parcialmente ordenados. É isso que torna o heap barato de manter.

### 7.4 Seleção do alerta mais urgente

Ordem de atendimento obtida com extrações sucessivas:

1. **93,0:** Suporte Médico, latência 86% acima do previsto no enlace médico (essencial, aguardando há 4 ciclos)
2. **89,0:** Microrrede Solar, sinal degradado pela tempestade (sinal de 54%)
3. **89,0:** Comunicação Interplanetária, sinal degradado pela tempestade
4. **88,0:** Suporte Médico, nova latência acima do previsto
5. **86,7:** Comunicação Interplanetária, sobrecarga de tráfego no enlace com a Terra

Os alertas do Rover (não essencial, criticidade 2) ficam por último, mesmo com erro relativo alto. O critério combina **impacto** e **tamanho do desvio**, e não apenas o desvio.

### 7.5 Vantagem em relação a uma lista simples

| Operação | Lista simples | Heap |
|---|---|---|
| Inserir alerta | O(1) | O(log n) |
| Consultar o mais urgente | O(n) | O(1) |
| Remover o mais urgente | O(n) | O(log n) |

No teste do próprio sistema, com 5.000 alertas e 1.000 atendimentos, a lista levou **77,6 ms** e o heap **10,2 ms**, cerca de **8× mais rápido**. Os tempos variam de máquina para máquina, mas a proporção se mantém. A diferença cresce com o volume, o que importa numa rede em que sensores geram alertas o tempo todo. Ordenar a lista a cada novo alerta custaria O(n log n) por inserção.

---

## 8. Busca de registros com trie

A classe `Trie` guarda cada palavra caractere por caractere. Palavras com o mesmo início compartilham o mesmo caminho, e cada nó final guarda os registros associados à palavra. Os textos são normalizados (minúsculas e sem acento), então digitar "comunicacao" encontra "Comunicação".

O sistema mantém **quatro índices**:

| Índice | Palavras | Nós | Exemplo |
|---|---|---|---|
| Nomes de módulos (nome completo e cada palavra) | 35 | 292 | `com` → Comando Central, Combustível e Energia, Comunicação Interplanetária |
| Códigos de sensores | 12 | 40 | `0xC0` → 0xC011 e 0xC0A2 (setor de comunicação) |
| Palavras-chave de alertas | 28 | 176 | `tens` → registro 51, queda de tensão no Controle Ambiental |
| Comandos cadastrados | 10 | 166 | `re` → redirecionar_trafego, registrar_evento, reiniciar_modulo |

Com o prefixo `co`, o resultado inclui também o **Controle Ambiental**, como no exemplo da atividade.

**Por que a trie é adequada:** a busca desce apenas *m* nós (m = tamanho do prefixo) e depois visita só a subárvore dos resultados compatíveis. Numa lista, cada busca compara o prefixo com **todos** os registros, com custo O(n × m). No teste com **50.000 códigos de sensores**, a varredura da lista levou **1,004 ms** por busca e a trie **0,005 ms**, cerca de **200× mais rápida**. As duas encontraram os mesmos 11 resultados. O custo é usar mais memória, um nó por caractere. Em compensação, prefixos comuns (como `0xC0`, o setor de comunicação) são armazenados uma única vez. Na colônia, isso permite que um operador localize sensores, módulos ou comandos enquanto digita, mesmo com milhares de dispositivos cadastrados.

---

## 9. Dispositivos, bases numéricas e eletricidade aplicada à comunicação

### 9.1 Dispositivos de entrada, saída e interfaces

| Tipo | Dispositivo | Dado no SCIC |
|---|---|---|
| Entrada | Sensores de latência e qualidade de sinal nos roteadores | `latencia_observada_ms`, `qualidade_sinal_pct` |
| Entrada | Medidores de tráfego de rede | `carga_trafego_mbps` |
| Entrada | Voltímetro e amperímetro na alimentação dos módulos | `tensao_v`, `corrente_a` |
| Entrada | Teclado do operador | Cadastro manual de registros (opção 3) |
| Saída | Monitor/terminal | Menu, tabelas e alertas priorizados |
| Saída | Relatórios e gráficos | `relatorio_tecnico.md`, PNGs em `graficos_ou_imagens/` |
| Saída (conceitual) | Alarmes sonoros e luminosos | Acionados pelo topo do heap |
| Interface (conceitual) | Ethernet | Ligação cabeada entre domos: baixa latência e alta confiabilidade |
| Interface (conceitual) | Wi-Fi / Bluetooth | Habitações / sensores médicos portáteis |
| Interface (conceitual) | USB | Descarga de dados do rover quando volta à base |
| Interface (conceitual) | Rádio de longa distância | Enlace com a Terra (módulo Comunicação Interplanetária) |

No protótipo, os sensores são **simulados** pelo arquivo CSV e pela opção de cadastro.

### 9.2 Bases numéricas

Os códigos de sensores usam **16 bits** escritos em hexadecimal. Por padrão do SCIC, o **primeiro byte identifica o setor** e o **segundo identifica o sensor**. O sistema faz as conversões com funções manuais e as confere com `int()` e `format()` do Python.

Exemplo, o código **0xC011** (Comunicação Interplanetária):

- **Hexadecimal → decimal:** C(12)×16³ + 0×16² + 1×16¹ + 1×16⁰ = 49152 + 0 + 16 + 1 = **49169**
- **Decimal → binário** (divisões sucessivas por 2): **1100 0000 0001 0001**
- **Atalho:** cada dígito hexadecimal vale exatamente 4 bits (C = 1100, 0 = 0000, 1 = 0001)
- **Interpretação:** setor 0xC0 = 192 (rede de comunicação), sensor 0x11 = 17

O Comando Central (0xC0A2) pertence ao mesmo setor 192. Por isso a busca pelo prefixo `0xC0` na trie retorna os dois sensores de comunicação.

### 9.3 Eletricidade aplicada à comunicação

Medição do transmissor interplanetário no ciclo 6: **V = 47,79 V** e **I = 13,49 A**.

| Grandeza | Cálculo | Resultado |
|---|---|---|
| Potência elétrica | P = V × I = 47,79 × 13,49 | **644,7 W** |
| Resistência equivalente (Lei de Ohm) | R = V / I | **3,54 Ω** |
| Energia por sol (24,65 h) | E = P × t | **15,89 kWh** |
| Potência de transmissão (eficiência de 35%) | P_RF = 0,35 × P | **225,6 W = 53,5 dBm** |

**Circuito simples:** um LED indicador de alerta (2 V, 20 mA) ligado em 24 V precisa de um resistor R = (24 − 2) / 0,020 = **1100 Ω**. Usa-se o valor comercial acima mais próximo, 1,2 kΩ.

**Consumo da colônia:** no ciclo 6, a soma de P = V × I dos 12 módulos foi **3475,1 W**, ou **77,2%** da capacidade da microrrede (4500 W), com folga de 1025 W. O transmissor interplanetário é o maior consumidor individual.

---

## 10. Gerenciamento inteligente da comunicação

A discussão abaixo parte dos resultados do SCIC:

- **Sensores e medidores inteligentes:** cada linha da base corresponde a uma leitura de sensores IoT de latência, sinal, tráfego, tensão e corrente. Os valores ausentes na base mostram que sensores reais falham. O sistema precisa tratar essas falhas (aqui, com a mediana do módulo) em vez de parar.
- **Monitoramento contínuo:** comparar latência prevista e observada a cada ciclo detectou os 8 registros com erro acima de 25% no momento em que aconteceram. Também revelou um problema estrutural: o viés de +8,83 ms da regra de planejamento, que só aparece com acompanhamento contínuo.
- **Automação para decisões rápidas:** como uma resposta da Terra pode levar até 44,6 minutos, o SCIC ordena os alertas no heap e **sugere** um comando cadastrado para cada tipo de alerta. Exemplos: `comutar_enlace_reserva` para a tempestade, `redirecionar_trafego` para a sobrecarga e `controlar_carga` para a queda de tensão. A execução depende de validação humana.
- **Armazenamento e enlaces redundantes:** a falha de disco do ciclo 6 (erro de 52,3%) e a tempestade do ciclo 4, que afetou três módulos ao mesmo tempo, mostram a necessidade de cópias dos dados em mais de um módulo e de um enlace reserva para o tráfego crítico.
- **Manutenção preditiva:** o SCIC calcula a **tendência do erro relativo** de cada módulo ao longo dos ciclos. O Armazenamento de Dados (+7,10 p.p. por ciclo), o Rover (+4,29) e a Habitação Alfa (+2,42) são os primeiros candidatos a inspeção **antes** de falharem. A Habitação Alfa ainda está na faixa aceitável, e é exatamente esse tipo de desvio crescente que a manutenção preditiva procura.
- **Redes inteligentes e microrredes:** a tempestade do ciclo 4 atingiu ao mesmo tempo a comunicação e a Microrrede Solar. Integrar dados de rede e de energia (P = V × I) permite, num evento desses, desligar cargas não essenciais e manter alimentados suporte de vida, suporte médico e comunicação. Com 77,2% da capacidade em uso, a colônia tem folga, mas uma queda na geração solar tornaria essa priorização necessária.

---

## 11. Reflexão social, cultural e sustentável

**Uso eficiente da comunicação e sustentabilidade.** Numa colônia, toda energia é escassa. O transmissor interplanetário consome sozinho cerca de 645 W, o maior consumo individual da base. Prever a latência com mais precisão (RMSE 66% menor que a regra atual) e saber, pela simulação de Euler, que o enlace se recupera em cerca de 3 horas evita retransmissões e ativações desnecessárias do enlace reserva. Isso economiza energia e banda. O mesmo raciocínio vale na Terra: redes bem gerenciadas desperdiçam menos.

**Conhecimentos tradicionais e respeito à natureza.** Muitos povos indígenas organizam o uso de recursos a partir da observação atenta dos ciclos naturais, retirando do ambiente apenas o necessário e pensando nas gerações futuras. A Aurora Siger também vive sob ciclos que não controla, como as tempestades de poeira. A lição para o SCIC é planejar o consumo de energia e de comunicação **de acordo com esses ciclos**, por exemplo reduzindo cargas não essenciais em épocas de tempestade, em vez de apenas reagir às falhas.

**Diversidade cultural e sistemas não excludentes.** Um sistema de priorização define quem é atendido primeiro, e por isso precisa de critérios justos. No SCIC, a prioridade depende da **função** do módulo (suporte de vida, médico, comunicação) e do **desvio medido**, nunca de quem ocupa cada espaço. As duas habitações têm a mesma criticidade de propósito. Práticas de organização coletiva presentes em comunidades quilombolas e em tradições afro-brasileiras, como o mutirão e a decisão partilhada sobre bens comuns, inspiram a ideia de que os critérios de prioridade devem ser **discutidos e aceitos pela comunidade**, e não impostos por quem programa o sistema.

**Transparência nas decisões baseadas em dados.** Cada alerta do heap mostra os **motivos** que formaram sua pontuação (por exemplo: "criticidade 5, módulo essencial, latência 86% acima do previsto, aguardando há 4 ciclos"). Qualquer pessoa da colônia consegue entender por que um alerta passou na frente de outro e contestar o critério, se discordar.

**Responsabilidade humana sobre decisões automatizadas.** O SCIC **sugere** comandos, mas não os executa, e informa que cada ação requer validação do operador. Os próprios resultados mostram por quê: o modelo teve R² de 0,966 num teste sem eventos extremos e não prevê falhas de disco. Uma automação sem supervisão confiaria demais em um número que parece perfeito.

**Linguagem e interpretação justa.** As mensagens do sistema descrevem **equipamentos e eventos** ("queda de tensão na alimentação do módulo"), nunca pessoas ou grupos. A normalização de acentos na trie garante que a busca funcione independentemente de teclado ou idioma, um passo pequeno na direção de uma interface acessível para uma tripulação diversa.

---

## 12. Limitações e possíveis melhorias

**Limitações**

- Os dados são simulados, e a regra que gera a latência é linear. Por isso uma regressão linear se ajusta tão bem; dados reais seriam mais ruidosos.
- Com 72 registros, o conjunto de teste tem só 15 exemplos e não contém eventos extremos. As métricas variam conforme o sorteio.
- Os pesos da prioridade no heap foram definidos pela equipe e não foram validados com operadores.
- O cadastro de novos registros vale só para a sessão e não é salvo no CSV.
- A simulação de Euler usa uma taxa de recuperação k fixa, que é uma suposição e não uma medição.

**Melhorias**

- Usar validação cruzada (k-fold) para métricas mais estáveis com poucos dados.
- Incluir variáveis de evento (por exemplo, "tempestade ativa") no modelo, ou um classificador de risco de alerta.
- Ajustar os pesos da prioridade com Grid Search ou Random Search, usando decisões históricas dos operadores.
- Persistir os novos registros em CSV/JSON e receber leituras contínuas, simulando telemetria em tempo real.
- Estimar o parâmetro k da simulação a partir de várias tempestades registradas.

---

## 13. Conclusão

O SCIC mostra como estruturas de dados e análise numérica simples apoiam decisões numa colônia que não pode esperar a Terra. A análise de erros revelou que a regra de planejamento subestima a latência em 8,83 ms. A regressão múltipla reduziu o RMSE de 10,71 ms para 3,64 ms. O heap colocou no topo o alerta do Suporte Médico, e não o de maior erro bruto. A trie permitiu buscas por prefixo cerca de 200 vezes mais rápidas que a varredura de uma lista. Os cálculos elétricos ligaram a comunicação ao orçamento de energia da microrrede. A principal lição é que nenhum número isolado (um R² alto, uma prioridade, uma sugestão automática) substitui a interpretação humana. O sistema é mais útil quando torna seus critérios transparentes e deixa a decisão final com a equipe.
