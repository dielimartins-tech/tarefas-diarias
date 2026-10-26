---
name: dashboard-espaco-humanidade
description: Gera dashboards de distribuição de conteúdo no padrão visual da Espaço Humanidade (fundo azul-marinho, destaque azul claro, sem logo), a partir dos CSVs exportados do Gerenciador de Anúncios. Use quando o usuário pedir dashboard, painel ou relatório da Espaço Humanidade, ou de distribuição de conteúdo com Fase 1, Fase 2 ou Fase 3. Não use para outros clientes.
---

# Dashboard Espaço Humanidade

Este padrão vale **somente** para a Espaço Humanidade. Outros clientes usam o layout neutro, em outra skill.

## Padrão visual

As cores abaixo são **provisórias** (estimadas a partir da central de dashboards). Confirmar com os códigos exatos antes de finalizar.

| Token | Valor provisório | Uso |
|---|---|---|
| `--bg-top` | `#0B2A4A` | Topo do fundo (degradê) |
| `--bg-bottom` | `#07111F` | Base do fundo (degradê) |
| `--card` | `#0F1E33` | Cartões e painéis |
| `--border` | `#1E3350` | Bordas finas dos cartões |
| `--accent` | `#4DA3E0` | Destaque: setas, etiquetas, links, série principal |
| `--text` | `#F1F5F9` | Títulos e números |
| `--muted` | `#94A3B8` | Textos de apoio, legendas e rótulos |
| `--ok` | `#34D399` | Ativo, aprovado, bom |
| `--warn` | `#FBBF24` | Atenção |
| `--late` | `#F87171` | Atrasado, ruim, acima do limite |

- Tema escuro único. Não criar modo claro.
- Sem logo. Não embutir imagem da marca.
- Fonte: `Inter`, com fallback `system-ui, sans-serif`.
- Cartões com borda fina de `--border`, cantos de 12px, sem sombra pesada.
- Etiquetas de período (por exemplo `JUL/26`) em pílula, com borda e texto `--accent`.
- Cabeçalho com nome da página em texto, sem imagem. "Uma" pode receber `--accent` como detalhe, se fizer sentido.

## Estrutura

Manter a mesma estrutura do painel aprovado:
1. Cabeçalho com nome do painel e período.
2. Filtro de datas (período predefinido ou personalizado) e checkbox "Comparar com período anterior".
3. Abas: **Visão geral**, **Facebook**, **Instagram**, **Anúncios**.
4. Visão geral: indicadores acumulados e dois quadros de métricas com definições.
5. Anúncios: total por fase, gráfico diário empilhado por fase, e uma seção por fase (Fase 1 aquisição, Fase 2 recuperação, Fase 3 engajamento).
6. Cada fase tem indicadores principais e uma tabela de anúncios, com botão **Ativos hoje** / **Ativos no período** (ativos hoje por padrão), permalink e ordenação por coluna.
7. Frequência da Fase 2 com alerta acima de 2. Frequência da Fase 3 é exibida, sem limite definido.

## Dados de entrada

Os CSVs vêm do Gerenciador de Anúncios, em nível **Anúncios**, com detalhamento **por dia**. Colunas esperadas:

- `Início dos relatórios`, `Encerramento dos relatórios`
- `ID do anúncio`, `Nome da campanha`, `Nome do anúncio`
- `Veiculação de anúncio` (`active`, `inactive`, `not_delivering`)
- `Valor gasto (BRL)`, `Seguidores no Instagram`, `Custo x seguidor`, `Visitas ao perfil do Instagram`, `% Visitas`, `Alcance`, `Custo por 1.000 Contas Meta alcançadas (BRL)`, `Impressões`, `CPM (custo por 1.000 impressões) (BRL)`, `CTR (taxa de cliques no link)`

Regras:
- **Se faltar `ID do anúncio` ou `Nome da campanha`, parar e pedir nova exportação.** Sem o ID, anúncios com o mesmo nome se misturam.
- **Fase pelo nome da campanha**, com a expressão `\[FASE(\d)\]`. Anúncios sem tag ficam em "sem fase" e não entram nas seções de fase.
- **Deduplicar por (dia, ID do anúncio).**
- **`% Visitas` não é a conversão de visita em seguidor.** A coluna é visitas ÷ impressões × 1.000. A conversão que interessa é `Seguidores no Instagram` ÷ `Visitas ao perfil do Instagram`, e deve ser calculada e rotulada assim.
- **Alcance não se soma entre dias.** Usar o CSV de período total para o alcance do período. Se só existir o diário, marcar o alcance como aproximado.
- Valores do CSV são oficiais. Não estimar seguidores por anúncio quando o CSV existir.

## Passo a passo

1. Ler os CSVs da pasta de dados e validar as colunas acima. Se faltar alguma coluna essencial, parar e informar qual.
2. Separar fases pelo nome da campanha e deduplicar por dia e anúncio.
3. Gerar um único `dashboard.html`, com os dados embutidos em JSON e JavaScript puro, sem dependências externas além da fonte.
4. Abrir o arquivo no navegador para conferência.
5. Não publicar, não subir para o repositório e não fazer commit sem pedido explícito.

## Limites e avisos

- Facebook e Instagram (página e conta) ficam com aviso "sem dados automáticos" enquanto não houver fonte. Não preencher com zeros.
- Nunca incluir tokens, senhas ou o conteúdo de arquivos de credenciais no dashboard ou no chat.
- Textos em português do Brasil, sem termos em inglês na interface.
