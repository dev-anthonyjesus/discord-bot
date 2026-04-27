"""Cog: Shop, Economia, VIPs e Mimos."""
import time
import logging

import nextcord
from nextcord.ext import commands, tasks
from nextcord.ui import View, Select, Button

from utils.constants import (
    CANAL_LOG_PRIV,
    CANAL_SHOP,
    CARGO_PROTEGIDO,
    VIPS,
    EMOJI_MIMO_ID,
    EMOJI_MOEDA_ID,
)
from utils.db import get_user, save_db

log = logging.getLogger(__name__)

MIMO_EMOJI  = nextcord.PartialEmoji(name="mimo",  id=EMOJI_MIMO_ID)
MOEDA_EMOJI = nextcord.PartialEmoji(name="moeda", id=EMOJI_MOEDA_ID)


# ── Helpers ──────────────────────────────────────────────────────────────────

async def log_priv(guild: nextcord.Guild, msg: str) -> None:
    canal = guild.get_channel(CANAL_LOG_PRIV)
    if canal:
        await canal.send(msg)


def create_shop_embed() -> nextcord.Embed:
    embed = nextcord.Embed(
        description="""
## <:shop:1492371812288561194> CandySHOP
<a:seta:1492410834557599794> **Seja um romântico oficial:**
*Confira os benefícios:*
<:moeda:1492371478362980393> <@&1492358391475998892>  
> 50 <:moeda:1492371478362980393> Escolher a metadinha ou foto do outro da semana  
<:cash:1492371548122779758> <@&1492358453174472754>  
> 80 <:moeda:1492371478362980393>   Escolher o próximo filme/série da semana
<:cashh:1492372609780814004> <@&1492358529775046793>  
> 150 <:moeda:1492371478362980393>  
<:cashbag:1492371672156733470> <@&1492358174999707758>  
> 300 <:moeda:1492371478362980393>  
<:card:1492371918010056826> <@&1492358982923321485>  
> 500 <:moeda:1492371478362980393> Direito a print de conversa + prioridade nas reclamações  

<a:seta:1492410834557599794> <@&1492378409781694484> 70 <:moeda:1492371478362980393>  
<:lulu:1492378695950667931> **Protegido da Lulu:**  
**_Este não é apenas um cargo, é um pacto de paz._**
> Ambos colocam "<:escudo:1492386745877135561>" no perfil  
> Se a conversa ficar tensa → manda o selo e encerra  
> ❌ Penalidade: -75 moedas  
> ✅ Bônus: +30 moedas sem brigas  

<a:seta:1492410834557599794> **Converta seus <:mimo:1492379169999552563> em <:moeda:1492371478362980393>**
> <:gift1:1492415234605060160> Você recebe 5 moedas diárias!
""",
        color=0xFF69B4,
    )
    embed.set_image(
        url="https://i.pinimg.com/736x/66/dc/14/66dc1473d8a304264a89365191ac1d31.jpg"
    )
    return embed


# ── UI Components ─────────────────────────────────────────────────────────────

class FecharVipView(View):
    def __init__(self, author_id: int):
        super().__init__(timeout=120)
        self.author_id = author_id

    @nextcord.ui.button(label="Fechar", style=nextcord.ButtonStyle.red, emoji="❌")
    async def fechar(self, button: Button, interaction: nextcord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Só quem abriu essa mensagem pode fechar.", ephemeral=True
            )
            return
        await interaction.message.delete()


class MimoSelect(Select):
    def __init__(self, target: nextcord.Member, author: nextcord.Member):
        self.target = target
        self.author = author
        options = [
            nextcord.SelectOption(label="100",   description="Não tava merecendo mas vou enviar",   value="100",   emoji=MIMO_EMOJI),
            nextcord.SelectOption(label="300",   description="Fez algo que gostei hoje",             value="300",   emoji=MIMO_EMOJI),
            nextcord.SelectOption(label="500",   description="Você me faz um bem danado",            value="500",   emoji=MIMO_EMOJI),
            nextcord.SelectOption(label="1000",  description="Obrigado por ser meu porto seguro",    value="1000",  emoji=MIMO_EMOJI),
            nextcord.SelectOption(label="10000", description="Hoje foi um dia especial!",            value="10000", emoji=MIMO_EMOJI),
        ]
        super().__init__(placeholder="Escolha a quantidade de mimos", options=options)

    async def callback(self, interaction: nextcord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Essa interação não é sua.", ephemeral=True)
            return
        if self.target.id == self.author.id:
            await interaction.response.send_message("❌ Você não pode enviar mimos para si mesmo.", ephemeral=True)
            return

        value = int(self.values[0])
        data = get_user(self.target.id)
        data[str(self.target.id)]["mimos"] += value
        save_db(data)

        await log_priv(interaction.guild, f"[MIMOS] {interaction.user} enviou {value} mimos para {self.target}")
        await interaction.response.send_message(
            f"💖 Você enviou {value} <:mimo:1492379169999552563> para {self.target.mention}.",
            ephemeral=True,
        )


class UserSelect(Select):
    def __init__(self, guild: nextcord.Guild, author: nextcord.Member):
        self.author = author
        options = [
            nextcord.SelectOption(
                label=m.display_name[:100],
                value=str(m.id),
                description=f"@{m.name}"[:100],
            )
            for m in guild.members
            if not m.bot
        ][:25]
        super().__init__(placeholder="Escolha a pessoa", options=options)

    async def callback(self, interaction: nextcord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Essa interação não é sua.", ephemeral=True)
            return

        membro = interaction.guild.get_member(int(self.values[0]))
        if not membro:
            await interaction.response.send_message("❌ Não encontrei esse membro.", ephemeral=True)
            return

        embed = nextcord.Embed(
            title="Enviar mimos",
            description=(
                f"**Destinatário:** {membro.mention}\n"
                f"**Nome:** {membro.display_name}\n"
                f"**Usuário:** @{membro.name}"
            ),
            color=0xFF69B4,
        )
        if membro.display_avatar:
            embed.set_thumbnail(url=membro.display_avatar.url)

        view = View(timeout=300)
        view.add_item(MimoSelect(membro, self.author))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class VipSelect(Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label="VIP MOMO",               value="momo",      description="50 moedas",  emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="VIP PICANTE",            value="picante",   description="80 moedas",  emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="VIP PROMESSA",           value="promessa",  description="150 moedas", emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="VIP DENGO VITALÍCIO",    value="dengo",     description="300 moedas", emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="PATROCÍNIO ALMA GÊMEA",  value="alma",      description="500 moedas", emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="PROTEGIDO",              value="protegido", description="70 moedas",  emoji=MOEDA_EMOJI),
        ]
        super().__init__(placeholder="Escolha o cargo para comprar", options=options)

    async def callback(self, interaction: nextcord.Interaction):
        data  = get_user(interaction.user.id)
        user  = data[str(interaction.user.id)]
        key   = self.values[0]
        vip   = VIPS[key]
        agora = int(time.time())

        if vip["tipo"] == "protegido":
            if user.get("protegido") and user.get("protegido_expira", 0) > agora:
                await interaction.response.send_message("❌ Você já possui PROTEGIDO ativo.", ephemeral=True)
                return
            if user["moedas"] < vip["preco"]:
                await interaction.response.send_message("❌ Você não tem moedas suficientes.", ephemeral=True)
                return

            user["moedas"] -= vip["preco"]
            user["protegido"] = True
            user["protegido_comprado_em"] = agora
            user["protegido_expira"] = agora + vip["duracao_dias"] * 86400

            cargo = interaction.guild.get_role(vip["cargo_id"])
            if cargo:
                await interaction.user.add_roles(cargo)
            save_db(data)
            await log_priv(interaction.guild, f"[COMPRA] {interaction.user} comprou PROTEGIDO por {vip['preco']} moedas")
            await interaction.response.send_message("✅ Você comprou **PROTEGIDO** com sucesso.", ephemeral=True)
            return

        if user.get("vip") and user.get("vip_expira", 0) > agora:
            await interaction.response.send_message("❌ Você já possui um VIP/PATROCÍNIO ativo.", ephemeral=True)
            return
        if user["moedas"] < vip["preco"]:
            await interaction.response.send_message("❌ Você não tem moedas suficientes.", ephemeral=True)
            return

        user["moedas"] -= vip["preco"]
        user["vip"] = key
        user["vip_comprado_em"] = agora
        user["vip_expira"] = agora + vip["duracao_dias"] * 86400

        cargo = interaction.guild.get_role(vip["cargo_id"])
        if cargo:
            await interaction.user.add_roles(cargo)
        save_db(data)
        await log_priv(interaction.guild, f"[COMPRA] {interaction.user} comprou {vip['nome']} por {vip['preco']} moedas")
        await interaction.response.send_message(f"✅ Você comprou **{vip['nome']}** com sucesso.", ephemeral=True)


class ConfirmarConversao(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @nextcord.ui.button(label="Confirmar Conversão", style=nextcord.ButtonStyle.green)
    async def confirmar(self, button: Button, interaction: nextcord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Essa interação não é sua.", ephemeral=True)
            return

        data = get_user(self.user_id)
        user = data[str(self.user_id)]
        mimos  = user["mimos"]
        moedas = (mimos // 100) * 10
        usados = (mimos // 100) * 100

        if usados <= 0:
            await interaction.response.send_message("❌ Você não tem mimos suficientes para converter.", ephemeral=True)
            return

        user["mimos"]  -= usados
        user["moedas"] += moedas
        save_db(data)

        await log_priv(interaction.guild, f"[CONVERSÃO] {interaction.user} converteu {usados} mimos em {moedas} moedas")
        await interaction.response.send_message(f"✅ Você converteu {usados} mimos em {moedas} moedas.", ephemeral=True)


class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="💖 Enviar Mimos", style=nextcord.ButtonStyle.green, custom_id="shop_send_mimos")
    async def enviar(self, button: Button, interaction: nextcord.Interaction):
        view = View(timeout=300)
        view.add_item(UserSelect(interaction.guild, interaction.user))
        await interaction.response.send_message("Escolha a pessoa:", view=view, ephemeral=True)

    @nextcord.ui.button(label="💰 Meu Saldo", style=nextcord.ButtonStyle.gray, custom_id="shop_saldo")
    async def saldo(self, button: Button, interaction: nextcord.Interaction):
        data = get_user(interaction.user.id)
        user = data[str(interaction.user.id)]

        embed = nextcord.Embed(title="💖 Seu saldo", color=0xFF69B4, timestamp=nextcord.utils.utcnow())
        embed.add_field(name="<:moeda:1492371478362980393> Moedas", value=f"```{user['moedas']}```", inline=True)
        embed.add_field(name="<:mimo:1492379169999552563> Mimos",   value=f"```{user['mimos']}```",  inline=True)

        icon = interaction.guild.icon.url if interaction.guild.icon else None
        embed.set_thumbnail(url=icon)
        embed.set_footer(text=interaction.guild.name, icon_url=icon)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="🔄 Converter", style=nextcord.ButtonStyle.gray, custom_id="shop_converter")
    async def converter(self, button: Button, interaction: nextcord.Interaction):
        data = get_user(interaction.user.id)
        user = data[str(interaction.user.id)]

        embed = nextcord.Embed(
            title="💖 Conversão",
            description=(
                f"**Seus mimos:** {user['mimos']} <:mimo:1492379169999552563>\n\n"
                "**Taxa:** 100 <:mimo:1492379169999552563> = 10 <:moeda:1492371478362980393>"
            ),
            color=0xFF69B4,
        )
        await interaction.response.send_message(embed=embed, view=ConfirmarConversao(interaction.user.id), ephemeral=True)

    @nextcord.ui.button(label="🛒 Comprar VIP", style=nextcord.ButtonStyle.gray, custom_id="shop_comprar")
    async def comprar(self, button: Button, interaction: nextcord.Interaction):
        view = View(timeout=300)
        view.add_item(VipSelect())
        await interaction.response.send_message("Escolha o cargo que deseja comprar:", view=view, ephemeral=True)

    @nextcord.ui.button(emoji="🎁", style=nextcord.ButtonStyle.gray, custom_id="shop_daily")
    async def daily(self, button: Button, interaction: nextcord.Interaction):
        data = get_user(interaction.user.id)
        user = data[str(interaction.user.id)]

        now = time.time()
        if now - user["daily"] < 86400:
            restante = int(86400 - (now - user["daily"]))
            horas    = restante // 3600
            minutos  = (restante % 3600) // 60
            await interaction.response.send_message(f"⏳ Volte em {horas}h {minutos}m.", ephemeral=True)
            return

        user["moedas"] += 5
        user["daily"]   = now
        save_db(data)

        await log_priv(interaction.guild, f"[DAILY] {interaction.user} recebeu +5 moedas")
        await interaction.response.send_message("🎁 Você recebeu +5 moedas.", ephemeral=True)


# ── Cog ───────────────────────────────────────────────────────────────────────

class ShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Tarefa: expirar VIPs ──────────────────────────────────────────────────

    @tasks.loop(minutes=1)
    async def verificar_vips(self):
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if guild is None:
            return

        from utils.db import load_db, save_db as _save
        data  = load_db()
        agora = int(time.time())

        for user_id, info in data.items():
            if not isinstance(info, dict):
                continue

            membro = guild.get_member(int(user_id))
            if membro is None:
                continue

            if info.get("vip") and info.get("vip_expira", 0) > 0 and info["vip_expira"] <= agora:
                key = info["vip"]
                vip = VIPS.get(key)
                if vip:
                    cargo = guild.get_role(vip["cargo_id"])
                    if cargo and cargo in membro.roles:
                        await membro.remove_roles(cargo)
                await log_priv(guild, f"[EXPIRAÇÃO] {membro} perdeu {vip['nome'] if vip else key}")
                info["vip"]             = None
                info["vip_comprado_em"] = 0
                info["vip_expira"]      = 0

            if info.get("protegido") and info.get("protegido_expira", 0) > 0 and info["protegido_expira"] <= agora:
                cargo = guild.get_role(CARGO_PROTEGIDO)
                if cargo and cargo in membro.roles:
                    await membro.remove_roles(cargo)
                await log_priv(guild, f"[EXPIRAÇÃO] {membro} perdeu PROTEGIDO")
                info["protegido"]             = False
                info["protegido_comprado_em"] = 0
                info["protegido_expira"]      = 0

        _save(data)

    @verificar_vips.before_loop
    async def before_verificar_vips(self):
        await self.bot.wait_until_ready()

    # ── Comando: vip ─────────────────────────────────────────────────────────

    @commands.command()
    async def vip(self, ctx: commands.Context):
        data  = get_user(ctx.author.id)
        user  = data[str(ctx.author.id)]
        agora = int(time.time())

        vip_nome    = "Nenhum"
        cargo_nome  = "Nenhum"
        comprado_em = "Não registrado"
        expira_em   = "Nenhum"

        if user.get("vip"):
            key = user["vip"]
            vip = VIPS.get(key)
            if vip:
                vip_nome   = vip["nome"]
                cargo      = ctx.guild.get_role(vip["cargo_id"])
                cargo_nome = cargo.mention if cargo else "Cargo não encontrado"
            if user.get("vip_comprado_em"):
                comprado_em = f"<t:{user['vip_comprado_em']}:F>"
            if user.get("vip_expira", 0) > agora:
                restante  = user["vip_expira"] - agora
                dias      = restante // 86400
                horas     = (restante % 86400) // 3600
                minutos   = (restante % 3600) // 60
                expira_em = f"{dias}d {horas}h {minutos}m"
            else:
                expira_em = "Expirado ❌"

        protegido_status  = "❌ Não"
        protegido_comprado = "Não registrado"
        protegido_expira  = "Nenhum"

        if user.get("protegido"):
            protegido_status = "✅ Ativo"
            if user.get("protegido_comprado_em"):
                protegido_comprado = f"<t:{user['protegido_comprado_em']}:F>"
            if user.get("protegido_expira", 0) > agora:
                restante         = user["protegido_expira"] - agora
                dias             = restante // 86400
                horas            = (restante % 86400) // 3600
                minutos          = (restante % 3600) // 60
                protegido_expira = f"{dias}d {horas}h {minutos}m"
            else:
                protegido_status = "Expirado ❌"
                protegido_expira = "Expirado ❌"

        embed = nextcord.Embed(
            title="💎 Perfil Premium",
            description="Aqui estão suas informações atuais no sistema.",
            color=0xFF69B4,
            timestamp=nextcord.utils.utcnow(),
        )
        icon = ctx.guild.icon.url if ctx.guild.icon else None
        embed.set_thumbnail(url=icon)
        embed.add_field(name="👤 Usuário",            value=ctx.author.mention, inline=False)
        embed.add_field(name="👑 VIP Atual",          value=vip_nome,           inline=True)
        embed.add_field(name="🎭 Cargo",              value=cargo_nome,         inline=True)
        embed.add_field(name="⏳ VIP expira em",      value=expira_em,          inline=True)
        embed.add_field(name="🛍️ VIP comprado em",   value=comprado_em,        inline=False)
        embed.add_field(name="🛡️ Protegido",         value=protegido_status,   inline=True)
        embed.add_field(name="🛒 Protegido comprado", value=protegido_comprado, inline=True)
        embed.add_field(name="⏳ Protegido expira",   value=protegido_expira,   inline=True)
        embed.add_field(name="<:moeda:1492371478362980393> Moedas", value=f"```{user['moedas']}```", inline=True)
        embed.add_field(name="<:mimo:1492379169999552563> Mimos",   value=f"```{user['mimos']}```",  inline=True)
        embed.add_field(name="📌 Conversão",          value="100 mimos = 10 moedas", inline=False)
        embed.set_footer(text=f"{ctx.guild.name} • Status do seu perfil", icon_url=icon)

        await ctx.send(embed=embed, view=FecharVipView(ctx.author.id))

    # ── on_ready: registrar view persistente + painel ────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ShopView())
        if not self.verificar_vips.is_running():
            self.verificar_vips.start()

        from utils.panels import send_or_update_panel
        try:
            await send_or_update_panel(
                bot=self.bot,
                channel_id=CANAL_SHOP,
                panel_key="shop_panel",
                embed=create_shop_embed(),
                view=ShopView(),
            )
            log.info("Painel da shop enviado/atualizado.")
        except Exception as e:
            log.error(f"Erro no painel da shop: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(ShopCog(bot))

    import json

ARQUIVO = "database.json"


def carregar():
    try:
        with open(ARQUIVO, "r") as f:
            return json.load(f)
    except:
        return {}


def salvar(dados):
    with open(ARQUIVO, "w") as f:
        json.dump(dados, f, indent=4)


def get_user(user_id):
    dados = carregar()
    if str(user_id) not in dados:
        dados[str(user_id)] = {"moedas": 0, "mimos": 0}
        salvar(dados)
    return dados


# ===== MOEDAS =====
def add_moedas(user_id, valor):
    dados = get_user(user_id)
    dados[str(user_id)]["moedas"] += valor
    salvar(dados)


def get_moedas(user_id):
    dados = get_user(user_id)
    return dados[str(user_id)]["moedas"]


# ===== MIMOS =====
def add_mimos(user_id, valor):
    dados = get_user(user_id)
    dados[str(user_id)]["mimos"] += valor
    salvar(dados)


def get_mimos(user_id):
    dados = get_user(user_id)
    return dados[str(user_id)]["mimos"]


def remove_mimos(user_id, valor):
    dados = get_user(user_id)
    dados[str(user_id)]["mimos"] = max(0, dados[str(user_id)]["mimos"] - valor)
    salvar(dados)
