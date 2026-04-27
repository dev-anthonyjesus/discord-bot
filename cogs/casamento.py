"""Cog: Sistema de compatibilidade do casamento."""
import json
import time
import logging
import os

import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Select, Button

from utils.constants import CANAL_CASAMENTO, SEU_ID, ID_DA_NOIVA, CASAMENTO_FILE
from utils.db import get_user, save_db

log = logging.getLogger(__name__)


# ── JSON helpers ─────────────────────────────────────────────────────────────

def _estrutura_default() -> dict:
    return {
        "canal_id": CANAL_CASAMENTO,
        "casal_ids": [SEU_ID, ID_DA_NOIVA],
        "usuarios": {
            str(SEU_ID): {"respostas": {}, "pronto_resultado": False, "ultimo_envio": None},
            str(ID_DA_NOIVA): {"respostas": {}, "pronto_resultado": False, "ultimo_envio": None},
        },
        "ultima_rodada_id": 0,
        "ultimo_resultado": None,
        "recompensas_entregues": [],
    }


def load_casamento() -> dict:
    if not os.path.exists(CASAMENTO_FILE):
        data = _estrutura_default()
        _save(data)
        return data
    try:
        with open(CASAMENTO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = {}

    data.setdefault("usuarios", {})
    for uid in [str(SEU_ID), str(ID_DA_NOIVA)]:
        data["usuarios"].setdefault(uid, {"respostas": {}, "pronto_resultado": False, "ultimo_envio": None})
    data.setdefault("ultima_rodada_id", 0)
    data.setdefault("ultimo_resultado", None)
    data.setdefault("recompensas_entregues", [])
    _save(data)
    return data


def _save(data: dict) -> None:
    with open(CASAMENTO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def usuario_autorizado(user_id: int) -> bool:
    return user_id in (SEU_ID, ID_DA_NOIVA)


def salvar_resposta(user_id: int, campo: str, valor) -> None:
    data = load_casamento()
    data["usuarios"][str(user_id)]["respostas"][campo] = valor
    data["usuarios"][str(user_id)]["pronto_resultado"] = False
    _save(data)


def validar_respostas(respostas: dict) -> bool:
    obrigatorios = ["lugar", "bolo", "musica", "periodo", "qtd_convidados", "tipo_convidados", "decoracao"]
    for campo in obrigatorios:
        if campo not in respostas:
            return False
    if not isinstance(respostas.get("bolo"), list) or len(respostas["bolo"]) != 2:
        return False
    if not isinstance(respostas.get("musica"), list) or len(respostas["musica"]) != 2:
        return False
    return True


# ── Opções ────────────────────────────────────────────────────────────────────

LUGARES = [("praia","Praia"),("igreja","Igreja"),("campo","Campo / Sítio"),("salao","Salão elegante"),("jardim","Jardim"),("simples","Algo simples / íntimo")]
BOLOS   = [("chocolate","Chocolate"),("morango","Morango"),("red_velvet","Red Velvet"),("ninho","Ninho"),("baunilha","Baunilha"),("prestigio","Prestígio"),("doce_de_leite","Doce de leite")]
MUSICAS = [("romantico","Romântico"),("sertanejo","Sertanejo"),("pop","Pop"),("pagode","Pagode"),("mpb","MPB"),("gospel","Gospel"),("funk","Funk"),("eletronica","Eletrônica")]
PERIODOS = [("manha","Manhã"),("tarde","Tarde"),("por_do_sol","Pôr do sol"),("noite","Noite")]
QTD_CONVIDADOS = [("mini","Só nós dois / mini cerimônia"),("intimo","Bem íntimo"),("pequeno","Pequeno"),("medio","Médio"),("grande","Grande"),("muita_gente","Muita gente")]
TIPO_CONVIDADOS = [("familia_proxima","Só família próxima"),("familia_amigos_proximos","Família + amigos próximos"),("misto","Família + amigos + alguns conhecidos"),("todos_importantes","Todo mundo importante"),("festa_grande","Festa grande com conhecidos também")]
DECORACOES = [("luxuosa","Luxuosa"),("minimalista","Minimalista"),("romantica","Romântica"),("floral","Floral"),("elegante_escura","Elegante escura"),("fofa","Fofa / delicada"),("rustica","Rústica")]

ORDENACAO_PERIODO   = {"manha":0,"tarde":1,"por_do_sol":2,"noite":3}
ORDENACAO_QTD       = {"mini":0,"intimo":1,"pequeno":2,"medio":3,"grande":4,"muita_gente":5}
ORDENACAO_TIPO      = {"familia_proxima":0,"familia_amigos_proximos":1,"misto":2,"todos_importantes":3,"festa_grande":4}


def label(opcoes: list, valor: str) -> str:
    for k, v in opcoes:
        if k == valor:
            return v
    return valor


# ── Lógica de pontuação ───────────────────────────────────────────────────────

def _pontuar_igual(a, b) -> int:
    return 10 if a == b else 0


def _pontuar_proximidade(mapa: dict, a: str, b: str) -> int:
    if a == b:
        return 10
    return 5 if abs(mapa.get(a, 999) - mapa.get(b, 999)) == 1 else 0


def _pontuar_multiselect(a: list, b: list) -> int:
    comuns = len(set(a) & set(b))
    return 10 if comuns >= 2 else (5 if comuns == 1 else 0)


def nivel_compat(p: int) -> str:
    if p <= 20: return "Casamento caótico 😭"
    if p <= 40: return "Vai precisar de negociação 😂"
    if p <= 60: return "Tem química, mas precisam alinhar 💫"
    if p <= 80: return "Casal bem conectado 💕"
    return "Almas gêmeas do altar 💍"


def calcular_recompensa(porcentagem: int) -> dict:
    if porcentagem == 100: return {"moedas": 20, "mimos": 1}
    if porcentagem >= 90:  return {"moedas": 10, "mimos": 1}
    if porcentagem >= 70:  return {"moedas": 10, "mimos": 0}
    return {"moedas": 5, "mimos": 0}


def calcular_compatibilidade(r1: dict, r2: dict) -> dict:
    total, maximo, compat, diverg = 0, 70, [], []

    def check_campo(pts, nome_emoji, opcoes, val1, val2):
        if pts == 10:
            compat.append(f"{nome_emoji}: {label(opcoes, val1)}")
        elif pts == 5:
            compat.append(f"{nome_emoji} parecido: {label(opcoes, val1)} x {label(opcoes, val2)}")
        else:
            diverg.append(f"{nome_emoji}: {label(opcoes, val1)} x {label(opcoes, val2)}")

    p = _pontuar_igual(r1["lugar"], r2["lugar"])
    total += p; check_campo(p, "📍 Lugar", LUGARES, r1["lugar"], r2["lugar"])

    p = _pontuar_multiselect(r1["bolo"], r2["bolo"])
    total += p
    comuns_b = list(set(r1["bolo"]) & set(r2["bolo"]))
    if p >= 5: compat.append(f"🎂 Bolo: {', '.join(label(BOLOS, x) for x in comuns_b)} em comum")
    else: diverg.append(f"🎂 Bolo: {', '.join(label(BOLOS, x) for x in r1['bolo'])} x {', '.join(label(BOLOS, x) for x in r2['bolo'])}")

    p = _pontuar_multiselect(r1["musica"], r2["musica"])
    total += p
    comuns_m = list(set(r1["musica"]) & set(r2["musica"]))
    if p >= 5: compat.append(f"🎵 Música: {', '.join(label(MUSICAS, x) for x in comuns_m)} em comum")
    else: diverg.append(f"🎵 Música: {', '.join(label(MUSICAS, x) for x in r1['musica'])} x {', '.join(label(MUSICAS, x) for x in r2['musica'])}")

    p = _pontuar_proximidade(ORDENACAO_PERIODO, r1["periodo"], r2["periodo"])
    total += p; check_campo(p, "🌅 Período", PERIODOS, r1["periodo"], r2["periodo"])

    p = _pontuar_proximidade(ORDENACAO_QTD, r1["qtd_convidados"], r2["qtd_convidados"])
    total += p; check_campo(p, "👥 Quantidade", QTD_CONVIDADOS, r1["qtd_convidados"], r2["qtd_convidados"])

    p = _pontuar_proximidade(ORDENACAO_TIPO, r1["tipo_convidados"], r2["tipo_convidados"])
    total += p; check_campo(p, "💌 Tipo convidados", TIPO_CONVIDADOS, r1["tipo_convidados"], r2["tipo_convidados"])

    p = _pontuar_igual(r1["decoracao"], r2["decoracao"])
    total += p; check_campo(p, "🎀 Decoração", DECORACOES, r1["decoracao"], r2["decoracao"])

    return {
        "pontos": total,
        "maximo": maximo,
        "porcentagem": round((total / maximo) * 100),
        "nivel": nivel_compat(round((total / maximo) * 100)),
        "compatibilidades": compat,
        "divergencias": diverg,
    }


# ── Embeds ────────────────────────────────────────────────────────────────────

def embed_painel_casamento() -> nextcord.Embed:
    embed = nextcord.Embed(
        title="💍 Compatibilidade do Casamento",
        description=(
            "Cliquem no botão abaixo para montar as escolhas do grande dia.\n\n"
            "O resultado só aparece quando **os dois** estiverem prontos. 💖"
        ),
        color=0xFF69B4,
    )
    embed.set_footer(text="Painel de compatibilidade do casal")
    return embed


def embed_menu(user: nextcord.User) -> nextcord.Embed:
    return nextcord.Embed(
        title="💌 Painel privado de compatibilidade",
        description=f"Oi, {user.mention}.\n\nUse os botões abaixo para preencher, editar ou enviar suas escolhas.",
        color=0xFF69B4,
    )


def embed_resultado(resultado: dict) -> nextcord.Embed:
    barra_cheia = max(1, resultado["porcentagem"] // 10)
    barra       = "█" * barra_cheia + "░" * (10 - barra_cheia)
    recompensa  = calcular_recompensa(resultado["porcentagem"])

    embed = nextcord.Embed(
        title="💍 Resultado da Compatibilidade",
        description=(
            f"<@{SEU_ID}> + <@{ID_DA_NOIVA}>\n\n"
            f"**Compatibilidade final:** `{resultado['porcentagem']}%`\n"
            f"`{barra}`\n"
            f"**Nível:** {resultado['nivel']}"
        ),
        color=0xFFD700,
    )
    embed.add_field(
        name="✅ Compatibilidades",
        value="\n".join(resultado["compatibilidades"]) or "Nenhuma compatibilidade encontrada.",
        inline=False,
    )
    embed.add_field(
        name="❌ Diferenças",
        value="\n".join(resultado["divergencias"]) or "Nenhuma diferença encontrada.",
        inline=False,
    )
    txt = f"+{recompensa['moedas']} moedas para cada"
    if recompensa["mimos"] > 0:
        txt += f"\n+{recompensa['mimos']} mimo(s) para cada"
    embed.add_field(name="🎁 Recompensas", value=txt, inline=False)
    embed.set_footer(text="O amor venceu mais uma escolha do casamento 💖")
    return embed


# ── Selects ───────────────────────────────────────────────────────────────────

class LugarSelect(Select):
    def __init__(self):
        super().__init__(placeholder="Escolha o lugar...", options=[nextcord.SelectOption(label=lbl, value=val) for val, lbl in LUGARES])
    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta(interaction.user.id, "lugar", self.values[0])
        await interaction.response.send_message("📍 Lugar salvo.", ephemeral=True)


class BoloSelect(Select):
    def __init__(self):
        super().__init__(placeholder="Escolha 2 sabores de bolo...", min_values=2, max_values=2, options=[nextcord.SelectOption(label=lbl, value=val) for val, lbl in BOLOS])
    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta(interaction.user.id, "bolo", self.values)
        await interaction.response.send_message("🎂 Sabores salvos.", ephemeral=True)


class MusicaSelect(Select):
    def __init__(self):
        super().__init__(placeholder="Escolha 2 gêneros musicais...", min_values=2, max_values=2, options=[nextcord.SelectOption(label=lbl, value=val) for val, lbl in MUSICAS])
    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta(interaction.user.id, "musica", self.values)
        await interaction.response.send_message("🎵 Gêneros salvos.", ephemeral=True)


class PeriodoSelect(Select):
    def __init__(self):
        super().__init__(placeholder="Escolha o período...", options=[nextcord.SelectOption(label=lbl, value=val) for val, lbl in PERIODOS])
    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta(interaction.user.id, "periodo", self.values[0])
        await interaction.response.send_message("🌅 Período salvo.", ephemeral=True)


class QtdConvidadosSelect(Select):
    def __init__(self):
        super().__init__(placeholder="Quantidade de convidados...", options=[nextcord.SelectOption(label=lbl, value=val) for val, lbl in QTD_CONVIDADOS])
    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta(interaction.user.id, "qtd_convidados", self.values[0])
        await interaction.response.send_message("👥 Quantidade salva.", ephemeral=True)


class TipoConvidadosSelect(Select):
    def __init__(self):
        super().__init__(placeholder="Tipo de convidados...", options=[nextcord.SelectOption(label=lbl, value=val) for val, lbl in TIPO_CONVIDADOS])
    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta(interaction.user.id, "tipo_convidados", self.values[0])
        await interaction.response.send_message("💌 Tipo de convidados salvo.", ephemeral=True)


class DecoracaoSelect(Select):
    def __init__(self):
        super().__init__(placeholder="Escolha a decoração...", options=[nextcord.SelectOption(label=lbl, value=val) for val, lbl in DECORACOES])
    async def callback(self, interaction: nextcord.Interaction):
        salvar_resposta(interaction.user.id, "decoracao", self.values[0])
        await interaction.response.send_message("🎀 Decoração salva.", ephemeral=True)


# ── Views de formulário ───────────────────────────────────────────────────────

class FormularioParte1(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(LugarSelect())
        self.add_item(BoloSelect())
        self.add_item(MusicaSelect())
        self.add_item(PeriodoSelect())

    @nextcord.ui.button(label="➡️ Próxima página", style=nextcord.ButtonStyle.blurple)
    async def proxima(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("Agora complete a segunda parte:", view=FormularioParte2(), ephemeral=True)


class FormularioParte2(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(QtdConvidadosSelect())
        self.add_item(TipoConvidadosSelect())
        self.add_item(DecoracaoSelect())


class MenuCasamentoView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @nextcord.ui.button(label="📋 Ir para as opções", style=nextcord.ButtonStyle.primary)
    async def opcoes(self, button: Button, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message("❌ Só o casal pode usar esse painel.", ephemeral=True)
            return
        await interaction.response.send_message("Preencha a primeira parte das opções:", view=FormularioParte1(), ephemeral=True)

    @nextcord.ui.button(label="✏️ Editar informações", style=nextcord.ButtonStyle.secondary)
    async def editar(self, button: Button, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message("❌ Só o casal pode usar esse painel.", ephemeral=True)
            return
        data = load_casamento()
        uid  = str(interaction.user.id)
        if not data["usuarios"][uid]["respostas"]:
            await interaction.response.send_message("⚠️ Você ainda não salvou nada. Use `Ir para as opções` primeiro.", ephemeral=True)
            return
        data["usuarios"][uid]["pronto_resultado"] = False
        _save(data)
        await interaction.response.send_message("✏️ Modo de edição aberto. Altere o que quiser:", view=FormularioParte1(), ephemeral=True)

    @nextcord.ui.button(label="📨 Enviar e ver resultado", style=nextcord.ButtonStyle.green)
    async def enviar(self, button: Button, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message("❌ Só o casal pode usar esse painel.", ephemeral=True)
            return

        data = load_casamento()
        uid  = str(interaction.user.id)
        if not validar_respostas(data["usuarios"][uid]["respostas"]):
            await interaction.response.send_message("⚠️ Você ainda não respondeu tudo.", ephemeral=True)
            return

        data["usuarios"][uid]["pronto_resultado"] = True
        data["usuarios"][uid]["ultimo_envio"]      = int(time.time())
        _save(data)

        outro_id  = SEU_ID if interaction.user.id == ID_DA_NOIVA else ID_DA_NOIVA
        outro_uid = str(outro_id)

        if not data["usuarios"][outro_uid]["pronto_resultado"] or not validar_respostas(data["usuarios"][outro_uid]["respostas"]):
            await interaction.response.send_message("💌 Suas escolhas foram enviadas. Agora falta a outra pessoa ficar pronta.", ephemeral=True)
            return

        r1       = data["usuarios"][str(SEU_ID)]["respostas"]
        r2       = data["usuarios"][str(ID_DA_NOIVA)]["respostas"]
        resultado = calcular_compatibilidade(r1, r2)

        data["ultima_rodada_id"] += 1
        rodada_id = data["ultima_rodada_id"]
        data["ultimo_resultado"] = {"rodada_id": rodada_id, "gerado_em": int(time.time()), "resultado": resultado}
        data["usuarios"][str(SEU_ID)]["pronto_resultado"]     = False
        data["usuarios"][str(ID_DA_NOIVA)]["pronto_resultado"] = False
        _save(data)

        recompensa_key = f"rodada_{rodada_id}"
        if recompensa_key not in data["recompensas_entregues"]:
            recompensa = calcular_recompensa(resultado["porcentagem"])
            for uid_r in [SEU_ID, ID_DA_NOIVA]:
                db = get_user(uid_r)
                db[str(uid_r)]["moedas"] += recompensa["moedas"]
                db[str(uid_r)]["mimos"]  += recompensa["mimos"]
                save_db(db)
            data["recompensas_entregues"].append(recompensa_key)
            _save(data)

        canal = interaction.client.get_channel(CANAL_CASAMENTO)
        if canal:
            await canal.send(embed=embed_resultado(resultado))

        await interaction.response.send_message("💍 Os dois estavam prontos. O resultado foi revelado!", ephemeral=True)


class PainelCasamentoView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="💍 Começar compatibilidade", style=nextcord.ButtonStyle.green, custom_id="painel_casamento_comecar")
    async def comecar(self, button: Button, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message("❌ Esse painel é exclusivo do casal.", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed_menu(interaction.user), view=MenuCasamentoView(), ephemeral=True)


# ── Cog ───────────────────────────────────────────────────────────────────────

class CasamentoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(PainelCasamentoView())
        log.info("View persistente do casamento carregada.")

    @commands.command()
    async def painelcasamento(self, ctx: commands.Context):
        if ctx.channel.id != CANAL_CASAMENTO:
            await ctx.send("❌ Esse comando só pode ser usado no canal de casamento.")
            return
        await ctx.send(embed=embed_painel_casamento(), view=PainelCasamentoView())
        log.info("Painel de casamento enviado manualmente.")


def setup(bot: commands.Bot):
    bot.add_cog(CasamentoCog(bot))
