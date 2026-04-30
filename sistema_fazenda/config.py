# ─────────────────────────────────────────────────────────────
# Canais da categoria Farmhouse
# ─────────────────────────────────────────────────────────────

CANAL_FARMHOUSE_ID = 1499393422522581104
CANAL_CANGACO_ID = 1499393648997961738
CANAL_PREFEITURA_ID = 1499393713837969438

# Se quiser colocar a categoria depois, preenche aqui.
# Por enquanto o bot vai usar a mesma categoria do canal farmhouse.
CATEGORIA_FARMHOUSE_ID = None

# ─────────────────────────────────────────────────────────────
# JSON
# ─────────────────────────────────────────────────────────────

FAZENDA_FILE = "json/fazenda.json"

# ─────────────────────────────────────────────────────────────
# Config inicial
# ─────────────────────────────────────────────────────────────

NOME_FAZENDA = "Farmhouse"
MOEDA_NOME = "moedas rurais"

ENERGIA_INICIAL = 100
ENERGIA_MAXIMA = 100

ESTACAO_INICIAL = "outono"

TOTAL_LOTES = 6
CANTEIROS_POR_LOTE = 4
SLOTS_POR_CANTEIRO = 3

LOTES_DESBLOQUEADOS_INICIAIS = [1]

PACOTE_SEMENTES = 3

# Tempo de crescimento em segundos.
# Para teste, deixei curto.
CULTIVOS = {
    "milho": {
        "emoji": "milho",
        "semente_emoji": "semente_milho",
        "nome": "Milho",
        "estacoes": ["outono"],
        "tempo_segundos": 300,
        "preco_semente": 8,
        "valor_venda": 18,
        "rendimento": 2,
        "energia_plantar": 3,
        "energia_colher": 4,
    },
    "feijao": {
        "emoji": "feijao",
        "semente_emoji": "semente_feijao",
        "nome": "Feijão",
        "estacoes": ["outono"],
        "tempo_segundos": 420,
        "preco_semente": 10,
        "valor_venda": 24,
        "rendimento": 2,
        "energia_plantar": 3,
        "energia_colher": 4,
    },
    "cafe": {
        "emoji": "cafe",
        "semente_emoji": "semente_cafe",
        "nome": "Café",
        "estacoes": ["outono"],
        "tempo_segundos": 600,
        "preco_semente": 14,
        "valor_venda": 34,
        "rendimento": 2,
        "energia_plantar": 4,
        "energia_colher": 5,
    },
    "mandioca": {
        "emoji": "mandioca",
        "semente_emoji": "semente_mandioca",
        "nome": "Mandioca",
        "estacoes": ["outono"],
        "tempo_segundos": 480,
        "preco_semente": 12,
        "valor_venda": 28,
        "rendimento": 2,
        "energia_plantar": 3,
        "energia_colher": 4,
    },
}

ESTACOES = {
    "outono": {
        "emoji": "outono",
        "nome": "Outono",
        "descricao": "Tempo de colheitas fortes, grãos e raízes.",
    },
    "inverno": {
        "emoji": "inverno",
        "nome": "Inverno",
        "descricao": "Clima frio para cultivos resistentes.",
    },
    "primavera": {
        "emoji": "primavera",
        "nome": "Primavera",
        "descricao": "Estação fértil, colorida e cheia de crescimento.",
    },
    "verao": {
        "emoji": "verao",
        "nome": "Verão",
        "descricao": "Sol forte, frutas e cultivos tropicais.",
    },
}

SEMENTES_INICIAIS = {
    "milho": 3,
    "feijao": 3,
    "cafe": 3,
    "mandioca": 3,
}

MOEDAS_INICIAIS = 100
TAXA_FORNECEDOR = 0.10
