import asyncio
import logging

import nextcord
from nextcord.ui import View, Select, Button

from sistema_ticket.config import load_config
from sistema_ticket.embeds import build_ticket_embed

log = logging.getLogger(__name__)


async def enviar_log(guild: nextcord.Guild, texto: str):
    cfg = load_config()
    canal = guild.get_channel(cfg.get("log_channel_id"))

    if canal:
        await canal.send(texto)


def nome_ticket(user: nextcord.Member) -> str:
    nome = user.display_name.lower()

    limpo = ""

    for c in nome:
        if c.isalnum() or c in "-_":
            limpo += c
        elif c == " ":
            limpo += "-"

    limpo = limpo.strip("-_")[:20]

    if not limpo:
        limpo = str(user.id)

    return f"ticket-{limpo}"


class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(
        label="Fechar ticket",
        style=nextcord.ButtonStyle.red,
        custom_id="ticket_close_button",
        emoji="🔒",
    )
    async def fechar(self, button: Button, interaction: nextcord.Interaction):
        cfg = load_config()
        manager_role = interaction.guild.get_role(cfg.get("manager_role_id"))

        pode_fechar = interaction.user.guild_permissions.administrator

        if manager_role and manager_role in interaction.user.roles:
            pode_fechar = True

        if not pode_fechar:
            await interaction.response.send_message(
                "❌ Apenas administradores ou gestores podem fechar este ticket.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "🔒 Ticket será fechado em 5 segundos.",
            ephemeral=True,
        )

        await enviar_log(
            interaction.guild,
            f"[TICKET] {interaction.user.mention} fechou {interaction.channel.mention}.",
        )

        await asyncio.sleep(5)

        try:
            await interaction.channel.delete(
                reason=f"Ticket fechado por {interaction.user}"
            )
        except Exception as e:
            log.error(f"Erro ao deletar ticket: {e}")


class TicketSelect(Select):
    def __init__(self):
        cfg = load_config()

        options = [
            nextcord.SelectOption(
                label=cfg.get("ticket_name", "Report Love")[:100],
                value="abrir_ticket",
                description="Abrir um espaço privado de conversa",
                emoji=cfg.get("ticket_icon", "💗"),
            )
        ]

        super().__init__(
            placeholder=cfg.get("select_placeholder", "Escolha uma opção")[:100],
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select_menu",
        )

    async def callback(self, interaction: nextcord.Interaction):
        if self.values[0] != "abrir_ticket":
            await interaction.response.send_message(
                "❌ Opção inválida.",
                ephemeral=True,
            )
            return

        cfg = load_config()
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            await interaction.response.send_message(
                "❌ Esse comando só funciona em servidor.",
                ephemeral=True,
            )
            return

        nome = nome_ticket(user)

        existente = nextcord.utils.get(guild.text_channels, name=nome)

        if existente:
            await interaction.response.send_message(
                f"⚠️ Você já tem um ticket aberto: {existente.mention}",
                ephemeral=True,
            )
            return

        manager_role = guild.get_role(cfg.get("manager_role_id"))

        overwrites = {
            guild.default_role: nextcord.PermissionOverwrite(view_channel=False),
            user: nextcord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            guild.me: nextcord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True,
            ),
        }

        if manager_role:
            overwrites[manager_role] = nextcord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            )

        category = interaction.channel.category

        canal = await guild.create_text_channel(
            name=nome,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket aberto por {user}",
        )

        embed = build_ticket_embed(cfg, user)
        mention_gestor = manager_role.mention if manager_role else ""

        await canal.send(
            content=f"{user.mention} {mention_gestor}",
            embed=embed,
            view=TicketCloseView(),
        )

        await enviar_log(
            guild,
            f"[TICKET] {user.mention} abriu {canal.mention}.",
        )

        await interaction.response.send_message(
            f"✅ Ticket aberto: {canal.mention}",
            ephemeral=True,
        )


class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())
