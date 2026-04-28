import nextcord

# ── Canais ──────────────────────────────────────────────────────────────────

CANAL_LOG_PRIV = 1491930461750952108
CANAL_SHOP = 1491190154512171038

# ── Cargos ──────────────────────────────────────────────────────────────────

CARGO_PROTEGIDO = 1492378409781694484

# ── Emojis ──────────────────────────────────────────────────────────────────

EMOJI_MIMO_ID = 1492379169999552563
EMOJI_MOEDA_ID = 1492371478362980393

MIMO_EMOJI = nextcord.PartialEmoji(name="mimo", id=EMOJI_MIMO_ID)
MOEDA_EMOJI = nextcord.PartialEmoji(name="moeda", id=EMOJI_MOEDA_ID)

# ── Arquivo exclusivo dessa economia ────────────────────────────────────────

ECONOMIA_FILE = "json/economia_amor.json"

# ── VIPs / Loja ─────────────────────────────────────────────────────────────

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
        "cargo_id": 1492358453179472754,
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
        "cargo_id": CARGO_PROTEGIDO,
        "duracao_dias": 7,
        "tipo": "protegido",
    },
}
