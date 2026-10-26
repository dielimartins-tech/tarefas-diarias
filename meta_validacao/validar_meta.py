"""Valida quais dados da Meta esta conta consegue buscar para o painel.

Como usar, no terminal do VS Code, dentro desta pasta:
    python validar_meta.py

O token fica no arquivo .env ao lado deste script (modelo em .env.example).
Nunca cole o token no código nem no chat.

O script só lê dados. Ele gera relatorio_meta.json e imprime uma tabela resumida.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

AD_ACCOUNT = "act_828755630509508"
FB_PAGE = "espacohumanidade"

PASTA = os.path.dirname(os.path.abspath(__file__))
RELATORIO = os.path.join(PASTA, "relatorio_meta.json")


def carregar_env(caminho):
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


carregar_env(os.path.join(PASTA, ".env"))
TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
VERSAO = os.environ.get("GRAPH_VERSION", "v23.0")
BASE = f"https://graph.facebook.com/{VERSAO}/"

AGORA = int(time.time())
INICIO_30_DIAS = AGORA - 30 * 86400

RESULTADOS = []


def chamar(caminho, **params):
    """Faz uma chamada à Graph API. Devolve (dados, erro). O token nunca é impresso."""
    params["access_token"] = TOKEN
    url = BASE + caminho + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as resposta:
            return json.loads(resposta.read().decode("utf-8")), None
    except urllib.error.HTTPError as erro:
        try:
            corpo = json.loads(erro.read().decode("utf-8")).get("error", {})
        except (ValueError, AttributeError):
            corpo = {}
        mensagem = corpo.get("message", erro.reason)
        return None, f"HTTP {erro.code}: {mensagem} (código {corpo.get('code', '-')})"
    except urllib.error.URLError as erro:
        return None, f"Sem conexão: {erro.reason}"


def resumo_padrao(dados):
    item = dados.get("data", [dados])[0] if isinstance(dados, dict) else dados
    texto = json.dumps(item, ensure_ascii=False)
    return texto[:160]


def teste(area, nome, caminho, resumir=None, **params):
    dados, erro = chamar(caminho, **params)
    if erro:
        status, detalhe = "ERRO", erro
    else:
        vazio = isinstance(dados, dict) and "data" in dados and not dados["data"]
        if vazio:
            status, detalhe = "VAZIO", "resposta sem dados no período"
        else:
            status = "OK"
            detalhe = resumir(dados) if resumir else resumo_padrao(dados)
    RESULTADOS.append({"area": area, "teste": nome, "status": status, "detalhe": detalhe})
    print(f"{status:6} {area:12} {nome[:52]:52} {detalhe[:110]}")
    return None if erro else dados


def tipos_de_acao(dados):
    tipos = set()
    for linha in dados.get("data", []):
        for acao in linha.get("actions", []):
            tipos.add(acao.get("action_type"))
    return f"{len(dados.get('data', []))} linhas; tipos de ação: {', '.join(sorted(t for t in tipos if t))[:400]}"


def contar_status(dados):
    contagem = {}
    for anuncio in dados.get("data", []):
        status = anuncio.get("effective_status", "?")
        contagem[status] = contagem.get(status, 0) + 1
    return f"{len(dados.get('data', []))} anúncios; " + ", ".join(f"{k}: {v}" for k, v in contagem.items())


def secao(titulo):
    print(f"\n== {titulo} ==")


def main():
    if not TOKEN:
        sys.exit("Falta META_ACCESS_TOKEN. Crie o arquivo .env ao lado deste script (veja .env.example).")

    secao("Acesso")
    teste("Acesso", "Permissões concedidas", "me/permissions",
          resumir=lambda d: ", ".join(f"{p['permission']}={p['status']}" for p in d["data"]))

    secao("Conta de anúncios")
    teste("Anúncios", "Dados da conta", AD_ACCOUNT, fields="name,account_status,currency,timezone_name")
    teste("Anúncios", "Métricas da conta (30 dias)", f"{AD_ACCOUNT}/insights",
          fields="spend,impressions,reach,frequency,clicks,ctr,cpm,cpc", date_preset="last_30d")
    teste("Anúncios", "Status dos anúncios", f"{AD_ACCOUNT}/ads",
          fields="id,name,effective_status,creative{instagram_permalink_url}", limit=50,
          resumir=contar_status)
    teste("Anúncios", "Métricas por anúncio (30 dias)", f"{AD_ACCOUNT}/insights",
          level="ad", fields="ad_id,ad_name,spend,impressions,reach,frequency,clicks,actions",
          date_preset="last_30d", limit=50, resumir=tipos_de_acao)
    teste("Anúncios", "Reprodução 25/50/100% por anúncio", f"{AD_ACCOUNT}/insights",
          level="ad", fields="ad_id,video_p25_watched_actions,video_p50_watched_actions,video_p100_watched_actions",
          date_preset="last_30d", limit=50)
    teste("Anúncios", "Quebra por idade e gênero", f"{AD_ACCOUNT}/insights",
          level="ad", fields="ad_id,spend,impressions,reach", breakdowns="age,gender",
          date_preset="last_30d", limit=50)
    teste("Anúncios", "Quebra por região", f"{AD_ACCOUNT}/insights",
          level="ad", fields="ad_id,spend,impressions,reach", breakdowns="region",
          date_preset="last_30d", limit=50)
    teste("Anúncios", "Quebra por idade e país (esperado falhar)", f"{AD_ACCOUNT}/insights",
          level="ad", fields="ad_id,spend", breakdowns="age,country", date_preset="last_30d", limit=50)

    secao("Página do Facebook")
    pagina = teste("Página", "Dados da página", FB_PAGE,
                   fields="id,name,fan_count,followers_count,instagram_business_account{id,username}")
    for metrica in ["page_impressions", "page_post_engagements", "page_views_total", "page_follows"]:
        if pagina:
            teste("Página", f"Insight: {metrica}", f"{pagina['id']}/insights",
                  metric=metrica, period="day", since=INICIO_30_DIAS, until=AGORA)

    ig_id = (pagina or {}).get("instagram_business_account", {}).get("id")
    if not ig_id:
        print("\nAVISO: a Página não retornou um Instagram profissional vinculado. Os testes de Instagram foram pulados.")
        salvar()
        return

    secao("Instagram: conta")
    teste("Instagram", "Dados da conta", ig_id, fields="username,followers_count,media_count")
    for metrica in ["reach", "views", "profile_views", "website_clicks", "follower_count"]:
        teste("Instagram", f"Conta: {metrica}", f"{ig_id}/insights",
              metric=metrica, period="day", since=INICIO_30_DIAS, until=AGORA)
    teste("Instagram", "Conta: alcance por seguidor x não seguidor", f"{ig_id}/insights",
          metric="reach", breakdown="follow_type", metric_type="total_value",
          since=INICIO_30_DIAS, until=AGORA)

    secao("Instagram: publicações")
    publicacoes = teste("Instagram", "Lista de publicações", f"{ig_id}/media",
                        fields="id,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
                        limit=10, resumir=lambda d: f"{len(d['data'])} publicações")
    if publicacoes and publicacoes.get("data"):
        primeira = publicacoes["data"][0]
        for metrica in ["reach", "views", "saved", "shares", "total_interactions", "comments", "likes"]:
            teste("Instagram", f"Publicação: {metrica}", f"{primeira['id']}/insights", metric=metrica)
        teste("Instagram", "Publicação: alcance por seguidor x não seguidor", f"{primeira['id']}/insights",
              metric="reach", breakdown="follow_type")

        reel = next((p for p in publicacoes["data"] if p.get("media_product_type") == "REELS"), None)
        if reel:
            teste("Instagram", "Reel: tempo médio assistido", f"{reel['id']}/insights",
                  metric="ig_reels_avg_watch_time")
            teste("Instagram", "Reel: tempo total assistido", f"{reel['id']}/insights",
                  metric="ig_reels_video_view_total_time")
        else:
            print("VAZIO  Instagram     Nenhum Reel entre as 10 últimas publicações; testes de reel pulados.")

    salvar()


def salvar():
    relatorio = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "versao_api": VERSAO,
        "conta_anuncios": AD_ACCOUNT,
        "pagina": FB_PAGE,
        "resultados": RESULTADOS,
    }
    with open(RELATORIO, "w", encoding="utf-8") as arquivo:
        json.dump(relatorio, arquivo, ensure_ascii=False, indent=2)
    total = {"OK": 0, "VAZIO": 0, "ERRO": 0}
    for linha in RESULTADOS:
        total[linha["status"]] = total.get(linha["status"], 0) + 1
    print(f"\nResumo: {total}. Relatório salvo em {RELATORIO}")


if __name__ == "__main__":
    main()
