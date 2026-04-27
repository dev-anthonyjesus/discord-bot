import os

# ── Canais ──────────────────────────────────────────────────────────────────
CANAL_LOG_PRIV       = 1491930461750952108
CANAL_SHOP           = 1491190154512171038
CANAL_CASAMENTO      = 1494420437453635766
CANAL_BEBE           = 1494700943894118466
CANAL_COMANDOS       = 1494508908826464438
CANAL_WELCOME        = 1491170989160136704

# ── Cargos ───────────────────────────────────────────────────────────────────
CARGO_PROTEGIDO      = 1492378409781694484
NOIVO_ROLE_ID        = 1491166369859764314
NOIVA_ROLE_ID        = 1491166441515257927

# ── Usuários ─────────────────────────────────────────────────────────────────
SEU_ID               = 1431111401522462741
ID_DA_NOIVA          = 715329753032163379

# ── Categorias / canais de reação ────────────────────────────────────────────
CATEGORIA_MIDIA_ID   = 1491169377217941675

CANAIS_REACAO = {
    1491169795398176889: 1493059675070009425,   # receita -> capcake
    1491192043672830084: 1493059522594607164,   # cinema -> pipoca
    1492357739588878449: 1492415234605060160,   # gifts -> gift1
    1491169251459862799: 1493059465958653982,   # memes -> kaka
    1491169848250597769: 1494093082667257866,   # viagens -> malas
}

# ── Emojis ───────────────────────────────────────────────────────────────────
EMOJI_CHECK_ID       = 1495102972680736768
EMOJI_MIMO_ID        = 1492379169999552563
EMOJI_MOEDA_ID       = 1492371478362980393

# ── Arquivos JSON ────────────────────────────────────────────────────────────
DB_FILE              = "database.json"
CASAMENTO_FILE       = "casamento_compatibilidade.json"
BEBE_FILE            = "bebe_virtual.json"
PANEL_FILE           = "panel_messages.json"

# ── Imagens ──────────────────────────────────────────────────────────────────
PASTA_IMAGENS_BEBE   = "imagens_bebe"

# ── GIF / Fig ────────────────────────────────────────────────────────────────
MAX_FIG_SIZE         = 512 * 1024   # 512 KB
FIG_DIM              = (320, 320)

# Caminho do gifsicle — use variável de ambiente ou fallback local
GIFSICLE_PATH        = os.getenv(
    "GIFSICLE_PATH",
    r"C:\Users\antho\Downloads\gifsicle-1.95-win32\gifsicle.exe",
)

# ── VIPs ─────────────────────────────────────────────────────────────────────
VIPS = {
    "momo": {
        "nome": "VIP MOMO",
        "preco": 50,
        "cargo_id": 1492358391475998892,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "picante": {
        "nome": "VIP PICANTE",
        "preco": 80,
        "cargo_id": 1492358453174472754,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "promessa": {
        "nome": "VIP PROMESSA",
        "preco": 150,
        "cargo_id": 1492358529775046793,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "dengo": {
        "nome": "VIP DENGO VITALÍCIO",
        "preco": 300,
        "cargo_id": 1492358174999707758,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "alma": {
        "nome": "PATROCÍNIO ALMA GÊMEA",
        "preco": 500,
        "cargo_id": 1492358982923321485,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "protegido": {
        "nome": "PROTEGIDO",
        "preco": 70,
        "cargo_id": 1492378409781694484,
        "duracao_dias": 7,
        "tipo": "protegido",
    },
}

PANEL_FILE = "panel_messages.json"

CANAL_LOG_PRIV = 1491930461750952108
CANAL_SHOP = 1491190154512171038
CARGO_PROTEGIDO = 1492378409781694484
# ============================casamento==================
CANAL_CASAMENTO = 1494420437453635766
SEU_ID = 1431111401522462741
ID_DA_NOIVA = 715329753032163379
CASAMENTO_FILE = "casamento_compatibilidade.json"
ARQUIVO_ECONOMIA = "database.json"
# ===================================================================
CANAL_BEBE = 1494700943894118466
BEBE_FILE = "bebe_virtual.json"
PASTA_IMAGENS_BEBE = "imagens_bebe"

BEBE_IMAGENS = {
    "tranquilo": os.path.join(PASTA_IMAGENS_BEBE, "feliz.png"),
    "instável": os.path.join(PASTA_IMAGENS_BEBE, "neutro.png"),
    "chorando bastante": os.path.join(PASTA_IMAGENS_BEBE, "chorando.png"),
    "colapso": os.path.join(PASTA_IMAGENS_BEBE, "colapso.png"),
}
# mod bebe======================

NOIVO_ROLE_ID = 1491166369859764314
NOIVA_ROLE_ID = 1491166441515257927


CANAL_COMANDOS = 1494508908826464438
GIFSICLE_PATH = r"C:\Users\antho\Downloads\gifsicle-1.95-win32\gifsicle.exe"

CANAIS_REACAO = {
    1491169795398176889: 1493059675070009425,  # receita -> capcake
    1491192043672830084: 1493059522594607164,  # cinema -> pipoca
    1492357739588878449: 1492415234605060160,  # gifts -> gift1
    1491169251459862799: 1493059465958653982,  # memes -> kaka
    1491169848250597769: 1494093082667257866,  # viagens -> malas
}

DB_FILE = "database.json"

MIMO_EMOJI = nextcord.PartialEmoji(name="mimo", id=1492379169999552563)
MOEDA_EMOJI = nextcord.PartialEmoji(name="moeda", id=1492371478362980393)

VIPS = {
    "momo": {
        "nome": "VIP MOMO",
        "preco": 50,
        "cargo_id": 1492358391475998892,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "picante": {
        "nome": "VIP PICANTE",
        "preco": 80,
        "cargo_id": 1492358453174472754,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "promessa": {
        "nome": "VIP PROMESSA",
        "preco": 150,
        "cargo_id": 1492358529775046793,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "dengo": {
        "nome": "VIP DENGO VITALÍCIO",
        "preco": 300,
        "cargo_id": 1492358174999707758,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "alma": {
        "nome": "PATROCÍNIO ALMA GÊMEA",
        "preco": 500,
        "cargo_id": 1492358982923321485,
        "duracao_dias": 14,
        "tipo": "vip",
    },
    "protegido": {
        "nome": "PROTEGIDO",
        "preco": 70,
        "cargo_id": 1492378409781694484,
        "duracao_dias": 7,
        "tipo": "protegido",
    },
}


CATEGORIA_MIDIA_ID = 1491169377217941675
EMOJI_CHECK = "<a:check:1495102972680736768>"


# ================= FIG =================

MAX_FIG_SIZE = 512 * 1024
FIG_DIM = (320, 320)
