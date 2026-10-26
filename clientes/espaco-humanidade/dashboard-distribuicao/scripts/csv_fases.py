#!/usr/bin/env python3
"""Le os CSVs diarios do Gerenciador de Anuncios e devolve linhas por dia e anuncio.

Espera exportacao em nivel Anuncios, com detalhamento por dia e as colunas:
  Início dos relatórios, Nome da campanha, ID do anúncio, Nome do anúncio,
  Veiculação de anúncio, Valor gasto (BRL), Seguidores no Instagram,
  Visitas ao perfil do Instagram, Alcance, Impressões,
  CTR (taxa de cliques no link)

A fase sai do nome da campanha: [FASE1] = aquisição, [FASE2] = recuperação,
[FASE3] = engajamento. Linhas sem tag de fase ficam de fora.

Duplicados (mesmo dia e mesmo ID de anúncio) são somados: o mesmo anúncio pode
aparecer mais de uma vez quando o Gerenciador quebra por conjunto.
"""

import csv
import re

COLUNAS_OBRIGATORIAS = [
    "Início dos relatórios",
    "Nome da campanha",
    "ID do anúncio",
    "Nome do anúncio",
    "Veiculação de anúncio",
    "Valor gasto (BRL)",
    "Seguidores no Instagram",
    "Visitas ao perfil do Instagram",
    "Alcance",
    "Impressões",
    "CTR (taxa de cliques no link)",
]

FASE_RE = re.compile(r"\[FASE([123])\]")


class CsvInvalido(Exception):
    pass


def _num(valor):
    if valor is None or str(valor).strip() == "":
        return 0.0
    return float(str(valor).replace(",", "."))


def fase_da_campanha(nome):
    achado = FASE_RE.search(nome or "")
    return f"fase{achado.group(1)}" if achado else None


def ler_csv(caminho):
    """Devolve lista de dicts, uma linha por dia e anuncio, ja somada e com fase."""
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in (leitor.fieldnames or [])]
        if faltando:
            raise CsvInvalido(
                "Colunas faltando: " + ", ".join(faltando) +
                ". Reexporte com essas colunas (Colunas > Identificação e Métricas)."
            )
        linhas = list(leitor)

    agregado = {}
    for linha in linhas:
        fase = fase_da_campanha(linha["Nome da campanha"])
        if fase is None:
            continue
        chave = (linha["Início dos relatórios"], linha["ID do anúncio"])
        impressoes = _num(linha["Impressões"])
        ctr = _num(linha["CTR (taxa de cliques no link)"])
        registro = agregado.setdefault(chave, {
            "dia": linha["Início dos relatórios"],
            "fase": fase,
            "campanha": linha["Nome da campanha"],
            "ad_id": linha["ID do anúncio"],
            "anuncio": linha["Nome do anúncio"],
            "status": linha["Veiculação de anúncio"],
            "gasto": 0.0,
            "seguidores": 0,
            "visitas": 0,
            "alcance": 0,
            "impressoes": 0,
            "cliques_link": 0.0,
        })
        registro["gasto"] += _num(linha["Valor gasto (BRL)"])
        registro["seguidores"] += int(_num(linha["Seguidores no Instagram"]))
        registro["visitas"] += int(_num(linha["Visitas ao perfil do Instagram"]))
        registro["alcance"] += int(_num(linha["Alcance"]))
        registro["impressoes"] += int(impressoes)
        registro["cliques_link"] += impressoes * ctr / 100
        if linha["Veiculação de anúncio"] == "active":
            registro["status"] = "active"

    return sorted(agregado.values(), key=lambda r: (r["dia"], r["fase"], r["ad_id"]))


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        sys.exit("Uso: python3 csv_fases.py <arquivo.csv>")
    try:
        registros = ler_csv(sys.argv[1])
    except CsvInvalido as erro:
        sys.exit(f"ERRO: {erro}")
    por_fase = {}
    for r in registros:
        por_fase.setdefault(r["fase"], set()).add(r["ad_id"])
    dias = sorted({r["dia"] for r in registros})
    print(f"{len(registros)} linhas (dia x anúncio) | dias: {len(dias)}"
          + (f" ({dias[0]} a {dias[-1]})" if dias else ""))
    for fase, ids in sorted(por_fase.items()):
        print(f"  {fase}: {len(ids)} anúncios")
    if not registros:
        print("Nenhuma linha com tag [FASE1], [FASE2] ou [FASE3] no nome da campanha.")
