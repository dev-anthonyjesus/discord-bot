# ─────────────────────────────────────────────────────────────
# Canais
# ─────────────────────────────────────────────────────────────

CANAL_BEBE_ID = 1494700943894118466

# ─────────────────────────────────────────────────────────────
# Cargos
# ─────────────────────────────────────────────────────────────

CARGO_NOIVO_ID = 1491166369859764314
CARGO_NOIVA_ID = 1491166441515257927

# ─────────────────────────────────────────────────────────────
# JSON
# ─────────────────────────────────────────────────────────────

BEBE_FILE = "json/bebe_virtual.json"

# ─────────────────────────────────────────────────────────────
# Status inicial
# ─────────────────────────────────────────────────────────────

STATUS_INICIAL = {
    "fome": 70,
    "fralda": 80,
    "sono": 60,
    "atencao": 70,
    "higiene": 80,
}

DISPOSICAO_INICIAL = 100

# ─────────────────────────────────────────────────────────────
# Traços
# ─────────────────────────────────────────────────────────────

TRACOS = {
    "dorminhoco": {
        "emoji": "dorminhoco",
        "label": "Dorminhoco",
        "descricao": "Sono cai mais devagar, mas ninar custa mais disposição.",
    },
    "faminto": {
        "emoji": "faminto",
        "label": "Faminto",
        "descricao": "Fome cai mais rápido, mas mamadeira recupera mais.",
    },
    "carente": {
        "emoji": "carente",
        "label": "Carente",
        "descricao": "Atenção cai mais rápido, mas aninhar melhora muito o humor.",
    },
    "bagunceiro": {
        "emoji": "bagunceiro",
        "label": "Bagunceiro",
        "descricao": "Higiene cai mais rápido, mas brincar melhora mais a atenção.",
    },
    "calminho": {
        "emoji": "calminho",
        "label": "Calminho",
        "descricao": "Humor cai mais devagar e o bebê se estabiliza melhor.",
    },
    "sensivel": {
        "emoji": "sensivel",
        "label": "Sensível",
        "descricao": "Noites ruins pesam mais na disposição dos pais.",
    },
}

# ─────────────────────────────────────────────────────────────
# Ações grátis
# ─────────────────────────────────────────────────────────────

ACOES_BASICAS = {
    "mamadeira": {
        "emoji": "mamadeira",
        "label": "Dar mamadeira",
        "custo_disposicao": 8,
        "efeitos": {"fome": 22, "atencao": 2},
    },
    "fralda": {
        "emoji": "trocar_fralda",
        "label": "Trocar fralda",
        "custo_disposicao": 10,
        "efeitos": {"fralda": 28, "higiene": 5},
    },
    "ninar": {
        "emoji": "ninar",
        "label": "Ninar até dormir",
        "custo_disposicao": 14,
        "efeitos": {"sono": 25, "atencao": 4},
    },
    "aninhar": {
        "emoji": "aninhar",
        "label": "Aninhar",
        "custo_disposicao": 6,
        "efeitos": {"atencao": 20},
    },
    "banho": {
        "emoji": "banho",
        "label": "Dar banho",
        "custo_disposicao": 12,
        "efeitos": {"higiene": 25, "sono": 5, "atencao": 4},
    },
}

# ─────────────────────────────────────────────────────────────
# Ações pagas com moedas
# ─────────────────────────────────────────────────────────────

ACOES_PAGAS = {
    "parquinho": {
        "emoji": "parquinho",
        "label": "Levar ao parquinho",
        "preco": 20,
        "efeitos": {"atencao": 28, "sono": -5},
    },
    "brinquedo": {
        "emoji": "brinquedo",
        "label": "Comprar brinquedo novo",
        "preco": 35,
        "efeitos": {"atencao": 30},
    },
    "roupinhas": {
        "emoji": "roupinhas",
        "label": "Roupinhas novas",
        "preco": 30,
        "efeitos": {"higiene": 12, "atencao": 12},
    },
    "papinha": {
        "emoji": "papinha",
        "label": "Dar papinha especial",
        "preco": 25,
        "efeitos": {"fome": 30, "fralda": -12},
    },
    "avos": {
        "emoji": "avos",
        "label": "Visita dos avôs",
        "preco": 40,
        "efeitos": {"atencao": 35, "sono": -15},
    },
    "musica": {
        "emoji": "musica",
        "label": "Colocar música de ninar",
        "preco": 25,
        "efeitos": {"sono": 25, "atencao": 5},
    },
    "bercinho": {
        "emoji": "bercinho",
        "label": "Melhorar o bercinho",
        "preco": 60,
        "efeitos": {"sono": 30},
    },
    "abajur": {
        "emoji": "abajur",
        "label": "Abajur fofo",
        "preco": 80,
        "efeitos": {"sono": 20},
        "ativa_noite_tranquila": True,
    },
    "remedio_colica": {
        "emoji": "remedio_colica",
        "label": "Remédio de cólica",
        "preco": 45,
        "efeitos": {"atencao": 10, "sono": 15},
        "cura_colica": True,
    },
    "historinha": {
        "emoji": "historinha",
        "label": "Contar historinha",
        "preco": 15,
        "efeitos": {"sono": 15, "atencao": 10},
    },
    "kit_higiene": {
        "emoji": "kit_higiene",
        "label": "Comprar kit de higiene",
        "preco": 35,
        "efeitos": {"higiene": 25, "fralda": 5},
    },
    "quartinho": {
        "emoji": "quartinho",
        "label": "Organizar o quartinho",
        "preco": 30,
        "efeitos": {"higiene": 12, "atencao": 10, "sono": 5},
    },
}

# ─────────────────────────────────────────────────────────────
# Melhorias passivas preparadas para depois
# ─────────────────────────────────────────────────────────────

MELHORIAS_INICIAIS = {
    "quarto": 1,
    "bercinho": 1,
    "luz_noturna": 1,
    "higiene": 1,
    "brinquedos": 1,
}

# ─────────────────────────────────────────────────────────────
# Teste / debug
# ─────────────────────────────────────────────────────────────

MODO_TESTE_PADRAO = True
