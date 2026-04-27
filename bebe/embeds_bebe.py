import os
import nextcord

PASTA_IMAGENS_BEBE = "imagens_bebe"
NOIVO_ROLE_ID = 1491166369859764314
NOIVA_ROLE_ID = 1491166441515257927


TRACOS_INFO = {
    "calminho": "Piora mais devagar.",
    "sensivel": "Humor cai mais fácil.",
    "intenso": "Fome e humor oscilam mais rápido.",
    "risonho": "Melhora mais com atenção.",
    "grudento": "Precisa de mais atenção.",
    "agitado": "Dorme pior."
}

ADICIONAIS_INFO = {
    "baba": ("Babá", "Ajuda forte, mas custa caro."),
    "brinquedo": ("Brinquedo", "Ajuda atenção e humor."),
    "chupeta": ("Chupeta", "Ajuda pouco, mas rápido."),
    "remedio": ("Remédio", "Ajuda em momentos ruins."),
    "comida_especial": ("Comida especial", "Ajuda fome e humor."),
    "passeio": ("Passeio", "Melhora o humor."),
    "musica_ninar": ("Música de ninar", "Ajuda o sono."),
}

EMOJI_STATUS = {
    "fome": "🍼",
    "fralda": "🧻",
    "sono": "😴",
    "atencao": "❤️",
    "higiene": "🧼",
    "humor": "😊",
}

MAPA_IMAGEM_ESTADO = {
    "tranquilo": "feliz.png",
    "instável": "neutro.png",
    "chorando bastante": "chorando.png",
    "colapso": "colapso.png",
    "dormindo": "dormindo.png",
    "fome": "fome.png",
    "sono": "sono.png",
    "sujo": "sujo.png",
    "atencao": "atencao.png",
}

def caminho_imagem(nome_arquivo: str):
    path = os.path.join(PASTA_IMAGENS_BEBE, nome_arquivo)
    return path if os.path.exists(path) else None

def nome_imagem_por_estado(chave: str):
    return MAPA_IMAGEM_ESTADO.get(chave)

def barra(valor: int) -> str:
    valor = max(0, min(100, int(valor)))
    blocos = int(round(valor / 10))
    return "🟩" * blocos + "⬜" * (10 - blocos)

def embed_setup_bebe(data: dict) -> nextcord.Embed:
    nome = data.get("nome", "Bebê")
    genero = data.get("genero", "Neutro")
    traco_noivo = data.get("traco_noivo") or "Ainda não escolheu"
    traco_noiva = data.get("traco_noiva") or "Ainda não escolheu"

    embed = nextcord.Embed(
        title="🍼 Configuração do Bebê",
        description=(
            "Antes de começar, configurem o bebê.\n\n"
            f"**Nome atual:** {nome}\n"
            f"**Gênero atual:** {genero}\n\n"
            f"<@&{NOIVO_ROLE_ID}>: **{str(traco_noivo).title()}**\n"
            f"<@&{NOIVA_ROLE_ID}>: **{str(traco_noiva).title()}**\n\n"
            "Cada um precisa escolher **1 traço diferente**."
        ),
        color=0x2F3136
    )

    linhas = [f"**{k.title()}** — {v}" for k, v in TRACOS_INFO.items()]
    embed.add_field(name="Traços disponíveis", value="\n".join(linhas), inline=False)
    embed.set_footer(text="Quando os dois terminarem, esse painel será substituído pelo painel principal.")
    return embed

def embed_principal_bebe(data: dict) -> nextcord.Embed:
    tracos = data.get("tracos", [])
    tracos_txt = ", ".join(t.title() for t in tracos) if tracos else "Não definidos"
    satisfacao = data.get("satisfacao_geral", 0)

    cuidados_dia = data.get("cuidados_dia", 0)
    ultimo_cuidado = data.get("ultimo_cuidado") or "Nenhum"
    ultimo_por = data.get("quem_cuidou_por_ultimo") or "Ninguém"

    embed = nextcord.Embed(
        title=f"👶 {data.get('nome', 'Bebê')}",
        description=(
            f"**Gênero:** {data.get('genero', 'Neutro')}\n"
            f"**Traços:** {tracos_txt}"
        ),
        color=0x2F3136
    )

    for chave in ["fome", "fralda", "sono", "atencao", "higiene", "humor"]:
        valor = data.get(chave, 50)

        # nessas necessidades, o número interno maior = pior
        # então a barra visual precisa ser invertida
        if chave in ["fome", "fralda", "sono", "atencao", "higiene"]:
            valor_barra = 100 - valor
        else:
            valor_barra = valor  # humor continua normal

        # se estiver dormindo, mostra a barra de sono cheia
        if chave == "sono" and data.get("estado") == "dormindo":
            valor_barra = 100

        embed.add_field(
            name=f"{EMOJI_STATUS[chave]} {chave.title()}",
            value=barra(valor_barra),
            inline=True
        )

    embed.add_field(
        name="🧍 Disposição",
        value=(
            f"Noivo: {data.get('disp_noivo', 100)}\n"
            f"Noiva: {data.get('disp_noiva', 100)}"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 Estado atual",
        value=data.get("estado", "tranquilo").title(),
        inline=True
    )
    embed.add_field(
        name="🧾 Cuidados hoje",
        value=str(cuidados_dia),
        inline=True
    )
    embed.add_field(
        name="🕒 Último cuidado",
        value=f"{ultimo_cuidado} — {ultimo_por}",
        inline=False
    )

    embed.add_field(
        name="⭐ Satisfação geral", value=f"**{satisfacao}%**", inline=False
    )

    embed.set_footer(text=data.get("mensagem", "Tudo tranquilo por enquanto."))
    return embed

def embed_alerta_bebe(titulo: str, descricao: str) -> nextcord.Embed:
    return nextcord.Embed(
        title=titulo,
        description=descricao,
        color=0xED4245
    )

def embed_noite_bebe(descricao: str) -> nextcord.Embed:
    return nextcord.Embed(
        title="🌙 Noite do bebê",
        description=descricao,
        color=0x5865F2
    )

def embed_admin_bebe(data: dict) -> nextcord.Embed:
    tracos = data.get("tracos", [])
    tracos_txt = ", ".join(t.title() for t in tracos) if tracos else "Não definidos"

    embed = nextcord.Embed(
        title="⚙️ BabyConfig",
        description="Painel privado de administração do bebê.",
        color=0x2F3136
    )
    embed.add_field(name="Nome", value=data.get("nome", "Bebê"), inline=True)
    embed.add_field(name="Gênero", value=data.get("genero", "Neutro"), inline=True)
    embed.add_field(name="Traços", value=tracos_txt, inline=False)
    embed.add_field(name="Estado", value=data.get("estado", "tranquilo").title(), inline=True)
    embed.add_field(
        name="Disposição",
        value=f"Noivo: {data.get('disp_noivo', 100)} | Noiva: {data.get('disp_noiva', 100)}",
        inline=False
    )
    return embed

def embed_adicionais_bebe() -> nextcord.Embed:
    linhas = []
    precos = {
        "baba": 45,
        "brinquedo": 15,
        "chupeta": 8,
        "remedio": 18,
        "comida_especial": 20,
        "passeio": 22,
        "musica_ninar": 12,
    }
    for chave, (nome, desc) in ADICIONAIS_INFO.items():
        linhas.append(f"**{nome}** — {precos[chave]} moedas\n> {desc}")
    return nextcord.Embed(
        title="🛒 Adicionais do bebê",
        description="\n\n".join(linhas),
        color=0x2F3136
    )
    

def embed_memoria_bebe(
    titulo: str = "📸 Momentos do bebê",
    descricao: str = "Escolha uma foto para enviar um momento.",
) -> nextcord.Embed:
    return nextcord.Embed(
        title=titulo,
        description=descricao,
        color=0x2F3136
    )
    
    
