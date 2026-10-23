#!/usr/bin/env python3
"""Analisa o Instagram de um cliente e separa os posts com potencial para tráfego pago.

Uso:
    python3 scripts/instagram_analysis.py <cliente> [--limit 30] [--out relatorios]

Configuração: clients.json na raiz do projeto (modelo em clients.example.json).
O token de acesso nunca fica no arquivo: ele vem de uma variável de ambiente cujo
nome está em "token_env". Só lê contas que deram acesso ao seu app na Meta.
"""

import argparse
import csv
import json
import os
import statistics
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "clients.json"
GRAPH_VERSION = os.environ.get("GRAPH_API_VERSION", "v21.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
MEDIA_FIELDS = "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count"
FORMATS = {"REELS": "Reel", "VIDEO": "Vídeo", "CAROUSEL_ALBUM": "Carrossel", "IMAGE": "Imagem"}
CTA_WORDS = [
    "link in bio", "book", "call", "dm", "comment", "shop", "order", "visit", "free",
    "offer", "sale", "discount", "contact", "click", "reserve", "agende", "link na bio",
    "comente", "chame", "reserve", "compre", "garanta", "fale conosco",
]


class GraphError(Exception):
    pass


def graph_get(path_or_url, token=None, **params):
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        params["access_token"] = token
        url = f"{GRAPH}/{path_or_url}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        try:
            message = json.loads(err.read().decode(errors="replace")).get("error", {}).get("message")
        except ValueError:
            message = None
        raise GraphError(f"HTTP {err.code}: {message or 'sem detalhe'}") from None


def load_client(name):
    if not CONFIG.exists():
        raise SystemExit("Crie clients.json a partir de clients.example.json.")
    clients = json.loads(CONFIG.read_text(encoding="utf-8")).get("clientes", {})
    if name not in clients:
        raise SystemExit(f"Cliente '{name}' não encontrado. Disponíveis: {', '.join(clients) or 'nenhum'}")
    cfg = clients[name]
    token = os.environ.get(cfg["token_env"])
    if not token:
        raise SystemExit(f"Defina a variável de ambiente {cfg['token_env']} com o token deste cliente.")
    return cfg, token


def fetch_media(ig_id, token, limit):
    page = graph_get(f"{ig_id}/media", token, fields=MEDIA_FIELDS, limit=min(limit, 50))
    items = []
    while True:
        items.extend(page.get("data", []))
        nxt = page.get("paging", {}).get("next")
        if not nxt or len(items) >= limit:
            return items[:limit]
        page = graph_get(nxt)


def fetch_insights(media, token):
    is_video = media.get("media_product_type") == "REELS" or media.get("media_type") == "VIDEO"
    metrics = ["reach", "saved", "shares"] + (["plays"] if is_video else [])
    try:
        data = graph_get(f"{media['id']}/insights", token, metric=",".join(metrics))
    except GraphError:
        # Métricas mudam entre versões da API; tenta o conjunto básico antes de desistir.
        try:
            data = graph_get(f"{media['id']}/insights", token, metric="reach,saved,shares")
        except GraphError:
            return {}
    out = {}
    for item in data.get("data", []):
        values = item.get("values")
        value = values[0]["value"] if values else item.get("total_value", {}).get("value")
        out[item["name"]] = value or 0
    return out


def build_row(media, insights, followers):
    likes = media.get("like_count", 0)
    comments = media.get("comments_count", 0)
    saved = insights.get("saved", 0)
    shares = insights.get("shares", 0)
    reach = insights.get("reach", 0)
    caption = media.get("caption") or ""
    lowered = caption.lower()
    first_line = caption.strip().split("\n")[0] if caption.strip() else ""
    base = reach or followers  # sem alcance na métrica, usa seguidores como referência
    interactions = likes + comments + saved + shares
    fmt_key = media.get("media_product_type") if media.get("media_product_type") == "REELS" else media.get("media_type")
    return {
        "data": datetime.strptime(media["timestamp"], "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d"),
        "formato": FORMATS.get(fmt_key, fmt_key or "n/d"),
        "link": media.get("permalink", ""),
        "alcance": reach,
        "plays": insights.get("plays", 0),
        "curtidas": likes,
        "comentarios": comments,
        "salvamentos": saved,
        "compartilhamentos": shares,
        "engajamento_pct": round(interactions / base * 100, 2) if base else 0.0,
        "salv_comp_pct": round((saved + shares) / reach * 100, 2) if reach else 0.0,
        "tem_cta": any(word in lowered for word in CTA_WORDS),
        "hashtags": caption.count("#"),
        "tamanho_legenda": len(caption),
        "gancho": first_line[:120],
        "legenda": caption,
    }


def md_table(headers, rows):
    def esc(value):
        return str(value).replace("|", "/").replace("\n", " ")

    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(esc(c) for c in row) + " |" for row in rows]
    return lines + [""]


def write_report(profile, rows, path):
    by_eng = sorted(rows, key=lambda r: r["engajamento_pct"], reverse=True)
    reaches = [r["alcance"] for r in rows if r["alcance"]]
    engs = [r["engajamento_pct"] for r in rows]
    dates = sorted(r["data"] for r in rows)

    lines = [
        f"# Instagram: {profile.get('name') or profile['username']} (@{profile['username']})",
        "",
        f"- Período: {dates[0]} a {dates[-1]} ({len(rows)} posts)",
        f"- Seguidores: {profile.get('followers_count', 'n/d')}",
    ]
    if reaches:
        lines.append(f"- Alcance mediano por post: {statistics.median(reaches):,.0f}")
    lines += [
        f"- Engajamento: média {statistics.mean(engs):.2f}%, mediana {statistics.median(engs):.2f}%",
        "- Engajamento = (curtidas + comentários + salvamentos + compartilhamentos) / alcance",
        "",
        "## Desempenho por formato",
        "",
    ]
    groups = {}
    for r in rows:
        groups.setdefault(r["formato"], []).append(r)
    ordered = sorted(groups.items(), key=lambda kv: -statistics.mean(i["engajamento_pct"] for i in kv[1]))
    lines += md_table(
        ["Formato", "Posts", "Alcance médio", "Engajamento médio", "Salv.+comp. / alcance"],
        [
            [
                fmt,
                len(items),
                f"{statistics.mean(i['alcance'] for i in items):,.0f}",
                f"{statistics.mean(i['engajamento_pct'] for i in items):.2f}%",
                f"{statistics.mean(i['salv_comp_pct'] for i in items):.2f}%",
            ]
            for fmt, items in ordered
        ],
    )

    lines += ["## Legendas com e sem chamada para ação (CTA)", ""]
    for flag, label in ((True, "Com CTA"), (False, "Sem CTA")):
        items = [r for r in rows if r["tem_cta"] == flag]
        if items:
            avg = statistics.mean(i["engajamento_pct"] for i in items)
            lines.append(f"- {label}: {len(items)} posts, engajamento médio {avg:.2f}%")
    lines.append("")

    lines += ["## Top 10 por engajamento", ""]
    lines += md_table(
        ["Data", "Formato", "Alcance", "Engajamento", "Salv.+comp.", "Gancho", "Link"],
        [
            [
                r["data"], r["formato"], f"{r['alcance']:,}", f"{r['engajamento_pct']:.2f}%",
                f"{r['salv_comp_pct']:.2f}%", r["gancho"], r["link"],
            ]
            for r in by_eng[:10]
        ],
    )

    if reaches and len(engs) >= 4:
        median_reach = statistics.median(reaches)
        eng_cut = statistics.quantiles(engs, n=4)[2]  # topo de 25%
        candidates = [r for r in by_eng if r["alcance"] >= median_reach and r["engajamento_pct"] >= eng_cut]
        lines += [
            "## Candidatos para tráfego pago",
            "",
            "Alcance acima da mediana e engajamento no topo de 25%. Um post orgânico com esses números "
            "já provou o criativo: teste no anúncio com o mesmo gancho e a mesma edição.",
            "",
        ]
        lines += md_table(
            ["Data", "Formato", "Alcance", "Engajamento", "Gancho", "Link"],
            [
                [r["data"], r["formato"], f"{r['alcance']:,}", f"{r['engajamento_pct']:.2f}%", r["gancho"], r["link"]]
                for r in candidates[:10]
            ] or [["Nenhum post atingiu os dois critérios", "", "", "", "", ""]],
        )

    value = sorted(rows, key=lambda r: r["salvamentos"] + r["compartilhamentos"], reverse=True)
    lines += ["## Conteúdo de valor (mais salvamentos e compartilhamentos)", ""]
    lines += md_table(
        ["Data", "Formato", "Salvamentos", "Compartilhamentos", "Gancho", "Link"],
        [
            [r["data"], r["formato"], r["salvamentos"], r["compartilhamentos"], r["gancho"], r["link"]]
            for r in value[:5]
        ],
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(rows, path):
    fields = [
        "data", "formato", "link", "alcance", "plays", "curtidas", "comentarios", "salvamentos",
        "compartilhamentos", "engajamento_pct", "salv_comp_pct", "tem_cta", "hashtags",
        "tamanho_legenda", "gancho", "legenda",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Analisa o Instagram de um cliente para tráfego pago.")
    parser.add_argument("cliente", help="chave do cliente em clients.json")
    parser.add_argument("--limit", type=int, default=30, help="quantidade de posts recentes (padrão 30)")
    parser.add_argument("--out", default=str(ROOT / "relatorios"), help="pasta de saída")
    args = parser.parse_args()

    cfg, token = load_client(args.cliente)
    try:
        profile = graph_get(cfg["ig_user_id"], token, fields="username,name,followers_count")
        media = fetch_media(cfg["ig_user_id"], token, args.limit)
        if not media:
            raise SystemExit("Nenhum post retornado. Confira se o token tem permissão de leitura desta conta.")
        followers = profile.get("followers_count", 0)
        rows = [build_row(m, fetch_insights(m, token), followers) for m in media]
    except GraphError as err:
        raise SystemExit(f"Erro na Graph API: {err}")

    out_dir = Path(args.out) / args.cliente / datetime.now().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    write_report(profile, rows, out_dir / "relatorio.md")
    write_csv(rows, out_dir / "posts.csv")
    print(f"Relatório: {out_dir / 'relatorio.md'}")
    print(f"Dados:     {out_dir / 'posts.csv'}")
    print(f"{len(rows)} posts analisados de @{profile['username']}.")


if __name__ == "__main__":
    main()
