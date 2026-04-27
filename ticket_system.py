import io
import json
import os
import logging
from datetime import datetime, timezone

import nextcord
from nextcord.ext import tasks

NOIVO_ROLE_ID = 1491166369859764314
NOIVA_ROLE_ID = 1491166441515257927
DEFAULT_LOG_CHANNEL_ID = 1491930461750952108
DEFAULT_REPORT_CHANNEL_ID = 1491172827527778304

FIXED_PANEL_TITLE = "<:tell:1493022801362423931> Report Love"
FIXED_PANEL_DESCRIPTION = (
    "Espaço para ajustes na nossa convivência. O diálogo é a nossa base. "
    "Regras rápidas: Respeito acima de tudo. O que é dito aqui, morre aqui. "
    "Se for urgente, priorize a call. Clique no botão abaixo para abrir um espaço de conversa."
)
FIXED_TICKET_ICON = "<:tell:1493022801362423931>"
FIXED_SELECT_PLACEHOLDER = "Escolha uma opção"

CONFIG_FILE = "ticket_config.json"
STATE_FILE = "ticket_state.json"

_ticket_bot = None
log = logging.getLogger(__name__)


def setup_ticket_system(bot):
    global _ticket_bot
    _ticket_bot = bot


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: str, default: dict) -> dict:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default.copy()

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default.copy()


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_config() -> dict:
    default = {
        "panel_channel_id": DEFAULT_REPORT_CHANNEL_ID,
        "manager_role_id": None,
        "log_channel_id": DEFAULT_LOG_CHANNEL_ID,
        "panel_title": FIXED_PANEL_TITLE,
        "panel_description": FIXED_PANEL_DESCRIPTION,
        "panel_image_url": "",
        "ticket_name": "Report Love",
        "ticket_description": "Abra um ticket para conversar com seu parceiro.",
        "ticket_image_url": "",
        "ticket_icon": FIXED_TICKET_ICON,
        "select_placeholder": FIXED_SELECT_PLACEHOLDER,
    }
    cfg = load_json(CONFIG_FILE, default)

    for key, value in default.items():
        cfg.setdefault(key, value)

    # Mantém o texto e aparência do painel exatamente no padrão solicitado.
    cfg["panel_title"] = FIXED_PANEL_TITLE
    cfg["panel_description"] = FIXED_PANEL_DESCRIPTION
    cfg["ticket_name"] = "Report Love"
    cfg["ticket_icon"] = FIXED_TICKET_ICON
    cfg["select_placeholder"] = FIXED_SELECT_PLACEHOLDER

    save_json(CONFIG_FILE, cfg)
    return cfg


def save_config(cfg: dict) -> None:
    save_json(CONFIG_FILE, cfg)


def load_state() -> dict:
    default = {"tickets": {}}
    state = load_json(STATE_FILE, default)
    state.setdefault("tickets", {})
    save_json(STATE_FILE, state)
    return state


def save_state(state: dict) -> None:
    save_json(STATE_FILE, state)


def get_guild() -> nextcord.Guild | None:
    if _ticket_bot and _ticket_bot.guilds:
        return _ticket_bot.guilds[0]
    return None


def can_manage_ticket(
    user: nextcord.abc.User | nextcord.Member, guild: nextcord.Guild, cfg: dict
) -> bool:
    if not isinstance(user, nextcord.Member):
        return False

    if user.guild_permissions.administrator:
        return True

    manager_role_id = cfg.get("manager_role_id")
    if manager_role_id and any(role.id == manager_role_id for role in user.roles):
        return True

    if any(role.id in (NOIVO_ROLE_ID, NOIVA_ROLE_ID) for role in user.roles):
        return True

    return False


def get_opposite_role_id(member: nextcord.Member) -> int | None:
    role_ids = {role.id for role in member.roles}
    if NOIVA_ROLE_ID in role_ids:
        return NOIVO_ROLE_ID
    if NOIVO_ROLE_ID in role_ids:
        return NOIVA_ROLE_ID
    return None


def format_custom_emoji(raw: str):
    if not raw:
        return "🎫"

    if raw.startswith("<") and raw.endswith(">"):
        return raw

    if raw.startswith(":") and raw.endswith(":"):
        emoji_name = raw.strip(":")
        guild = get_guild()
        if guild is not None:
            emoji = nextcord.utils.get(guild.emojis, name=emoji_name)
            if emoji is not None:
                return emoji

    return raw


def build_panel_embed(cfg: dict) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=cfg["panel_title"],
        description=cfg["panel_description"],
        color=nextcord.Color.from_rgb(255, 105, 180),
        timestamp=utcnow(),
    )
    if cfg.get("panel_image_url"):
        embed.set_image(url=cfg["panel_image_url"])
    return embed


def build_ticket_open_embed(opener: nextcord.Member) -> nextcord.Embed:
    noivo_role = opener.guild.get_role(NOIVO_ROLE_ID)
    noiva_role = opener.guild.get_role(NOIVA_ROLE_ID)

    embed = nextcord.Embed(
        title="💌 Ticket aberto",
        description=(
            f"{opener.mention} abriu este ticket.\n\n"
            f"{noivo_role.mention if noivo_role else '<@&1491166369859764314>'} "
            f"{noiva_role.mention if noiva_role else '<@&1491166441515257927>'}\n\n"
            "Use o botão abaixo quando quiser encerrar este atendimento."
        ),
        color=nextcord.Color.blurple(),
        timestamp=utcnow(),
    )
    if opener.guild.icon:
        embed.set_thumbnail(url=opener.guild.icon.url)
    embed.set_footer(text="Sistema de Tickets Love")
    return embed


def build_resolution_embed() -> nextcord.Embed:
    return nextcord.Embed(
        title="Fechamento do ticket",
        description="Esse atendimento foi resolvido?",
        color=nextcord.Color.orange(),
        timestamp=utcnow(),
    )


def build_rating_embed() -> nextcord.Embed:
    return nextcord.Embed(
        title="Avaliação",
        description="Como seu parceiro te tratou neste atendimento?",
        color=nextcord.Color.purple(),
        timestamp=utcnow(),
    )


def build_script_embed() -> nextcord.Embed:
    return nextcord.Embed(
        title="Finalizar ticket",
        description="Escolha se deseja salvar o script antes de apagar o tópico.",
        color=nextcord.Color.teal(),
        timestamp=utcnow(),
    )


def build_config_embed(cfg: dict, guild: nextcord.Guild) -> nextcord.Embed:
    manager_role = (
        guild.get_role(cfg["manager_role_id"]) if cfg.get("manager_role_id") else None
    )
    panel_channel = (
        guild.get_channel(cfg["panel_channel_id"])
        if cfg.get("panel_channel_id")
        else None
    )
    log_channel = (
        guild.get_channel(cfg["log_channel_id"]) if cfg.get("log_channel_id") else None
    )

    embed = nextcord.Embed(
        title="Configuração de Tickets",
        color=nextcord.Color.from_rgb(255, 105, 180),
        timestamp=utcnow(),
    )
    embed.add_field(
        name="Canal do painel",
        value=panel_channel.mention if panel_channel else "Não definido",
        inline=False,
    )
    embed.add_field(
        name="Canal de logs",
        value=log_channel.mention if log_channel else "Não definido",
        inline=False,
    )
    embed.add_field(
        name="Cargo gestor",
        value=manager_role.mention if manager_role else "Não definido",
        inline=False,
    )
    embed.add_field(name="Título do painel", value=cfg["panel_title"], inline=False)
    embed.add_field(
        name="Descrição do painel", value=cfg["panel_description"], inline=False
    )
    embed.add_field(
        name="Imagem do painel",
        value=cfg["panel_image_url"] or "Sem imagem",
        inline=False,
    )
    embed.add_field(name="Nome do ticket", value=cfg["ticket_name"], inline=False)
    embed.add_field(
        name="Descrição do ticket", value=cfg["ticket_description"], inline=False
    )
    embed.add_field(
        name="Imagem do ticket",
        value=cfg["ticket_image_url"] or "Sem imagem",
        inline=False,
    )
    embed.add_field(name="Ícone", value=cfg["ticket_icon"], inline=False)
    embed.add_field(
        name="Placeholder do seletor", value=cfg["select_placeholder"], inline=False
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="painelconfig")
    return embed


async def send_private_log(
    guild: nextcord.Guild,
    content: str | None = None,
    embed: nextcord.Embed | None = None,
    file: nextcord.File | None = None,
) -> None:
    cfg = load_config()
    channel = guild.get_channel(cfg["log_channel_id"])
    if channel and isinstance(channel, nextcord.TextChannel):
        await channel.send(content=content, embed=embed, file=file)


async def generate_transcript(thread: nextcord.Thread) -> bytes:
    lines: list[str] = []

    async for msg in thread.history(limit=None, oldest_first=True):
        created = msg.created_at.astimezone(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        author = f"{msg.author} ({msg.author.id})"
        content = msg.content if msg.content else "[sem texto]"
        lines.append(f"[{created}] {author}: {content}")

        if msg.attachments:
            for att in msg.attachments:
                lines.append(f"    [anexo] {att.url}")

        if msg.embeds:
            lines.append("    [embed enviada]")

    transcript_text = "\n".join(lines) if lines else "Sem mensagens no ticket."
    return transcript_text.encode("utf-8")


class TicketSelect(nextcord.ui.Select):
    def __init__(self):
        cfg = load_config()

        option = nextcord.SelectOption(
            label=cfg["ticket_name"][:100],
            description=cfg["ticket_description"][:100],
            emoji=format_custom_emoji(cfg["ticket_icon"]),
            value="open_ticket",
        )

        super().__init__(
            placeholder=cfg["select_placeholder"][:150],
            min_values=1,
            max_values=1,
            options=[option],
            custom_id="ticket_panel_select",
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        async def _reply(content: str) -> None:
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(content, ephemeral=True)
                else:
                    await interaction.response.send_message(content, ephemeral=True)
            except nextcord.errors.NotFound:
                # Interaction token expired; avoid bubbling noisy traceback.
                log.warning("Interação de ticket expirou antes da resposta ao usuário.")

        # Acknowledge immediately to avoid 10062 (Unknown interaction)
        # when thread creation or network calls take longer than 3 seconds.
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=True)
            except nextcord.errors.NotFound:
                log.warning("Interação de ticket já expirou ao tentar defer.")

        cfg = load_config()
        guild = interaction.guild

        if guild is None:
            await _reply("Servidor não encontrado.")
            return

        parent = guild.get_channel(cfg["panel_channel_id"])
        if not isinstance(parent, nextcord.TextChannel):
            await _reply("O canal configurado precisa ser um canal de texto.")
            return

        opener = interaction.user
        if not isinstance(opener, nextcord.Member):
            await _reply("Não consegui identificar seu membro.")
            return

        thread_name = f"ticket-{opener.display_name}".lower().replace(" ", "-")[:90]

        starter = await parent.send(f"Abrindo ticket para {opener.mention}...")
        await starter.delete(delay=5)

        thread = await starter.create_thread(
            name=thread_name,
            auto_archive_duration=1440,
        )

        state = load_state()
        state["tickets"][str(thread.id)] = {
            "opener_id": opener.id,
            "created_at": int(utcnow().timestamp()),
            "resolved": None,
            "rating": None,
            "reminder_sent": False,
            "closed_by": None,
            "closed_at": None,
        }
        save_state(state)

        open_embed = build_ticket_open_embed(opener)
        if cfg.get("ticket_image_url"):
            open_embed.set_image(url=cfg["ticket_image_url"])

        view = TicketOpenView(thread.id)
        noivo_role = guild.get_role(NOIVO_ROLE_ID)
        noiva_role = guild.get_role(NOIVA_ROLE_ID)

        await thread.send(
            content=(
                f"{noivo_role.mention if noivo_role else '<@&1491166369859764314>'} "
                f"{noiva_role.mention if noiva_role else '<@&1491166441515257927>'}"
            ),
            embed=open_embed,
            view=view,
            allowed_mentions=nextcord.AllowedMentions(roles=True, users=True),
        )

        await send_private_log(
            guild,
            content=f"[TICKET ABERTO] {opener} abriu {thread.mention} em {utcnow().strftime('%d/%m/%Y %H:%M:%S UTC')}",
        )

        await _reply(f"Seu ticket foi criado: {thread.mention}")


class TicketPanelView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class TicketOpenView(nextcord.ui.View):
    def __init__(self, thread_id: int):
        super().__init__(timeout=None)
        self.thread_id = thread_id

    @nextcord.ui.button(
        label="FECHAR TICKET",
        style=nextcord.ButtonStyle.danger,
        custom_id="ticket_close_button",
    )
    async def close_ticket(self, button, interaction: nextcord.Interaction) -> None:
        cfg = load_config()
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "Servidor não encontrado.", ephemeral=True
            )
            return

        if not can_manage_ticket(interaction.user, guild, cfg):
            await interaction.response.send_message(
                "Você não pode fechar este ticket.", ephemeral=True
            )
            return

        view = ResolutionView(self.thread_id)
        await interaction.response.send_message(
            embed=build_resolution_embed(),
            view=view,
            ephemeral=True,
        )


class ResolutionView(nextcord.ui.View):
    def __init__(self, thread_id: int):
        super().__init__(timeout=300)
        self.thread_id = thread_id

    @nextcord.ui.button(label="RESOLVIDO", style=nextcord.ButtonStyle.success)
    async def resolved(self, button, interaction: nextcord.Interaction) -> None:
        await self._handle_resolution(interaction, True)

    @nextcord.ui.button(label="NÃO RESOLVIDO", style=nextcord.ButtonStyle.secondary)
    async def unresolved(self, button, interaction: nextcord.Interaction) -> None:
        await self._handle_resolution(interaction, False)

    async def _handle_resolution(
        self, interaction: nextcord.Interaction, resolved: bool
    ) -> None:
        state = load_state()
        ticket = state["tickets"].get(str(self.thread_id))

        if ticket is None:
            await interaction.response.send_message(
                "Ticket não encontrado.", ephemeral=True
            )
            return

        ticket["resolved"] = resolved
        ticket["closed_by"] = interaction.user.id
        ticket["closed_at"] = int(utcnow().timestamp())
        save_state(state)

        await interaction.response.send_message(
            embed=build_rating_embed(),
            view=RatingView(self.thread_id),
            ephemeral=True,
        )


class RatingSelect(nextcord.ui.Select):
    def __init__(self, thread_id: int):
        self.thread_id = thread_id
        options = [
            nextcord.SelectOption(label="⭐ 1 estrela", value="1"),
            nextcord.SelectOption(label="⭐⭐ 2 estrelas", value="2"),
            nextcord.SelectOption(label="⭐⭐⭐ 3 estrelas", value="3"),
            nextcord.SelectOption(label="⭐⭐⭐⭐ 4 estrelas", value="4"),
            nextcord.SelectOption(label="⭐⭐⭐⭐⭐ 5 estrelas", value="5"),
        ]
        super().__init__(
            placeholder="Escolha uma nota de 1 a 5",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"ticket_rating_select_{thread_id}",
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        state = load_state()
        ticket = state["tickets"].get(str(self.thread_id))

        if ticket is None:
            await interaction.response.send_message(
                "Ticket não encontrado.", ephemeral=True
            )
            return

        ticket["rating"] = int(self.values[0])
        save_state(state)

        await interaction.response.send_message(
            embed=build_script_embed(),
            view=ScriptActionView(self.thread_id),
            ephemeral=True,
        )


class RatingView(nextcord.ui.View):
    def __init__(self, thread_id: int):
        super().__init__(timeout=300)
        self.add_item(RatingSelect(thread_id))


class ScriptActionView(nextcord.ui.View):
    def __init__(self, thread_id: int):
        super().__init__(timeout=300)
        self.thread_id = thread_id

    @nextcord.ui.button(label="SAVE SCRIPT", style=nextcord.ButtonStyle.success)
    async def save_script(self, button, interaction: nextcord.Interaction) -> None:
        guild = interaction.guild
        channel = interaction.channel

        if guild is None or not isinstance(channel, nextcord.Thread):
            await interaction.response.send_message("Erro no canal.", ephemeral=True)
            return

        state = load_state()
        ticket = state["tickets"].get(str(self.thread_id))

        if ticket is None:
            await interaction.response.send_message(
                "Ticket não encontrado.", ephemeral=True
            )
            return

        transcript_bytes = await generate_transcript(channel)
        opener = guild.get_member(ticket["opener_id"])
        created_ts = ticket["created_at"]
        resolved_text = "Sim" if ticket.get("resolved") is True else "Não"

        embed = nextcord.Embed(
            title="Transcript de Ticket",
            color=nextcord.Color.green(),
            timestamp=utcnow(),
        )
        embed.add_field(name="Criado em", value=f"<t:{created_ts}:F>", inline=False)
        embed.add_field(
            name="Aberto por",
            value=opener.mention if opener else str(ticket["opener_id"]),
            inline=False,
        )
        embed.add_field(name="Resolvido", value=resolved_text, inline=False)

        rating = ticket.get("rating")
        rating_texto = f"{'⭐' * rating} ({rating}/5)" if rating else "Não avaliado"

        embed.add_field(name="Avaliação", value=rating_texto, inline=False)
        embed.add_field(name="Tópico", value=channel.name, inline=False)

        file = nextcord.File(
            io.BytesIO(transcript_bytes), filename=f"ticket-{channel.id}.txt"
        )
        await send_private_log(guild, embed=embed, file=file)

        await interaction.response.send_message(
            "Script salvo. O ticket será apagado.",
            ephemeral=True,
        )

        state["tickets"].pop(str(self.thread_id), None)
        save_state(state)
        await channel.delete()

    @nextcord.ui.button(label="DELETAR", style=nextcord.ButtonStyle.danger)
    async def delete_ticket(self, button, interaction: nextcord.Interaction) -> None:
        guild = interaction.guild
        channel = interaction.channel

        if guild is None or not isinstance(channel, nextcord.Thread):
            await interaction.response.send_message("Erro no canal.", ephemeral=True)
            return

        state = load_state()
        ticket = state["tickets"].get(str(self.thread_id))

        created_ts = ticket["created_at"] if ticket else int(utcnow().timestamp())
        opener_id = ticket["opener_id"] if ticket else 0
        resolved_text = "Sim" if ticket and ticket.get("resolved") is True else "Não"
        rating = ticket.get("rating") if ticket else None
        rating_texto = f"{'⭐' * rating} ({rating}/5)" if rating else "Não avaliado"

        embed = nextcord.Embed(
            title="Ticket apagado sem transcript",
            color=nextcord.Color.red(),
            timestamp=utcnow(),
        )
        embed.add_field(name="Criado em", value=f"<t:{created_ts}:F>", inline=False)
        embed.add_field(name="Aberto por", value=f"<@{opener_id}>", inline=False)
        embed.add_field(name="Resolvido", value=resolved_text, inline=False)
        embed.add_field(name="Avaliação", value=rating_texto, inline=False)
        embed.add_field(name="Tópico", value=channel.name, inline=False)

        await send_private_log(guild, embed=embed)

        await interaction.response.send_message("Ticket apagado.", ephemeral=True)

        state["tickets"].pop(str(self.thread_id), None)
        save_state(state)
        await channel.delete()


@tasks.loop(minutes=5)
async def ticket_reminder_loop() -> None:
    guild = get_guild()
    if guild is None:
        return

    state = load_state()
    now_ts = int(utcnow().timestamp())
    changed = False

    for thread_id, ticket in list(state["tickets"].items()):
        created_at = ticket.get("created_at", 0)
        reminder_sent = ticket.get("reminder_sent", False)

        if reminder_sent or (now_ts - created_at < 2 * 60 * 60):
            continue

        thread = guild.get_thread(int(thread_id))
        if thread is None:
            continue

        opener = guild.get_member(ticket["opener_id"])
        if opener is None:
            continue

        opposite_role_id = get_opposite_role_id(opener)
        if opposite_role_id is None:
            continue

        opposite_role = guild.get_role(opposite_role_id)
        if opposite_role:
            await thread.send(
                content=f"{opposite_role.mention} este ticket está aberto há mais de 2 horas.",
                allowed_mentions=nextcord.AllowedMentions(roles=True),
            )

            for member in opposite_role.members:
                try:
                    await member.send(
                        f"O ticket `{thread.name}` no servidor **{guild.name}** está aberto há mais de 2h."
                    )
                except nextcord.Forbidden:
                    pass

            ticket["reminder_sent"] = True
            changed = True
            await send_private_log(
                guild,
                content=f"[LEMBRETE 2H] Ticket {thread.name} avisado.",
            )

    if changed:
        save_state(state)
