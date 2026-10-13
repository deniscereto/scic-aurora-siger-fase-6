"""
=====================================================================
 SCIC - Sistema de Comunicação Interplanetária da Colônia
 Missão Aurora Siger  |  FIAP - Fase 6
 Autor: Denis Urbano Cereto - RM 569187
---------------------------------------------------------------------
 ARQUIVO PRINCIPAL DO SISTEMA

 Como executar (dentro da pasta do projeto):
     py codigo_fonte.py           -> menu interativo no terminal
     py codigo_fonte.py --demo    -> executa todas as funcionalidades em
                                     sequência, com entradas de exemplo
     (no Linux/macOS use "python3" no lugar de "py")

 Dependências: pandas, numpy, matplotlib, scikit-learn
=====================================================================
"""
import math
import random
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # gera os gráficos direto em arquivo PNG, sem abrir janelas
import matplotlib.pyplot as plt
import matplotlib.ticker
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# Garante acentuação correta no terminal do Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 30)

# =====================================================================
# 0. CONFIGURAÇÕES E CONSTANTES DO SISTEMA
# =====================================================================
PASTA = Path(__file__).resolve().parent
ARQUIVO_DADOS = PASTA / "dados_aurora_siger.csv"
PASTA_GRAFICOS = PASTA / "graficos_ou_imagens"

LIMITE_ACEITAVEL = 0.10          # erro relativo de até 10%: aceitável
LIMITE_PREOCUPANTE = 0.25        # acima de 25%: preocupante
QUALIDADE_MINIMA = 60.0          # qualidade de sinal (%) abaixo disso = risco operacional
CAPACIDADE_MICRORREDE_W = 4500.0 # potência máxima que a microrrede entrega aos módulos
EFICIENCIA_TRANSMISSOR = 0.35    # fração da potência elétrica convertida em sinal de rádio
HORAS_POR_CICLO = 24.65          # um sol marciano dura cerca de 24 h 39 min
VELOCIDADE_LUZ_KM_S = 299_792.458

FEATURES = ["distancia_hub_km", "carga_trafego_mbps", "qualidade_sinal_pct"]
ALVO = "latencia_observada_ms"

# Comandos operacionais cadastrados (usados na busca por prefixo e nas sugestões automáticas)
COMANDOS_CADASTRADOS = {
    "comandar_antena": "Reposiciona a antena de alto ganho",
    "comutar_enlace_reserva": "Transfere o tráfego para o enlace redundante",
    "compactar_logs": "Compacta registros antigos para liberar espaço",
    "consultar_status": "Exibe o status atual de um módulo",
    "controlar_carga": "Reduz o consumo de cargas não essenciais",
    "reiniciar_modulo": "Reinicia o roteador local do módulo",
    "redirecionar_trafego": "Envia os dados por outra rota da rede",
    "registrar_evento": "Registra manualmente uma ocorrência",
    "desligar_carga_nao_essencial": "Desliga cargas não essenciais da microrrede",
    "diagnosticar_sensor": "Executa autoteste em um sensor",
}

MODO_DEMO = False  # no modo demo as entradas do teclado são substituídas por exemplos


# =====================================================================
# 1. FUNÇÕES AUXILIARES DE INTERFACE
# =====================================================================
def titulo(texto):
    print("\n" + "=" * 72)
    print(f" {texto}")
    print("=" * 72)


def subtitulo(texto):
    print(f"\n--- {texto} ---")


def pausar():
    if not MODO_DEMO:
        input("\nPressione Enter para voltar ao menu...")


def normalizar(texto):
    """Converte para minúsculas e remove acentos ("Comunicação" -> "comunicacao").
    Assim a busca funciona mesmo se o usuário digitar sem acento."""
    texto = unicodedata.normalize("NFD", str(texto).lower().strip())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def ler_texto(mensagem, exemplo):
    """Lê uma entrada do teclado. No modo demo usa o valor de exemplo."""
    if MODO_DEMO:
        print(f"{mensagem}{exemplo}   [exemplo automático]")
        return str(exemplo)
    return input(mensagem).strip()


def ler_numero(mensagem, exemplo, minimo=None, maximo=None, inteiro=False):
    """Lê um número validando o formato e o intervalo permitido."""
    while True:
        valor = ler_texto(mensagem, exemplo).replace(",", ".")
        try:
            numero = int(float(valor)) if inteiro else float(valor)
        except ValueError:
            print("  Valor inválido. Digite um número (ex.: 12.5).")
            continue
        if (minimo is not None and numero < minimo) or (maximo is not None and numero > maximo):
            print(f"  O valor deve estar entre {minimo} e {maximo}.")
            continue
        return numero


def classificar_erro(erro_relativo):
    if erro_relativo <= LIMITE_ACEITAVEL:
        return "aceitável"
    if erro_relativo <= LIMITE_PREOCUPANTE:
        return "atenção"
    return "preocupante"


# =====================================================================
# 2. CARGA, LIMPEZA E ORGANIZAÇÃO DOS DADOS (Pandas)
# =====================================================================
def calcular_colunas_derivadas(df):
    """Cria as colunas calculadas usadas em todo o sistema."""
    df = df.copy()
    # Potência elétrica: P = V x I (watts)
    df["potencia_w"] = (df["tensao_v"] * df["corrente_a"]).round(2)
    # Erro absoluto: |observado - previsto| (ms)
    df["erro_absoluto_ms"] = (df["latencia_observada_ms"] - df["latencia_prevista_ms"]).abs()
    # Erro relativo: erro absoluto / |valor observado| (fração; x100 = %)
    df["erro_relativo"] = df["erro_absoluto_ms"] / df["latencia_observada_ms"].abs()
    df["classificacao_erro"] = df["erro_relativo"].apply(classificar_erro)
    return df


def carregar_dados(caminho=ARQUIVO_DADOS):
    """Lê o CSV, trata valores ausentes e cria as colunas derivadas."""
    if not caminho.exists():
        print(f"Arquivo {caminho.name} não encontrado. Execute 'py arquivos_extras/gerar_dados.py' para recriá-lo.")
        sys.exit(1)
    df = pd.read_csv(caminho, encoding="utf-8-sig")
    ausentes = df.isna().sum()
    ausentes = ausentes[ausentes > 0]
    # Limpeza: leituras de sensor ausentes são preenchidas com a mediana do próprio módulo,
    # que representa melhor o comportamento daquele equipamento do que a média geral.
    for coluna in ["qualidade_sinal_pct", "corrente_a"]:
        df[coluna] = df[coluna].fillna(df.groupby("modulo")[coluna].transform("median"))
    return calcular_colunas_derivadas(df), ausentes


# =====================================================================
# 3. OPÇÃO 1 - VISUALIZAR DADOS
# =====================================================================
def opcao_visualizar(df, ausentes):
    titulo("1. DADOS OPERACIONAIS E DE COMUNICAÇÃO DA AURORA SIGER")
    print(f"Arquivo: {ARQUIVO_DADOS.name}")
    print(f"Registros: {len(df)} | Módulos: {df['modulo'].nunique()} | "
          f"Ciclos: {df['ciclo'].min()} a {df['ciclo'].max()} "
          f"({df['data_registro'].min()} a {df['data_registro'].max()})")

    subtitulo("Limpeza dos dados")
    if ausentes.empty:
        print("Nenhum valor ausente encontrado.")
    for coluna, qtd in ausentes.items():
        print(f"  {coluna}: {qtd} valor(es) ausente(s) -> preenchido(s) com a mediana do módulo")

    subtitulo("Módulos monitorados")
    modulos = df.drop_duplicates("modulo")[
        ["modulo", "tipo_modulo", "essencial", "codigo_sensor", "nivel_criticidade"]]
    print(modulos.to_string(index=False))

    subtitulo("Primeiros registros")
    print(df[["id_registro", "ciclo", "modulo", "latencia_prevista_ms", "latencia_observada_ms",
              "qualidade_sinal_pct", "status"]].head(8).to_string(index=False))

    subtitulo("Quantidade de registros por status")
    print(df["status"].value_counts().to_string())

    subtitulo("Estatísticas descritivas")
    print(df[["latencia_observada_ms", "qualidade_sinal_pct", "carga_trafego_mbps", "potencia_w"]]
          .describe().round(2).to_string())
    pausar()


# =====================================================================
# 4. OPÇÃO 2 - CONSULTAR REGISTROS
# =====================================================================
def opcao_consultar(df):
    titulo("2. CONSULTAR REGISTROS")
    print("[1] Por módulo   [2] Por status   [3] Por ciclo")
    tipo = ler_texto("Escolha o tipo de consulta: ", "1")
    colunas = ["id_registro", "ciclo", "modulo", "latencia_prevista_ms", "latencia_observada_ms",
               "qualidade_sinal_pct", "status", "mensagem_alerta"]
    if tipo == "1":
        termo = normalizar(ler_texto("Nome (ou parte do nome) do módulo: ", "interplanet"))
        resultado = df[df["modulo"].apply(normalizar).str.contains(termo, regex=False)]
    elif tipo == "2":
        termo = normalizar(ler_texto("Status (ativo, manutenção ou alerta): ", "alerta"))
        resultado = df[df["status"].apply(normalizar) == termo]
    elif tipo == "3":
        ciclo = ler_numero("Número do ciclo: ", 4, inteiro=True)
        resultado = df[df["ciclo"] == ciclo]
    else:
        print("Opção inválida.")
        pausar()
        return
    if resultado.empty:
        print("Nenhum registro encontrado.")
    else:
        print(f"\n{len(resultado)} registro(s) encontrado(s):")
        print(resultado[colunas].to_string(index=False))
    pausar()


# =====================================================================
# 5. OPÇÃO 3 - CADASTRAR NOVO REGISTRO
# =====================================================================
def opcao_cadastrar(df):
    titulo("3. CADASTRAR NOVO REGISTRO (simula a leitura de um sensor)")
    print("O registro é adicionado à sessão atual; o CSV original não é alterado.")
    modulos = df.drop_duplicates("modulo").reset_index(drop=True)
    for i, nome in enumerate(modulos["modulo"], start=1):
        print(f"  [{i:2}] {nome}")
    idx = ler_numero("Número do módulo: ", 1, minimo=1, maximo=len(modulos), inteiro=True)
    base = modulos.iloc[idx - 1]

    ciclo = ler_numero("Ciclo do registro: ", int(df["ciclo"].max()) + 1, minimo=1, inteiro=True)
    dist = ler_numero("Distância até o hub de rede (km): ", base["distancia_hub_km"], minimo=0)
    carga = ler_numero("Carga de tráfego (Mbps): ", 95, minimo=0)
    qualidade = ler_numero("Qualidade do sinal (%): ", 55, minimo=0, maximo=100)
    tensao = ler_numero("Tensão medida (V): ", base["tensao_v"], minimo=0)
    corrente = ler_numero("Corrente medida (A): ", 13, minimo=0)
    prevista = ler_numero("Latência prevista (ms): ", base["latencia_prevista_ms"], minimo=0.1)
    observada = ler_numero("Latência observada (ms): ", 78, minimo=0.1)

    # Status definido automaticamente pelas mesmas regras usadas na base
    erro_rel = abs(observada - prevista) / observada
    if erro_rel > LIMITE_PREOCUPANTE:
        status, mensagem = "alerta", "Latência acima do previsto"
    elif qualidade < QUALIDADE_MINIMA:
        status, mensagem = "alerta", "Qualidade de sinal baixa"
    else:
        status, mensagem = "ativo", "Operação normal"

    novo = {
        "id_registro": int(df["id_registro"].max()) + 1, "ciclo": ciclo,
        "data_registro": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "modulo": base["modulo"], "tipo_modulo": base["tipo_modulo"], "essencial": base["essencial"],
        "codigo_sensor": base["codigo_sensor"], "distancia_hub_km": dist, "carga_trafego_mbps": carga,
        "qualidade_sinal_pct": qualidade, "tensao_v": tensao, "corrente_a": corrente,
        "latencia_prevista_ms": prevista, "latencia_observada_ms": observada, "status": status,
        "nivel_criticidade": base["nivel_criticidade"], "mensagem_alerta": mensagem,
    }
    df = pd.concat([df, calcular_colunas_derivadas(pd.DataFrame([novo]))], ignore_index=True)
    print(f"\nRegistro {novo['id_registro']} cadastrado para '{base['modulo']}'.")
    print(f"  Erro relativo: {erro_rel:.1%} ({classificar_erro(erro_rel)}) | "
          f"Potência: {tensao * corrente:.1f} W | Status automático: {status} ({mensagem})")
    pausar()
    return df


# =====================================================================
# 6. OPÇÃO 4 - INDICADORES DE COMUNICAÇÃO E OPERAÇÃO
# =====================================================================
def indicadores_por_ciclo(df):
    tabela = df.groupby("ciclo").agg(
        registros=("id_registro", "count"),
        latencia_media_ms=("latencia_observada_ms", "mean"),
        qualidade_media_pct=("qualidade_sinal_pct", "mean"),
        alertas=("status", lambda s: int((s == "alerta").sum())),
        potencia_total_w=("potencia_w", "sum"),
    )
    tabela["taxa_alertas_pct"] = 100 * tabela["alertas"] / tabela["registros"]
    tabela["uso_microrrede_pct"] = 100 * tabela["potencia_total_w"] / CAPACIDADE_MICRORREDE_W
    return tabela.round(2)


def opcao_indicadores(df):
    titulo("4. INDICADORES DE COMUNICAÇÃO E OPERAÇÃO")

    subtitulo("Atraso do enlace interplanetário Marte -> Terra (limitado pela velocidade da luz)")
    for rotulo, dist_km in [("Distância mínima", 54.6e6), ("Distância média", 225e6),
                            ("Distância máxima", 401e6)]:
        atraso_s = dist_km / VELOCIDADE_LUZ_KM_S
        print(f"  {rotulo:17}: {dist_km / 1e6:6.1f} milhões de km -> {atraso_s / 60:5.1f} min só de ida "
              f"| {2 * atraso_s / 60:5.1f} min ida e volta")
    print("  Conclusão: uma consulta à Terra pode levar mais de 40 minutos para ter resposta.")
    print("  Por isso a colônia precisa analisar dados e priorizar alertas localmente (SCIC).")

    subtitulo("Rede interna: indicadores por módulo")
    tabela = df.groupby("modulo").agg(
        latencia_media_ms=("latencia_observada_ms", "mean"),
        latencia_max_ms=("latencia_observada_ms", "max"),
        qualidade_media_pct=("qualidade_sinal_pct", "mean"),
        disponibilidade_pct=("status", lambda s: 100 * (s == "ativo").mean()),
        alertas=("status", lambda s: int((s == "alerta").sum())),
        potencia_media_w=("potencia_w", "mean"),
    ).round(2).sort_values("latencia_media_ms", ascending=False)
    print(tabela.to_string())

    subtitulo("Rede interna: indicadores por ciclo")
    print(indicadores_por_ciclo(df).to_string())

    subtitulo("Resumo geral")
    print(f"  Latência média da rede interna ..: {df['latencia_observada_ms'].mean():.2f} ms")
    print(f"  Disponibilidade geral (ativos) ..: {100 * (df['status'] == 'ativo').mean():.1f}%")
    print(f"  Taxa geral de alertas ...........: {100 * (df['status'] == 'alerta').mean():.1f}%")
    print(f"  Módulo com maior latência média .: {tabela.index[0]} ({tabela.iloc[0]['latencia_media_ms']} ms)")
    pausar()


# =====================================================================
# 7. OPÇÃO 5 - ERRO ABSOLUTO, ERRO RELATIVO E PONTO FLUTUANTE
# =====================================================================
def tabela_erros_por_modulo(df):
    tabela = df.groupby("modulo").agg(
        essencial=("essencial", "first"),
        lat_prevista_ms=("latencia_prevista_ms", "mean"),
        lat_observada_ms=("latencia_observada_ms", "mean"),
        erro_abs_medio_ms=("erro_absoluto_ms", "mean"),
        erro_rel_medio=("erro_relativo", "mean"),
    )
    tabela["erro_rel_pct"] = 100 * tabela.pop("erro_rel_medio")
    tabela["classificacao"] = (tabela["erro_rel_pct"] / 100).apply(classificar_erro)
    return tabela.round(2).sort_values("erro_rel_pct", ascending=False)


def opcao_erros(df):
    titulo("5. ANÁLISE NUMÉRICA: ERRO ABSOLUTO E ERRO RELATIVO")
    print("Erro absoluto = |latência observada - latência prevista|   (em ms)")
    print("Erro relativo = erro absoluto / |latência observada|        (em %)")
    print(f"Critério: até {LIMITE_ACEITAVEL:.0%} aceitável | de {LIMITE_ACEITAVEL:.0%} a "
          f"{LIMITE_PREOCUPANTE:.0%} atenção | acima de {LIMITE_PREOCUPANTE:.0%} preocupante")

    subtitulo("Erro médio por módulo (todos os ciclos)")
    tabela = tabela_erros_por_modulo(df)
    print(tabela.to_string())

    vies = (df["latencia_observada_ms"] - df["latencia_prevista_ms"]).mean()
    acima = 100 * (df["latencia_observada_ms"] > df["latencia_prevista_ms"]).mean()
    print(f"\nViés da previsão do planejamento: em média a latência real ficou {vies:+.2f} ms em relação "
          f"ao previsto ({acima:.0f}% dos registros acima do previsto).")
    print("-> A regra do planejamento SUBESTIMA a latência, pois ignora a qualidade do sinal.")

    subtitulo("Por que o erro relativo é necessário?")
    menor = tabela["lat_prevista_ms"].idxmin()
    maior = tabela["lat_prevista_ms"].idxmax()
    lat_menor = tabela.loc[menor, "lat_observada_ms"]
    lat_maior = tabela.loc[maior, "lat_observada_ms"]
    print(f"Imagine o mesmo erro absoluto de 5 ms em dois módulos de escalas diferentes:")
    print(f"  {menor:28}: latência ~{lat_menor:6.2f} ms -> 5 ms = {5 / lat_menor:6.1%} de erro")
    print(f"  {maior:28}: latência ~{lat_maior:6.2f} ms -> 5 ms = {5 / lat_maior:6.1%} de erro")
    print("O erro absoluto é igual, mas o impacto é muito diferente. O erro relativo coloca")
    print("módulos de escalas diferentes na mesma régua.")

    subtitulo(f"Registros com erro preocupante (> {LIMITE_PREOCUPANTE:.0%})")
    graves = df[df["erro_relativo"] > LIMITE_PREOCUPANTE].sort_values("erro_relativo", ascending=False)
    exibir = graves[["id_registro", "ciclo", "modulo", "latencia_prevista_ms", "latencia_observada_ms",
                     "erro_absoluto_ms", "erro_relativo", "mensagem_alerta"]].copy()
    exibir["erro_relativo"] = (100 * exibir["erro_relativo"]).round(1).astype(str) + "%"
    print(exibir.round(2).to_string(index=False))

    subtitulo("Ponto flutuante e precisão numérica")
    print(f"  0.1 + 0.2 = {0.1 + 0.2!r}  -> é igual a 0.3? {0.1 + 0.2 == 0.3}")
    print(f"  math.isclose(0.1 + 0.2, 0.3) -> {math.isclose(0.1 + 0.2, 0.3)}")
    acumulado = 0.0
    for _ in range(10):
        acumulado += 0.1                  # acumula o erro de arredondamento a cada soma
    print(f"  Somar 0.1 dez vezes em um laço = {acumulado!r} (e não 1.0)")
    exemplo = float(df["latencia_observada_ms"].iloc[0])
    em_float32 = float(np.float32(exemplo))
    print(f"  Latência {exemplo} guardada em float64: {exemplo:.15f}")
    print(f"  Mesma latência guardada em float32:     {em_float32:.15f} "
          f"(diferença de {abs(exemplo - em_float32):.2e} ms)")
    prev_inteira = df["latencia_prevista_ms"].round(0)
    erro_original = df["erro_relativo"].mean()
    erro_arredondado = ((df["latencia_observada_ms"] - prev_inteira).abs() / df["latencia_observada_ms"]).mean()
    print(f"  Erro relativo médio com previsão em 1 casa decimal: {erro_original:.4%}")
    print(f"  Erro relativo médio arredondando a previsão para inteiro: {erro_arredondado:.4%} "
          f"(variação de {abs(erro_arredondado - erro_original) * 100:.4f} p.p.)")
    print("  Interpretação: erros de representação (~1e-15) e de float32 (~1e-6 ms) são desprezíveis")
    print("  perto dos erros físicos de vários ms. Mesmo assim, o sistema nunca compara floats com '==':")
    print("  usa limites (tolerâncias) como 10% e 25%. Arredondamentos agressivos (para inteiro) já")
    print("  alteram as métricas e devem ser evitados nos cálculos intermediários.")

    subtitulo("Quando o erro é aceitável ou preocupante na colônia?")
    print("  - Até 10%: variação normal da rede; nenhuma ação é necessária.")
    print("  - De 10% a 25%: atenção. Em módulos ESSENCIAIS (suporte médico, controle ambiental,")
    print("    comunicação) isso já justifica investigar, pois atrasos afetam a segurança da equipe.")
    print("  - Acima de 25%: preocupante. Indica evento anormal (tempestade, falha, sobrecarga) e gera alerta.")
    essenciais_atencao = tabela[(tabela["essencial"] == "sim") & (tabela["classificacao"] != "aceitável")]
    print(f"  Módulos essenciais fora da faixa aceitável: {', '.join(essenciais_atencao.index) or 'nenhum'}")
    pausar()


# =====================================================================
# 8. OPÇÃO 6 - MODELO SIMPLES DE PREVISÃO E MÉTRICAS (scikit-learn)
# =====================================================================
def calcular_metricas(y_real, y_previsto):
    """MAE, MSE, RMSE e R² de uma previsão."""
    mse = mean_squared_error(y_real, y_previsto)
    return {"MAE": mean_absolute_error(y_real, y_previsto), "MSE": mse,
            "RMSE": math.sqrt(mse), "R2": r2_score(y_real, y_previsto)}


def calcular_aic_bic(y_real, y_previsto, k):
    """AIC e BIC para regressão com erro gaussiano (k = número de parâmetros).
    Quanto menor, melhor o equilíbrio entre ajuste e simplicidade."""
    n = len(y_real)
    sse = float(np.sum((np.asarray(y_real) - np.asarray(y_previsto)) ** 2))
    base = n * math.log(sse / n)
    return base + 2 * k, base + k * math.log(n)


def treinar_modelos(df):
    """Divide os dados em treino (60%), validação (20%) e teste (20%), escolhe o melhor
    modelo na validação e faz a avaliação final no teste. Não imprime nada."""
    dados = df.dropna(subset=FEATURES + [ALVO])
    X, y = dados[FEATURES], dados[ALVO]
    X_resto, X_teste, y_resto, y_teste = train_test_split(X, y, test_size=0.20, random_state=42)
    X_treino, X_val, y_treino, y_val = train_test_split(X_resto, y_resto, test_size=0.25, random_state=42)

    candidatos = {
        "Regressão simples (só distância)": ["distancia_hub_km"],
        "Regressão múltipla (3 variáveis)": FEATURES,
    }
    validacao = []
    for nome, colunas in candidatos.items():
        modelo = LinearRegression().fit(X_treino[colunas], y_treino)
        m_val = calcular_metricas(y_val, modelo.predict(X_val[colunas]))
        aic, bic = calcular_aic_bic(y_treino, modelo.predict(X_treino[colunas]), k=len(colunas) + 1)
        validacao.append({"modelo": nome, "RMSE_validacao": m_val["RMSE"], "R2_validacao": m_val["R2"],
                          "AIC_treino": aic, "BIC_treino": bic})
    validacao = pd.DataFrame(validacao).set_index("modelo")
    escolhido = validacao["RMSE_validacao"].idxmin()
    colunas = candidatos[escolhido]

    # Modelo final: treinado com treino + validação e avaliado UMA vez no teste
    modelo_final = LinearRegression().fit(X_resto[colunas], y_resto)
    prev_modelo = modelo_final.predict(X_teste[colunas])
    prev_baseline = np.full(len(y_teste), y_resto.mean())                 # baseline: sempre prevê a média
    prev_planejamento = dados.loc[X_teste.index, "latencia_prevista_ms"]  # regra atual da colônia

    teste = pd.DataFrame({
        "Baseline (média do treino)": calcular_metricas(y_teste, prev_baseline),
        "Regra do planejamento": calcular_metricas(y_teste, prev_planejamento),
        "Modelo escolhido": calcular_metricas(y_teste, prev_modelo),
    }).T

    residuos = dados.loc[X_teste.index, ["id_registro", "ciclo", "modulo", "mensagem_alerta"]].copy()
    residuos["real_ms"] = y_teste.values
    residuos["previsto_ms"] = prev_modelo
    residuos["erro_ms"] = residuos["real_ms"] - residuos["previsto_ms"]

    return {"modelo": modelo_final, "colunas": colunas, "escolhido": escolhido,
            "validacao": validacao, "teste": teste, "residuos": residuos,
            "tamanhos": (len(X_treino), len(X_val), len(X_teste))}


def opcao_modelo(df):
    titulo("6. MODELO SIMPLES DE PREVISÃO DE LATÊNCIA E AVALIAÇÃO")
    print("Objetivo: estimar a latência interna (ms) de um módulo a partir de dados medidos pelos")
    print("sensores, para substituir a regra fixa do planejamento, que ignora a qualidade do sinal.")
    print(f"Variáveis de entrada: {', '.join(FEATURES)} | Variável prevista: {ALVO}")
    r = treinar_modelos(df)

    subtitulo("Divisão dos dados")
    print(f"  Treino: {r['tamanhos'][0]} | Validação: {r['tamanhos'][1]} | Teste: {r['tamanhos'][2]} registros")
    print("  Treino ajusta o modelo, validação escolhe entre candidatos e teste mede o desempenho final")
    print("  com dados que o modelo nunca viu.")

    subtitulo("Etapa 1 - comparação de candidatos na validação")
    print(r["validacao"].round(3).to_string())
    print(f"  Escolhido: {r['escolhido']} (menor RMSE na validação).")
    print("  AIC e BIC (no treino) penalizam modelos com mais parâmetros: o menor valor indica o melhor")
    print("  equilíbrio entre qualidade do ajuste e simplicidade.")

    subtitulo("Etapa 2 - avaliação final no conjunto de teste")
    print(r["teste"].round(3).to_string())

    subtitulo("Equação do modelo")
    modelo = r["modelo"]
    termos = " ".join(f"{c:+.3f} x {nome}" for c, nome in zip(modelo.coef_, r["colunas"]))
    print(f"  latência (ms) = {modelo.intercept_:.3f} {termos}")
    if "qualidade_sinal_pct" in r["colunas"]:
        coef_q = modelo.coef_[r["colunas"].index("qualidade_sinal_pct")]
        print(f"  Cada 1 ponto percentual a menos de qualidade de sinal aumenta a latência em ~{-coef_q:.2f} ms.")

    subtitulo("Interpretação das métricas")
    t = r["teste"]
    m = t.loc["Modelo escolhido"]
    b = t.loc["Baseline (média do treino)"]
    p = t.loc["Regra do planejamento"]
    razao = m["RMSE"] / m["MAE"]
    print(f"  MAE = {m['MAE']:.2f} ms: em média, a previsão erra {m['MAE']:.2f} ms para mais ou para menos.")
    print(f"  MSE = {m['MSE']:.2f} ms²: eleva os erros ao quadrado; penaliza muito os erros grandes.")
    print(f"  RMSE = {m['RMSE']:.2f} ms: volta para a unidade da latência (ms), facilitando a leitura.")
    print(f"  R² = {m['R2']:.3f}: o modelo explica {100 * max(m['R2'], 0):.1f}% da variação da latência no teste.")
    if razao > 1.25:
        print(f"  RMSE/MAE = {razao:.2f}: há poucos registros com erros bem maiores que a média,")
        print("  típicos de eventos anormais (tempestades, falhas) que as variáveis não capturam.")
    else:
        print(f"  RMSE/MAE = {razao:.2f}: os erros são parecidos entre si, sem grandes discrepâncias isoladas.")
    print(f"  Contra o baseline, o RMSE cai {100 * (1 - m['RMSE'] / b['RMSE']):.1f}%; contra a regra do "
          f"planejamento, cai {100 * (1 - m['RMSE'] / p['RMSE']):.1f}%.")
    print("  Atenção: um R² alto NÃO significa modelo perfeito. Ele não mostra erros grandes isolados,")
    print("  e com poucos registros de teste o valor pode variar bastante. Por isso as métricas")
    print("  são analisadas em conjunto e comparadas com referências (baseline e regra atual).")

    subtitulo("Maiores erros do modelo no teste")
    piores = r["residuos"].reindex(r["residuos"]["erro_ms"].abs().sort_values(ascending=False).index).head(3)
    print(piores.round(2).to_string(index=False))

    subtitulo("Simulação de previsão para um novo cenário")
    dist = ler_numero("Distância até o hub (km): ", 2.0, minimo=0)
    carga = ler_numero("Carga de tráfego (Mbps): ", 60, minimo=0)
    qualidade = ler_numero("Qualidade do sinal (%): ", 55, minimo=0, maximo=100)
    entrada = pd.DataFrame([{"distancia_hub_km": dist, "carga_trafego_mbps": carga,
                             "qualidade_sinal_pct": qualidade}])[r["colunas"]]
    previsao = float(modelo.predict(entrada)[0])
    print(f"  Latência estimada: {previsao:.2f} ms (incerteza típica: ± {m['RMSE']:.1f} ms, o RMSE do teste)")
    caminho = salvar_grafico_modelo(r, df)
    print(f"\nGráfico salvo em: {caminho}")
    pausar()


# =====================================================================
# 9. OPÇÃO 7 - PRIORIZAÇÃO DE ALERTAS COM HEAP (FILA DE PRIORIDADE)
# =====================================================================
class FilaPrioridadeAlertas:
    """Max-heap implementado manualmente sobre uma lista Python.

    O alerta mais urgente fica SEMPRE na posição 0 (topo).
    Para um nó na posição i:  pai = (i - 1) // 2 | filho esquerdo = 2i + 1 | filho direito = 2i + 2
    Regra do heap: a prioridade de um pai é sempre maior ou igual à dos seus filhos.
    """

    def __init__(self):
        self.heap = []

    def __len__(self):
        return len(self.heap)

    @staticmethod
    def _chave(alerta):
        # Compara pela prioridade; em caso de empate, vence o alerta que espera há mais tempo
        return (alerta["prioridade"], alerta.get("espera_ciclos", 0))

    def _maior(self, i, j):
        return self._chave(self.heap[i]) > self._chave(self.heap[j])

    def _trocar(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]

    def inserir(self, alerta):
        """Coloca o alerta no fim da lista e o faz 'subir' até a posição correta. O(log n)."""
        self.heap.append(alerta)
        self._heapify_up(len(self.heap) - 1)

    def _heapify_up(self, i):
        while i > 0:
            pai = (i - 1) // 2
            if self._maior(i, pai):      # filho mais urgente que o pai: sobe
                self._trocar(i, pai)
                i = pai
            else:
                break

    def extrair_mais_urgente(self):
        """Remove e devolve o topo; o último elemento vai para o topo e 'desce'. O(log n)."""
        if not self.heap:
            return None
        topo = self.heap[0]
        ultimo = self.heap.pop()
        if self.heap:
            self.heap[0] = ultimo
            self._heapify_down(0)
        return topo

    def _heapify_down(self, i):
        n = len(self.heap)
        while True:
            maior = i
            esquerdo, direito = 2 * i + 1, 2 * i + 2
            if esquerdo < n and self._maior(esquerdo, maior):
                maior = esquerdo
            if direito < n and self._maior(direito, maior):
                maior = direito
            if maior == i:               # já está na posição correta
                break
            self._trocar(i, maior)
            i = maior

    def espiar(self):
        """Consulta o alerta mais urgente sem removê-lo. O(1)."""
        return self.heap[0] if self.heap else None


def calcular_prioridade(reg, ciclo_atual, tensao_referencia):
    """Pontuação de urgência de um alerta (quanto maior, mais urgente).

      criticidade do módulo (1 a 5) x 10 ............. até 50 pontos
      módulo essencial ................................ +15 pontos
      latência acima do previsto: excesso % x 0,5 ..... até 20 pontos
      risco operacional (sinal < 60% ou queda de tensão) +10 pontos
      tempo desde o registro: 2 pontos por ciclo ...... evita que alertas antigos sejam esquecidos
    """
    pontos, motivos = 0.0, []
    pontos += reg["nivel_criticidade"] * 10
    motivos.append(f"criticidade {reg['nivel_criticidade']}")
    if normalizar(reg["essencial"]) == "sim":
        pontos += 15
        motivos.append("módulo essencial")
    excesso = max(0.0, (reg["latencia_observada_ms"] - reg["latencia_prevista_ms"])
                  / reg["latencia_prevista_ms"] * 100)
    if excesso > 0:
        pontos += min(excesso, 40) * 0.5
        motivos.append(f"latência {excesso:.0f}% acima do previsto")
    queda_tensao = reg["tensao_v"] < 0.9 * tensao_referencia
    if reg["qualidade_sinal_pct"] < QUALIDADE_MINIMA or queda_tensao:
        pontos += 10
        motivos.append("queda de tensão" if queda_tensao else f"sinal fraco ({reg['qualidade_sinal_pct']:.0f}%)")
    espera = int(ciclo_atual - reg["ciclo"])
    if espera > 0:
        pontos += 2 * espera
        motivos.append(f"aguardando há {espera} ciclo(s)")
    return round(pontos, 1), espera, motivos


def montar_alertas(df):
    """Transforma cada registro com status 'alerta' em um dicionário de alerta."""
    ciclo_atual = int(df["ciclo"].max())
    tensao_ref = df.groupby("modulo")["tensao_v"].median()
    alertas = []
    for _, reg in df[df["status"] == "alerta"].iterrows():
        prioridade, espera, motivos = calcular_prioridade(reg, ciclo_atual, tensao_ref[reg["modulo"]])
        alertas.append({
            "prioridade": prioridade, "espera_ciclos": espera, "id_registro": int(reg["id_registro"]),
            "ciclo": int(reg["ciclo"]), "modulo": reg["modulo"], "codigo_sensor": reg["codigo_sensor"],
            "mensagem": reg["mensagem_alerta"], "motivos": motivos,
        })
    return alertas


def imprimir_heap_por_niveis(fila):
    """Mostra a lista interna do heap como uma árvore, nível a nível."""
    nivel, inicio = 0, 0
    while inicio < len(fila.heap):
        fim = min(inicio + 2 ** nivel, len(fila.heap))
        itens = [f"[{i}] {fila.heap[i]['prioridade']:.1f} {fila.heap[i]['modulo'].split()[0]}"
                 for i in range(inicio, fim)]
        print(f"  Nível {nivel}: " + " | ".join(itens))
        inicio, nivel = fim, nivel + 1


def comparar_heap_com_lista(n_alertas=5000, n_atendimentos=1000):
    """Mede o tempo para inserir N alertas e atender os K mais urgentes nas duas estruturas."""
    gerador = random.Random(7)
    prioridades = [gerador.uniform(0, 100) for _ in range(n_alertas)]

    inicio = time.perf_counter()
    lista = []
    for p in prioridades:
        lista.append(p)                                               # inserir: O(1)
    for _ in range(n_atendimentos):
        indice = max(range(len(lista)), key=lista.__getitem__)       # procurar o maior: O(n)
        lista.pop(indice)
    tempo_lista = time.perf_counter() - inicio

    inicio = time.perf_counter()
    fila = FilaPrioridadeAlertas()
    for p in prioridades:
        fila.inserir({"prioridade": p})                               # inserir: O(log n)
    for _ in range(n_atendimentos):
        fila.extrair_mais_urgente()                                   # extrair: O(log n)
    tempo_heap = time.perf_counter() - inicio
    return tempo_lista, tempo_heap


def opcao_alertas_heap(df):
    titulo("7. PRIORIZAÇÃO DE ALERTAS COM HEAP (FILA DE PRIORIDADE)")
    print("Representação: cada alerta é um dicionário com prioridade, módulo, código do sensor,")
    print("ciclo, mensagem e os motivos que formaram a pontuação.")
    print("Critério: criticidade x10 + essencial (+15) + excesso de latência (até +20)")
    print("          + risco operacional (+10) + 2 pontos por ciclo de espera")
    alertas = montar_alertas(df)
    if not alertas:
        print("Nenhum alerta ativo.")
        pausar()
        return
    fila = FilaPrioridadeAlertas()

    subtitulo("Inserção dos alertas no heap (heapify-up a cada inserção)")
    for a in alertas:
        fila.inserir(a)
        print(f"  + {a['modulo']:28} ciclo {a['ciclo']} | prioridade {a['prioridade']:5.1f} "
              f"-> topo agora: {fila.espiar()['modulo']}")

    subtitulo("Organização interna do heap (lista vista como árvore)")
    imprimir_heap_por_niveis(fila)
    print("  Só o topo é garantidamente o maior; os demais níveis ficam apenas 'parcialmente ordenados'.")

    subtitulo("Atendimento em ordem de urgência (extração do topo + heapify-down)")
    qtd = ler_numero(f"Quantos alertas deseja atender agora (1 a {len(fila)})? ", min(5, len(fila)),
                     minimo=1, maximo=len(fila), inteiro=True)
    for posicao in range(1, qtd + 1):
        a = fila.extrair_mais_urgente()
        comando = sugerir_comando(a["mensagem"])
        print(f"  {posicao}º | prioridade {a['prioridade']:5.1f} | {a['modulo']} "
              f"(registro {a['id_registro']}, ciclo {a['ciclo']}, sensor {a['codigo_sensor']})")
        print(f"       {a['mensagem']}")
        print(f"       Motivos: {', '.join(a['motivos'])}")
        print(f"       Ação sugerida: {comando} (requer validação do operador)")
    print(f"\n  Alertas restantes na fila: {len(fila)}")

    subtitulo("Vantagem do heap em relação a uma lista simples")
    tempo_lista, tempo_heap = comparar_heap_com_lista()
    print("  Lista simples: inserir O(1), mas achar o mais urgente exige percorrer tudo: O(n).")
    print("  Heap: inserir e extrair custam O(log n); consultar o topo custa O(1).")
    print("  Teste com 5.000 alertas e 1.000 atendimentos:")
    print(f"    Lista simples: {tempo_lista * 1000:8.1f} ms")
    print(f"    Heap .........: {tempo_heap * 1000:8.1f} ms  (~{tempo_lista / tempo_heap:.0f}x mais rápido)")
    print("  Ordenar a lista inteira a cada novo alerta custaria O(n log n) por inserção. O heap mantém")
    print("  o mais urgente sempre acessível, o que importa quando alertas chegam continuamente.")
    pausar()


def sugerir_comando(mensagem):
    """Associa o tipo de alerta a um comando cadastrado (automação com supervisão humana)."""
    msg = normalizar(mensagem)
    regras = [("tempestade", "comutar_enlace_reserva"), ("trafego", "redirecionar_trafego"),
              ("tensao", "controlar_carga"), ("disco", "compactar_logs"),
              ("cobertura", "comandar_antena"), ("latencia", "diagnosticar_sensor"),
              ("sinal", "comandar_antena")]
    for palavra, comando in regras:
        if palavra in msg:
            return comando
    return "consultar_status"


# =====================================================================
# 10. OPÇÃO 8 - BUSCA POR PREFIXO COM TRIE
# =====================================================================
class NoTrie:
    """Cada nó representa um caractere. 'filhos' liga cada letra ao próximo nó."""

    def __init__(self):
        self.filhos = {}
        self.fim_de_palavra = False
        self.registros = []   # o que a palavra que termina neste nó representa


class Trie:
    """Árvore de prefixos: palavras com o mesmo início compartilham o mesmo caminho."""

    def __init__(self):
        self.raiz = NoTrie()
        self.total_nos = 1
        self.total_palavras = 0

    def inserir(self, palavra, registro):
        """Percorre (ou cria) um nó por caractere. Custo O(m), m = tamanho da palavra."""
        no = self.raiz
        for letra in normalizar(palavra):
            if letra not in no.filhos:
                no.filhos[letra] = NoTrie()
                self.total_nos += 1
            no = no.filhos[letra]
        if not no.fim_de_palavra:
            self.total_palavras += 1
        no.fim_de_palavra = True
        if registro not in no.registros:
            no.registros.append(registro)

    def buscar_prefixo(self, prefixo):
        """1) desce pela árvore seguindo o prefixo: O(m);
        2) coleta tudo o que está abaixo desse nó (só os resultados compatíveis)."""
        no = self.raiz
        for letra in normalizar(prefixo):
            if letra not in no.filhos:
                return []          # nenhuma palavra começa com esse prefixo
            no = no.filhos[letra]
        resultados, pilha = [], [no]
        while pilha:               # busca em profundidade a partir do nó do prefixo
            atual = pilha.pop()
            if atual.fim_de_palavra:
                resultados.extend(atual.registros)
            pilha.extend(atual.filhos.values())
        return sorted(set(resultados), key=str)


def limpar_codigo(codigo):
    """Aceita '0xC011', 'C011' ou 'c0' e devolve só os dígitos hexadecimais em minúsculo."""
    codigo = normalizar(codigo)
    return codigo[2:] if codigo.startswith("0x") else codigo


def construir_tries(df):
    """Cria quatro índices: nomes de módulos, códigos de sensores, palavras de alertas e comandos."""
    tries = {"modulos": Trie(), "codigos": Trie(), "alertas": Trie(), "comandos": Trie()}
    for _, linha in df.drop_duplicates("modulo").iterrows():
        nome = linha["modulo"]
        tries["modulos"].inserir(nome, nome)                 # nome completo
        for palavra in nome.split():
            if len(palavra) >= 3:
                tries["modulos"].inserir(palavra, nome)      # cada palavra ("Solar", "Dados"...)
        tries["codigos"].inserir(limpar_codigo(linha["codigo_sensor"]),
                                 f"{linha['codigo_sensor']} -> {nome}")
    for _, linha in df[df["status"] != "ativo"].iterrows():
        descricao = (f"registro {linha['id_registro']:>3} | ciclo {linha['ciclo']} | "
                     f"{linha['modulo']}: {linha['mensagem_alerta']}")
        for palavra in linha["mensagem_alerta"].split():
            if len(palavra) >= 4:
                tries["alertas"].inserir(palavra, descricao)
    for comando, descricao in COMANDOS_CADASTRADOS.items():
        tries["comandos"].inserir(comando, f"{comando}: {descricao}")
    return tries


NOMES_INDICES = {"1": ("modulos", "Nomes de módulos"), "2": ("codigos", "Códigos de sensores"),
                 "3": ("alertas", "Palavras-chave de alertas"), "4": ("comandos", "Comandos cadastrados")}


def executar_busca(tries, indice, prefixo):
    chave, nome = NOMES_INDICES[indice]
    consulta = limpar_codigo(prefixo) if chave == "codigos" else prefixo
    resultados = tries[chave].buscar_prefixo(consulta)
    print(f"\n  [{nome}] prefixo '{prefixo}' -> {len(resultados)} resultado(s)")
    for r in resultados:
        print(f"     - {r}")


def comparar_trie_com_lista(n_codigos=50000, repeticoes=200, prefixo="a1b"):
    """Compara a busca por prefixo na trie com a varredura de uma lista inteira."""
    gerador = random.Random(11)
    codigos = [f"{gerador.randrange(16 ** 6):06x}" for _ in range(n_codigos)]
    trie = Trie()
    for c in codigos:
        trie.inserir(c, c)
    inicio = time.perf_counter()
    for _ in range(repeticoes):
        res_lista = [c for c in codigos if c.startswith(prefixo)]
    tempo_lista = (time.perf_counter() - inicio) / repeticoes
    inicio = time.perf_counter()
    for _ in range(repeticoes):
        res_trie = trie.buscar_prefixo(prefixo)
    tempo_trie = (time.perf_counter() - inicio) / repeticoes
    return tempo_lista, tempo_trie, len(set(res_lista)), len(res_trie)


def opcao_trie(df):
    titulo("8. BUSCA POR PREFIXO COM TRIE")
    tries = construir_tries(df)
    for indice, (chave, nome) in NOMES_INDICES.items():
        t = tries[chave]
        print(f"  [{indice}] {nome:26} {t.total_palavras:3} palavras indexadas em {t.total_nos:4} nós")
    if MODO_DEMO:
        exemplos = [("1", "com"), ("1", "co"), ("1", "hab"), ("2", "0xC0"), ("2", "A1"),
                    ("3", "lat"), ("3", "tens"), ("4", "com"), ("4", "re")]
        for indice, prefixo in exemplos:
            print(f"\nÍndice [{indice}] | prefixo digitado: {prefixo}   [exemplo automático]")
            executar_busca(tries, indice, prefixo)
    else:
        while True:
            indice = input("\nEscolha o índice (1-4) ou Enter para sair: ").strip()
            if not indice:
                break
            if indice not in NOMES_INDICES:
                print("  Índice inválido.")
                continue
            prefixo = input("Digite o prefixo: ").strip()
            if prefixo:
                executar_busca(tries, indice, prefixo)

    subtitulo("Por que a trie é adequada para busca por prefixo?")
    tempo_lista, tempo_trie, n_lista, n_trie = comparar_trie_com_lista()
    print("  Na lista, cada busca compara o prefixo com TODOS os registros: O(n x m).")
    print("  Na trie, a busca desce só m nós (m = tamanho do prefixo) e depois visita apenas")
    print("  os registros compatíveis. O tempo não cresce com o total de registros da colônia.")
    print(f"  Teste com 50.000 códigos de sensores, prefixo 'a1b' ({n_trie} encontrados; lista achou {n_lista}):")
    print(f"    Lista (varredura): {tempo_lista * 1000:7.3f} ms por busca")
    print(f"    Trie ............: {tempo_trie * 1000:7.3f} ms por busca  (~{tempo_lista / tempo_trie:.0f}x mais rápida)")
    print("  Custo: a trie usa mais memória (um nó por caractere). Em compensação, prefixos comuns")
    print("  ('0xC0' = setor de comunicação) são armazenados uma única vez.")
    pausar()


# =====================================================================
# 11. OPÇÃO 9 - DISPOSITIVOS, BASES NUMÉRICAS E ELETRICIDADE
# =====================================================================
DIGITOS_HEX = "0123456789ABCDEF"


def hex_para_decimal_manual(codigo_hex):
    """Cada dígito é multiplicado por 16 elevado à sua posição (da direita para a esquerda)."""
    codigo = codigo_hex.upper().replace("0X", "")
    total, passos = 0, []
    for posicao, digito in enumerate(reversed(codigo)):
        valor = DIGITOS_HEX.index(digito)
        total += valor * 16 ** posicao
        passos.append(f"{digito}({valor}) x 16^{posicao} = {valor * 16 ** posicao}")
    return total, list(reversed(passos))


def decimal_para_base_manual(numero, base):
    """Divisões sucessivas pela base; os restos lidos de baixo para cima formam o resultado."""
    if numero == 0:
        return "0"
    restos = []
    while numero > 0:
        restos.append(DIGITOS_HEX[numero % base])
        numero //= base
    return "".join(reversed(restos))


def opcao_dispositivos(df):
    titulo("9. DISPOSITIVOS, BASES NUMÉRICAS E ELETRICIDADE APLICADA À COMUNICAÇÃO")

    subtitulo("Dispositivos de entrada, saída e interfaces do SCIC")
    print("  ENTRADA (alimentam o sistema):")
    print("    - Sensores de latência e qualidade de sinal nos roteadores -> latencia_observada_ms, qualidade_sinal_pct")
    print("    - Medidores de tráfego da rede -> carga_trafego_mbps")
    print("    - Medidores elétricos (voltímetro e amperímetro) -> tensao_v, corrente_a")
    print("    - Teclado do operador -> cadastro manual de registros (opção 3)")
    print("  SAÍDA (exibem os resultados):")
    print("    - Terminal/monitor com o menu do SCIC, gráficos PNG e o relatório técnico")
    print("    - Painel de alertas priorizados (opção 7), que poderia acionar alarmes sonoros ou luminosos")
    print("  INTERFACES DE COMUNICAÇÃO (conceituais):")
    print("    - Rede cabeada Ethernet entre domos (baixa latência, alta confiabilidade)")
    print("    - Wi-Fi nas habitações e Bluetooth para sensores médicos portáteis")
    print("    - USB para descarregar dados do rover quando ele retorna à base")
    print("    - Enlace de rádio de longa distância com a Terra (módulo Comunicação Interplanetária)")

    subtitulo("Códigos de sensores: hexadecimal, decimal e binário")
    print(f"  {'Módulo':28} {'Hex':>7} {'Decimal':>8}  {'Binário (16 bits)':19} Setor/Sensor")
    tudo_confere = True
    for _, linha in df.drop_duplicates("modulo").iterrows():
        codigo = linha["codigo_sensor"]
        decimal, _ = hex_para_decimal_manual(codigo)
        binario = decimal_para_base_manual(decimal, 2).zfill(16)
        tudo_confere &= (decimal == int(codigo, 16)) and (binario == format(decimal, "016b"))
        setor, sensor = decimal >> 8, decimal & 0xFF   # byte alto = setor | byte baixo = sensor
        print(f"  {linha['modulo']:28} {codigo:>7} {decimal:>8}  {binario[:8]} {binario[8:]}   {setor}/{sensor}")
    print(f"  Conversões manuais conferidas com int() e format() do Python: {'OK' if tudo_confere else 'ERRO'}")
    print("  Padrão do SCIC: o 1º byte identifica o SETOR (ex.: 0xC0 = 192 = rede de comunicação)")
    print("  e o 2º byte identifica o SENSOR dentro do setor.")

    subtitulo("Passo a passo de uma conversão")
    codigo = ler_texto("Digite um código hexadecimal de sensor: ", "0xC011")
    try:
        decimal, passos = hex_para_decimal_manual(codigo)
    except ValueError:
        print("  Código inválido: use apenas 0-9 e A-F (ex.: 0xC011).")
    else:
        print(f"  Hexadecimal -> decimal: {' + '.join(passos)}")
        print(f"  Resultado: {codigo.upper().replace('0X', '0x')} = {decimal} em decimal")
        print(f"  Decimal -> binário (divisões sucessivas por 2): {decimal_para_base_manual(decimal, 2)}")
        print(f"  Decimal -> hexadecimal (divisões sucessivas por 16): 0x{decimal_para_base_manual(decimal, 16)}")
        print("  Atalho: cada dígito hexadecimal corresponde a exatamente 4 bits (C = 1100, 0 = 0000, 1 = 0001).")

    subtitulo("Eletricidade aplicada ao transmissor interplanetário")
    tx = df[df["modulo"] == "Comunicação Interplanetária"].sort_values("ciclo").iloc[-1]
    v, i = tx["tensao_v"], tx["corrente_a"]
    p = v * i
    r = v / i
    energia_kwh = p * HORAS_POR_CICLO / 1000
    p_rf = p * EFICIENCIA_TRANSMISSOR
    dbm = 10 * math.log10(p_rf * 1000)
    print(f"  Medição do ciclo {tx['ciclo']}: tensão V = {v:.2f} V | corrente I = {i:.2f} A")
    print(f"  Potência elétrica:      P = V x I = {v:.2f} x {i:.2f} = {p:.1f} W")
    print(f"  Resistência equivalente (Lei de Ohm): R = V / I = {r:.2f} ohms")
    print(f"  Energia por sol ({HORAS_POR_CICLO} h): E = P x t = {energia_kwh:.2f} kWh")
    print(f"  Potência de transmissão (eficiência {EFICIENCIA_TRANSMISSOR:.0%}): {p_rf:.1f} W = {dbm:.1f} dBm")
    print("  Exemplo de circuito simples: um LED indicador de alerta de 2 V e 20 mA ligado em 24 V")
    print(f"  precisa de um resistor R = (24 - 2) / 0,020 = {(24 - 2) / 0.020:.0f} ohms (valor comercial: 1,2 kohm).")

    subtitulo("Consumo da colônia x capacidade da microrrede (último ciclo completo)")
    ciclos_completos = df.groupby("ciclo")["modulo"].nunique()
    ultimo = ciclos_completos[ciclos_completos == df["modulo"].nunique()].index.max()
    consumo = df[df["ciclo"] == ultimo].set_index("modulo")["potencia_w"].sort_values(ascending=False)
    for modulo, potencia in consumo.items():
        print(f"    {modulo:28} {potencia:8.1f} W")
    total = consumo.sum()
    print(f"  Total: {total:.1f} W de {CAPACIDADE_MICRORREDE_W:.0f} W disponíveis "
          f"({100 * total / CAPACIDADE_MICRORREDE_W:.1f}% da capacidade; folga de {CAPACIDADE_MICRORREDE_W - total:.0f} W)")
    pausar()


# =====================================================================
# 12. OPÇÃO 10 - SIMULAÇÃO NUMÉRICA COM O MÉTODO DE EULER
# =====================================================================
def simular_euler(df, k=0.35, horas=12):
    """Recuperação da latência do enlace interplanetário após a tempestade de poeira.
    Modelo: dL/dt = -k (L - L_base)  -> a latência volta ao normal a uma taxa k por hora.
    Solução exata: L(t) = L_base + (L_pico - L_base) e^(-k t), usada para medir o erro do método."""
    dados = df[df["modulo"] == "Comunicação Interplanetária"]
    pico = float(dados["latencia_observada_ms"].max())
    ativos = dados.loc[dados["status"] == "ativo", "latencia_observada_ms"]
    base = float(ativos.median() if not ativos.empty else dados["latencia_observada_ms"].median())

    def exata(t):
        return base + (pico - base) * np.exp(-k * t)

    resultados = {}
    for h in (2.0, 0.5):                         # dois tamanhos de passo para comparar
        t = np.arange(0, horas + h / 2, h)
        lat = np.empty_like(t)
        lat[0] = pico
        for n in range(len(t) - 1):
            lat[n + 1] = lat[n] + h * (-k * (lat[n] - base))   # passo de Euler
        resultados[h] = (t, lat, float(np.max(np.abs(lat - exata(t)))))
    return {"pico": pico, "base": base, "k": k, "horas": horas, "exata": exata, "resultados": resultados}


def opcao_euler(df):
    titulo("10. SIMULAÇÃO: RECUPERAÇÃO DA LATÊNCIA APÓS A TEMPESTADE (MÉTODO DE EULER)")
    sim = simular_euler(df)
    print(f"Latência no pico da tempestade: {sim['pico']:.2f} ms | latência normal do enlace: {sim['base']:.2f} ms")
    print(f"Equação: dL/dt = -{sim['k']} x (L - {sim['base']:.2f})   (k = taxa de recuperação por hora)")
    print("Euler: L(n+1) = L(n) + h x f(L(n)), em que h é o passo de tempo em horas.")

    subtitulo("Passo h = 2 h")
    t, lat, _ = sim["resultados"][2.0]
    print(f"  {'t (h)':>6} {'Euler (ms)':>11} {'Exata (ms)':>11} {'Erro abs.':>10}")
    for ti, li in zip(t, lat):
        ex = sim["exata"](ti)
        print(f"  {ti:6.1f} {li:11.2f} {ex:11.2f} {abs(li - ex):10.3f}")

    subtitulo("Efeito do tamanho do passo")
    for h, (_, _, erro_max) in sim["resultados"].items():
        print(f"  h = {h:3.1f} h -> erro absoluto máximo em relação à solução exata: {erro_max:.3f} ms")
    print("  Passos menores reduzem o erro do método (Euler tem erro proporcional a h), ao custo de")
    print("  mais cálculos. Aqui o erro é pequeno perto da variação real da latência.")
    if sim["pico"] > 1.1 * sim["base"]:
        t_rec = math.log((sim["pico"] - sim["base"]) / (0.1 * sim["base"])) / sim["k"]
        print(f"  Tempo estimado até a latência voltar a menos de 10% acima do normal: {t_rec:.1f} h.")
        print("  Esse tempo ajuda a decidir se vale ativar o enlace reserva ou só aguardar.")
    print(f"\nGráfico salvo em: {salvar_grafico_euler(sim)}")
    pausar()


# =====================================================================
# 13. OPÇÃO 11 - GRÁFICOS (Matplotlib)
# =====================================================================
def salvar_figura(fig, nome):
    PASTA_GRAFICOS.mkdir(exist_ok=True)
    caminho = PASTA_GRAFICOS / nome
    fig.tight_layout()
    fig.savefig(caminho, dpi=120)
    plt.close(fig)
    return caminho


def salvar_grafico_modelo(r, df=None):
    res = r["residuos"]
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.scatter(res["real_ms"], res["previsto_ms"], color="tab:blue", s=50, label="registros de teste")
    limites = [min(res["real_ms"].min(), res["previsto_ms"].min()) - 5,
               max(res["real_ms"].max(), res["previsto_ms"].max()) + 5]
    ax.plot(limites, limites, "--", color="gray", label="previsão perfeita")
    m = r["teste"].loc["Modelo escolhido"]
    ax.set_title(f"Latência real x prevista (teste)\nMAE {m['MAE']:.2f} | RMSE {m['RMSE']:.2f} | R² {m['R2']:.3f}")
    ax.set_xlabel("Latência real (ms)")
    ax.set_ylabel("Latência prevista pelo modelo (ms)")
    ax.legend()
    ax.grid(alpha=0.3)
    return salvar_figura(fig, "05_modelo_real_vs_previsto.png")


def salvar_grafico_euler(sim):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    t_fino = np.linspace(0, sim["horas"], 200)
    ax.plot(t_fino, sim["exata"](t_fino), color="black", label="solução exata")
    for h, (t, lat, _) in sim["resultados"].items():
        ax.plot(t, lat, "o--", markersize=4, label=f"Euler h = {h} h")
    ax.axhline(sim["base"], color="green", linestyle=":", label="latência normal")
    ax.set_title("Recuperação da latência do enlace interplanetário após a tempestade")
    ax.set_xlabel("Tempo após o pico (h)")
    ax.set_ylabel("Latência (ms)")
    ax.legend()
    ax.grid(alpha=0.3)
    return salvar_figura(fig, "06_simulacao_euler.png")


def gerar_graficos(df):
    """Gera todos os gráficos do projeto na pasta graficos_ou_imagens."""
    caminhos = []

    media = df.groupby("modulo")[["latencia_prevista_ms", "latencia_observada_ms"]].mean() \
              .sort_values("latencia_observada_ms")
    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(media))
    ax.barh(y - 0.2, media["latencia_prevista_ms"], 0.4, label="Prevista (planejamento)", color="tab:gray")
    ax.barh(y + 0.2, media["latencia_observada_ms"], 0.4, label="Observada (sensores)", color="tab:orange")
    ax.set_yticks(y, media.index)
    ax.set_xlabel("Latência média (ms)")
    ax.set_title("Latência prevista x observada por módulo")
    ax.legend()
    caminhos.append(salvar_figura(fig, "01_latencia_prevista_x_observada.png"))

    erros = tabela_erros_por_modulo(df).sort_values("erro_rel_pct")
    cores = erros["classificacao"].map({"aceitável": "tab:green", "atenção": "gold", "preocupante": "tab:red"})
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(erros.index, erros["erro_rel_pct"], color=cores)
    ax.axvline(100 * LIMITE_ACEITAVEL, color="green", linestyle="--", label="limite aceitável (10%)")
    ax.axvline(100 * LIMITE_PREOCUPANTE, color="red", linestyle="--", label="limite preocupante (25%)")
    ax.set_xlim(0, max(erros["erro_rel_pct"].max(), 100 * LIMITE_PREOCUPANTE) * 1.15)
    ax.set_xlabel("Erro relativo médio (%)")
    ax.set_title("Erro relativo médio da previsão de latência por módulo")
    ax.legend()
    caminhos.append(salvar_figura(fig, "02_erro_relativo_por_modulo.png"))

    ciclos = indicadores_por_ciclo(df)
    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    ax1.bar(ciclos.index, ciclos["alertas"], color="tab:red", alpha=0.4, label="alertas")
    ax1.set_xlabel("Ciclo")
    ax1.set_ylabel("Quantidade de alertas")
    ax1.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax2 = ax1.twinx()
    ax2.plot(ciclos.index, ciclos["latencia_media_ms"], "o-", color="tab:blue", label="latência média")
    ax2.set_ylabel("Latência média (ms)")
    ax1.set_title("Alertas e latência média por ciclo")
    fig.legend(loc="upper left", bbox_to_anchor=(0.08, 0.9))
    caminhos.append(salvar_figura(fig, "03_alertas_e_latencia_por_ciclo.png"))

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(ciclos.index, ciclos["potencia_total_w"], "o-", color="tab:purple", label="consumo total dos módulos")
    ax.axhline(CAPACIDADE_MICRORREDE_W, color="red", linestyle="--", label="capacidade da microrrede")
    ax.set_ylim(0, CAPACIDADE_MICRORREDE_W * 1.15)
    ax.set_xlabel("Ciclo")
    ax.set_ylabel("Potência (W)")
    ax.set_title("Consumo elétrico (P = V x I) x capacidade da microrrede")
    ax.legend(loc="lower right")
    caminhos.append(salvar_figura(fig, "04_potencia_x_capacidade.png"))

    caminhos.append(salvar_grafico_modelo(treinar_modelos(df)))
    caminhos.append(salvar_grafico_euler(simular_euler(df)))
    return caminhos


def opcao_graficos(df):
    titulo("11. GERAR GRÁFICOS")
    for caminho in gerar_graficos(df):
        print(f"  Salvo: {caminho.relative_to(PASTA)}")
    pausar()


# =====================================================================
# 14. OPÇÃO 12 - ANÁLISE FINAL E GERENCIAMENTO INTELIGENTE
# =====================================================================
def opcao_analise_final(df):
    titulo("12. ANÁLISE FINAL E GERENCIAMENTO INTELIGENTE DA COMUNICAÇÃO")
    r = treinar_modelos(df)
    erros = tabela_erros_por_modulo(df)
    ciclos = indicadores_por_ciclo(df)
    fila = FilaPrioridadeAlertas()
    for alerta in montar_alertas(df):
        fila.inserir(alerta)
    m = r["teste"].loc["Modelo escolhido"]
    p = r["teste"].loc["Regra do planejamento"]
    n_alertas = int((df["status"] == "alerta").sum())
    ciclo_critico = int(ciclos["alertas"].idxmax())
    afetados = df[(df["ciclo"] == ciclo_critico) & (df["status"] == "alerta")]["modulo"].tolist()

    subtitulo("Principais resultados do SCIC")
    print(f"  - {len(df)} registros de {df['modulo'].nunique()} módulos em {df['ciclo'].nunique()} ciclos; "
          f"{n_alertas} alertas ({100 * n_alertas / len(df):.1f}%).")
    print(f"  - Ciclo mais crítico: {ciclo_critico}, com alertas em {', '.join(afetados)}.")
    print(f"  - Maior erro relativo médio: {erros.index[0]} ({erros.iloc[0]['erro_rel_pct']:.1f}%).")
    print(f"  - A regra do planejamento subestima a latência; o modelo '{r['escolhido']}' reduz o RMSE")
    print(f"    de {p['RMSE']:.2f} ms para {m['RMSE']:.2f} ms (R² {m['R2']:.3f}).")
    if len(fila):
        topo = fila.espiar()
        print(f"  - Alerta mais urgente (topo do heap): {topo['modulo']} - {topo['mensagem']} "
              f"(prioridade {topo['prioridade']}).")
    print(f"  - Uso máximo da microrrede: {ciclos['uso_microrrede_pct'].max():.1f}% "
          f"(ciclo {int(ciclos['uso_microrrede_pct'].idxmax())}).")

    subtitulo("Manutenção preditiva: tendência do erro relativo por módulo")
    tendencias = {}
    for modulo, grupo in df.groupby("modulo"):
        if grupo["ciclo"].nunique() >= 3:
            tendencias[modulo] = np.polyfit(grupo["ciclo"], 100 * grupo["erro_relativo"], 1)[0]
    tendencias = pd.Series(tendencias).sort_values(ascending=False)
    for modulo, inclinacao in tendencias.head(3).items():
        print(f"  {modulo:28} {inclinacao:+.2f} pontos percentuais por ciclo")
    print("  Módulos cujo erro cresce ciclo após ciclo são candidatos a inspeção ANTES de falhar.")

    subtitulo("Ações automáticas sugeridas para os 3 alertas mais urgentes")
    for _ in range(min(3, len(fila))):
        a = fila.extrair_mais_urgente()
        print(f"  {a['modulo']:28} {a['mensagem']:45} -> {sugerir_comando(a['mensagem'])}")
    print("  As ações são SUGESTÕES: um operador humano valida antes da execução.")

    subtitulo("Relação com o gerenciamento inteligente da comunicação")
    print("  - Sensores e medidores inteligentes (IoT) geram cada linha da base: latência, sinal, tráfego, V e I.")
    print("  - Monitoramento contínuo: comparar observado x previsto a cada ciclo revelou os eventos anormais")
    print("    (erros acima de 25%) assim que aconteceram.")
    print("  - Automação: o heap ordena os alertas e associa comandos; decisões rápidas sem esperar a Terra,")
    print("    que pode levar mais de 40 minutos para responder.")
    print("  - Armazenamento e redundância: a falha de disco do ciclo 6 e a tempestade do ciclo 4 mostram a")
    print("    necessidade de cópias dos dados e de um enlace reserva para o tráfego crítico.")
    print("  - Manutenção preditiva: a tendência do erro aponta módulos para inspeção antes da falha.")
    print("  - Redes inteligentes e microrredes: a mesma tempestade afetou comunicação e geração solar;")
    print("    integrar dados de energia (P = V x I) e de rede permite cortar cargas não essenciais e")
    print("    priorizar suporte de vida, comunicação e suporte médico.")
    print("  - Responsabilidade: o sistema apoia, mas não substitui, a decisão da equipe humana.")
    pausar()


# =====================================================================
# 15. MENU PRINCIPAL E MODO DE DEMONSTRAÇÃO
# =====================================================================
OPCOES_MENU = [
    ("1", "Visualizar dados da colônia"),
    ("2", "Consultar registros"),
    ("3", "Cadastrar novo registro"),
    ("4", "Indicadores de comunicação e operação"),
    ("5", "Erro absoluto, erro relativo e ponto flutuante"),
    ("6", "Modelo de previsão de latência e métricas"),
    ("7", "Analisar alertas de comunicação (heap)"),
    ("8", "Busca por prefixo (trie)"),
    ("9", "Dispositivos, bases numéricas e eletricidade"),
    ("10", "Simulação de recuperação da latência (Euler)"),
    ("11", "Gerar gráficos"),
    ("12", "Análise final e gerenciamento inteligente"),
    ("0", "Sair"),
]


def banner():
    print("\n" + "#" * 72)
    print("#  SCIC - SISTEMA DE COMUNICAÇÃO INTERPLANETÁRIA DA COLÔNIA" + " " * 12 + "#")
    print("#  Missão Aurora Siger | Marte" + " " * 42 + "#")
    print("#" * 72)


def menu():
    df, ausentes = carregar_dados()
    banner()
    print(f"Base carregada: {len(df)} registros de {df['modulo'].nunique()} módulos.")
    acoes = {
        "1": lambda d: opcao_visualizar(d, ausentes), "2": opcao_consultar, "4": opcao_indicadores,
        "5": opcao_erros, "6": opcao_modelo, "7": opcao_alertas_heap, "8": opcao_trie,
        "9": opcao_dispositivos, "10": opcao_euler, "11": opcao_graficos, "12": opcao_analise_final,
    }
    while True:
        print("\n" + "-" * 72)
        for codigo, texto in OPCOES_MENU:
            print(f"  [{codigo:>2}] {texto}")
        escolha = input("Escolha uma opção: ").strip()
        if escolha == "0":
            print("Encerrando o SCIC. Até a próxima transmissão!")
            break
        if escolha == "3":
            df = opcao_cadastrar(df)
        elif escolha in acoes:
            acoes[escolha](df)
        else:
            print("Opção inválida. Digite um dos números do menu.")


def executar_demo():
    """Executa todas as funcionalidades em sequência com entradas de exemplo."""
    global MODO_DEMO
    MODO_DEMO = True
    df, ausentes = carregar_dados()
    banner()
    print("MODO DEMONSTRAÇÃO: todas as funcionalidades com entradas de exemplo.")
    opcao_visualizar(df, ausentes)
    opcao_consultar(df)
    opcao_indicadores(df)
    opcao_erros(df)
    opcao_modelo(df)
    opcao_alertas_heap(df)
    opcao_trie(df)
    opcao_dispositivos(df)
    opcao_euler(df)
    opcao_graficos(df)
    opcao_analise_final(df)
    # O cadastro fica por último para não alterar as análises acima, que usam a base original
    opcao_cadastrar(df)
    print("\nDemonstração concluída.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        executar_demo()
    else:
        try:
            menu()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando o SCIC.")
