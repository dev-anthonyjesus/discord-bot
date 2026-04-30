import nextcord

EMOJIS = {
    # Sistema
    "fazenda": "🚜",
    "farmhouse": "🏡",
    "cangaco": "🌵",
    "prefeitura": "🏛️",
    "moeda": "🪙",
    "energia": "⚡",
    "loja": "🛒",
    "celeiro": "📦",
    "ranking": "🏆",
    "info": "📋",
    "ok": "✅",
    "erro": "❌",
    "tempo": "⏳",
    "pronto": "✅",
    "bloqueado": "🔒",
    "lote": "🌱",
    # Ações
    "plantar": "🌱",
    "regar": "💧",
    "colher": "🧺",
    "vender": "💰",
    "comprar": "🛍️",
    "explorar": "🧭",
    "missao": "📜",
    # Estações
    "outono": "🍂",
    "inverno": "❄️",
    "primavera": "🌸",
    "verao": "☀️",
    # Cultivos e sementes
    "milho": "🌽",
    "semente_milho": "🌱",
    "feijao": "🫘",
    "semente_feijao": "🌱",
    "cafe": "☕",
    "semente_cafe": "🌱",
    "mandioca": "🍠",
    "semente_mandioca": "🌱",
    # Animais futuros
    "gado": "🐄",
    "galinha": "🐔",
    "cabra": "🐐",
    "cavalo": "🐎",
    "ovelha": "🐑",
    "abelha": "🐝",
}


def E(chave: str) -> str:
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
