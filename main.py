import asyncio
import logging
import os
import sys
import traceback
import warnings

from dotenv import load_dotenv

import nextcord
from nextcord.ext import commands

warnings.filterwarnings("ignore", category=DeprecationWarning)

if sys.platform.startswith("win") and hasattr(
    asyncio, "WindowsSelectorEventLoopPolicy"
):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# .env
# ─────────────────────────────────────────────────────────────

load_dotenv()


# ─────────────────────────────────────────────────────────────
# Logs
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

log = logging.getLogger("main")


def log_ok(msg: str):
    print(f"[OK] {msg}")


def log_warn(msg: str):
    print(f"[AVISO] {msg}")


def log_erro(msg: str):
    print(f"[ERRO] {msg}")


def log_bloco(titulo: str):
    print("\n" + "=" * 60)
    print(titulo)
    print("=" * 60)


# ─────────────────────────────────────────────────────────────
# Bot
# ─────────────────────────────────────────────────────────────

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="lv!", intents=intents)


# Coloque aqui exatamente os nomes dos arquivos dentro da pasta cogs.
# Exemplo: cogs/shop.py vira "cogs.shop".
EXTENSIONS = [
    "cogs.boas_vindas",
    "cogs.bot_reaction",
    "cogs.casamento",
    "cogs.cl_comando",
    "cogs.gif_comprimir_fig",
    "cogs.shop",
    "cogs.tickets",
]


COGS_OK = []
COGS_ERRO = []


def carregar_extensoes():
    log_bloco("CARREGANDO COGS")

    for ext in EXTENSIONS:
        try:
            bot.load_extension(ext)
            COGS_OK.append(ext)
            log_ok(f"Cog carregada: {ext}")
        except Exception as e:
            COGS_ERRO.append((ext, e))
            log_erro(f"Erro ao carregar cog: {ext}")
            print(f"      Motivo: {type(e).__name__}: {e}")

    print("-" * 60)
    print(f"Total carregadas: {len(COGS_OK)}")
    print(f"Total com erro:   {len(COGS_ERRO)}")

    if COGS_ERRO:
        print("\nCOGS COM ERRO:")
        for ext, e in COGS_ERRO:
            print(f" - {ext}: {type(e).__name__}: {e}")

    print("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────
# Eventos
# ─────────────────────────────────────────────────────────────


@bot.event
async def on_connect():
    log_ok("Bot conectado ao Discord.")


@bot.event
async def on_disconnect():
    log_warn("Bot desconectado do Discord.")


@bot.event
async def on_resumed():
    log_ok("Sessão retomada com sucesso.")


@bot.event
async def on_ready():
    log_bloco("BOT READY")

    if bot.user:
        log_ok(f"Bot online como: {bot.user}")
        log_ok(f"ID do bot: {bot.user.id}")
    else:
        log_warn("Bot online, mas bot.user não foi identificado.")

    log_ok(f"Servidores conectados: {len(bot.guilds)}")

    if bot.guilds:
        print("\nSERVIDORES:")
        for guild in bot.guilds:
            print(f" - {guild.name} | ID: {guild.id} | membros: {guild.member_count}")

    print("\nCOGS CARREGADAS:")
    if COGS_OK:
        for ext in COGS_OK:
            print(f" [OK] {ext}")
    else:
        print(" [AVISO] Nenhuma cog foi carregada.")

    print("\nCOGS COM ERRO:")
    if COGS_ERRO:
        for ext, e in COGS_ERRO:
            print(f" [ERRO] {ext} -> {type(e).__name__}: {e}")
    else:
        print(" [OK] Nenhuma cog com erro.")

    print("\nCOMANDOS PREFIXADOS CARREGADOS:")
    comandos_prefixo = sorted([cmd.name for cmd in bot.commands])
    if comandos_prefixo:
        for nome in comandos_prefixo:
            print(f" [OK] lv!{nome}")
    else:
        print(" [AVISO] Nenhum comando prefixado carregado.")

    print("\nSINCRONIZANDO SLASH COMMANDS:")
    try:
        await bot.sync_all_application_commands()
        log_ok("Comandos slash sincronizados.")
    except Exception as e:
        log_erro(f"Erro ao sincronizar comandos slash: {type(e).__name__}: {e}")

    print("\nSLASH COMMANDS REGISTRADOS LOCALMENTE:")
    try:
        slash_commands = []

        for cmd in bot.get_all_application_commands():
            slash_commands.append(cmd.name)

        slash_commands = sorted(set(slash_commands))

        if slash_commands:
            for nome in slash_commands:
                print(f" [OK] /{nome}")
        else:
            print(" [AVISO] Nenhum slash command encontrado localmente.")
    except Exception as e:
        log_erro(f"Erro ao listar slash commands: {type(e).__name__}: {e}")

    log_bloco("STATUS FINAL")

    if COGS_ERRO:
        log_warn("Bot iniciou, mas algumas cogs falharam.")
        log_warn("Veja a lista de erros acima.")
    else:
        log_ok("Todas as cogs foram carregadas sem erro.")

    log_ok("Sistema de bebê ignorado por enquanto.")
    log_ok("Bot pronto para uso.")


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        return

    log_erro(f"Erro em comando prefixado: {type(error).__name__}: {error}")

    try:
        await ctx.reply(f"❌ Erro no comando: `{type(error).__name__}: {error}`")
    except Exception:
        pass


@bot.event
async def on_application_command_error(
    interaction: nextcord.Interaction,
    error: Exception,
):
    log_erro(f"Erro em slash command: {type(error).__name__}: {error}")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                f"❌ Erro no comando: `{type(error).__name__}: {error}`",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"❌ Erro no comando: `{type(error).__name__}: {error}`",
                ephemeral=True,
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Inicialização
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    carregar_extensoes()

    token = os.getenv("DISCORD_TOKEN")

    if not token:
        log_erro("DISCORD_TOKEN não encontrado.")
        log_warn("Crie um arquivo .env com:")
        print("DISCORD_TOKEN=seu_token_aqui")
        raise RuntimeError("DISCORD_TOKEN não encontrado no .env")

    try:
        bot.run(token)
    except Exception as e:
        log_erro(f"Erro fatal ao iniciar o bot: {type(e).__name__}: {e}")
        traceback.print_exc()
