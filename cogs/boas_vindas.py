"""Cog: embed fixa de boas-vindas."""

import logging

import nextcord
from nextcord.ext import commands

from utils.constants import CANAL_WELCOME
from utils.panels import send_or_update_panel

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# IDs
# ─────────────────────────────────────────────────────────────

CARGO_VISITANTE_ID = 1492321990743162990
CARGO_NOIVO_ID = 1491166369859764314
CARGO_NOIVA_ID = 1491166441515257927

FOOTER_ICON_URL = (
    "https://i.pinimg.com/736x/4d/b7/f8/" "4db7f8881653225e19760f86e1f0c0c0.jpg"
)


# ─────────────────────────────────────────────────────────────
# Emojis
# ─────────────────────────────────────────────────────────────
# Para evitar aparecer ID quebrado na embed, deixei emojis normais.
# Depois, se você quiser, a gente troca por emoji customizado no formato correto:
# <:nome_do_emoji:ID_DO_EMOJI>

EMOJI_BELLHOP = "🔔"
EMOJI_LULI = "💖"
EMOJI_AV = "✨"


def create_welcome_embed() -> nextcord.Embed:
    visitante = f"<@&{CARGO_VISITANTE_ID}>"
    noivo = f"<@&{CARGO_NOIVO_ID}>"
    noiva = f"<@&{CARGO_NOIVA_ID}>"

    embed = nextcord.Embed(
        title=f"{EMOJI_BELLHOP} Bem vindo",
        description=(
            "_Abrimos as portas para uma nova fase!_\n\n"
            f'_"Olá {visitante}, este **lar** é o reflexo da nossa união '
            "e de cada passo que demos juntos. É uma alegria imensa receber você "
            "aqui para celebrar o início deste novo capítulo. Entre e sinta-se "
            f'parte da nossa família!"_ {EMOJI_LULI} {EMOJI_AV}'
        ),
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Sinta-se à vontade",
        value="Qualquer dúvida, não hesite em chamar.",
        inline=False,
    )

    embed.set_footer(
        text=f"Mensagem enviada pelo casal {noivo} {noiva}",
        icon_url=FOOTER_ICON_URL,
    )

    return embed


class BoasVindasCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_once = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ready_once:
            return

        self._ready_once = True

        try:
            await send_or_update_panel(
                bot=self.bot,
                channel_id=CANAL_WELCOME,
                panel_key="welcome_panel",
                embed=create_welcome_embed(),
                view=None,
            )

            log.info("[OK] Painel fixo de boas-vindas enviado/atualizado sem spam.")
        except Exception as e:
            log.error(f"[ERRO] Erro no painel fixo de boas-vindas: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(BoasVindasCog(bot))
