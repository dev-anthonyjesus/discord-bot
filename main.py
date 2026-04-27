import asyncio
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

if sys.platform.startswith("win") and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
import re
import json
import time
import io
import os
import subprocess  #import gif
import tempfile
import shutil


from dotenv import load_dotenv

import nextcord
from PIL import Image, ImageSequence, ImageFilter
from nextcord.ext import commands, tasks
from nextcord.ui import View, Select, Button
from bemvindo import create_welcome_embed

from ticket_system import (
    setup_ticket_system,
    TicketPanelView,
    build_panel_embed,
    build_config_embed,
    load_config,
    save_config,
    ticket_reminder_loop,
)

from bebe import BebeSistema, registrar_views_bebe

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="lv!", intents=intents)




def load_panels():
    try:
        with open(PANEL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_panels(data):
    with open(PANEL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

async def send_or_update_panel(channel_id: int, panel_key: str, embed, view=None):
    panels = load_panels()
    channel = await bot.fetch_channel(channel_id)

    message_id = panels.get(panel_key)

    if message_id:
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed, view=view)
            return
        except:
            pass

    msg = await channel.send(embed=embed, view=view)
    panels[panel_key] = msg.id
    save_panels(panels)


def fit_on_canvas(image: Image.Image, scale: float = 1.0) -> Image.Image:
    img = image.convert("RGBA")
    target_w, target_h = FIG_DIM

    # ===== fundo preenchido (sem transparência preta) =====
    bg_ratio = max(target_w / img.width, target_h / img.height)
    bg_w = max(1, int(img.width * bg_ratio))
    bg_h = max(1, int(img.height * bg_ratio))

    background = img.resize((bg_w, bg_h), Image.Resampling.LANCZOS)
    left = (bg_w - target_w) // 2
    top = (bg_h - target_h) // 2
    background = background.crop((left, top, left + target_w, top + target_h))
    background = background.filter(ImageFilter.GaussianBlur(12))

    # escurece um pouco o fundo pra destacar o centro
    dark = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 70))
    background = Image.alpha_composite(background, dark)

    # ===== imagem principal centralizada =====
    fg_ratio = min(target_w / img.width, target_h / img.height) * scale
    fg_w = max(1, int(img.width * fg_ratio))
    fg_h = max(1, int(img.height * fg_ratio))

    foreground = img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

    x = (target_w - fg_w) // 2
    y = (target_h - fg_h) // 2

    background.paste(foreground, (x, y), foreground)
    return background


def compress_static_image(data: bytes) -> io.BytesIO:
    original = Image.open(io.BytesIO(data))

    for scale in [1.0, 0.9, 0.8, 0.7, 0.6]:
        processed = fit_on_canvas(original, scale=scale)
        output = io.BytesIO()
        processed.save(output, format="PNG", optimize=True, compress_level=9)
        output.seek(0)

        if output.getbuffer().nbytes <= MAX_FIG_SIZE:
            return output

    raise ValueError("Não consegui comprimir a imagem para 512KB.")


def _quantize_rgba_frame(img: Image.Image, colors: int) -> Image.Image:
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    transparent_mask = alpha.point(lambda a: 255 if a <= 10 else 0)

    rgb = Image.new("RGB", rgba.size, (255, 255, 255))
    rgb.paste(rgba, mask=alpha)

    pal = rgb.quantize(
        colors=min(colors, 255),
        method=Image.Quantize.FASTOCTREE,
        dither=Image.Dither.NONE,
    )

    transparent_index = 255
    palette = pal.getpalette()
    if palette is None:
        palette = [0, 0, 0] * 256
    elif len(palette) < 768:
        palette += [0] * (768 - len(palette))
    pal.putpalette(palette)

    pal.paste(transparent_index, mask=transparent_mask)
    pal.info["transparency"] = transparent_index
    return pal


def prepare_gif_frames(data: bytes, scale: float, colors: int, frame_step: int = 1, min_duration: int = 80):
    img = Image.open(io.BytesIO(data))
    frames = []
    durations = []
    loop = img.info.get("loop", 0)

    all_frames = list(ImageSequence.Iterator(img))

    for i, frame in enumerate(all_frames):
        if i % frame_step != 0:
            continue

        original_duration = frame.info.get("duration", 80)
        duration = max(min_duration, original_duration * frame_step)

        fitted = fit_on_canvas(frame.convert("RGBA"), scale=scale)
        paletted = _quantize_rgba_frame(fitted, colors=colors)

        frames.append(paletted)
        durations.append(duration)

    if not frames:
        first = fit_on_canvas(all_frames[0].convert("RGBA"), scale=scale)
        frames = [_quantize_rgba_frame(first, colors=colors)]
        durations = [min_duration]

    return frames, durations, loop


def compress_gif(data: bytes) -> io.BytesIO:
    """
    Comprime GIF preservando animação e cores o máximo possível.
    Estratégia:
    - mantém todos os frames
    - mantém duração original
    - reduz só a escala aos poucos
    - usa otimização do GIF
    """
    img = Image.open(io.BytesIO(data))

    attempts = [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5]
    best_output = None
    best_size = None

    for scale in attempts:
        frames = []
        durations = []
        loop = img.info.get("loop", 0)

        for frame in ImageSequence.Iterator(img):
            duration = frame.info.get("duration", 80)

            # redimensiona mantendo transparência
            fitted = fit_on_canvas(frame.convert("RGBA"), scale=scale)

            # converte para paleta GIF sem destruir demais as cores
            paletted = fitted.quantize(
                colors=255,
                method=Image.Quantize.FASTOCTREE,
                dither=Image.Dither.NONE
            )

            paletted.info["transparency"] = 255
            frames.append(paletted)
            durations.append(duration)

        output = io.BytesIO()
        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            optimize=True,
            loop=loop,
            duration=durations,
            disposal=2,
        )
        output.seek(0)

        current_size = output.getbuffer().nbytes

        if best_size is None or current_size < best_size:
            best_size = current_size
            best_output = io.BytesIO(output.getvalue())
            best_output.seek(0)

        if current_size <= MAX_FIG_SIZE:
            return output

    # se não conseguiu 512 KB sem estragar demais, devolve erro honesto
    raise ValueError(
        f"Não consegui deixar esse GIF em 512KB sem destruir a animação. "
        f"O menor tamanho que consegui foi {round(best_size / 1024, 1)} KB."
    )
# ================= DB =================


def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_user(user_id: int):
    data = load_db()
    uid = str(user_id)

    if uid not in data or not isinstance(data[uid], dict):
        data[uid] = {}

    user = data[uid]
    user.setdefault("mimos", 0)
    user.setdefault("moedas", 0)
    user.setdefault("daily", 0)

    user.setdefault("vip", None)
    user.setdefault("vip_comprado_em", 0)
    user.setdefault("vip_expira", 0)

    user.setdefault("protegido", False)
    user.setdefault("protegido_comprado_em", 0)
    user.setdefault("protegido_expira", 0)

    save_db(data)
    return data


async def log_priv(guild: nextcord.Guild, msg: str):
    canal = guild.get_channel(CANAL_LOG_PRIV)
    if canal:
        await canal.send(msg)

# ================= EMBED SHOP =================


def create_shop_embed():
    embed = nextcord.Embed(
        description=f"""
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
        color=0xFF69B4
    )
    embed.set_image(url="https://i.pinimg.com/736x/66/dc/14/66dc1473d8a304264a89365191ac1d31.jpg")
    return embed


class FecharVipView(View):
    def __init__(self, author_id: int):
        super().__init__(timeout=120)
        self.author_id = author_id

    @nextcord.ui.button(label="Fechar", style=nextcord.ButtonStyle.red, emoji="❌")
    async def fechar(self, button: Button, interaction: nextcord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Só quem abriu essa mensagem pode fechar.",
                ephemeral=True
            )
            return
        await interaction.message.delete()


class MimoSelect(Select):
    def __init__(self, target: nextcord.Member, author: nextcord.Member):
        self.target = target
        self.author = author

        options = [
            nextcord.SelectOption(label="100", description="Não tava merecendo mas vou enviar", value="100", emoji=MIMO_EMOJI),
            nextcord.SelectOption(label="300", description="Fez algo que gostei hoje", value="300", emoji=MIMO_EMOJI),
            nextcord.SelectOption(label="500", description="Você me faz um bem danado", value="500", emoji=MIMO_EMOJI),
            nextcord.SelectOption(label="1000", description="Obrigado por ser meu porto seguro", value="1000", emoji=MIMO_EMOJI),
            nextcord.SelectOption(label="10000", description="Hoje foi um dia especial!", value="10000", emoji=MIMO_EMOJI),
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
            ephemeral=True
        )


class UserSelect(Select):
    def __init__(self, guild: nextcord.Guild, author: nextcord.Member):
        self.author = author

        options = [
            nextcord.SelectOption(
                label=m.display_name[:100],
                value=str(m.id),
                description=f"@{m.name}"[:100]
            )
            for m in guild.members if not m.bot
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
            color=0xFF69B4
        )
        if membro.display_avatar:
            embed.set_thumbnail(url=membro.display_avatar.url)

        view = View(timeout=300)
        view.add_item(MimoSelect(membro, self.author))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class VipSelect(Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label="VIP MOMO", value="momo", description="50 moedas", emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="VIP PICANTE", value="picante", description="80 moedas", emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="VIP PROMESSA", value="promessa", description="150 moedas", emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="VIP DENGO VITALÍCIO", value="dengo", description="300 moedas", emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="PATROCÍNIO ALMA GÊMEA", value="alma", description="500 moedas", emoji=MOEDA_EMOJI),
            nextcord.SelectOption(label="PROTEGIDO", value="protegido", description="70 moedas", emoji=MOEDA_EMOJI),
        ]
        super().__init__(placeholder="Escolha o cargo para comprar", options=options)

    async def callback(self, interaction: nextcord.Interaction):
        data = get_user(interaction.user.id)
        user = data[str(interaction.user.id)]

        key = self.values[0]
        vip = VIPS[key]
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
            user["protegido_expira"] = agora + (vip["duracao_dias"] * 86400)

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
        user["vip_expira"] = agora + (vip["duracao_dias"] * 86400)

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

        mimos = user["mimos"]
        moedas = (mimos // 100) * 10
        usados = (mimos // 100) * 100

        if usados <= 0:
            await interaction.response.send_message("❌ Você não tem mimos suficientes para converter.", ephemeral=True)
            return

        user["mimos"] -= usados
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

        embed = nextcord.Embed(
            title="💖 Seu saldo",
            color=0xFF69B4,
            timestamp=nextcord.utils.utcnow()
        )
        embed.add_field(name="<:moeda:1492371478362980393> Moedas", value=f"```{user['moedas']}```", inline=True)
        embed.add_field(name="<:mimo:1492379169999552563> Mimos", value=f"```{user['mimos']}```", inline=True)

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(
            text=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="🔄 Converter", style=nextcord.ButtonStyle.gray, custom_id="shop_converter")
    async def converter(self, button: Button, interaction: nextcord.Interaction):
        data = get_user(interaction.user.id)
        user = data[str(interaction.user.id)]

        embed = nextcord.Embed(
            title="💖 Conversão",
            description=(
                f"**Seus mimos:** {user['mimos']} <:mimo:1492379169999552563>\n\n"
                f"**Taxa:** 100 <:mimo:1492379169999552563> = 10 <:moeda:1492371478362980393>"
            ),
            color=0xFF69B4
        )

        await interaction.response.send_message(
            embed=embed,
            view=ConfirmarConversao(interaction.user.id),
            ephemeral=True
        )

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
            horas = restante // 3600
            minutos = (restante % 3600) // 60
            await interaction.response.send_message(f"⏳ Volte em {horas}h {minutos}m.", ephemeral=True)
            return

        user["moedas"] += 5
        user["daily"] = now
        save_db(data)

        await log_priv(interaction.guild, f"[DAILY] {interaction.user} recebeu +5 moedas")
        await interaction.response.send_message("🎁 Você recebeu +5 moedas.", ephemeral=True)


@tasks.loop(minutes=1)
async def verificar_vips():
    guild = bot.guilds[0] if bot.guilds else None
    if guild is None:
        return

    data = load_db()
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

            info["vip"] = None
            info["vip_comprado_em"] = 0
            info["vip_expira"] = 0

        if info.get("protegido") and info.get("protegido_expira", 0) > 0 and info["protegido_expira"] <= agora:
            cargo = guild.get_role(CARGO_PROTEGIDO)
            if cargo and cargo in membro.roles:
                await membro.remove_roles(cargo)

            await log_priv(guild, f"[EXPIRAÇÃO] {membro} perdeu PROTEGIDO")

            info["protegido"] = False
            info["protegido_comprado_em"] = 0
            info["protegido_expira"] = 0

    save_db(data)


# ================= CASAMENTO JSON =================

def log_ok(msg):
    print(f"[OK] {msg}")

def log_warn(msg):
    print(f"[AVISO] {msg}")

def log_erro(msg):
    print(f"[ERRO] {msg}")

def load_casamento():
    default = {
        "canal_id": CANAL_CASAMENTO,
        "casal_ids": [SEU_ID, ID_DA_NOIVA],
        "usuarios": {
            str(SEU_ID): {
                "respostas": {},
                "pronto_resultado": False,
                "ultimo_envio": None,
            },
            str(ID_DA_NOIVA): {
                "respostas": {},
                "pronto_resultado": False,
                "ultimo_envio": None,
            }
        },
        "ultima_rodada_id": 0,
        "ultimo_resultado": None,
        "recompensas_entregues": []
    }

    try:
        with open(CASAMENTO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        with open(CASAMENTO_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        log_ok("Arquivo de casamento criado.")
        return default

    if "usuarios" not in data:
        data["usuarios"] = {}

    for uid in [str(SEU_ID), str(ID_DA_NOIVA)]:
        if uid not in data["usuarios"]:
            data["usuarios"][uid] = {
                "respostas": {},
                "pronto_resultado": False,
                "ultimo_envio": None,
            }

    data.setdefault("ultima_rodada_id", 0)
    data.setdefault("ultimo_resultado", None)
    data.setdefault("recompensas_entregues", [])

    save_casamento(data)
    return data


def save_casamento(data):
    with open(CASAMENTO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def usuario_autorizado_casamento(user_id: int):
    return user_id in [SEU_ID, ID_DA_NOIVA]


def salvar_resposta_casamento(user_id: int, campo: str, valor):
    data = load_casamento()
    uid = str(user_id)

    data["usuarios"][uid]["respostas"][campo] = valor
    data["usuarios"][uid]["pronto_resultado"] = False
    save_casamento(data)

    log_ok(f"Resposta salva no casamento | user={user_id} | campo={campo} | valor={valor}")


def validar_respostas_casamento(respostas: dict):
    obrigatorios = [
        "lugar",
        "bolo",
        "musica",
        "periodo",
        "qtd_convidados",
        "tipo_convidados",
        "decoracao"
    ]

    for campo in obrigatorios:
        if campo not in respostas:
            return False

    if not isinstance(respostas.get("bolo"), list) or len(respostas["bolo"]) != 2:
        return False

    if not isinstance(respostas.get("musica"), list) or len(respostas["musica"]) != 2:
        return False

    return True


# ================= CASAMENTO OPÇÕES =================

LUGARES_CASAMENTO = [
    ("praia", "Praia"),
    ("igreja", "Igreja"),
    ("campo", "Campo / Sítio"),
    ("salao", "Salão elegante"),
    ("jardim", "Jardim"),
    ("simples", "Algo simples / íntimo"),
]

BOLOS_CASAMENTO = [
    ("chocolate", "Chocolate"),
    ("morango", "Morango"),
    ("red_velvet", "Red Velvet"),
    ("ninho", "Ninho"),
    ("baunilha", "Baunilha"),
    ("prestigio", "Prestígio"),
    ("doce_de_leite", "Doce de leite"),
]

MUSICAS_CASAMENTO = [
    ("romantico", "Romântico"),
    ("sertanejo", "Sertanejo"),
    ("pop", "Pop"),
    ("pagode", "Pagode"),
    ("mpb", "MPB"),
    ("gospel", "Gospel"),
    ("funk", "Funk"),
    ("eletronica", "Eletrônica"),
]

PERIODOS_CASAMENTO = [
    ("manha", "Manhã"),
    ("tarde", "Tarde"),
    ("por_do_sol", "Pôr do sol"),
    ("noite", "Noite"),
]

QTD_CONVIDADOS_CASAMENTO = [
    ("mini", "Só nós dois / mini cerimônia"),
    ("intimo", "Bem íntimo"),
    ("pequeno", "Pequeno"),
    ("medio", "Médio"),
    ("grande", "Grande"),
    ("muita_gente", "Muita gente"),
]

TIPO_CONVIDADOS_CASAMENTO = [
    ("familia_proxima", "Só família próxima"),
    ("familia_amigos_proximos", "Família + amigos próximos"),
    ("misto", "Família + amigos + alguns conhecidos"),
    ("todos_importantes", "Todo mundo importante"),
    ("festa_grande", "Festa grande com conhecidos também"),
]

DECORACOES_CASAMENTO = [
    ("luxuosa", "Luxuosa"),
    ("minimalista", "Minimalista"),
    ("romantica", "Romântica"),
    ("floral", "Floral"),
    ("elegante_escura", "Elegante escura"),
    ("fofa", "Fofa / delicada"),
    ("rustica", "Rústica"),
]


def label_casamento(opcoes, valor):
    for k, v in opcoes:
        if k == valor:
            return v
    return valor

# ============================== casamento

# ================= CASAMENTO LÓGICA =================

ORDENACAO_PERIODO_CASAMENTO = {
    "manha": 0,
    "tarde": 1,
    "por_do_sol": 2,
    "noite": 3,
}

ORDENACAO_QTD_CASAMENTO = {
    "mini": 0,
    "intimo": 1,
    "pequeno": 2,
    "medio": 3,
    "grande": 4,
    "muita_gente": 5,
}

ORDENACAO_TIPO_CASAMENTO = {
    "familia_proxima": 0,
    "familia_amigos_proximos": 1,
    "misto": 2,
    "todos_importantes": 3,
    "festa_grande": 4,
}


def pontuar_igual(a, b):
    return 10 if a == b else 0


def pontuar_proximidade(mapa, a, b):
    if a == b:
        return 10

    diff = abs(mapa.get(a, 999) - mapa.get(b, 999))
    if diff == 1:
        return 5
    return 0


def pontuar_multiselect(a, b):
    comuns = len(set(a) & set(b))
    if comuns >= 2:
        return 10
    if comuns == 1:
        return 5
    return 0


def nivel_compatibilidade(p):
    if p <= 20:
        return "Casamento caótico 😭"
    elif p <= 40:
        return "Vai precisar de negociação 😂"
    elif p <= 60:
        return "Tem química, mas precisam alinhar 💫"
    elif p <= 80:
        return "Casal bem conectado 💕"
    return "Almas gêmeas do altar 💍"


def calcular_recompensa_casamento(porcentagem: int):
    if porcentagem == 100:
        return {"moedas": 20, "mimos": 1}
    elif porcentagem >= 90:
        return {"moedas": 10, "mimos": 1}
    elif porcentagem >= 70:
        return {"moedas": 10, "mimos": 0}
    return {"moedas": 5, "mimos": 0}


def adicionar_recompensa_db(user_id: int, moedas=0, mimos=0):
    data = get_user(user_id)
    uid = str(user_id)
    data[uid]["moedas"] += moedas
    data[uid]["mimos"] += mimos
    save_db(data)


def calcular_compatibilidade_casamento(r1: dict, r2: dict):
    total = 0
    maximo = 70
    compat = []
    diverg = []

    p = pontuar_igual(r1["lugar"], r2["lugar"])
    total += p
    if p == 10:
        compat.append(f"📍 Lugar: {label_casamento(LUGARES_CASAMENTO, r1['lugar'])}")
    else:
        diverg.append(f"📍 Lugar: {label_casamento(LUGARES_CASAMENTO, r1['lugar'])} x {label_casamento(LUGARES_CASAMENTO, r2['lugar'])}")

    p = pontuar_multiselect(r1["bolo"], r2["bolo"])
    total += p
    comuns_bolo = list(set(r1["bolo"]) & set(r2["bolo"]))
    if p == 10:
        compat.append(f"🎂 Bolo: 2 sabores em comum ({', '.join(label_casamento(BOLOS_CASAMENTO, x) for x in comuns_bolo)})")
    elif p == 5:
        compat.append(f"🎂 Bolo: 1 sabor em comum ({label_casamento(BOLOS_CASAMENTO, comuns_bolo[0])})")
    else:
        diverg.append(f"🎂 Bolo: {', '.join(label_casamento(BOLOS_CASAMENTO, x) for x in r1['bolo'])} x {', '.join(label_casamento(BOLOS_CASAMENTO, x) for x in r2['bolo'])}")

    p = pontuar_multiselect(r1["musica"], r2["musica"])
    total += p
    comuns_musica = list(set(r1["musica"]) & set(r2["musica"]))
    if p == 10:
        compat.append(f"🎵 Música: 2 gêneros em comum ({', '.join(label_casamento(MUSICAS_CASAMENTO, x) for x in comuns_musica)})")
    elif p == 5:
        compat.append(f"🎵 Música: 1 gênero em comum ({label_casamento(MUSICAS_CASAMENTO, comuns_musica[0])})")
    else:
        diverg.append(f"🎵 Música: {', '.join(label_casamento(MUSICAS_CASAMENTO, x) for x in r1['musica'])} x {', '.join(label_casamento(MUSICAS_CASAMENTO, x) for x in r2['musica'])}")

    p = pontuar_proximidade(ORDENACAO_PERIODO_CASAMENTO, r1["periodo"], r2["periodo"])
    total += p
    if p == 10:
        compat.append(f"🌅 Período: {label_casamento(PERIODOS_CASAMENTO, r1['periodo'])}")
    elif p == 5:
        compat.append(f"🌅 Período parecido: {label_casamento(PERIODOS_CASAMENTO, r1['periodo'])} x {label_casamento(PERIODOS_CASAMENTO, r2['periodo'])}")
    else:
        diverg.append(f"🌅 Período: {label_casamento(PERIODOS_CASAMENTO, r1['periodo'])} x {label_casamento(PERIODOS_CASAMENTO, r2['periodo'])}")

    p = pontuar_proximidade(ORDENACAO_QTD_CASAMENTO, r1["qtd_convidados"], r2["qtd_convidados"])
    total += p
    if p == 10:
        compat.append(f"👥 Quantidade: {label_casamento(QTD_CONVIDADOS_CASAMENTO, r1['qtd_convidados'])}")
    elif p == 5:
        compat.append(f"👥 Quantidade parecida: {label_casamento(QTD_CONVIDADOS_CASAMENTO, r1['qtd_convidados'])} x {label_casamento(QTD_CONVIDADOS_CASAMENTO, r2['qtd_convidados'])}")
    else:
        diverg.append(f"👥 Quantidade: {label_casamento(QTD_CONVIDADOS_CASAMENTO, r1['qtd_convidados'])} x {label_casamento(QTD_CONVIDADOS_CASAMENTO, r2['qtd_convidados'])}")

    p = pontuar_proximidade(ORDENACAO_TIPO_CASAMENTO, r1["tipo_convidados"], r2["tipo_convidados"])
    total += p
    if p == 10:
        compat.append(f"💌 Tipo de convidados: {label_casamento(TIPO_CONVIDADOS_CASAMENTO, r1['tipo_convidados'])}")
    elif p == 5:
        compat.append(f"💌 Tipo parecido: {label_casamento(TIPO_CONVIDADOS_CASAMENTO, r1['tipo_convidados'])} x {label_casamento(TIPO_CONVIDADOS_CASAMENTO, r2['tipo_convidados'])}")
    else:
        diverg.append(f"💌 Tipo de convidados: {label_casamento(TIPO_CONVIDADOS_CASAMENTO, r1['tipo_convidados'])} x {label_casamento(TIPO_CONVIDADOS_CASAMENTO, r2['tipo_convidados'])}")

    p = pontuar_igual(r1["decoracao"], r2["decoracao"])
    total += p
    if p == 10:
        compat.append(f"🎀 Decoração: {label_casamento(DECORACOES_CASAMENTO, r1['decoracao'])}")
    else:
        diverg.append(f"🎀 Decoração: {label_casamento(DECORACOES_CASAMENTO, r1['decoracao'])} x {label_casamento(DECORACOES_CASAMENTO, r2['decoracao'])}")

    porcentagem = round((total / maximo) * 100)

    return {
        "pontos": total,
        "maximo": maximo,
        "porcentagem": porcentagem,
        "nivel": nivel_compatibilidade(porcentagem),
        "compatibilidades": compat,
        "divergencias": diverg,
    }

# ================= CASAMENTO EMBEDS =================

def criar_embed_painel_casamento():
    embed = nextcord.Embed(
        title="💍 Compatibilidade do Casamento",
        description=(
            "Cliquem no botão abaixo para montar as escolhas do grande dia.\n\n"
            "O resultado só aparece quando **os dois** estiverem prontos. 💖"
        ),
        color=0xFF69B4
    )
    embed.set_footer(text="Painel de compatibilidade do casal")
    return embed


def criar_embed_menu_casamento(user: nextcord.User):
    return nextcord.Embed(
        title="💌 Painel privado de compatibilidade",
        description=(
            f"Oi, {user.mention}.\n\n"
            "Use os botões abaixo para preencher, editar ou enviar suas escolhas."
        ),
        color=0xFF69B4
    )


def criar_embed_resultado_casamento(resultado: dict):
    barra_cheia = max(1, resultado["porcentagem"] // 10)
    barra = "█" * barra_cheia + "░" * (10 - barra_cheia)

    recompensa = calcular_recompensa_casamento(resultado["porcentagem"])

    embed = nextcord.Embed(
        title="💍 Resultado da Compatibilidade",
        description=(
            f"<@{SEU_ID}> + <@{ID_DA_NOIVA}>\n\n"
            f"**Compatibilidade final:** `{resultado['porcentagem']}%`\n"
            f"`{barra}`\n"
            f"**Nível:** {resultado['nivel']}"
        ),
        color=0xFFD700
    )

    embed.add_field(
        name="✅ Compatibilidades",
        value="\n".join(resultado["compatibilidades"]) if resultado["compatibilidades"] else "Nenhuma compatibilidade encontrada.",
        inline=False
    )

    embed.add_field(
        name="❌ Diferenças",
        value="\n".join(resultado["divergencias"]) if resultado["divergencias"] else "Nenhuma diferença encontrada.",
        inline=False
    )

    texto_recompensa = f"+{recompensa['moedas']} moedas para cada"
    if recompensa["mimos"] > 0:
        texto_recompensa += f"\n+{recompensa['mimos']} mimo(s) para cada"

    embed.add_field(
        name="🎁 Recompensas",
        value=texto_recompensa,
        inline=False
    )

    embed.set_footer(text="O amor venceu mais uma escolha do casamento 💖")
    return embed

# ========================================

def create_gif_panel_embed():
    embed = nextcord.Embed(
        title="🖼️ Compressor de GIF",
        description=(
            "Envie seu GIF e eu vou tentar comprimir para **até 512 KB**.\n\n"
            "Escolha abaixo o modo que você quer usar."
        ),
        color=0xFF69B4
    )

    embed.add_field(
        name="🖼️ Comprimir normal",
        value="Tenta reduzir o tamanho sem destruir muito a animação.",
        inline=False
    )

    embed.add_field(
        name="💥 Forçar 512KB",
        value="Se precisar, reduz qualidade, cores, escala e até frames para caber em 512 KB.",
        inline=False
    )

    embed.set_footer(text="Painel de compressão de GIF")
    return embed


def quantize_preserving_transparency(img: Image.Image, colors: int) -> Image.Image:
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    transparent_mask = alpha.point(lambda a: 255 if a <= 10 else 0)

    rgb = Image.new("RGB", rgba.size, (255, 255, 255))
    rgb.paste(rgba, mask=alpha)

    pal = rgb.quantize(
        colors=min(colors, 255),
        method=Image.Quantize.FASTOCTREE,
        dither=Image.Dither.NONE
    )

    transparent_index = 255

    palette = pal.getpalette()
    if palette is None:
        palette = [0, 0, 0] * 256
    elif len(palette) < 768:
        palette += [0] * (768 - len(palette))
    pal.putpalette(palette)

    pal.paste(transparent_index, mask=transparent_mask)
    pal.info["transparency"] = transparent_index
    return pal


def resize_frame_keep_aspect(frame: Image.Image, scale: float) -> Image.Image:
    frame = frame.convert("RGBA")
    new_w = max(1, int(frame.width * scale))
    new_h = max(1, int(frame.height * scale))
    return frame.resize((new_w, new_h), Image.Resampling.LANCZOS)


def compress_gif_quality(data: bytes) -> io.BytesIO:
    if not os.path.exists(GIFSICLE_PATH):
        raise RuntimeError(f"gifsicle.exe não encontrado em: {GIFSICLE_PATH}")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.gif")
        work_path = os.path.join(temp_dir, "work.gif")
        output_path = os.path.join(temp_dir, "output.gif")

        with open(input_path, "wb") as f:
            f.write(data)

        def rodar_gifsicle(entrada, saida, extra_args=None):
            if extra_args is None:
                extra_args = []

            cmd = [GIFSICLE_PATH, "-O3", *extra_args, entrada, "-o", saida]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "Erro ao rodar gifsicle.")

        tentativas_diretas = [
            ["--colors", "256"],
            ["--colors", "256", "--lossy=20"],
            ["--colors", "256", "--lossy=40"],
            ["--colors", "192", "--lossy=40"],
            ["--colors", "160", "--lossy=60"],
        ]

        for tentativa in tentativas_diretas:
            try:
                rodar_gifsicle(input_path, output_path, tentativa)
                if os.path.exists(output_path):
                    tamanho = os.path.getsize(output_path)
                    if tamanho <= MAX_FIG_SIZE:
                        with open(output_path, "rb") as f:
                            return io.BytesIO(f.read())
            except Exception as e:
                print(f"[AVISO] qualidade direta falhou: {e}")

        original = Image.open(io.BytesIO(data))
        loop = original.info.get("loop", 0)

        escalas = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]
        color_sets = [256, 192, 160]
        lossy_sets = [20, 40, 60]

        melhor_bytes = None
        melhor_tamanho = None

        original_frames = []
        original_durations = []

        for frame in ImageSequence.Iterator(original):
            fr = frame.copy().convert("RGBA")
            original_frames.append(fr)
            original_durations.append(frame.info.get("duration", 80))

        if not original_frames:
            raise ValueError("Não consegui ler os frames do GIF.")

        for scale in escalas:
            frames = []
            durations = []

            for i, frame in enumerate(original_frames):
                resized = resize_frame_keep_aspect(frame, scale)
                frames.append(resized)
                durations.append(original_durations[i] if i < len(original_durations) else 80)

            for colors in color_sets:
                paletted_frames = []

                for frame in frames:
                    paletted = quantize_preserving_transparency(frame, colors)
                    paletted_frames.append(paletted)

                if not paletted_frames:
                    continue

                paletted_frames[0].save(
                    work_path,
                    format="GIF",
                    save_all=True,
                    append_images=paletted_frames[1:],
                    optimize=False,
                    loop=loop,
                    duration=durations,
                    disposal=2,
                    transparency=255
                )

                for lossy in lossy_sets:
                    try:
                        rodar_gifsicle(
                            work_path,
                            output_path,
                            [f"--lossy={lossy}"]
                        )

                        if os.path.exists(output_path):
                            tamanho = os.path.getsize(output_path)

                            if melhor_tamanho is None or tamanho < melhor_tamanho:
                                melhor_tamanho = tamanho
                                with open(output_path, "rb") as f:
                                    melhor_bytes = f.read()

                            if tamanho <= MAX_FIG_SIZE:
                                print(
                                    f"[OK] GIF qualidade | scale={scale} colors={colors} lossy={lossy} "
                                    f"| {round(tamanho / 1024, 1)} KB"
                                )
                                with open(output_path, "rb") as f:
                                    return io.BytesIO(f.read())

                    except Exception as e:
                        print(f"[AVISO] qualidade resize falhou: {e}")

        if melhor_bytes is not None:
            raise ValueError(
                f"Não consegui chegar em 512KB sem pesar demais a compressão. "
                f"O menor tamanho ficou em {round(melhor_tamanho / 1024, 1)} KB."
            )

        raise ValueError("Não consegui processar esse GIF.")


def compress_gif_force(data: bytes) -> io.BytesIO:
    if not os.path.exists(GIFSICLE_PATH):
        raise RuntimeError(f"gifsicle.exe não encontrado em: {GIFSICLE_PATH}")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.gif")
        work_path = os.path.join(temp_dir, "work.gif")
        output_path = os.path.join(temp_dir, "output.gif")

        with open(input_path, "wb") as f:
            f.write(data)

        def rodar_gifsicle(entrada, saida, extra_args=None):
            if extra_args is None:
                extra_args = []

            cmd = [GIFSICLE_PATH, "-O3", *extra_args, entrada, "-o", saida]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "Erro ao rodar gifsicle.")

        tentativas_diretas = [
            ["--colors", "128", "--lossy=80"],
            ["--colors", "96", "--lossy=120"],
            ["--colors", "64", "--lossy=160"],
            ["--colors", "48", "--lossy=200"],
            ["--colors", "32", "--lossy=240"],
        ]

        for tentativa in tentativas_diretas:
            try:
                rodar_gifsicle(input_path, output_path, tentativa)
                if os.path.exists(output_path):
                    tamanho = os.path.getsize(output_path)
                    if tamanho <= MAX_FIG_SIZE:
                        with open(output_path, "rb") as f:
                            return io.BytesIO(f.read())
            except Exception as e:
                print(f"[AVISO] força direta falhou: {e}")

        original = Image.open(io.BytesIO(data))
        loop = original.info.get("loop", 0)

        escalas = [0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30]
        frame_steps = [1, 2, 3, 4, 5]
        color_sets = [128, 96, 64, 48, 32, 16]
        lossy_sets = [80, 120, 160, 200, 240, 300]

        melhor_bytes = None
        melhor_tamanho = None

        original_frames = []
        original_durations = []

        for frame in ImageSequence.Iterator(original):
            fr = frame.copy().convert("RGBA")
            original_frames.append(fr)
            original_durations.append(frame.info.get("duration", 80))

        if not original_frames:
            raise ValueError("Não consegui ler os frames do GIF.")

        for scale in escalas:
            for frame_step in frame_steps:
                frames = []
                durations = []

                for i, frame in enumerate(original_frames):
                    if i % frame_step != 0:
                        continue

                    duration = original_durations[i] if i < len(original_durations) else 80
                    duration = max(80, duration * frame_step)

                    resized = resize_frame_keep_aspect(frame, scale)
                    frames.append(resized)
                    durations.append(duration)

                if not frames:
                    continue

                for colors in color_sets:
                    paletted_frames = []

                    for frame in frames:
                        paletted = quantize_preserving_transparency(frame, colors)
                        paletted_frames.append(paletted)

                    if not paletted_frames:
                        continue

                    paletted_frames[0].save(
                        work_path,
                        format="GIF",
                        save_all=True,
                        append_images=paletted_frames[1:],
                        optimize=False,
                        loop=loop,
                        duration=durations,
                        disposal=2,
                        transparency=255
                    )

                    for lossy in lossy_sets:
                        try:
                            rodar_gifsicle(
                                work_path,
                                output_path,
                                [f"--lossy={lossy}"]
                            )

                            if os.path.exists(output_path):
                                tamanho = os.path.getsize(output_path)

                                if melhor_tamanho is None or tamanho < melhor_tamanho:
                                    melhor_tamanho = tamanho
                                    with open(output_path, "rb") as f:
                                        melhor_bytes = f.read()

                                if tamanho <= MAX_FIG_SIZE:
                                    print(
                                        f"[OK] GIF forçado | "
                                        f"scale={scale} step={frame_step} colors={colors} lossy={lossy} "
                                        f"| {round(tamanho / 1024, 1)} KB"
                                    )
                                    with open(output_path, "rb") as f:
                                        return io.BytesIO(f.read())

                        except Exception as e:
                            print(f"[AVISO] força agressiva falhou: {e}")

        if melhor_bytes is not None:
            raise ValueError(
                f"Não consegui chegar em 512KB. O menor tamanho ficou em {round(melhor_tamanho / 1024, 1)} KB."
            )

        raise ValueError("Não consegui processar esse GIF.")


def quantize_preserving_transparency(img: Image.Image, colors: int) -> Image.Image:
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")

    transparent_mask = alpha.point(lambda a: 255 if a <= 10 else 0)

    rgb = Image.new("RGB", rgba.size, (255, 255, 255))
    rgb.paste(rgba, mask=alpha)

    pal = rgb.quantize(
        colors=min(colors, 255),
        method=Image.Quantize.FASTOCTREE,
        dither=Image.Dither.NONE
    )

    transparent_index = 255

    palette = pal.getpalette()
    if palette is None:
        palette = [0, 0, 0] * 256
    elif len(palette) < 768:
        palette += [0] * (768 - len(palette))

    pal.putpalette(palette)
    pal.paste(transparent_index, mask=transparent_mask)
    pal.info["transparency"] = transparent_index

    return pal


# ==============midia
def mensagem_tem_midia(message: nextcord.Message) -> bool:
    if message.attachments:
        return True

    if message.embeds:
        return True

    content_lower = message.content.lower()
    media_exts = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov", ".webm")

    if ("http://" in content_lower or "https://" in content_lower) and any(ext in content_lower for ext in media_exts):
        return True

    return False


async def reagir_midia_categoria_existente():
    guild = bot.guilds[0] if bot.guilds else None
    if guild is None:
        return

    categoria = guild.get_channel(CATEGORIA_MIDIA_ID)
    if not categoria or not isinstance(categoria, nextcord.CategoryChannel):
        print("Categoria de mídia não encontrada.")
        return

    emoji = bot.get_emoji(1495102972680736768)
    if emoji is None:
        print("Emoji check não encontrado.")
        return

    for canal in categoria.text_channels:
        try:
            async for message in canal.history(limit=None, oldest_first=True):
                if message.author.bot:
                    continue

                if not mensagem_tem_midia(message):
                    continue

                ja_tem = False
                for reaction in message.reactions:
                    if str(reaction.emoji) == str(emoji):
                        ja_tem = True
                        break

                if not ja_tem:
                    try:
                        await message.add_reaction(emoji)
                    except Exception as e:
                        print(f"Erro ao reagir em {canal.name}: {e}")

        except Exception as e:
            print(f"Erro ao ler histórico de {canal.name}: {e}")


# ================= CASAMENTO SELECTS =================

class LugarCasamentoSelect(Select):
    def __init__(self):
        options = [nextcord.SelectOption(label=label, value=value) for value, label in LUGARES_CASAMENTO]
        super().__init__(placeholder="Escolha o lugar...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta_casamento(interaction.user.id, "lugar", self.values[0])
        await interaction.response.send_message("📍 Lugar salvo.", ephemeral=True)


class BoloCasamentoSelect(Select):
    def __init__(self):
        options = [nextcord.SelectOption(label=label, value=value) for value, label in BOLOS_CASAMENTO]
        super().__init__(placeholder="Escolha 2 sabores de bolo...", min_values=2, max_values=2, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta_casamento(interaction.user.id, "bolo", self.values)
        await interaction.response.send_message("🎂 Sabores salvos.", ephemeral=True)


class MusicaCasamentoSelect(Select):
    def __init__(self):
        options = [nextcord.SelectOption(label=label, value=value) for value, label in MUSICAS_CASAMENTO]
        super().__init__(placeholder="Escolha 2 gêneros musicais...", min_values=2, max_values=2, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta_casamento(interaction.user.id, "musica", self.values)
        await interaction.response.send_message("🎵 Gêneros salvos.", ephemeral=True)


class PeriodoCasamentoSelect(Select):
    def __init__(self):
        options = [nextcord.SelectOption(label=label, value=value) for value, label in PERIODOS_CASAMENTO]
        super().__init__(placeholder="Escolha o período...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta_casamento(interaction.user.id, "periodo", self.values[0])
        await interaction.response.send_message("🌅 Período salvo.", ephemeral=True)


class QtdConvidadosCasamentoSelect(Select):
    def __init__(self):
        options = [nextcord.SelectOption(label=label, value=value) for value, label in QTD_CONVIDADOS_CASAMENTO]
        super().__init__(placeholder="Escolha a quantidade de convidados...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta_casamento(interaction.user.id, "qtd_convidados", self.values[0])
        await interaction.response.send_message("👥 Quantidade salva.", ephemeral=True)


class TipoConvidadosCasamentoSelect(Select):
    def __init__(self):
        options = [nextcord.SelectOption(label=label, value=value) for value, label in TIPO_CONVIDADOS_CASAMENTO]
        super().__init__(placeholder="Escolha o tipo de convidados...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta_casamento(interaction.user.id, "tipo_convidados", self.values[0])
        await interaction.response.send_message("💌 Tipo de convidados salvo.", ephemeral=True)


class DecoracaoCasamentoSelect(Select):
    def __init__(self):
        options = [nextcord.SelectOption(label=label, value=value) for value, label in DECORACOES_CASAMENTO]
        super().__init__(placeholder="Escolha a decoração...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta_casamento(interaction.user.id, "decoracao", self.values[0])
        await interaction.response.send_message("🎀 Decoração salva.", ephemeral=True)


class FormularioCasamentoParte1(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(LugarCasamentoSelect())
        self.add_item(BoloCasamentoSelect())
        self.add_item(MusicaCasamentoSelect())
        self.add_item(PeriodoCasamentoSelect())

    @nextcord.ui.button(label="➡️ Próxima página", style=nextcord.ButtonStyle.blurple)
    async def proxima(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Agora complete a segunda parte:",
            view=FormularioCasamentoParte2(),
            ephemeral=True
        )


class FormularioCasamentoParte2(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(QtdConvidadosCasamentoSelect())
        self.add_item(TipoConvidadosCasamentoSelect())
        self.add_item(DecoracaoCasamentoSelect())


class MenuCasamentoView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @nextcord.ui.button(label="📋 Ir para as opções", style=nextcord.ButtonStyle.primary)
    async def opcoes(self, button: Button, interaction: nextcord.Interaction):
        if not usuario_autorizado_casamento(interaction.user.id):
            await interaction.response.send_message("❌ Só o casal pode usar esse painel.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Preencha a primeira parte das opções:",
            view=FormularioCasamentoParte1(),
            ephemeral=True
        )

    @nextcord.ui.button(label="✏️ Editar informações", style=nextcord.ButtonStyle.secondary)
    async def editar(self, button: Button, interaction: nextcord.Interaction):
        if not usuario_autorizado_casamento(interaction.user.id):
            await interaction.response.send_message("❌ Só o casal pode usar esse painel.", ephemeral=True)
            return

        data = load_casamento()
        uid = str(interaction.user.id)
        respostas = data["usuarios"][uid]["respostas"]

        if not respostas:
            await interaction.response.send_message(
                "⚠️ Você ainda não salvou nada. Use `Ir para as opções` primeiro.",
                ephemeral=True
            )
            return

        data["usuarios"][uid]["pronto_resultado"] = False
        save_casamento(data)

        await interaction.response.send_message(
            "✏️ Modo de edição aberto. Altere o que quiser:",
            view=FormularioCasamentoParte1(),
            ephemeral=True
        )

    @nextcord.ui.button(label="📨 Enviar e ver resultado", style=nextcord.ButtonStyle.green)
    async def enviar(self, button: Button, interaction: nextcord.Interaction):
        if not usuario_autorizado_casamento(interaction.user.id):
            await interaction.response.send_message("❌ Só o casal pode usar esse painel.", ephemeral=True)
            return

        data = load_casamento()
        uid = str(interaction.user.id)

        respostas = data["usuarios"][uid]["respostas"]
        if not validar_respostas_casamento(respostas):
            await interaction.response.send_message(
                "⚠️ Você ainda não respondeu tudo.",
                ephemeral=True
            )
            return

        data["usuarios"][uid]["pronto_resultado"] = True
        data["usuarios"][uid]["ultimo_envio"] = int(time.time())
        save_casamento(data)

        outro_id = SEU_ID if interaction.user.id == ID_DA_NOIVA else ID_DA_NOIVA
        outro_uid = str(outro_id)

        outro_pronto = data["usuarios"][outro_uid]["pronto_resultado"]
        outro_completo = validar_respostas_casamento(data["usuarios"][outro_uid]["respostas"])

        log_ok(f"Usuário {interaction.user.id} marcou pronto no casamento.")

        if not outro_pronto or not outro_completo:
            await interaction.response.send_message(
                "💌 Suas escolhas foram enviadas. Agora falta a outra pessoa ficar pronta.",
                ephemeral=True
            )
            return

        r1 = data["usuarios"][str(SEU_ID)]["respostas"]
        r2 = data["usuarios"][str(ID_DA_NOIVA)]["respostas"]

        resultado = calcular_compatibilidade_casamento(r1, r2)
        data["ultima_rodada_id"] += 1
        rodada_id = data["ultima_rodada_id"]

        data["ultimo_resultado"] = {
            "rodada_id": rodada_id,
            "gerado_em": int(time.time()),
            "resultado": resultado
        }

        data["usuarios"][str(SEU_ID)]["pronto_resultado"] = False
        data["usuarios"][str(ID_DA_NOIVA)]["pronto_resultado"] = False
        save_casamento(data)

        recompensa_key = f"rodada_{rodada_id}"
        if recompensa_key not in data["recompensas_entregues"]:
            recompensa = calcular_recompensa_casamento(resultado["porcentagem"])
            adicionar_recompensa_db(SEU_ID, moedas=recompensa["moedas"], mimos=recompensa["mimos"])
            adicionar_recompensa_db(ID_DA_NOIVA, moedas=recompensa["moedas"], mimos=recompensa["mimos"])
            data["recompensas_entregues"].append(recompensa_key)
            save_casamento(data)
            log_ok(f"Recompensas do casamento entregues na rodada {rodada_id}.")

        embed = criar_embed_resultado_casamento(resultado)
        canal = bot.get_channel(CANAL_CASAMENTO)

        if canal:
            await canal.send(embed=embed)
            log_ok("Resultado do casamento enviado no canal.")
        else:
            log_warn("Canal de casamento não encontrado para enviar resultado.")

        await interaction.response.send_message(
            "💍 Os dois estavam prontos. O resultado foi revelado!",
            ephemeral=True
        )


class PainelCasamentoView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="💍 Começar compatibilidade", style=nextcord.ButtonStyle.green, custom_id="painel_casamento_comecar")
    async def comecar(self, button: Button, interaction: nextcord.Interaction):
        if not usuario_autorizado_casamento(interaction.user.id):
            await interaction.response.send_message("❌ Esse painel é exclusivo do casal.", ephemeral=True)
            return

        await interaction.response.send_message(
            embed=criar_embed_menu_casamento(interaction.user),
            view=MenuCasamentoView(),
            ephemeral=True
        )


# =============================

class GifPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _processar_gif(self, interaction: nextcord.Interaction, modo: str):
        await interaction.response.send_message(
            "📩 Envie um **GIF** neste canal em até **2 minutos**.",
            ephemeral=True
        )

        def check(msg: nextcord.Message):
            return (
                msg.author.id == interaction.user.id
                and msg.channel.id == interaction.channel.id
                and len(msg.attachments) > 0
            )

        try:
            msg = await bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "⏰ Tempo esgotado. Clique no botão novamente.",
                ephemeral=True
            )
            return

        attachment = msg.attachments[0]
        filename = attachment.filename.lower()

        if not filename.endswith(".gif"):
            await interaction.followup.send(
                "❌ O arquivo enviado não é um GIF.",
                ephemeral=True
            )
            return

        try:
            texto = "🛠️ Comprimindo o GIF sem destruir muito..." if modo == "quality" else "💥 Forçando compressão para 512KB..."
            await interaction.followup.send(texto, ephemeral=True)

            data = await attachment.read()

            if modo == "quality":
                result = compress_gif_quality(data)
                nome = "gif_comprimido_qualidade.gif"
            else:
                result = compress_gif_force(data)
                nome = "gif_comprimido_forcado.gif"

            size_kb = round(result.getbuffer().nbytes / 1024, 1)
            result.seek(0)

            await interaction.followup.send(
                content=f"✅ GIF pronto. Tamanho final: **{size_kb} KB**",
                file=nextcord.File(result, filename=nome),
                ephemeral=True
            )

            log_ok(f"GIF comprimido | modo={modo} | user={interaction.user} | tamanho={size_kb} KB")

        except Exception as e:
            log_erro(f"Erro ao comprimir GIF | modo={modo} | erro={e}")
            await interaction.followup.send(
                f"❌ Falha ao comprimir o GIF.\n`{e}`",
                ephemeral=True
            )

    @nextcord.ui.button(label="🖼️ Comprimir normal", style=nextcord.ButtonStyle.green, custom_id="gif_panel_normal")
    async def comprimir_normal(self, button: Button, interaction: nextcord.Interaction):
        await self._processar_gif(interaction, "quality")

    @nextcord.ui.button(label="💥 Forçar 512KB", style=nextcord.ButtonStyle.red, custom_id="gif_panel_force")
    async def comprimir_forcado(self, button: Button, interaction: nextcord.Interaction):
        await self._processar_gif(interaction, "force")


# ======================================== bebe======


@bot.command()
async def vip(ctx: commands.Context):
    data = get_user(ctx.author.id)
    user = data[str(ctx.author.id)]
    agora = int(time.time())

    vip_nome = "Nenhum"
    cargo_nome = "Nenhum"
    comprado_em = "Não registrado"
    expira_em = "Nenhum"

    if user.get("vip"):
        key = user["vip"]
        vip = VIPS.get(key)
        if vip:
            vip_nome = vip["nome"]
            cargo = ctx.guild.get_role(vip["cargo_id"])
            cargo_nome = cargo.mention if cargo else "Cargo não encontrado"

        if user.get("vip_comprado_em"):
            comprado_em = f"<t:{user['vip_comprado_em']}:F>"

        if user.get("vip_expira", 0) > agora:
            restante = user["vip_expira"] - agora
            dias = restante // 86400
            horas = (restante % 86400) // 3600
            minutos = (restante % 3600) // 60
            expira_em = f"{dias}d {horas}h {minutos}m"
        else:
            expira_em = "Expirado ❌"

    protegido_status = "❌ Não"
    protegido_comprado = "Não registrado"
    protegido_expira = "Nenhum"

    if user.get("protegido"):
        protegido_status = "✅ Ativo"
        if user.get("protegido_comprado_em"):
            protegido_comprado = f"<t:{user['protegido_comprado_em']}:F>"
        if user.get("protegido_expira", 0) > agora:
            restante = user["protegido_expira"] - agora
            dias = restante // 86400
            horas = (restante % 86400) // 3600
            minutos = (restante % 3600) // 60
            protegido_expira = f"{dias}d {horas}h {minutos}m"
        else:
            protegido_status = "Expirado ❌"
            protegido_expira = "Expirado ❌"

    embed = nextcord.Embed(
        title="💎 Perfil Premium",
        description="Aqui estão suas informações atuais no sistema.",
        color=0xFF69B4,
        timestamp=nextcord.utils.utcnow()
    )

    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    embed.add_field(name="👤 Usuário", value=ctx.author.mention, inline=False)
    embed.add_field(name="👑 VIP Atual", value=vip_nome, inline=True)
    embed.add_field(name="🎭 Cargo", value=cargo_nome, inline=True)
    embed.add_field(name="⏳ VIP expira em", value=expira_em, inline=True)

    embed.add_field(name="🛍️ VIP comprado em", value=comprado_em, inline=False)
    embed.add_field(name="🛡️ Protegido", value=protegido_status, inline=True)
    embed.add_field(name="🛒 Protegido comprado em", value=protegido_comprado, inline=True)
    embed.add_field(name="⏳ Protegido expira em", value=protegido_expira, inline=True)

    embed.add_field(name="<:moeda:1492371478362980393> Moedas", value=f"```{user['moedas']}```", inline=True)
    embed.add_field(name="<:mimo:1492379169999552563> Mimos", value=f"```{user['mimos']}```", inline=True)
    embed.add_field(name="📌 Conversão", value="100 mimos = 10 moedas", inline=False)

    embed.set_footer(
        text=f"{ctx.guild.name} • Status do seu perfil",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    await ctx.send(embed=embed, view=FecharVipView(ctx.author.id))


@bot.event
async def on_message(message: nextcord.Message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    if mensagem_tem_midia(message):
        try:
            if isinstance(message.channel, nextcord.TextChannel):
                # categoria de mídia
                categoria = message.channel.category
                if categoria and categoria.id == CATEGORIA_MIDIA_ID:
                    emoji = bot.get_emoji(1495102972680736768)
                    if emoji and not any(str(r.emoji) == str(emoji) for r in message.reactions):
                        await message.add_reaction(emoji)

                # canais específicos antigos
                if message.channel.id in CANAIS_REACAO:
                    emoji2 = bot.get_emoji(CANAIS_REACAO[message.channel.id])
                    if emoji2 and not any(str(r.emoji) == str(emoji2) for r in message.reactions):
                        await message.add_reaction(emoji2)

        except Exception as e:
            print(f"Erro ao reagir automaticamente: {e}")

    await bot.process_commands(message)


@bot.slash_command(name="fig", description="Comprime imagem ou GIF para até 512KB")
async def fig(interaction: nextcord.Interaction):
    await interaction.response.send_message(
        "Envie o anexo neste canal em até 2 minutos.",
        ephemeral=True
    )

    def check(msg: nextcord.Message):
        return (
            msg.author.id == interaction.user.id
            and msg.channel.id == interaction.channel.id
            and len(msg.attachments) > 0
        )

    try:
        msg = await bot.wait_for("message", timeout=120, check=check)
    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ Tempo esgotado. Use `/fig` novamente.", ephemeral=True)
        return

    attachment = msg.attachments[0]
    filename = attachment.filename.lower()

    if not filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        await interaction.followup.send("❌ Envie PNG, JPG, WEBP ou GIF.", ephemeral=True)
        return

    try:
        await interaction.followup.send("🛠️ Processando arquivo...", ephemeral=True)

        data = await attachment.read()

        if filename.endswith(".gif"):
            result = compress_gif_force(data)
            out_name = "figurinha.gif"
        else:
            result = compress_static_image(data)
            out_name = "figurinha.png"

        size_kb = round(result.getbuffer().nbytes / 1024, 1)
        result.seek(0)

        await interaction.followup.send(
            content=f"✅ Pronto. Tamanho final: **{size_kb} KB**",
            file=nextcord.File(result, filename=out_name),
            ephemeral=True
        )

    except Exception as e:
        print(f"Erro no /fig: {e}")
        await interaction.followup.send(
            f"❌ Erro ao processar o arquivo: `{e}`",
            ephemeral=True
        )


@bot.command()
async def painelcasamento(ctx: commands.Context):
    if ctx.channel.id != CANAL_CASAMENTO:
        await ctx.send("❌ Esse comando só pode ser usado no canal de casamento.")
        return

    await ctx.send(embed=criar_embed_painel_casamento(), view=PainelCasamentoView())
    log_ok("Painel de casamento enviado manualmente.")


@bot.command()
async def painelgif(ctx: commands.Context):
    if ctx.channel.id != CANAL_COMANDOS:
        await ctx.send("❌ Esse comando só pode ser usado no canal de comandos.")
        return

    await ctx.send(embed=create_gif_panel_embed(), view=GifPanelView())
    log_ok("Painel de GIF enviado manualmente.")

@bot.command()
async def reagirmidias(ctx: commands.Context):
    await ctx.send("⏳ Vou começar a reagir as mídias antigas da categoria.")
    try:
        await reagir_midia_categoria_existente()
        await ctx.send("✅ Reações antigas concluídas.")
    except Exception as e:
        await ctx.send(f"❌ Erro ao reagir mídias antigas: {e}")


# =========== ticket

@bot.slash_command(name="painelembed", description="Envia o painel de ticket")
async def painelembed(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Negado.", ephemeral=True)
        return

    cfg = load_config()
    canal = interaction.guild.get_channel(cfg["panel_channel_id"])

    if isinstance(canal, nextcord.TextChannel):
        await canal.send(embed=build_panel_embed(cfg), view=TicketPanelView())
        await interaction.response.send_message("Painel enviado.", ephemeral=True)
    else:
        await interaction.response.send_message("Canal do painel inválido.", ephemeral=True)


@bot.slash_command(name="ticketconfig", description="Configura o sistema de ticket")
async def ticketconfig(
    interaction: nextcord.Interaction,
    canal_painel: nextcord.TextChannel,
    cargo_gestor: nextcord.Role,
    canal_logs: nextcord.TextChannel,
    titulo: str,
    descricao: str,
    imagem: str = "",
    nome_ticket: str = "Report Love",
    descricao_ticket: str = "Abra um ticket.",
    imagem_ticket: str = "",
    icone: str = "💗",
    placeholder: str = "Escolha uma opção",
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Permissão negada.", ephemeral=True)
        return

    cfg = load_config()
    cfg.update(
        {
            "panel_channel_id": canal_painel.id,
            "manager_role_id": cargo_gestor.id,
            "log_channel_id": canal_logs.id,
            "panel_title": titulo,
            "panel_description": descricao,
            "panel_image_url": imagem or "",
            "ticket_name": nome_ticket,
            "ticket_description": descricao_ticket,
            "ticket_image_url": imagem_ticket or "",
            "ticket_icon": icone,
            "select_placeholder": placeholder,
        }
    )
    save_config(cfg)

    await interaction.response.send_message("Configuração salva.", ephemeral=True)


@bot.slash_command(
    name="ticketcfgview", description="Mostra a configuração atual do ticket"
)
async def ticketcfgview(interaction: nextcord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Permissão negada.", ephemeral=True)
        return

    cfg = load_config()
    embed = build_config_embed(cfg, interaction.guild)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ================ cl
@bot.slash_command(name="cl", description="Apaga mensagens do canal")
async def cl(
    interaction: nextcord.Interaction,
    quantidade: int = nextcord.SlashOption(
        name="quantidade",
        description="Quantidade de mensagens para apagar",
        required=True,
        min_value=1,
        max_value=100,
    ),
):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ Você não tem permissão para apagar mensagens.", ephemeral=True
        )
        return

    canal = interaction.channel
    if not isinstance(canal, nextcord.TextChannel):
        await interaction.response.send_message(
            "❌ Esse comando só funciona em canal de texto.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"🧹 Apagando {quantidade} mensagens...", ephemeral=True
    )

    await canal.purge(limit=quantidade)


bot_ready_once = False

@bot.event
async def on_ready():
    global bot_ready_once

    print("\n" + "=" * 50)
    print(f"Bot online como {bot.user}")
    print("=" * 50)

    if bot_ready_once:
        print("on_ready já executado antes, pulando reinicialização.")
        return

    bot_ready_once = True

    try:
        await bot.sync_all_application_commands()
        log_ok("Comandos sincronizados.")
    except Exception as e:
        log_erro(f"Erro ao sincronizar comandos: {e}")

    try:
        if not verificar_vips.is_running():
            verificar_vips.start()
        log_ok("Task verificar_vips iniciada.")
    except Exception as e:
        log_erro(f"Erro ao iniciar verificar_vips: {e}")

    try:
        bot.add_view(ShopView())
        log_ok("View persistente da shop carregada.")
    except Exception as e:
        log_erro(f"Erro ao carregar view da shop: {e}")

    try:
        bot.add_view(PainelCasamentoView())
        log_ok("View persistente do casamento carregada.")
    except Exception as e:
        log_erro(f"Erro ao carregar view do casamento: {e}")

    try:
        bot.add_view(GifPanelView())
        log_ok("View persistente do painel de GIF carregada.")
    except Exception as e:
        log_erro(f"Erro ao carregar view do painel de GIF: {e}")

    try:
        if os.path.exists(GIFSICLE_PATH):
            log_ok(f"gifsicle encontrado em: {GIFSICLE_PATH}")
        else:
            log_warn(f"gifsicle não encontrado em: {GIFSICLE_PATH}")
    except Exception as e:
        log_erro(f"Erro ao verificar gifsicle: {e}")

    try:
        await send_or_update_panel(
            channel_id=CANAL_SHOP,
            panel_key="shop_panel",
            embed=create_shop_embed(),
            view=ShopView()
        )
        log_ok("Painel da shop enviado/atualizado.")
    except Exception as e:
        log_erro(f"Erro no painel da shop: {e}")

    try:
        await send_or_update_panel(
            channel_id=1491170989160136704,
            panel_key="welcome_panel",
            embed=create_welcome_embed(bot, bot.user),
            view=None
        )
        log_ok("Painel de boas-vindas enviado/atualizado.")
    except Exception as e:
        log_erro(f"Erro no painel de boas-vindas: {e}")

    try:
        await send_or_update_panel(
            channel_id=CANAL_COMANDOS,
            panel_key="gif_panel",
            embed=create_gif_panel_embed(),
            view=GifPanelView()
        )
        log_ok("Painel de GIF enviado/atualizado.")
    except Exception as e:
        log_erro(f"Erro no painel de GIF: {e}")

    # ===== BEBÊ =====
    try:
        registrar_views_bebe(bot, bebe_sistema)
        log_ok("Views persistentes do bebê carregadas.")
    except Exception as e:
        log_erro(f"Erro ao carregar views do bebê: {e}")

    try:
        if not bebe_sistema.loop_bebe.is_running():
            bebe_sistema.iniciar_loops()
            log_ok("Loop do bebê iniciado.")
        else:
            log_ok("Loop do bebê já estava rodando.")
    except Exception as e:
        log_erro(f"Erro ao iniciar loop do bebê: {e}")

    try:
        if not bebe_sistema.data.get("setup"):
            await bebe_sistema.atualizar_setup()
            log_ok("Setup do bebê enviado/atualizado.")
        else:
            await bebe_sistema.atualizar_painel_principal()
            log_ok("Painel principal do bebê enviado/atualizado.")
    except Exception as e:
        log_erro(f"Erro ao atualizar sistema do bebê: {e}")

    # ===== TICKET =====
    try:
        setup_ticket_system(bot)
        bot.add_view(TicketPanelView())
        log_ok("View persistente do ticket carregada.")
    except Exception as e:
        log_erro(f"Erro ao carregar view do ticket: {e}")

    try:
        if not ticket_reminder_loop.is_running():
            ticket_reminder_loop.start()
        log_ok("Loop do ticket iniciado.")
    except Exception as e:
        log_erro(f"Erro ao iniciar loop do ticket: {e}")

    try:
        cfg = load_config()
        await send_or_update_panel(
            channel_id=cfg["panel_channel_id"],
            panel_key="ticket_panel",
            embed=build_panel_embed(cfg),
            view=TicketPanelView()
        )
        log_ok("Painel de ticket enviado/atualizado.")
    except Exception as e:
        log_erro(f"Erro ao enviar/atualizar painel de ticket: {e}")

    log_ok("Bot pronto.")
    print("=" * 50 + "\n") 


# Carrega as variáveis do arquivo .env
load_dotenv()

# Pega o token de forma segura
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO: O DISCORD_TOKEN não foi encontrado no arquivo .env")
