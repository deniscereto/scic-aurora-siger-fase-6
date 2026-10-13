"""
gerar_dados.py  |  SCIC - Aurora Siger (FIAP - Fase 6)
-------------------------------------------------------------------
Script AUXILIAR que cria a base simulada "dados_aurora_siger.csv".

A base já acompanha a entrega, então este script NÃO precisa ser
executado para usar o sistema. Ele existe para documentar como os
dados simulados foram construídos e para permitir recriá-los.
A semente aleatória é fixa: os dados gerados são sempre os mesmos.

Execução (a partir da pasta principal do projeto):
    py arquivos_extras/gerar_dados.py
O CSV é gravado na pasta principal, ao lado de codigo_fonte.py.
"""
from pathlib import Path

import numpy as np
import pandas as pd

PASTA = Path(__file__).resolve().parent.parent   # pasta principal do projeto
rng = np.random.default_rng(2026)   # semente fixa = dados reproduzíveis
NUM_CICLOS = 6                       # cada ciclo representa um registro a cada 5 sols

# (nome, tipo, essencial, código do sensor, distância até o hub de rede em km,
#  carga média de tráfego em Mbps, tensão nominal em V, corrente média em A,
#  nível de criticidade de 1 a 5)
MODULOS = [
    ("Comunicação Interplanetária", "comunicação", "sim", "0xC011", 1.8, 85, 48, 12.5, 5),
    ("Comando Central", "comunicação", "sim", "0xC0A2", 0.3, 60, 24, 6.0, 5),
    ("Controle Ambiental", "suporte de vida", "sim", "0xCA13", 0.9, 25, 48, 9.0, 5),
    ("Combustível e Energia", "energia", "sim", "0xCE24", 2.4, 18, 120, 4.2, 4),
    ("Microrrede Solar", "energia", "sim", "0x50A6", 3.1, 12, 120, 3.5, 4),
    ("Suporte Médico", "suporte médico", "sim", "0x5E94", 0.6, 30, 24, 5.5, 5),
    ("Habitação Alfa", "habitação", "não", "0xA1F0", 1.2, 40, 24, 4.0, 3),
    ("Habitação Beta", "habitação", "não", "0xA1F1", 1.5, 35, 24, 3.8, 3),
    ("Agricultura Hidropônica", "agricultura", "não", "0xA6B2", 2.0, 15, 48, 7.5, 3),
    ("Laboratório de Geologia", "laboratório", "não", "0x1A83", 2.7, 45, 24, 4.8, 2),
    ("Armazenamento de Dados", "armazenamento de dados", "sim", "0xDA75", 0.8, 70, 48, 8.0, 4),
    ("Rover de Exploração", "exploração", "não", "0xE0B7", 6.5, 20, 24, 3.0, 2),
]


def latencia_real(dist_km, carga_mbps, qualidade_pct):
    """Comportamento 'real' da latência interna (ms). A equipe de planejamento não conhece esta regra."""
    return 6 + 9.5 * dist_km + 0.32 * carga_mbps + 0.55 * (100 - qualidade_pct)


def latencia_planejada(dist_km, carga_mbps):
    """Regra simples usada pelo planejamento: ignora a qualidade do sinal e usa valores médios."""
    return 8 + 9.0 * dist_km + 0.30 * carga_mbps


registros = []
id_registro = 1
for ciclo in range(1, NUM_CICLOS + 1):
    data = pd.Timestamp("2026-09-05") + pd.Timedelta(days=5 * (ciclo - 1))
    for nome, tipo, essencial, codigo, dist, carga_base, tensao_nom, corrente_base, crit in MODULOS:
        dist_real = dist
        carga = carga_base * rng.uniform(0.85, 1.20)
        qualidade = 93 - 2.5 * dist + rng.normal(0, 2.5)
        tensao = tensao_nom * rng.uniform(0.97, 1.02)
        corrente = corrente_base * rng.uniform(0.92, 1.10)
        extra_ms = 0.0
        evento = None

        # ---------------- eventos simulados da missão ----------------
        if ciclo == 2 and nome == "Suporte Médico":
            extra_ms += 15
            evento = "Latência acima do previsto no enlace médico"
        if ciclo == 3 and nome == "Agricultura Hidropônica":
            evento = "Manutenção programada do sensor"
        if ciclo == 4 and nome in ("Comunicação Interplanetária", "Microrrede Solar", "Rover de Exploração"):
            qualidade -= 28
            evento = "Sinal degradado por tempestade de poeira"
        if ciclo == 5 and nome == "Comunicação Interplanetária":
            carga *= 1.7
            evento = "Sobrecarga de tráfego no enlace com a Terra"
        if ciclo == 5 and nome == "Controle Ambiental":
            tensao = tensao_nom * 0.84
            evento = "Queda de tensão na alimentação do módulo"
        if ciclo == 6 and nome == "Armazenamento de Dados":
            extra_ms += 32
            evento = "Falha em disco do armazenamento de dados"
        if ciclo == 6 and nome == "Rover de Exploração":
            dist_real += 3.5
            evento = "Rover fora da área de cobertura ideal"

        qualidade = float(np.clip(qualidade, 35, 99))
        observada = latencia_real(dist_real, carga, qualidade) + extra_ms + rng.normal(0, 2.0)
        prevista = latencia_planejada(dist, carga_base)
        erro_rel = abs(observada - prevista) / observada

        # ---------------- status e mensagem ----------------
        if evento == "Manutenção programada do sensor":
            status = "manutenção"
        elif evento or erro_rel > 0.25 or qualidade < 60:
            status = "alerta"
        else:
            status = "ativo"
        if evento:
            mensagem = evento
        elif erro_rel > 0.25:
            mensagem = "Latência acima do previsto"
        elif qualidade < 60:
            mensagem = "Qualidade de sinal baixa"
        else:
            mensagem = "Operação normal"

        registros.append({
            "id_registro": id_registro,
            "ciclo": ciclo,
            "data_registro": data.strftime("%Y-%m-%d"),
            "modulo": nome,
            "tipo_modulo": tipo,
            "essencial": essencial,
            "codigo_sensor": codigo,
            "distancia_hub_km": round(dist_real, 2),
            "carga_trafego_mbps": round(carga, 1),
            "qualidade_sinal_pct": round(qualidade, 1),
            "tensao_v": round(tensao, 2),
            "corrente_a": round(corrente, 2),
            "latencia_prevista_ms": round(prevista, 1),
            "latencia_observada_ms": round(observada, 2),
            "status": status,
            "nivel_criticidade": crit,
            "mensagem_alerta": mensagem,
        })
        id_registro += 1

df = pd.DataFrame(registros)

# Dois valores ausentes propositais, para demonstrar a etapa de limpeza no sistema
df.loc[14, "qualidade_sinal_pct"] = np.nan
df.loc[39, "corrente_a"] = np.nan

df.to_csv(PASTA / "dados_aurora_siger.csv", index=False, encoding="utf-8-sig")
print(f"Base criada com {len(df)} registros em {PASTA / 'dados_aurora_siger.csv'}")
print(df["status"].value_counts().to_string())
