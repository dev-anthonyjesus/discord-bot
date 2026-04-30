import asyncio
import io
import logging
from datetime import datetime

import nextcord
from nextcord.ui import View, Select, Button

from sistema_ticket.config import load_config

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Configurações do casal
# ─────────────────────────────────────────────────────────────

CARGO_NOIVO_ID = 1491166369859764314
CARGO_NOIVA_ID = 1491166441515257927

EMOJI_CAFE = "<:cafe:1492348154316587219>"
EMOJI_ESTRELA = nextcord.PartialEmoji(name="⭐")


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def usuario_tem_cargo_ticket(member: nextcord.Member) -> bool:
    cargos_permitidos = {CARGO_NOIVO_ID, CARGO_NOIVA_ID}
    return any(role.id in cargos_permitidos for role in member.roles)


def cargo_casal_do_usuario(member: nextcord.Member) -> tuple[str, int, str]:
    role_ids = {role.id for role in member.roles}

    if CARGO_NOIVO_ID in role_ids:
        return "noivo", CARGO_NOIVO_ID, f"<@&{CARGO_NOIVO_ID}>"

    if CARGO_NOIVA_ID in role_ids:
        return "noiva", CARGO_NOIVA_ID, f"<@&{CARGO_NOIVA_ID}>"

    return "casal", 0, member.mention


def nome_topico_ticket(user: nextcord.Member) -> str:
    nome_cargo, _, _ = cargo_casal_do_usuario(user)
    return f"🎫report-{nome_cargo}"


async def enviar_log(
    guild: nextcord.Guild,
    texto: str | None = None,
    embed: nextcord.Embed | None = None,
    file: nextcord.File | None = None,
):
    cfg = load_config()
    canal = guild.get_channel(cfg.get("log_channel_id"))

    if canal:
        await canal.send(content=texto, embed=embed, file=file)


def criar_log_embed(
    titulo: str,
    descricao: str,
    color: int = 0xFF69B4,
) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=titulo,
        description=descricao,
        color=color,
        timestamp=nextcord.utils.utcnow(),
    )
    embed.set_footer(text="Sistema de tickets")
    return embed


def embed_log_abertura(cargo_mention: str, topico) -> nextcord.Embed:
    return criar_log_embed(
        titulo="📣 Ticket aberto",
        descricao=(
            f"**Aberto por:** {cargo_mention}\n" f"**Tópico:** {topico.mention}"
        ),
        color=0xFF69B4,
    )


def embed_log_fechamento(
    titulo: str,
    topico_nome: str,
    fechado_por: nextcord.Member,
    status: str,
    nota: int,
    salvou_script: bool,
) -> nextcord.Embed:
    cor = 0x2ECC71 if status == "Resolvido" else 0xE74C3C
    estrelas = "⭐" * nota
    script_txt = "Sim" if salvou_script else "Não"

    return criar_log_embed(
        titulo=titulo,
        descricao=(
            f"**Tópico:** `{topico_nome}`\n"
            f"**Fechado por:** {fechado_por.mention}\n"
            f"**Status:** **{status}**\n"
            f"**Nota:** **{nota}/5** {estrelas}\n"
            f"**Script salvo:** **{script_txt}**"
        ),
        color=cor,
    )


def formatar_data(dt) -> str:
    if dt is None:
        return "Data desconhecida"

    try:
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(dt)


def criar_embed_ticket(cargo_mention: str, user: nextcord.Member) -> nextcord.Embed:
    embed = nextcord.Embed(
        title="☎️ Report Love",
        description=(
            "Esse ticket foi aberto para resolver algum problema casual. "
            "Por favor, espere o outro responder e seja paciente.\n\n"
            "Caso seja algo sério, priorize uma ligação quando o outro estiver disponível. "
            f"Sente-se, sirva-se de um café {EMOJI_CAFE} e elabore seu problema "
            "para trazer para o outro."
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Aberto por",
        value=cargo_mention,
        inline=False,
    )

    if user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)

    embed.set_footer(text="Ticket privado")
    return embed


async def gerar_transcricao_ticket(
    canal,
    fechado_por: nextcord.Member,
    status_resolvido: str,
    nota: int,
) -> nextcord.File:
    mensagens = []

    async for msg in canal.history(limit=None, oldest_first=True):
        autor = f"{msg.author} ({msg.author.id})"
        data = formatar_data(msg.created_at)

        conteudo = msg.content or ""

        if msg.attachments:
            anexos = "\n".join(a.url for a in msg.attachments)
            conteudo += f"\n[ANEXOS]\n{anexos}"

        if msg.embeds:
            conteudo += f"\n[EMBEDS] {len(msg.embeds)} embed(s)"

        if not conteudo.strip():
            conteudo = "[mensagem sem texto]"

        mensagens.append(f"[{data}] {autor}\n" f"{conteudo}\n")

    estrelas = "⭐" * nota

    texto = (
        "============================================================\n"
        "                    SCRIPT DO TICKET\n"
        "============================================================\n\n"
        f"Tópico: #{canal.name}\n"
        f"Tópico ID: {canal.id}\n"
        f"Fechado por: {fechado_por} ({fechado_por.id})\n"
        f"Status: {status_resolvido}\n"
        f"Avaliação: {nota}/5 {estrelas}\n"
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        "============================================================\n"
        "                         MENSAGENS\n"
        "============================================================\n\n"
        + "\n".join(mensagens)
    )

    nome_arquivo = f"script-{canal.name}-{canal.id}.txt"
    buffer = io.BytesIO(texto.encode("utf-8"))
    buffer.seek(0)

    return nextcord.File(buffer, filename=nome_arquivo)


async def fechar_topico_ou_deletar(canal):
    """
    Fecha o ticket.

    Em tópicos, tenta arquivar e bloquear.
    Algumas versões do nextcord não aceitam `reason` em Thread.edit/delete.
    """
    try:
        if isinstance(canal, nextcord.Thread):
            await canal.edit(archived=True, locked=True)
            return
    except Exception as e:
        log.error(f"Erro ao arquivar/bloquear tópico: {e}")

    try:
        await canal.delete()
    except Exception as e:
        log.error(f"Erro ao deletar ticket/tópico: {e}")


# ─────────────────────────────────────────────────────────────
# Fechamento: salvar script ou não
# ─────────────────────────────────────────────────────────────


class TicketFinalizarView(View):
    def __init__(self, owner_id: int, status_resolvido: str, nota: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.status_resolvido = status_resolvido
        self.nota = nota

    async def _validar_dono(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu este ticket pode finalizar.",
                ephemeral=True,
            )
            return False

        return True

    @nextcord.ui.button(
        label="Salvar script e fechar",
        style=nextcord.ButtonStyle.green,
        emoji="📄",
    )
    async def salvar_script(self, button: Button, interaction: nextcord.Interaction):
        if not await self._validar_dono(interaction):
            return

        await interaction.response.send_message(
            "📄 Salvando script e fechando o tópico em 5 segundos...",
            ephemeral=True,
        )

        arquivo = None

        try:
            arquivo = await gerar_transcricao_ticket(
                canal=interaction.channel,
                fechado_por=interaction.user,
                status_resolvido=self.status_resolvido,
                nota=self.nota,
            )
        except Exception as e:
            log.error(f"Erro ao gerar script do ticket: {e}")

        embed = embed_log_fechamento(
            titulo="📄 Ticket fechado com script",
            topico_nome=interaction.channel.name,
            fechado_por=interaction.user,
            status=self.status_resolvido,
            nota=self.nota,
            salvou_script=True,
        )

        await enviar_log(
            interaction.guild,
            embed=embed,
            file=arquivo,
        )

        await asyncio.sleep(5)

        await fechar_topico_ou_deletar(interaction.channel)

    @nextcord.ui.button(
        label="Não salvar e fechar",
        style=nextcord.ButtonStyle.red,
        emoji="🗑️",
    )
    async def nao_salvar(self, button: Button, interaction: nextcord.Interaction):
        if not await self._validar_dono(interaction):
            return

        await interaction.response.send_message(
            "🗑️ Ticket será fechado sem salvar script em 5 segundos.",
            ephemeral=True,
        )

        embed = embed_log_fechamento(
            titulo="🗑️ Ticket fechado sem script",
            topico_nome=interaction.channel.name,
            fechado_por=interaction.user,
            status=self.status_resolvido,
            nota=self.nota,
            salvou_script=False,
        )

        await enviar_log(
            interaction.guild,
            embed=embed,
        )

        await asyncio.sleep(5)

        await fechar_topico_ou_deletar(interaction.channel)


# ─────────────────────────────────────────────────────────────
# Avaliação com emoji de estrela
# ─────────────────────────────────────────────────────────────


class NotaTicketSelect(Select):
    def __init__(self, owner_id: int, status_resolvido: str):
        self.owner_id = owner_id
        self.status_resolvido = status_resolvido

        options = [
            nextcord.SelectOption(
                label="1 estrela",
                value="1",
                description="Muito ruim",
                emoji=EMOJI_ESTRELA,
            ),
            nextcord.SelectOption(
                label="2 estrelas",
                value="2",
                description="Ruim",
                emoji=EMOJI_ESTRELA,
            ),
            nextcord.SelectOption(
                label="3 estrelas",
                value="3",
                description="Mediano",
                emoji=EMOJI_ESTRELA,
            ),
            nextcord.SelectOption(
                label="4 estrelas",
                value="4",
                description="Bom",
                emoji=EMOJI_ESTRELA,
            ),
            nextcord.SelectOption(
                label="5 estrelas",
                value="5",
                description="Excelente",
                emoji=EMOJI_ESTRELA,
            ),
        ]

        super().__init__(
            placeholder="Avalie este ticket de 1 a 5 estrelas",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: nextcord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu este ticket pode avaliar.",
                ephemeral=True,
            )
            return

        nota = int(self.values[0])

        embed = nextcord.Embed(
            title="📄 Salvar script do ticket?",
            description=(
                f"Status escolhido: **{self.status_resolvido}**\n"
                f"Avaliação: **{nota}/5** {'⭐' * nota}\n\n"
                "Você deseja salvar a conversa em um arquivo `.txt` antes de fechar?"
            ),
            color=0xFF69B4,
        )

        await interaction.response.send_message(
            embed=embed,
            view=TicketFinalizarView(
                owner_id=self.owner_id,
                status_resolvido=self.status_resolvido,
                nota=nota,
            ),
            ephemeral=True,
        )


class NotaTicketView(View):
    def __init__(self, owner_id: int, status_resolvido: str):
        super().__init__(timeout=180)
        self.add_item(NotaTicketSelect(owner_id, status_resolvido))


# ─────────────────────────────────────────────────────────────
# Status resolvido/não resolvido
# ─────────────────────────────────────────────────────────────


class StatusTicketView(View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def _validar_dono(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu este ticket pode responder.",
                ephemeral=True,
            )
            return False

        return True

    @nextcord.ui.button(
        label="Resolvido",
        style=nextcord.ButtonStyle.green,
        emoji="✅",
    )
    async def resolvido(self, button: Button, interaction: nextcord.Interaction):
        if not await self._validar_dono(interaction):
            return

        await interaction.response.send_message(
            "✅ Ticket marcado como **resolvido**. Agora escolha uma nota:",
            view=NotaTicketView(self.owner_id, "Resolvido"),
            ephemeral=True,
        )

    @nextcord.ui.button(
        label="Não resolvido",
        style=nextcord.ButtonStyle.red,
        emoji="❌",
    )
    async def nao_resolvido(self, button: Button, interaction: nextcord.Interaction):
        if not await self._validar_dono(interaction):
            return

        await interaction.response.send_message(
            "❌ Ticket marcado como **não resolvido**. Agora escolha uma nota:",
            view=NotaTicketView(self.owner_id, "Não resolvido"),
            ephemeral=True,
        )


# ─────────────────────────────────────────────────────────────
# Botão principal de fechar
# ─────────────────────────────────────────────────────────────


class TicketCloseView(View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @nextcord.ui.button(
        label="Fechar ticket",
        style=nextcord.ButtonStyle.red,
        custom_id="ticket_close_button",
        emoji="🔒",
    )
    async def fechar(self, button: Button, interaction: nextcord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu este ticket pode fechar.",
                ephemeral=True,
            )
            return

        embed = nextcord.Embed(
            title="🔒 Fechamento do ticket",
            description="Antes de fechar, escolha se o ticket foi resolvido ou não.",
            color=0xFF69B4,
        )

        await interaction.response.send_message(
            embed=embed,
            view=StatusTicketView(self.owner_id),
            ephemeral=True,
        )


# ─────────────────────────────────────────────────────────────
# Select do painel
# ─────────────────────────────────────────────────────────────


class TicketSelect(Select):
    def __init__(self):
        cfg = load_config()

        options = [
            nextcord.SelectOption(
                label=cfg.get("ticket_name", "Report Love")[:100],
                value="abrir_ticket",
                description="Abrir um tópico privado de conversa",
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

        guild = interaction.guild
        user = interaction.user

        if guild is None:
            await interaction.response.send_message(
                "❌ Esse comando só funciona em servidor.",
                ephemeral=True,
            )
            return

        if not isinstance(user, nextcord.Member):
            await interaction.response.send_message(
                "❌ Não consegui identificar seus cargos.",
                ephemeral=True,
            )
            return

        if not usuario_tem_cargo_ticket(user):
            await interaction.response.send_message(
                (
                    "❌ Apenas os cargos "
                    f"<@&{CARGO_NOIVO_ID}> e <@&{CARGO_NOIVA_ID}> "
                    "podem abrir ticket."
                ),
                ephemeral=True,
            )
            return

        nome = nome_topico_ticket(user)
        nome_cargo, cargo_id, cargo_mention = cargo_casal_do_usuario(user)

        canal_painel = interaction.channel

        if not isinstance(canal_painel, nextcord.TextChannel):
            await interaction.response.send_message(
                "❌ Este painel precisa estar em um canal de texto para criar tópico.",
                ephemeral=True,
            )
            return

        topicos_ativos = list(canal_painel.threads)
        existente = nextcord.utils.get(topicos_ativos, name=nome)

        if existente:
            await interaction.response.send_message(
                f"⚠️ Já existe um tópico aberto: {existente.mention}",
                ephemeral=True,
            )
            return

        embed = criar_embed_ticket(cargo_mention, user)

        conteudo_inicial = f"📣 | Bem-vindos <@&{CARGO_NOIVO_ID}> <@&{CARGO_NOIVA_ID}>"

        try:
            topico = await canal_painel.create_thread(
                name=nome,
                type=nextcord.ChannelType.private_thread,
                invitable=False,
                reason=f"Ticket aberto por {user}",
            )
        except Exception as e:
            log.error(f"Erro ao criar tópico privado: {e}")

            try:
                topico = await canal_painel.create_thread(
                    name=nome,
                    type=nextcord.ChannelType.public_thread,
                    reason=f"Ticket aberto por {user}",
                )
            except Exception as erro_publico:
                log.error(f"Erro ao criar tópico público: {erro_publico}")
                await interaction.response.send_message(
                    (
                        "❌ Não consegui criar o tópico do ticket.\n"
                        f"`{type(erro_publico).__name__}: {erro_publico}`"
                    ),
                    ephemeral=True,
                )
                return

        try:
            await topico.add_user(user)
        except Exception:
            pass

        await topico.send(
            content=conteudo_inicial,
            embed=embed,
            view=TicketCloseView(owner_id=user.id),
        )

        embed_log = embed_log_abertura(cargo_mention, topico)

        await enviar_log(
            guild,
            embed=embed_log,
        )

        await interaction.response.send_message(
            f"✅ Ticket aberto: {topico.mention}",
            ephemeral=True,
        )


class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())
