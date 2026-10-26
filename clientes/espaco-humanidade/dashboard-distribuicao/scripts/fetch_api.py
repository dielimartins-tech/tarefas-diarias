#!/usr/bin/env python3
"""Coleta, pela Graph API, o que o painel precisa e a planilha/CSV nao entrega.

  - Instagram (conta): seguidores por dia e alcance por dia (serie diaria);
    visualizacoes, visitas ao perfil e toques no site do periodo (total).
  - Anuncios da Fase 3 (campanhas com [FASE3] no nome): gasto, alcance,
    impressoes, cliques, engajamento real (reacoes, comentarios, salvamentos,
    compartilhamentos), reproducao de video 25/50/100%, por anuncio e por dia.
  - Anuncios no total (todas as campanhas): gasto por dia, para o total da conta.

Os seguidores e visitas por anuncio das Fases 1 e 2 NAO vem daqui: vem do CSV.

Uso: python3 fetch_api.py
Precisa de META_ADS_TOKEN no .env (mesmo token da rotina) e do config.json.
Gera: data_api.json, na pasta do dashboard. Nao imprime o token.
"""

import datetime
import json
import os
import re
import sys

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.dirname(SCRIPT_DIR)
SAIDA = os.path.join(DASHBOARD_DIR, "data_api.json")
CONFIG = os.path.join(DASHBOARD_DIR, "config.json")

GRAPH = "https://graph.facebook.com/v23.0"
INICIO = datetime.date(2026, 6, 1)
HOJE = datetime.date.today()

# Mapa de tipos de acao da API para as metricas do painel. Os nomes foram
# confirmados na exportacao da conta (post_reaction, comment,
# onsite_conversion.post_save, post, video_view).
ACOES = {
    "post_reaction": "reacoes",
    "comment": "comentarios",
    "onsite_conversion.post_save": "salvamentos",
    "post": "compartilhamentos",
}

CAMPOS_ANUNCIO = (
    "ad_id,ad_name,campaign_name,spend,impressions,reach,clicks,actions,"
    "video_p25_watched_actions,video_p50_watched_actions,video_p100_watched_actions"
)


def carregar_env(caminho):
    if not os.path.isfile(caminho):
        return
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def chamar(caminho, token, **params):
    """GET na Graph API. Devolve o JSON. Erros viram excecao SEM a URL (sem token)."""
    params["access_token"] = token
    resposta = requests.get(f"{GRAPH}/{caminho}", params=params, timeout=60)
    corpo = resposta.json()
    if "error" in corpo:
        erro = corpo["error"]
        raise RuntimeError(f"{caminho}: {erro.get('message')} (código {erro.get('code')})")
    return corpo


def paginas(caminho, token, **params):
    itens, cursor = [], None
    while True:
        if cursor:
            params["after"] = cursor
        corpo = chamar(caminho, token, **params)
        itens.extend(corpo.get("data", []))
        paginacao = corpo.get("paging", {})
        cursor = paginacao.get("cursors", {}).get("after")
        if not paginacao.get("next") or not cursor:
            return itens


def blocos_de_30_dias(inicio, fim):
    """A API limita a serie diaria de seguidores a 30 dias por chamada."""
    atual = inicio
    while atual <= fim:
        final = min(atual + datetime.timedelta(days=29), fim)
        yield atual, final
        atual = final + datetime.timedelta(days=1)


def instagram(ig_id, token):
    seguidores, alcance = {}, {}
    for ini, fim in blocos_de_30_dias(INICIO, HOJE):
        corpo = chamar(f"{ig_id}/insights", token, metric="follower_count,reach", period="day",
                       since=ini.isoformat(), until=(fim + datetime.timedelta(days=1)).isoformat())
        for metrica in corpo.get("data", []):
            destino = seguidores if metrica["name"] == "follower_count" else alcance
            for valor in metrica.get("values", []):
                destino[valor["end_time"][:10]] = valor["value"]

    totais = {}
    corpo = chamar(f"{ig_id}/insights", token, metric="views,profile_views,website_clicks",
                   period="day", metric_type="total_value",
                   since=INICIO.isoformat(), until=(HOJE + datetime.timedelta(days=1)).isoformat())
    for metrica in corpo.get("data", []):
        totais[metrica["name"]] = metrica.get("total_value", {}).get("value", 0)

    perfil = chamar(ig_id, token, fields="username,followers_count,media_count")
    return {
        "username": perfil.get("username"),
        "seguidores_atuais": perfil.get("followers_count"),
        "seguidores_por_dia": seguidores,
        "alcance_por_dia": alcance,
        "periodo_total": totais,
    }


def anuncios_do_dia(conta, token):
    """Insights por anuncio e por dia, so das campanhas da Fase 3 e da conta toda."""
    fase3, total_por_dia = [], {}
    params = {
        "level": "ad",
        "fields": CAMPOS_ANUNCIO,
        "time_increment": 1,
        "time_range": json.dumps({"since": INICIO.isoformat(), "until": HOJE.isoformat()}),
        "limit": 500,
    }
    for linha in paginas(f"{conta}/insights", token, **params):
        dia = linha.get("date_start")
        gasto = float(linha.get("spend", 0) or 0)
        total_por_dia[dia] = total_por_dia.get(dia, 0) + gasto
        if "[FASE3]" not in (linha.get("campaign_name") or ""):
            continue
        acoes = {}
        for item in linha.get("actions", []) or []:
            chave = ACOES.get(item.get("action_type"))
            if chave:
                acoes[chave] = acoes.get(chave, 0) + int(float(item.get("value", 0)))
        fase3.append({
            "dia": dia,
            "ad_id": linha.get("ad_id"),
            "anuncio": linha.get("ad_name"),
            "campanha": linha.get("campaign_name"),
            "gasto": gasto,
            "alcance": int(linha.get("reach", 0) or 0),
            "impressoes": int(linha.get("impressions", 0) or 0),
            "cliques": int(linha.get("clicks", 0) or 0),
            "reacoes": acoes.get("reacoes", 0),
            "comentarios": acoes.get("comentarios", 0),
            "salvamentos": acoes.get("salvamentos", 0),
            "compartilhamentos": acoes.get("compartilhamentos", 0),
            "video_p25": _valor(linha.get("video_p25_watched_actions")),
            "video_p50": _valor(linha.get("video_p50_watched_actions")),
            "video_p100": _valor(linha.get("video_p100_watched_actions")),
        })
    return fase3, total_por_dia


def _valor(lista):
    if not lista:
        return 0
    return int(float(lista[0].get("value", 0)))


def main():
    carregar_env(os.path.join(DASHBOARD_DIR, "..", "..", "..", ".claude", "skills", "meta-ads", ".env"))
    carregar_env(os.path.join(DASHBOARD_DIR, ".env"))
    token = os.environ.get("META_ADS_TOKEN")
    if not token:
        sys.exit("ERRO: META_ADS_TOKEN não encontrado no .env")

    with open(CONFIG, encoding="utf-8") as arquivo:
        config = json.load(arquivo)

    print("Instagram...", file=sys.stderr)
    ig = instagram(config["ig_user_id"], token)

    print("Anúncios (Fase 3 e total da conta)...", file=sys.stderr)
    fase3, gasto_conta = anuncios_do_dia(config["ad_account_id"], token)

    dados = {
        "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "periodo": {"inicio": INICIO.isoformat(), "fim": HOJE.isoformat()},
        "instagram": ig,
        "fase3_anuncios_dia": fase3,
        "gasto_conta_por_dia": gasto_conta,
    }
    with open(SAIDA, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
    print(f"OK: {len(fase3)} linhas da Fase 3 e {len(ig['seguidores_por_dia'])} dias de seguidores. Gravado em {SAIDA}",
          file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as erro:
        sys.exit(f"ERRO: {re.sub(r'access_token=[^&\\s]+', 'access_token=***', str(erro))}")
