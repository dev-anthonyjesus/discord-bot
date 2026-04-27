import json
import os
import random
import time

import nextcord
from nextcord.ext import tasks

from .embeds_bebe import (
    embed_setup_bebe,
    embed_principal_bebe,
    embed_admin_bebe,
    embed_adicionais_bebe,
    embed_memoria_bebe,
    nome_imagem_por_estado,
    caminho_imagem,
)
from .views_bebe import (
    SetupBebeView,
    PainelBebeView,
    BabyAdminView,
    AdicionaisBebeView,
    MomentosBebeView,
)

SEU_ID = 1431111401522462741
ID_DA_NOIVA = 715329753032163379
CANAL_BEBE = 1494700943894118466
NOIVO_ROLE_ID = 1491166369859764314
NOIVA_ROLE_ID = 1491166441515257927
BEBE_FILE = "bebe_virtual.json"
MEMORIAS_DIR = "memorias_bebe"

PRECO_ADICIONAIS = {
    "baba": 45,
    "brinquedo": 15,
    "chupeta": 8,
    "remedio": 18,
    "comida_especial": 20,
    "passeio": 22,
    "musica_ninar": 12,
}


def agora_ts() -> int:
    return int(time.time())


def hora_local() -> tuple[int, int]:
    t = time.localtime()
    return t.tm_hour, t.tm_min


def data_local_str() -> str:
    t = time.localtime()
    return f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}"


class BebeSistema:
    def __init__(self, bot):
        self.bot = bot
        self.data = self.load()

    def get_default_data(self):
        return {
            "setup": False,
            "setup_message_id": None,
            "painel_message_id": None,
            "nome": "Bebê",
            "genero": "Neutro",
            "tracos": [],
            "traco_noivo": None,
            "traco_noiva": None,
            "estado": "tranquilo",
            "ultimo_estado": "tranquilo",
            "fome": 18,
            "fralda": 12,
            "sono": 15,
            "atencao": 18,
            "higiene": 10,
            "humor": 82,
            "satisfacao_geral": 80,
            "disp_noivo": 100,
            "disp_noiva": 100,
            "cuidados_dia": 0,
            "ultimo_cuidado": None,
            "quem_cuidou_por_ultimo": None,
            "ultimo_ciclo_ts": 0,
            "ultima_noite_data": None,
            "ultima_manha_data": None,
            "mensagem": "Tudo tranquilo por enquanto.",
            "evento_noite": None,
            "ultimo_alerta": None,
            "ultima_memoria_auto_ts": 0,
            "ultima_memoria_nome": None,
        }

    def load(self):
        default = self.get_default_data()

        if not os.path.exists(BEBE_FILE):
            with open(BEBE_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4, ensure_ascii=False)
            return default

        try:
            with open(BEBE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        for k, v in default.items():
            data.setdefault(k, v)

        self.data = data
        self.atualizar_satisfacao_geral()
        self.save()
        return self.data

    def save(self):
        with open(BEBE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_canal(self):
        return self.bot.get_channel(CANAL_BEBE)

    def setup_pronto(self) -> bool:
        return bool(
            self.data.get("nome")
            and self.data.get("genero")
            and self.data.get("traco_noivo")
            and self.data.get("traco_noiva")
        )

    def ativo_agora(self) -> bool:
        h, m = hora_local()
        minutos = h * 60 + m
        return 420 <= minutos <= 1290  # 07:00 até 21:30

    def calcular_satisfacao_geral(self) -> int:
        componentes = [
            100 - self.data.get("fome", 0),
            100 - self.data.get("fralda", 0),
            100 - self.data.get("sono", 0),
            100 - self.data.get("atencao", 0),
            100 - self.data.get("higiene", 0),
            self.data.get("humor", 100),
        ]
        return max(0, min(100, round(sum(componentes) / len(componentes))))

    def atualizar_satisfacao_geral(self):
        self.data["satisfacao_geral"] = self.calcular_satisfacao_geral()

    def iniciar(self):
        if not self.loop_bebe.is_running():
            self.loop_bebe.start()

    def iniciar_loops(self):
        self.iniciar()

    async def enviar_arquivo_imagem(self, chave_imagem: str):
        nome = nome_imagem_por_estado(chave_imagem)
        if not nome:
            return None
        path = caminho_imagem(nome)
        if not path:
            return None
        return nextcord.File(path, filename=nome)

    async def enviar_setup_inicial(self):
        canal = self.get_canal()
        if not canal:
            return

        embed = embed_setup_bebe(self.data)
        view = SetupBebeView(self)
        msg_id = self.data.get("setup_message_id")

        if msg_id:
            try:
                msg = await canal.fetch_message(msg_id)
                await msg.edit(
                    content=f"<@&{NOIVO_ROLE_ID}> <@&{NOIVA_ROLE_ID}>",
                    embed=embed,
                    view=view,
                )
                return
            except Exception:
                pass

        msg = await canal.send(
            content=f"<@&{NOIVO_ROLE_ID}> <@&{NOIVA_ROLE_ID}>",
            embed=embed,
            view=view,
        )
        self.data["setup_message_id"] = msg.id
        self.save()

    async def atualizar_setup(self):
        await self.enviar_setup_inicial()

    async def remover_setup(self):
        canal = self.get_canal()
        if not canal:
            return

        msg_id = self.data.get("setup_message_id")
        if not msg_id:
            return

        try:
            msg = await canal.fetch_message(msg_id)
            await msg.delete()
        except Exception:
            pass

        self.data["setup_message_id"] = None
        self.save()

    async def atualizar_painel_principal(self):
        canal = self.get_canal()
        if not canal:
            return

        self.atualizar_satisfacao_geral()
        self.atualizar_estado()

        embed = embed_principal_bebe(self.data)
        view = PainelBebeView(self)

        img_key = (
            "dormindo"
            if self.data.get("estado") == "dormindo"
            else self.data.get("estado", "tranquilo")
        )
        file = await self.enviar_arquivo_imagem(img_key)
        if file:
            embed.set_thumbnail(url=f"attachment://{file.filename}")

        msg_id = self.data.get("painel_message_id")
        if msg_id:
            try:
                msg = await canal.fetch_message(msg_id)
                if file:
                    await msg.edit(embed=embed, view=view, attachments=[file], content=None)
                else:
                    await msg.edit(embed=embed, view=view, content=None)
                return
            except Exception:
                pass

        if file:
            msg = await canal.send(embed=embed, view=view, file=file)
        else:
            msg = await canal.send(embed=embed, view=view)

        self.data["painel_message_id"] = msg.id
        self.save()

    async def finalizar_setup(self):
        self.data["tracos"] = [
            self.data.get("traco_noivo"),
            self.data.get("traco_noiva"),
        ]
        self.data["setup"] = True
        self.data["mensagem"] = "O bebê foi configurado e agora precisa de cuidados."
        self.atualizar_satisfacao_geral()
        self.save()

        await self.remover_setup()
        await self.atualizar_painel_principal()

    def aplicar_efeitos_tracos_no_decay(self) -> dict:
        mods = {
            "fome": 0,
            "fralda": 0,
            "sono": 0,
            "atencao": 0,
            "higiene": 0,
            "humor_queda": 0,
        }

        tracos = set(self.data.get("tracos", []))

        if "calminho" in tracos:
            mods["fome"] -= 1
            mods["fralda"] -= 1
            mods["sono"] -= 1
            mods["atencao"] -= 1

        if "sensivel" in tracos:
            mods["humor_queda"] += 2

        if "intenso" in tracos:
            mods["fome"] += 2
            mods["humor_queda"] += 1

        if "grudento" in tracos:
            mods["atencao"] += 2

        if "agitado" in tracos:
            mods["sono"] += 2

        return mods

    def aplicar_bonus_cuidado(self, tipo: str, bonus_base: int) -> int:
        tracos = set(self.data.get("tracos", []))
        bonus = bonus_base

        if tipo == "atencao" and "risonho" in tracos:
            bonus += 8

        if tipo == "dormir" and "agitado" in tracos:
            bonus -= 8

        if tipo == "atencao" and "grudento" in tracos:
            bonus += 4

        return max(4, bonus)

    def atualizar_estado(self):
        media_ruim = (
            self.data["fome"]
            + self.data["fralda"]
            + self.data["sono"]
            + self.data["atencao"]
            + self.data["higiene"]
        ) / 5

        humor = self.data["humor"]
        anterior = self.data.get("estado", "tranquilo")

        if not self.ativo_agora():
            novo = "dormindo"
        elif media_ruim >= 88 or humor <= 18:
            novo = "colapso"
        elif media_ruim >= 68 or humor <= 38:
            novo = "chorando bastante"
        elif media_ruim >= 42 or humor <= 58:
            novo = "instável"
        else:
            novo = "tranquilo"

        self.data["ultimo_estado"] = anterior
        self.data["estado"] = novo

    def atualizar_humor_por_necessidades(self):
        media = (
            self.data["fome"]
            + self.data["fralda"]
            + self.data["sono"]
            + self.data["atencao"]
            + self.data["higiene"]
        ) / 5

        queda = 0
        if media >= 80:
            queda = 6
        elif media >= 65:
            queda = 4
        elif media >= 50:
            queda = 2

        queda += self.aplicar_efeitos_tracos_no_decay()["humor_queda"]
        self.data["humor"] = max(0, min(100, self.data["humor"] - queda))

    def aplicar_decay_diurno(self):
        mods = self.aplicar_efeitos_tracos_no_decay()

        self.data["fome"] = min(100, self.data["fome"] + random.randint(3, 6) + mods["fome"])
        self.data["fralda"] = min(100, self.data["fralda"] + random.randint(2, 5) + mods["fralda"])
        self.data["sono"] = min(100, self.data["sono"] + random.randint(3, 6) + mods["sono"])
        self.data["atencao"] = min(100, self.data["atencao"] + random.randint(2, 5) + mods["atencao"])
        self.data["higiene"] = min(100, self.data["higiene"] + random.randint(2, 4) + mods["higiene"])

        for k in ["fome", "fralda", "sono", "atencao", "higiene"]:
            self.data[k] = max(0, min(100, self.data[k]))

    async def processar_noite_e_manha(self):
        hoje = data_local_str()

        if not self.ativo_agora() and self.data.get("ultima_noite_data") != hoje:
            evento = random.choice(
            [
            "noite tranquila",
            "noite difícil",
            "acordou algumas vezes",
            "chorou muito",
            "dormiu bem",
            ]
        )
            self.data["evento_noite"] = evento
            self.data["ultima_noite_data"] = hoje
            self.data["estado"] = "dormindo"
            self.data["sono"] = 0

            if evento == "noite tranquila":
                self.data["mensagem"] = "🌙 A noite está tranquila. O bebê dormiu sem muitos problemas."
            elif evento == "dormiu bem":
                self.data["mensagem"] = "🌙 Ele finalmente adormeceu e descansou bem."
            elif evento == "acordou algumas vezes":
                self.data["mensagem"] = "🌙 O bebê acordou algumas vezes durante a madrugada."
            elif evento == "chorou muito":
                self.data["mensagem"] = "🌙 A madrugada foi difícil e ele chorou bastante."
            else:
                self.data["mensagem"] = "🌙 A noite foi difícil e cansativa."

            self.save()

        if self.ativo_agora() and self.data.get("ultima_manha_data") != hoje:
            evento = self.data.get("evento_noite") or "noite tranquila"

            self.data["ultima_manha_data"] = hoje
            self.data["cuidados_dia"] = 0
            self.data["ultimo_alerta"] = None

            if evento in ["noite tranquila", "dormiu bem"]:
                self.data["fome"] = random.randint(18, 28)
                self.data["fralda"] = random.randint(15, 25)
                self.data["sono"] = random.randint(12, 22)
                self.data["atencao"] = random.randint(15, 28)
                self.data["higiene"] = random.randint(10, 20)
                self.data["humor"] = random.randint(76, 90)
                self.data["disp_noivo"] = random.randint(82, 100)
                self.data["disp_noiva"] = random.randint(82, 100)
                self.data["mensagem"] = "☀️ O bebê acordou bem hoje."
            elif evento == "acordou algumas vezes":
                self.data["fome"] = random.randint(25, 38)
                self.data["fralda"] = random.randint(20, 34)
                self.data["sono"] = random.randint(28, 42)
                self.data["atencao"] = random.randint(25, 38)
                self.data["higiene"] = random.randint(15, 28)
                self.data["humor"] = random.randint(58, 76)
                self.data["disp_noivo"] = random.randint(70, 92)
                self.data["disp_noiva"] = random.randint(70, 92)
                self.data["mensagem"] = "☀️ O bebê acordou um pouco cansado."
            else:
                self.data["fome"] = random.randint(35, 50)
                self.data["fralda"] = random.randint(30, 45)
                self.data["sono"] = random.randint(38, 58)
                self.data["atencao"] = random.randint(30, 48)
                self.data["higiene"] = random.randint(25, 40)
                self.data["humor"] = random.randint(40, 65)
                self.data["disp_noivo"] = random.randint(60, 85)
                self.data["disp_noiva"] = random.randint(60, 85)
                self.data["mensagem"] = "☀️ O bebê acordou mais sensível hoje."

            self.atualizar_satisfacao_geral()
            self.atualizar_estado()
            self.save()
            await self.atualizar_painel_principal()

    def nome_cuidador(self, user_id: int) -> str:
        if user_id == SEU_ID:
            return "Noivo"
        if user_id == ID_DA_NOIVA:
            return "Noiva"
        return "Alguém"

    async def cuidar(self, interaction: nextcord.Interaction, acao: str):
        if self.data.get("estado") == "dormindo" or not self.ativo_agora():
            await interaction.response.send_message(
            "😴 O bebê está dormindo agora. Você só pode cuidar dele entre 07:00 e 21:30.",
            ephemeral=True
    )
            return

        bonus = 0
        texto = ""

        if acao == "mamadeira":
            bonus = self.aplicar_bonus_cuidado("fome", 24)
            self.data["fome"] = max(0, self.data["fome"] - bonus)
            self.data["humor"] = min(100, self.data["humor"] + 4)
            texto = f"🍼 {interaction.user.mention} deu mamadeira no bebê."
        elif acao == "fralda":
            bonus = self.aplicar_bonus_cuidado("fralda", 26)
            self.data["fralda"] = max(0, self.data["fralda"] - bonus)
            self.data["higiene"] = max(0, self.data["higiene"] - 12)
            self.data["humor"] = min(100, self.data["humor"] + 3)
            texto = f"🧻 {interaction.user.mention} trocou a fralda do bebê."
        elif acao == "dormir":
            bonus = self.aplicar_bonus_cuidado("dormir", 22)
            self.data["sono"] = max(0, self.data["sono"] - bonus)
            self.data["humor"] = min(100, self.data["humor"] + 5)
            texto = f"😴 {interaction.user.mention} fez o bebê descansar."
        elif acao == "atencao":
            bonus = self.aplicar_bonus_cuidado("atencao", 20)
            self.data["atencao"] = max(0, self.data["atencao"] - bonus)
            self.data["humor"] = min(100, self.data["humor"] + 8)
            texto = f"❤️ {interaction.user.mention} deu atenção ao bebê."
        elif acao == "banho":
            bonus = self.aplicar_bonus_cuidado("higiene", 24)
            self.data["higiene"] = max(0, self.data["higiene"] - bonus)
            self.data["humor"] = min(100, self.data["humor"] + 4)
            texto = f"🧼 {interaction.user.mention} deu banho no bebê."
        else:
            await interaction.response.send_message("❌ Ação inválida.", ephemeral=True)
            return

        self.data["cuidados_dia"] += 1
        self.data["ultimo_cuidado"] = acao.title()
        self.data["quem_cuidou_por_ultimo"] = self.nome_cuidador(interaction.user.id)
        self.data["mensagem"] = texto

        gasto_disposicao = {
         "mamadeira": 8,
         "fralda": 6,
         "dormir": 5,
         "atencao": 4,
         "banho": 10,
        }.get(acao, 5)

        if interaction.user.id == SEU_ID:
            self.data["disp_noivo"] = max(0, self.data.get("disp_noivo", 100) - gasto_disposicao)
        elif interaction.user.id == ID_DA_NOIVA:
            self.data["disp_noiva"] = max(0, self.data.get("disp_noiva", 100) - gasto_disposicao)

        self.atualizar_satisfacao_geral()
        self.atualizar_estado()
        self.save()

        await self.atualizar_painel_principal()
        await interaction.response.send_message("✅ Cuidado aplicado.", ephemeral=True)

    async def usar_adicional(self, interaction: nextcord.Interaction, tipo: str):
        if tipo == "baba":
            self.data["fome"] = max(0, self.data["fome"] - 8)
            self.data["fralda"] = max(0, self.data["fralda"] - 8)
            self.data["sono"] = max(0, self.data["sono"] - 8)
            self.data["atencao"] = max(0, self.data["atencao"] - 8)
            self.data["higiene"] = max(0, self.data["higiene"] - 8)
            self.data["humor"] = min(100, self.data["humor"] + 6)
            self.data["mensagem"] = "👩‍🍼 A babá ajudou bastante hoje."
        elif tipo == "brinquedo":
            self.data["atencao"] = max(0, self.data["atencao"] - 18)
            self.data["humor"] = min(100, self.data["humor"] + 8)
            self.data["mensagem"] = "🧸 O brinquedo distraiu o bebê."
        elif tipo == "chupeta":
            self.data["humor"] = min(100, self.data["humor"] + 5)
            self.data["atencao"] = max(0, self.data["atencao"] - 6)
            self.data["mensagem"] = "🍼 A chupeta acalmou o bebê."
        elif tipo == "remedio":
            self.data["humor"] = min(100, self.data["humor"] + 10)
            self.data["sono"] = max(0, self.data["sono"] - 10)
            self.data["mensagem"] = "💊 O remédio ajudou o bebê a melhorar."
        elif tipo == "comida_especial":
            self.data["fome"] = max(0, self.data["fome"] - 20)
            self.data["humor"] = min(100, self.data["humor"] + 7)
            self.data["mensagem"] = "🍲 A comida especial deixou o bebê mais satisfeito."
        elif tipo == "passeio":
            self.data["atencao"] = max(0, self.data["atencao"] - 10)
            self.data["humor"] = min(100, self.data["humor"] + 12)
            self.data["mensagem"] = "🌳 O passeio melhorou bastante o humor do bebê."
        elif tipo == "musica_ninar":
            self.data["sono"] = max(0, self.data["sono"] - 18)
            self.data["humor"] = min(100, self.data["humor"] + 4)
            self.data["mensagem"] = "🎵 A música de ninar acalmou o bebê."
        else:
            await interaction.response.send_message("❌ Adicional inválido.", ephemeral=True)
            return

        self.atualizar_satisfacao_geral()
        self.atualizar_estado()
        self.save()
        await self.atualizar_painel_principal()
        await interaction.response.send_message("✅ Adicional usado.", ephemeral=True)

    async def abrir_admin(self, interaction: nextcord.Interaction):
        embed = embed_admin_bebe(self.data)
        view = BabyAdminView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def abrir_adicionais(self, interaction: nextcord.Interaction):
        embed = embed_adicionais_bebe()
        view = AdicionaisBebeView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def abrir_painel_adicionais(self, interaction: nextcord.Interaction):
        # Compatibilidade com views antigas que chamam o nome legado.
        await self.abrir_adicionais(interaction)

    async def abrir_momentos(self, interaction: nextcord.Interaction):
        embed = embed_memoria_bebe()
        view = MomentosBebeView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def abrir_painel_momentos(self, interaction: nextcord.Interaction):
        # Compatibilidade com views antigas que chamam o nome legado.
        await self.abrir_momentos(interaction)

    def listar_memorias(self):
        if not os.path.exists(MEMORIAS_DIR):
            os.makedirs(MEMORIAS_DIR, exist_ok=True)
            return []

        arquivos = []
        for nome in os.listdir(MEMORIAS_DIR):
            if nome.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                arquivos.append(nome)

        arquivos.sort()
        return arquivos

    async def enviar_memoria_manual(
        self,
        interaction: nextcord.Interaction,
        foto_nome: str,
        titulo: str,
        descricao: str,
    ):
        canal = self.get_canal()
        if not canal:
            await interaction.response.send_message("❌ Canal do bebê não encontrado.", ephemeral=True)
            return

        path = os.path.join(MEMORIAS_DIR, foto_nome)
        if not os.path.exists(path):
            await interaction.response.send_message("❌ Foto não encontrada.", ephemeral=True)
            return

        embed = embed_memoria_bebe(titulo=titulo, descricao=descricao)
        file = nextcord.File(path, filename=foto_nome)
        embed.set_image(url=f"attachment://{foto_nome}")

        await canal.send(embed=embed, file=file)
        await interaction.response.send_message("✅ Momento enviado.", ephemeral=True)

    async def verificar_alertas(self):
        canal = self.get_canal()
        if not canal or not self.data.get("setup"):
            return

        criticos = []
        if self.data["fome"] >= 85:
            criticos.append("fome")
        if self.data["fralda"] >= 85:
            criticos.append("fralda")
        if self.data["sono"] >= 85:
            criticos.append("sono")
        if self.data["atencao"] >= 85:
            criticos.append("atencao")
        if self.data["higiene"] >= 85:
            criticos.append("higiene")

        if not criticos:
            self.data["ultimo_alerta"] = None
            self.save()
            return

        alerta = ",".join(sorted(criticos))
        if self.data.get("ultimo_alerta") == alerta:
            return

        self.data["ultimo_alerta"] = alerta
        self.save()

        nomes = {
            "fome": "🍼 fome",
            "fralda": "🧻 fralda",
            "sono": "😴 sono",
            "atencao": "❤️ atenção",
            "higiene": "🧼 higiene",
        }

        texto = ", ".join(nomes[c] for c in criticos)
        await canal.send(f"<@&{NOIVO_ROLE_ID}> <@&{NOIVA_ROLE_ID}> o bebê precisa de: **{texto}**.")

    @tasks.loop(minutes=15)
    async def loop_bebe(self):
        if not self.data.get("setup"):
            await self.atualizar_setup()
            return

        await self.processar_noite_e_manha()
             

        agora = agora_ts()
        ultimo = self.data.get("ultimo_ciclo_ts", 0)

        if self.ativo_agora() and (agora - ultimo >= 900):
            self.aplicar_decay_diurno()
            self.atualizar_humor_por_necessidades()
            self.atualizar_estado()
            self.atualizar_satisfacao_geral()
            self.data["ultimo_ciclo_ts"] = agora

            if self.data["estado"] == "colapso":
                self.data["mensagem"] = "🚨 O bebê entrou em colapso e precisa de cuidados urgentes."
            elif self.data["estado"] == "chorando bastante":
                self.data["mensagem"] = "😭 O bebê está chorando bastante."
            elif self.data["estado"] == "instável":
                self.data["mensagem"] = "😕 O bebê está mais instável agora."
            else:
                self.data["mensagem"] = "🙂 O bebê está estável no momento."

            self.save()
            await self.atualizar_painel_principal()
            await self.verificar_alertas()
        else:
            await self.atualizar_painel_principal()

    @loop_bebe.before_loop
    async def before_loop_bebe(self):
        await self.bot.wait_until_ready()


async def setup_bebe(bot, sistema_instancia: BebeSistema | None = None):
    sistema = sistema_instancia if sistema_instancia is not None else BebeSistema(bot)
    if not sistema.loop_bebe.is_running():
        sistema.loop_bebe.start()
    await sistema.atualizar_setup()
    return sistema
