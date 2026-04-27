"""Cog: Reação automática a mídias e comando reagirmidias."""
import logging

import nextcord
from nextcord.ext import commands

from utils.constants import CATEGORIA_MIDIA_ID, CANAIS_REACAO, EMOJI_CHECK_ID

log = logging.getLogger(__name__)


def mensagem_tem_midia(message: nextcord.Message) -> bool:
    if message.attachments or message.embeds:
        return True
    content_lower = message.content.lower()
    media_exts = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov", ".webm")
    return ("http://" in content_lower or "https://" in content_lower) and any(
        ext in content_lower for ext in media_exts
    )


class MidiaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.author.bot:
            return

        if not mensagem_tem_midia(message):
            return

        if not isinstance(message.channel, nextcord.TextChannel):
            return

        try:
            categoria = message.channel.category
            if categoria and categoria.id == CATEGORIA_MIDIA_ID:
                emoji = self.bot.get_emoji(EMOJI_CHECK_ID)
                if emoji and not any(str(r.emoji) == str(emoji) for r in message.reactions):
                    await message.add_reaction(emoji)

            if message.channel.id in CANAIS_REACAO:
                emoji2 = self.bot.get_emoji(CANAIS_REACAO[message.channel.id])
                if emoji2 and not any(str(r.emoji) == str(emoji2) for r in message.reactions):
                    await message.add_reaction(emoji2)

        except Exception as e:
            log.error(f"Erro ao reagir automaticamente: {e}")

    @commands.command()
    async def reagirmidias(self, ctx: commands.Context):
        """Adiciona reações a mídias históricas da categoria de mídia."""
        await ctx.send("⏳ Vou começar a reagir as mídias antigas da categoria.")
        try:
            await self._reagir_historico()
            await ctx.send("✅ Reações antigas concluídas.")
        except Exception as e:
            await ctx.send(f"❌ Erro ao reagir mídias antigas: {e}")

    async def _reagir_historico(self):
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            return

        categoria = guild.get_channel(CATEGORIA_MIDIA_ID)
        if not categoria or not isinstance(categoria, nextcord.CategoryChannel):
            log.warning("Categoria de mídia não encontrada.")
            return

        emoji = self.bot.get_emoji(EMOJI_CHECK_ID)
        if not emoji:
            log.warning("Emoji check não encontrado.")
            return

        for canal in categoria.text_channels:
            try:
                async for message in canal.history(limit=None, oldest_first=True):
                    if message.author.bot or not mensagem_tem_midia(message):
                        continue
                    if not any(str(r.emoji) == str(emoji) for r in message.reactions):
                        try:
                            await message.add_reaction(emoji)
                        except Exception as e:
                            log.error(f"Erro ao reagir em {canal.name}: {e}")
            except Exception as e:
                log.error(f"Erro ao ler histórico de {canal.name}: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(MidiaCog(bot))
