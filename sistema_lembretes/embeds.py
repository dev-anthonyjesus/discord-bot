from datetime import datetime, timedelta

import nextcord

from sistema_lembretes.config import (
    CARGO_NOIVO_ID,
    CARGO_NOIVA_ID,
    EMOJI_GELADEIRA,
    EMOJI_POSTIT_AZUL,
    EMOJI_POSTIT_ROSA,
    EMOJI_MIMO,
    FOOTER_ICON_URL,
    PET_SLEEP_ICON_URL,
    MAX_LEMBRETES_POR_PESSOA,
    RECOMPENSA_PET_MIMOS,
    INTERVALOS_PET_TEXTO,
)
from sistema_lembretes.db import listar_ativos


def mes_pt_br(numero: int) -> str:
    meses = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }
    return meses.get(numero, "Mês")


def hoje_label() -> str:
    hoje = datetime.now()
    return f"Hoje, {hoje.strftime('%d/%m')}"


def amanha_label() -> str:
    amanha = datetime.now() + timedelta(days=1)
    return f"Amanhã, {amanha.strftime('%d/%m')}"


def domingo_label() -> str:
    hoje = datetime.now()
    dias_ate_domingo = (6 - hoje.weekday()) % 7
    domingo = hoje + timedelta(days=dias_ate_domingo)
    return f"Até domingo, {domingo.strftime('%d/%m')}"


def prazo_label(prazo: str) -> str:
    if prazo == "hoje":
        return hoje_label()

    if prazo == "amanha":
        return amanha_label()

    if prazo == "semana":
        return domingo_label()

    return "Sem prazo"


def autor_label(item: dict) -> str:
    autor = item.get("autor")

    if autor == "noivo":
        return f"<@&{CARGO_NOIVO_ID}>"

    if autor == "noiva":
        return f"<@&{CARGO_NOIVA_ID}>"

    return "próprio"


def formatar_linha(item: dict, destino: str) -> str:
    texto = item.get("texto", "").strip()
    item_id = item.get("id")
    prazo = item.get("prazo_label") or prazo_label(item.get("prazo", ""))

    enviado_por_outro = item.get("autor") != destino

    if enviado_por_outro:
        texto_fmt = f'_"{texto}"_'
        autor = autor_label(item)
    else:
        texto_fmt = texto
        autor = "próprio"

    return f"**#{item_id}** {texto_fmt}\n" f"`{prazo}` • {autor}"


def bloco_lembretes(destino: str) -> str:
    ativos = listar_ativos(destino)[:MAX_LEMBRETES_POR_PESSOA]

    if not ativos:
        return "_Nenhum lembrete colado por aqui._"

    linhas = [formatar_linha(item, destino) for item in ativos]

    return "\n\n".join(linhas)


def criar_embed_lembretes() -> nextcord.Embed:
    agora = datetime.now()
    mes_atual = mes_pt_br(agora.month)

    embed = nextcord.Embed(
        title=f"{EMOJI_GELADEIRA} Cole aqui um lembrete",
        description="_Bilhetes rápidos para lembrar do que importa._",
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name=f"{EMOJI_POSTIT_ROSA} Para ela",
        value=bloco_lembretes("noiva"),
        inline=False,
    )

    embed.add_field(
        name=f"{EMOJI_POSTIT_AZUL} Para ele",
        value=bloco_lembretes("noivo"),
        inline=False,
    )

    embed.set_footer(
        text=f"Aproveite e deixa um lanche pros pet | {mes_atual} de {agora.year} - Hoje às {agora.strftime('%H:%M')}",
        icon_url=FOOTER_ICON_URL,
    )

    return embed


def criar_embed_pet_comendo(pets: list[str]) -> nextcord.Embed:
    nomes = {
        "cachorros": "cachorrinhos",
        "gatos": "gatinhos",
    }

    pet_txt = " e ".join(nomes.get(p, p) for p in pets)

    embed = nextcord.Embed(
        title="🍽️ Hora do lanche",
        description=(
            f"Todos os {pet_txt} estão comendo agora.\n"
            "Volte mais tarde para deixar outro lanchinho."
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Recompensa",
        value=f"_{EMOJI_MIMO} você recebeu **{RECOMPENSA_PET_MIMOS} mimos** por alimentar os pet._",
        inline=False,
    )

    embed.set_footer(
        text="Os bichinhos agradecem o carinho.",
        icon_url=PET_SLEEP_ICON_URL,
    )

    return embed


def criar_embed_pet_soneca() -> nextcord.Embed:
    embed = nextcord.Embed(
        title="💤 Barriguinha cheia",
        description=(
            "Os bichinhos estão de barriga cheia e tirando uma soneca.\n"
            "Volte mais tarde para alimentar de novo."
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(
        text="Caminha dos pets",
        icon_url=PET_SLEEP_ICON_URL,
    )

    return embed


def criar_embed_pet_ja_alimentou() -> nextcord.Embed:
    embed = nextcord.Embed(
        title="🐾 Eles já comeram nesse intervalo",
        description=(
            "Você já deixou comida para os pets neste horário.\n"
            "Tenta de novo no próximo intervalo.\n\n"
            f"{INTERVALOS_PET_TEXTO}"
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(
        text="Os bichinhos estão descansando.",
        icon_url=PET_SLEEP_ICON_URL,
    )

    return embed


def criar_embed_pet_fora_horario() -> nextcord.Embed:
    embed = nextcord.Embed(
        title="🐾 Agora não é hora do lanchinho",
        description=(
            "Os pets só comem em horários específicos.\n\n" f"{INTERVALOS_PET_TEXTO}"
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(
        text="Volte no próximo horário de comida.",
        icon_url=PET_SLEEP_ICON_URL,
    )

    return embed


def criar_embed_log_pet(
    user: nextcord.Member, pets: list[str], janela: str
) -> nextcord.Embed:
    nomes = {
        "cachorros": "cachorrinhos",
        "gatos": "gatinhos",
    }

    pet_txt = " e ".join(nomes.get(p, p) for p in pets)

    embed = nextcord.Embed(
        title="🍽️ Pet alimentado",
        description=(
            f"{user.mention} deixou comida para os **{pet_txt}**.\n"
            f"Janela: `{janela}`\n"
            f"Recompensa: {EMOJI_MIMO} **{RECOMPENSA_PET_MIMOS} mimos**"
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(
        text="Geladeira dos lembretes",
        icon_url=PET_SLEEP_ICON_URL,
    )

    return embed
