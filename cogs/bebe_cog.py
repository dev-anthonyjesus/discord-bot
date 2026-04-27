"""Cog: Sistema do bebê virtual (wrapper do BebeSistema)."""
import logging

from nextcord.ext import commands

from bebe import BebeSistema, registrar_views_bebe

log = logging.getLogger(__name__)


class BebeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bebe_sistema = BebeSistema(bot)

    def _build_fresh_sistema(self) -> BebeSistema:
        # Evita manter instância antiga após reload parcial de extensão.
        self.bebe_sistema = BebeSistema(self.bot)
        return self.bebe_sistema

    @commands.Cog.listener()
    async def on_ready(self):
        sistema = self._build_fresh_sistema()
        
        log.info("=== INICIANDO CARREGAMENTO DO SISTEMA BEBÊ ===")
        log.info(f"Sistema criado: {sistema}")
        log.info(f"Tipo do sistema: {type(sistema)}")

        try:
            log.info("Iniciando registrar_views_bebe...")
            registrar_views_bebe(self.bot, sistema)
            log.info("✅ Views persistentes do bebê carregadas.")
        except Exception as e:
            log.error(f"❌ Erro ao registrar views: {type(e).__name__}: {e}")
            log.exception("Erro ao carregar views do bebê")

        try:
            log.info("Verificando se loop está rodando...")
            if not sistema.loop_bebe.is_running():
                log.info("Iniciando loop do bebê...")
                sistema.loop_bebe.start()
                log.info("✅ Loop do bebê iniciado.")
            else:
                log.info("ℹ️ Loop do bebê já estava rodando.")
        except Exception as e:
            log.error(f"❌ Erro ao iniciar loop: {type(e).__name__}: {e}")
            log.exception("Erro ao iniciar loop do bebê")

            # Segunda tentativa com nova instância para evitar estado stale após reload.
            try:
                log.info("Tentando segunda vez com nova instância...")
                sistema = self._build_fresh_sistema()
                if not sistema.loop_bebe.is_running():
                    sistema.loop_bebe.start()
                    log.info("✅ Loop do bebê iniciado na segunda tentativa.")
            except Exception as e2:
                log.error(f"❌ Falha na segunda tentativa: {type(e2).__name__}: {e2}")
                log.exception("Falha na segunda tentativa do loop do bebê")

        try:
            log.info("Verificando setup...")
            if not sistema.data.get("setup"):
                log.info("Setup não iniciado, enviando setup inicial...")
                await sistema.atualizar_setup()
                log.info("✅ Setup do bebê enviado/atualizado.")
            else:
                log.info("Setup já feito, atualizando painel principal...")
                await sistema.atualizar_painel_principal()
                log.info("✅ Painel principal do bebê enviado/atualizado.")
        except Exception as e:
            log.error(f"❌ Erro ao atualizar sistema: {type(e).__name__}: {e}")
            log.exception("Erro ao atualizar sistema do bebê")
        
        log.info("=== CARREGAMENTO DO SISTEMA BEBÊ CONCLUÍDO ===")


def setup(bot: commands.Bot):
    bot.add_cog(BebeCog(bot))
