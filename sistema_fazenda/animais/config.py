ANIMAIS = {
    "galinha": {
        "nome": "Galinha",
        "emoji": "🐔",
        "local": "galinheiro",
        "produto": "ovo",
        "produto_nome": "Ovos",
        "produto_emoji": "🥚",
        "tempo_produto_segundos": 20 * 60,
        "tempo_procriacao_segundos": 60 * 60,
        "consumo_racao_produto": 2,
        "consumo_racao_procriacao": 6,
        "preco_compra": 35,
        "valor_carne": 18,
    },
    "vaca": {
        "nome": "Vaca",
        "emoji": "🐄",
        "local": "celeiro",
        "produto": "leite_vaca",
        "produto_nome": "Leite de vaca",
        "produto_emoji": "🥛",
        "tempo_produto_segundos": 30 * 60,
        "tempo_procriacao_segundos": 60 * 60,
        "consumo_racao_produto": 5,
        "consumo_racao_procriacao": 14,
        "preco_compra": 120,
        "valor_carne": 90,
    },
    "ovelha": {
        "nome": "Ovelha",
        "emoji": "🐑",
        "local": "celeiro",
        "produto": "la",
        "produto_nome": "Lã",
        "produto_emoji": "🧶",
        "tempo_produto_segundos": 45 * 60,
        "tempo_procriacao_segundos": 60 * 60,
        "consumo_racao_produto": 4,
        "consumo_racao_procriacao": 10,
        "preco_compra": 90,
        "valor_carne": 55,
    },
    "cabra": {
        "nome": "Cabra",
        "emoji": "🐐",
        "local": "celeiro",
        "produto": "leite_cabra",
        "produto_nome": "Leite de cabra",
        "produto_emoji": "🥛",
        "tempo_produto_segundos": 35 * 60,
        "tempo_procriacao_segundos": 60 * 60,
        "consumo_racao_produto": 4,
        "consumo_racao_procriacao": 10,
        "preco_compra": 85,
        "valor_carne": 50,
    },
    "cavalo": {
        "nome": "Cavalo",
        "emoji": "🐎",
        "local": "estabulo",
        "produto": None,
        "produto_nome": None,
        "produto_emoji": None,
        "tempo_produto_segundos": None,
        "tempo_procriacao_segundos": 60 * 60,
        "consumo_racao_produto": 0,
        "consumo_racao_procriacao": 16,
        "preco_compra": 300,
        "valor_carne": 0,
    },
}

RACAO_MAXIMA = 100
RACAO_INICIAL = 50
CUSTO_ENTREGA_RACAO = 60
VALOR_ENTREGA_RACAO = 100


ANIMAIS_COMPRAVEIS = {
    "galinha": {
        "quantidade_unidade": 1,
        "quantidade_casal": 2,
    },
    "vaca": {
        "quantidade_unidade": 1,
        "quantidade_casal": 2,
    },
    "ovelha": {
        "quantidade_unidade": 1,
        "quantidade_casal": 2,
    },
    "cabra": {
        "quantidade_unidade": 1,
        "quantidade_casal": 2,
    },
}

ABATE_ANIMAIS = {
    "galinha": {
        "produto": "carne_frango",
        "nome": "Carne de frango",
        "emoji": "🍗",
        "kg": 2,
        "valor_por_kg": 9,
    },
    "vaca": {
        "produto": "carne_bovina",
        "nome": "Carne bovina",
        "emoji": "🥩",
        "kg": 30,
        "valor_por_kg": 3,
    },
    "ovelha": {
        "produto": "carne_ovina",
        "nome": "Carne ovina",
        "emoji": "🥩",
        "kg": 15,
        "valor_por_kg": 4,
    },
    "cabra": {
        "produto": "carne_caprina",
        "nome": "Carne caprina",
        "emoji": "🥩",
        "kg": 14,
        "valor_por_kg": 4,
    },
}

PRODUTOS_ANIMAIS = {
    "ovo": {
        "nome": "Ovos",
        "emoji": "🥚",
        "unidade": "un",
        "valor": 4,
    },
    "leite_vaca": {
        "nome": "Leite de vaca",
        "emoji": "🥛",
        "unidade": "L",
        "valor": 6,
    },
    "leite_cabra": {
        "nome": "Leite de cabra",
        "emoji": "🥛",
        "unidade": "L",
        "valor": 8,
    },
    "la": {
        "nome": "Lã",
        "emoji": "🧶",
        "unidade": "un",
        "valor": 10,
    },
    "carne_frango": {
        "nome": "Carne de frango",
        "emoji": "🍗",
        "unidade": "kg",
        "valor": 9,
    },
    "carne_bovina": {
        "nome": "Carne bovina",
        "emoji": "🥩",
        "unidade": "kg",
        "valor": 3,
    },
    "carne_ovina": {
        "nome": "Carne ovina",
        "emoji": "🥩",
        "unidade": "kg",
        "valor": 4,
    },
    "carne_caprina": {
        "nome": "Carne caprina",
        "emoji": "🥩",
        "unidade": "kg",
        "valor": 4,
    },
}


ANIMAIS_COMPRAVEIS = {
    "galinha": True,
    "vaca": True,
    "ovelha": True,
    "cabra": True,
}
