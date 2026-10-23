---
description: Analisa o Instagram de um cliente e indica posts que servem para tráfego pago
argument-hint: <cliente> [--limit 30]
---

Rode a análise de Instagram do cliente informado em `$ARGUMENTS`:

1. Execute `python3 scripts/instagram_analysis.py $ARGUMENTS`.
   - Se der erro de configuração (cliente não encontrado ou variável de token ausente), diga exatamente o que falta e pare. Não invente dados.
   - Se a Graph API recusar o acesso, informe a mensagem de erro e o que o cliente precisa conceder no Business Manager.
2. Leia o `relatorio.md` gerado e o `posts.csv` da mesma pasta.
3. Entregue uma análise para tráfego pago com:
   - **Posts para anunciar:** os candidatos do relatório, com o motivo de cada um (alcance, engajamento, salvamentos).
   - **Padrão de gancho:** o que os primeiros segundos ou a primeira linha dos posts de melhor desempenho têm em comum.
   - **Formato:** qual formato performa melhor, com os números.
   - **CTA:** se legendas com chamada para ação rendem mais, e quais palavras aparecem nos melhores posts.
   - **Próximos testes:** 3 variações de anúncio sugeridas a partir desses posts.
4. Deixe claro que engajamento orgânico é um sinal, não uma garantia de conversão no anúncio.

Escreva em português. Não copie o relatório inteiro; resuma o que muda a decisão de campanha.
