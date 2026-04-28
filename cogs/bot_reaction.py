"""Cog: reações automáticas em canais de mídia e vitrine."""

import logging

import nextcord
from nextcord.ext import commands

log = logging.getLogger(__name__)


# Categoria onde todos os canais recebem check.
CATEGORIA_MIDIA_ID = 1491169377217941675

# Categoria Vitrine.
CATEGORIA_VITRINE_ID = 1491169765551505551

# Emoji check para toda categoria de mídia.
EMOJI_CHECK_ID = 1498700421945102587


# Reações específicas por canal da vitrine.
CANAIS_VITRINE_REACAO = {
    1494060035431600312: 1498474497953632318,  # print -> pixelc
    1492357739588878449: 1492415234605060160,  # presente -> gift
    1491192043672830084: 1493059522594607164,  # cinema -> pipoca
    1491169251459862799: 1493059465958653982,  # memes -> kaka
    1496358911148687535: 1496536467953029120,  # ts4
    1491169795398176889: 1498474680372170793,  # receita
    1496192134729040063: 1434660502180462716,  # sex
    1491169848250597769: 1494093082667257866,  # ideia date -> malas
}


def mensagem_tem_midia(message: nextcord.Message) -> bool:
    if message.attachments:
        return True

    if message.embeds:
        return True

    content_lower = message.content.lower()

    media_exts = (
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".mp4",
        ".mov",
        ".webm",
    )

    tem_link = "http://" in content_lower or "https://" in content_lower
    tem_extensao = any(ext in content_lower for ext in media_exts)

    return tem_link and tem_extensao


def ja_tem_reacao(message: nextcord.Message, emoji) -> bool:
    return any(str(reaction.emoji) == str(emoji) for reaction in message.reactions)


async def adicionar_reacao_se_precisar(message: nextcord.Message, emoji) -> bool:
    if emoji is None:
        return False

    if ja_tem_reacao(message, emoji):
        return False

    await message.add_reaction(emoji)
    return True


class BotReactionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("[OK] Sistema de reação automática carregado.")

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.author.bot:
            return

        if not isinstance(message.channel, nextcord.TextChannel):
            return

        if not mensagem_tem_midia(message):
            return

        try:
            categoria = message.channel.category

            # Categoria de mídia: todos os canais recebem check.
            if categoria and categoria.id == CATEGORIA_MIDIA_ID:
                emoji_check = self.bot.get_emoji(EMOJI_CHECK_ID)

                adicionou = await adicionar_reacao_se_precisar(
                    message,
                    emoji_check,
                )

                if adicionou:
                    log.info(
                        f"[OK] Check adicionado em #{message.channel.name} | msg={message.id}"
                    )

                return

            # Categoria vitrine ou canais mapeados: cada canal recebe seu emoji.
            if (
                categoria
                and categoria.id == CATEGORIA_VITRINE_ID
                and message.channel.id in CANAIS_VITRINE_REACAO
            ):
                emoji_id = CANAIS_VITRINE_REACAO[message.channel.id]
                emoji = self.bot.get_emoji(emoji_id)

                adicionou = await adicionar_reacao_se_precisar(
                    message,
                    emoji,
                )

                if adicionou:
                    log.info(
                        f"[OK] Reação vitrine adicionada em #{message.channel.name} | msg={message.id}"
                    )

                return

            # Segurança: se o canal estiver no mapa mesmo fora da categoria, reage também.
            if message.channel.id in CANAIS_VITRINE_REACAO:
                emoji_id = CANAIS_VITRINE_REACAO[message.channel.id]
                emoji = self.bot.get_emoji(emoji_id)

                adicionou = await adicionar_reacao_se_precisar(
                    message,
                    emoji,
                )

                if adicionou:
                    log.info(
                        f"[OK] Reação por canal adicionada em #{message.channel.name} | msg={message.id}"
                    )

        except Exception as e:
            log.error(f"[ERRO] Erro ao reagir automaticamente: {type(e).__name__}: {e}")

    @commands.command(name="reagirmidias")
    @commands.has_permissions(administrator=True)
    async def reagirmidias(self, ctx: commands.Context):
        await ctx.send("⏳ Vou começar a reagir mídias antigas. Isso pode demorar.")

        try:
            total = await self._reagir_historico()

            await ctx.send(
                f"✅ Reações antigas concluídas. Total de reações adicionadas: `{total}`"
            )
        except Exception as e:
            log.error(f"[ERRO] Erro ao reagir mídias antigas: {type(e).__name__}: {e}")

            await ctx.send(
                f"❌ Erro ao reagir mídias antigas:\n`{type(e).__name__}: {e}`"
            )

    async def _reagir_historico(self) -> int:
        total_reacoes = 0

        guild = self.bot.guilds[0] if self.bot.guilds else None

        if not guild:
            log.warning("[AVISO] Nenhum servidor encontrado.")
            return total_reacoes

        emoji_check = self.bot.get_emoji(EMOJI_CHECK_ID)

        categoria_midia = guild.get_channel(CATEGORIA_MIDIA_ID)

        if categoria_midia and isinstance(categoria_midia, nextcord.CategoryChannel):
            for canal in categoria_midia.text_channels:
                total_reacoes += await self._reagir_historico_canal(
                    canal=canal,
                    emoji=emoji_check,
                    label="midia_check",
                )
        else:
            log.warning("[AVISO] Categoria de mídia não encontrada.")

        for canal_id, emoji_id in CANAIS_VITRINE_REACAO.items():
            canal = guild.get_channel(canal_id)
            emoji = self.bot.get_emoji(emoji_id)

            if not isinstance(canal, nextcord.TextChannel):
                log.warning(f"[AVISO] Canal de vitrine não encontrado: {canal_id}")
                continue

            total_reacoes += await self._reagir_historico_canal(
                canal=canal,
                emoji=emoji,
                label="vitrine",
            )

        return total_reacoes

    async def _reagir_historico_canal(
        self,
        canal: nextcord.TextChannel,
        emoji,
        label: str,
    ) -> int:
        total = 0

        if emoji is None:
            log.warning(f"[AVISO] Emoji não encontrado para #{canal.name}.")
            return total

        try:
            async for message in canal.history(limit=None, oldest_first=True):
                if message.author.bot:
                    continue

                if not mensagem_tem_midia(message):
                    continue

                try:
                    adicionou = await adicionar_reacao_se_precisar(
                        message,
                        emoji,
                    )

                    if adicionou:
                        total += 1

                except Exception as e:
                    log.error(
                        f"[ERRO] Falha ao reagir mensagem {message.id} em #{canal.name}: {e}"
                    )

            log.info(
                f"[OK] Histórico processado em #{canal.name} | tipo={label} | total={total}"
            )

        except Exception as e:
            log.error(f"[ERRO] Erro ao ler histórico de #{canal.name}: {e}")

        return total


def setup(bot: commands.Bot):
    bot.add_cog(BotReactionCog(bot))
