import nextcord

from sistema_bebe.config import (
    ACOES_BASICAS,
    ACOES_PAGAS,
    CARGO_NOIVO_ID,
    CARGO_NOIVA_ID,
    TRACOS,
)
from sistema_bebe.db import get_state
from sistema_bebe.emojis import E
from sistema_bebe.services import frase_bebe


def ansi(texto: str) -> str:
    return f"```ansi\n{texto}\n```"


def ansi_cor(valor: int) -> str:
    valor = int(valor)

    if valor >= 75:
        return "\u001b[32m"

    if valor >= 50:
        return "\u001b[33m"

    return "\u001b[31m"


def linha_status(nome: str, emoji_key: str, valor: int) -> str:
    cor = ansi_cor(valor)
    return f"{E(emoji_key)} {nome:<9}: {cor}{valor:>3}/100\u001b[0m"


def traco_label(traco_id: str | None) -> str:
    if not traco_id:
        return "`aguardando escolha`"

    traco = TRACOS.get(traco_id)

    if not traco:
        return "`traço desconhecido`"

    return f"{E(traco['emoji'])} **{traco['label']}**"


def criar_embed_escolha_tracos() -> nextcord.Embed:
    data = get_state()

    traco_noivo = data["tracos"].get(str(CARGO_NOIVO_ID))
    traco_noiva = data["tracos"].get(str(CARGO_NOIVA_ID))

    embed = nextcord.Embed(
        title=f"{E('bebe')} Escolha os traços do bebê",
        description=(
            "Antes de começar, cada responsável escolhe **um traço**.\n"
            "Quando os dois escolherem, este painel some e o painel de cuidados aparece."
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Responsáveis",
        value=(
            f"<@&{CARGO_NOIVO_ID}>: {traco_label(traco_noivo)}\n"
            f"<@&{CARGO_NOIVA_ID}>: {traco_label(traco_noiva)}"
        ),
        inline=False,
    )

    opcoes = []

    for key, traco in TRACOS.items():
        opcoes.append(
            f"{E(traco['emoji'])} **{traco['label']}** — {traco['descricao']}"
        )

    embed.add_field(
        name="Traços disponíveis",
        value="\n".join(opcoes),
        inline=False,
    )

    embed.set_footer(text="Baby System • escolha inicial")
    return embed


def criar_bloco_status(status: dict) -> str:
    texto = "\n".join(
        [
            linha_status("Fome", "fome", status["fome"]),
            linha_status("Fralda", "fralda", status["fralda"]),
            linha_status("Sono", "sono", status["sono"]),
            linha_status("Atenção", "atencao", status["atencao"]),
            linha_status("Higiene", "higiene", status["higiene"]),
        ]
    )

    return ansi(texto)


def criar_bloco_pais(data: dict) -> str:
    noivo = data["pais"][str(CARGO_NOIVO_ID)]
    noiva = data["pais"][str(CARGO_NOIVA_ID)]

    return (
        f"<@&{CARGO_NOIVO_ID}> — {E('disposicao')} `{noivo['disposicao']}/100` "
        f"• cuidados hoje: `{noivo['cuidados_hoje']}`\n"
        f"<@&{CARGO_NOIVA_ID}> — {E('disposicao')} `{noiva['disposicao']}/100` "
        f"• cuidados hoje: `{noiva['cuidados_hoje']}`"
    )


def criar_bloco_tracos(data: dict) -> str:
    traco_noivo = data["tracos"].get(str(CARGO_NOIVO_ID))
    traco_noiva = data["tracos"].get(str(CARGO_NOIVA_ID))

    return (
        f"<@&{CARGO_NOIVO_ID}>: {traco_label(traco_noivo)}\n"
        f"<@&{CARGO_NOIVA_ID}>: {traco_label(traco_noiva)}"
    )


def criar_bloco_inventario(data: dict) -> str:
    noite = data.get("noite", {})
    melhorias = data.get("melhorias", {})

    linhas = []

    if noite.get("abajur_ativo"):
        linhas.append(f"{E('abajur')} \u001b[35mAbajur fofo ativo\u001b[0m")
    else:
        linhas.append(f"{E('abajur')} \u001b[90mAbajur fofo inativo\u001b[0m")

    if noite.get("colica_ativa"):
        linhas.append(f"{E('remedio_colica')} \u001b[31mCólica ativa\u001b[0m")
    else:
        linhas.append(f"{E('remedio_colica')} \u001b[32mSem cólica no momento\u001b[0m")

    linhas.append(
        f"{E('quartinho')} Quarto nível: \u001b[36m{melhorias.get('quarto', 1)}\u001b[0m"
    )
    linhas.append(
        f"{E('bercinho')} Bercinho nível: \u001b[36m{melhorias.get('bercinho', 1)}\u001b[0m"
    )
    linhas.append(
        f"{E('brinquedo')} Brinquedos nível: \u001b[36m{melhorias.get('brinquedos', 1)}\u001b[0m"
    )

    return ansi("\n".join(linhas))


def criar_embed_painel_bebe() -> nextcord.Embed:
    data = get_state()
    status = data["status"]
    humor = data.get("humor", "Calminho")

    ultimo = data.get("ultimo_cuidado")

    if ultimo:
        ultimo_txt = f"{ultimo.get('acao')} por **{ultimo.get('por')}**"
    else:
        ultimo_txt = "Nenhum cuidado registrado ainda."

    modo_noite = data.get("noite", {}).get("modo_noturno", False)

    if modo_noite:
        modo_txt = f"{E('noite')} `Modo noturno ativo`"
    else:
        modo_txt = f"{E('manha')} `Modo dia ativo`"

    embed = nextcord.Embed(
        title=f"{E('bebe')} Baby Love — Painel de Cuidados",
        description=(
            f"{modo_txt}\n\n"
            f"{E('humor')} **Humor:** `{humor}`\n"
            f"> _“{frase_bebe(humor)}”_"
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Status do bebê",
        value=criar_bloco_status(status),
        inline=False,
    )

    embed.add_field(
        name="Responsáveis",
        value=criar_bloco_pais(data),
        inline=False,
    )

    embed.add_field(
        name="Traços",
        value=criar_bloco_tracos(data),
        inline=False,
    )

    embed.add_field(
        name="Inventário",
        value=criar_bloco_inventario(data),
        inline=False,
    )

    embed.add_field(
        name="Último cuidado",
        value=ultimo_txt,
        inline=False,
    )

    if data.get("noite", {}).get("colica_ativa"):
        embed.add_field(
            name=f"{E('remedio_colica')} Evento ativo",
            value="😭 Chorinho sem motivo aparente. Parece cólica. Talvez seja bom comprar um remédio.",
            inline=False,
        )

    embed.set_footer(text="Baby System • painel fixo de cuidados")
    return embed


def criar_embed_status() -> nextcord.Embed:
    embed = criar_embed_painel_bebe()
    embed.title = f"{E('painel')} Status atual do bebê"
    return embed


def criar_embed_resultado_acao(mensagem: str, sucesso: bool = True) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=f"{E('ok') if sucesso else E('erro')} Resultado do cuidado",
        description=mensagem,
        color=0x2ECC71 if sucesso else 0xE74C3C,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(text="Baby System")
    return embed


def criar_embed_noite(data: dict) -> nextcord.Embed:
    resultado = data["noite"].get("resultado")
    score = data["noite"].get("score")

    textos = {
        "tranquila": "O bebê foi colocado para dormir em boas condições. A chance de uma noite tranquila é alta.",
        "ok": "O bebê parece estável, mas ainda pode acordar algumas vezes.",
        "agitada": "O bebê dormiu meio incomodado. A noite pode ser agitada.",
        "ruim": "O bebê foi dormir precisando de cuidado. A madrugada pode ser difícil.",
    }

    embed = nextcord.Embed(
        title=f"{E('noite')} Modo noturno iniciado",
        description=textos.get(resultado, "O bebê entrou no modo noturno."),
        color=0x5865F2,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Score da noite",
        value=f"`{score}/100`",
        inline=True,
    )

    embed.add_field(
        name="Resultado previsto",
        value=f"`{resultado}`",
        inline=True,
    )

    embed.set_footer(text="Baby System • noite processada manualmente")
    return embed


def criar_embed_camera_manha(resultado: dict) -> nextcord.Embed:
    data = resultado["state"]
    mensagem = resultado["mensagem"]

    noivo = data["pais"][str(CARGO_NOIVO_ID)]
    noiva = data["pais"][str(CARGO_NOIVA_ID)]

    embed = nextcord.Embed(
        title=f"{E('camera')} Câmera do quartinho",
        description=mensagem,
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Disposição ao acordar",
        value=(
            f"<@&{CARGO_NOIVO_ID}>: `{noivo['disposicao']}/100`\n"
            f"<@&{CARGO_NOIVA_ID}>: `{noiva['disposicao']}/100`"
        ),
        inline=False,
    )

    embed.add_field(
        name="Bebê acordou assim",
        value=criar_bloco_status(data["status"]),
        inline=False,
    )

    embed.set_footer(text="Baby System • relatório da manhã")
    return embed


def formatar_nome_status(campo: str) -> str:
    nomes = {
        "fome": "fome",
        "fralda": "fralda",
        "sono": "sono",
        "atencao": "atenção",
        "higiene": "higiene",
    }

    return nomes.get(campo, campo)


def formatar_efeitos(efeitos: dict) -> str:
    partes = []

    for campo, valor in efeitos.items():
        sinal = "+" if valor > 0 else ""
        partes.append(f"`{sinal}{valor} {formatar_nome_status(campo)}`")

    return " ".join(partes)


def criar_embed_adicionais() -> nextcord.Embed:
    embed = nextcord.Embed(
        title=f"{E('adicionais')} Ações adicionais",
        description=(
            "Escolha uma ação no menu abaixo.\n"
            "Cada ação mostra o preço e o efeito no bebê."
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    for key, acao in ACOES_PAGAS.items():
        embed.add_field(
            name=f"{E(acao['emoji'])} {acao['label']}",
            value=(
                f"`{acao['preco']} moedas`\n"
                f"Efeito: {formatar_efeitos(acao['efeitos'])}"
            ),
            inline=False,
        )

    embed.set_footer(text="Baby System • ações pagas")
    return embed


def criar_embed_baby_monitor() -> nextcord.Embed:
    data = get_state()
    status = data["status"]
    humor = data.get("humor", "Calminho")

    embed = nextcord.Embed(
        title=f"{E('camera')} Baby Monitor",
        description=(
            "Informações rápidas para decidir qual cuidado fazer agora.\n\n"
            f"{E('humor')} Humor atual: `{humor}`\n"
            f"> _“{frase_bebe(humor)}”_"
        ),
        color=0x5865F2,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Status atual",
        value=criar_bloco_status(status),
        inline=False,
    )

    linhas = []

    for key, acao in ACOES_BASICAS.items():
        linhas.append(
            f"{E(acao['emoji'])} **{acao['label']}**\n"
            f"`-{acao['custo_disposicao']} disposição` • "
            f"{formatar_efeitos(acao['efeitos'])}"
        )

    embed.add_field(
        name="Cuidados básicos",
        value="\n\n".join(linhas),
        inline=False,
    )

    embed.set_footer(text="Baby System • monitor de cuidados")
    return embed
