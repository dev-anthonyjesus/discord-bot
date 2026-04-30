import nextcord

# ─────────────────────────────────────────────────────────────
# Como personalizar depois:
#
# Unicode:
# "mamadeira": "🍼"
#
# Emoji customizado:
# "mamadeira": {
#     "name": "mamadeira",
#     "id": 123456789012345678,
#     "animated": False,
# }
#
# Emoji animado:
# "sono": {
#     "name": "sono",
#     "id": 123456789012345678,
#     "animated": True,
# }
# ─────────────────────────────────────────────────────────────

EMOJIS = {
    # Sistema
    "bebe": "🍼",
    "painel": "📋",
    "camera": "📹",
    "noite": "🌙",
    "manha": "☀️",
    "reset": "♻️",
    "adicionais": "✨",
    "moeda": "🪙",
    "erro": "❌",
    "ok": "✅",
    # Status
    "fome": "🍼",
    "fralda": "🧷",
    "sono": "😴",
    "atencao": "🧸",
    "higiene": "🛁",
    "humor": "😊",
    "disposicao": "⚡",
    # Ações grátis
    "mamadeira": "🍼",
    "trocar_fralda": "🧷",
    "ninar": "😴",
    "aninhar": "🧸",
    "banho": "🛁",
    # Ações pagas
    "parquinho": "🎠",
    "brinquedo": "🧸",
    "roupinhas": "👕",
    "papinha": "🥣",
    "avos": "👴",
    "musica": "🎵",
    "bercinho": "🛏️",
    "abajur": "🌙",
    "remedio_colica": "💊",
    "historinha": "📚",
    "kit_higiene": "🧴",
    "quartinho": "🧺",
    # Traços
    "dorminhoco": "🌙",
    "faminto": "🍽️",
    "carente": "💞",
    "bagunceiro": "🧦",
    "calminho": "🍃",
    "sensivel": "🥺",
}


def E(chave: str) -> str:
    """
    Emoji em texto para embeds, descrições, labels e mensagens.
    """
    emoji = EMOJIS.get(chave, "•")

    if isinstance(emoji, str):
        return emoji

    if isinstance(emoji, dict):
        nome = emoji.get("name")
        emoji_id = emoji.get("id")
        animated = emoji.get("animated", False)
        prefixo = "a" if animated else ""
        return f"<{prefixo}:{nome}:{emoji_id}>"

    return "•"


def PE(chave: str):
    """
    Emoji compatível com nextcord Button/SelectOption.
    """
    emoji = EMOJIS.get(chave)

    if emoji is None:
        return None

    if isinstance(emoji, str):
        return emoji

    if isinstance(emoji, dict):
        return nextcord.PartialEmoji(
            name=emoji.get("name"),
            id=emoji.get("id"),
            animated=emoji.get("animated", False),
        )

    return None
