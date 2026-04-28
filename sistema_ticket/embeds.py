import nextcord

from sistema_ticket.config import DEFAULT_CONFIG


def build_panel_embed(cfg: dict) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=cfg.get("panel_title", DEFAULT_CONFIG["panel_title"]),
        description=cfg.get("panel_description", DEFAULT_CONFIG["panel_description"]),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    image_url = cfg.get("panel_image_url")
    if image_url:
        embed.set_image(url=image_url)

    embed.set_footer(text="Painel fixo de tickets")
    return embed


def build_ticket_embed(cfg: dict, user: nextcord.Member) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=cfg.get("ticket_name", DEFAULT_CONFIG["ticket_name"]),
        description=cfg.get("ticket_description", DEFAULT_CONFIG["ticket_description"]),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Aberto por",
        value=user.mention,
        inline=False,
    )

    image_url = cfg.get("ticket_image_url")
    if image_url:
        embed.set_image(url=image_url)

    if user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)

    embed.set_footer(text="Ticket privado")
    return embed


def build_config_embed(cfg: dict, guild: nextcord.Guild) -> nextcord.Embed:
    panel_channel = guild.get_channel(cfg.get("panel_channel_id"))
    log_channel = guild.get_channel(cfg.get("log_channel_id"))
    manager_role = guild.get_role(cfg.get("manager_role_id"))

    embed = nextcord.Embed(
        title="⚙️ Configuração atual do ticket",
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Canal do painel",
        value=panel_channel.mention if panel_channel else "`não encontrado`",
        inline=False,
    )

    embed.add_field(
        name="Cargo gestor",
        value=manager_role.mention if manager_role else "`não encontrado`",
        inline=False,
    )

    embed.add_field(
        name="Canal de logs",
        value=log_channel.mention if log_channel else "`não encontrado`",
        inline=False,
    )

    embed.add_field(
        name="Título do painel",
        value=cfg.get("panel_title", "sem título")[:1024],
        inline=False,
    )

    embed.add_field(
        name="Descrição do painel",
        value=cfg.get("panel_description", "sem descrição")[:1024],
        inline=False,
    )

    embed.add_field(
        name="Nome do ticket",
        value=cfg.get("ticket_name", "sem nome")[:1024],
        inline=False,
    )

    embed.add_field(
        name="Placeholder",
        value=cfg.get("select_placeholder", "sem placeholder")[:1024],
        inline=False,
    )

    return embed
