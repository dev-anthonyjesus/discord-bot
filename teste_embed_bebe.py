import os

import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

CANAL_LOG_ID = 1491930461750952108


intents = nextcord.Intents.default()
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)


def criar_embed_teste_bebe() -> nextcord.Embed:
    embed = nextcord.Embed(
        title="🍼 Baby Luna — Painel de Cuidados",
        description=(
            "```ansi\n"
            "\u001b[1;35mStatus geral do bebê\u001b[0m\n"
            "```\n"
            "Um painel experimental para visualizar atributos, cuidados, itens e humor."
        ),
        color=0xFF69B4,
    )

    embed.add_field(
        name="__Stats__",
        value=(
            "```ansi\n"
            "❤️ Fome: \u001b[33m72\u001b[0m/100\n"
            "💤 Sono: \u001b[34m48\u001b[0m/100\n"
            "🧼 Higiene: \u001b[32m85\u001b[0m/100\n"
            "🧸 Atenção: \u001b[31m22\u001b[0m/100\n"
            "😊 Humor: \u001b[35mCarente\u001b[0m\n"
            "```"
        ),
        inline=False,
    )

    embed.add_field(
        name="__Cuidados de hoje__",
        value=(
            "```ansi\n"
            "\u001b[32m✓\u001b[0m Mamadeira\n"
            "\u001b[32m✓\u001b[0m Trocar fralda\n"
            "\u001b[33m!\u001b[0m Fazer carinho\n"
            "\u001b[31m✕\u001b[0m Colocar para dormir\n"
            "```"
        ),
        inline=True,
    )

    embed.add_field(
        name="__Pais__",
        value=(
            "```ansi\n"
            "\u001b[36mNOIVO\u001b[0m: disposição 68\n"
            "\u001b[35mNOIVA\u001b[0m: disposição 74\n"
            "\n"
            "Sequência: 3 cuidados\n"
            "Vínculo: 12 pontos\n"
            "```"
        ),
        inline=True,
    )

    embed.add_field(
        name="__Inventário do bebê__",
        value=(
            "```ansi\n"
            "🍼 Mamadeira morna      \u001b[33m+15 fome\u001b[0m\n"
            "🧸 Ursinho macio        \u001b[35m+10 atenção\u001b[0m\n"
            "🧼 Lenço umedecido      \u001b[34m+12 higiene\u001b[0m\n"
            "🌙 Naninha              \u001b[36m+20 sono\u001b[0m\n"
            "```"
        ),
        inline=False,
    )

    embed.add_field(
        name="__Mensagem do bebê__",
        value=(
            "```ansi\n"
            "\u001b[1;33m“Eu tô com soninho, mas ainda quero colo.”\u001b[0m\n"
            "```"
        ),
        inline=False,
    )

    embed.set_footer(text="Baby System • Teste visual de embed com ANSI")
    return embed


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    canal = bot.get_channel(CANAL_LOG_ID) or await bot.fetch_channel(CANAL_LOG_ID)

    await canal.send(embed=criar_embed_teste_bebe())

    print("Embed teste enviada.")
    await bot.close()


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN não encontrado no .env")

    bot.run(TOKEN)
