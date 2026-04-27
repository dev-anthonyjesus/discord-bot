import asyncio
import io
from typing import List, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageSequence

MAX_SIZE = 512 * 1024  # 512 KB
STICKER_SIZE = (320, 320)
MAX_FIG_SIZE = 512 * 1024  # 512 KB
FIG_DIM = (320, 320)


def fit_on_canvas(image: Image.Image, scale: float = 1.0) -> Image.Image:
    img = image.convert("RGBA")
    canvas = Image.new("RGBA", FIG_DIM, (0, 0, 0, 0))

    max_w = max(1, int(FIG_DIM[0] * scale))
    max_h = max(1, int(FIG_DIM[1] * scale))

    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    x = (FIG_DIM[0] - img.width) // 2
    y = (FIG_DIM[1] - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


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


def prepare_gif_frames(data: bytes, scale: float, colors: int):
    img = Image.open(io.BytesIO(data))
    frames = []
    durations = []
    loop = img.info.get("loop", 0)

    for frame in ImageSequence.Iterator(img):
        duration = frame.info.get("duration", 80)
        fitted = fit_on_canvas(frame.convert("RGBA"), scale=scale)
        paletted = fitted.convert(
            "P", palette=Image.Palette.ADAPTIVE, colors=colors)
        frames.append(paletted)
        durations.append(duration)

    return frames, durations, loop


def compress_gif(data: bytes) -> io.BytesIO:
    attempts = [
        (1.0, 128),
        (0.95, 128),
        (0.9, 96),
        (0.85, 64),
        (0.8, 64),
        (0.75, 48),
        (0.7, 32),
        (0.65, 24),
        (0.6, 16),
    ]

    for scale, colors in attempts:
        frames, durations, loop = prepare_gif_frames(data, scale, colors)

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

        if output.getbuffer().nbytes <= MAX_FIG_SIZE:
            return output

    raise ValueError("Não consegui comprimir o GIF para 512KB.")

def fit_on_sticker_canvas(image: Image.Image, scale: float = 1.0) -> Image.Image:
    """Redimensiona mantendo proporção e centraliza numa tela 320x320 transparente."""
    img = image.convert("RGBA")
    canvas = Image.new("RGBA", STICKER_SIZE, (0, 0, 0, 0))

    max_w = max(1, int(STICKER_SIZE[0] * scale))
    max_h = max(1, int(STICKER_SIZE[1] * scale))

    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    x = (STICKER_SIZE[0] - img.width) // 2
    y = (STICKER_SIZE[1] - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


def compress_static_image(data: bytes) -> io.BytesIO:
    """Converte imagem estática para PNG 320x320 <= 512KB."""
    original = Image.open(io.BytesIO(data))
    processed = fit_on_sticker_canvas(original, scale=1.0)

    output = io.BytesIO()
    processed.save(output, format="PNG", optimize=True, compress_level=9)
    output.seek(0)

    if output.getbuffer().nbytes > MAX_SIZE:
        # fallback: reduz o conteúdo dentro do canvas
        for scale in [0.9, 0.8, 0.7, 0.6, 0.5]:
            processed = fit_on_sticker_canvas(original, scale=scale)
            output = io.BytesIO()
            processed.save(output, format="PNG",
                           optimize=True, compress_level=9)
            output.seek(0)
            if output.getbuffer().nbytes <= MAX_SIZE:
                return output

        raise ValueError("Não consegui comprimir a imagem para 512KB.")
    return output


def _prepare_gif_frames(data: bytes, scale: float, colors: int) -> Tuple[List[Image.Image], List[int], int]:
    img = Image.open(io.BytesIO(data))
    frames: List[Image.Image] = []
    durations: List[int] = []
    loop = img.info.get("loop", 0)

    for frame in ImageSequence.Iterator(img):
        duration = frame.info.get("duration", 80)

        fitted = fit_on_sticker_canvas(frame.convert("RGBA"), scale=scale)

        # reduz paleta para diminuir tamanho
        paletted = fitted.convert(
            "P", palette=Image.Palette.ADAPTIVE, colors=colors)
        frames.append(paletted)
        durations.append(duration)

    return frames, durations, loop


def compress_gif(data: bytes) -> io.BytesIO:
    """Converte GIF para 320x320 e tenta ficar <= 512KB."""
    attempts = [
        (1.0, 128),
        (0.95, 128),
        (0.9, 96),
        (0.85, 64),
        (0.8, 64),
        (0.75, 48),
        (0.7, 32),
        (0.65, 24),
        (0.6, 16),
    ]

    for scale, colors in attempts:
        frames, durations, loop = _prepare_gif_frames(
            data, scale=scale, colors=colors)

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
            transparency=0,
        )
        output.seek(0)

        if output.getbuffer().nbytes <= MAX_SIZE:
            return output

    raise ValueError("Não consegui comprimir o GIF para 512KB.")


class FigCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="fig", description="Converte imagem ou GIF para figurinha 320x320 e até 512KB")
    async def fig(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Envie a imagem ou GIF neste canal em até 2 minutos.",
            ephemeral=True
        )

        def check(msg: discord.Message) -> bool:
            return (
                msg.author.id == interaction.user.id
                and msg.channel.id == interaction.channel_id
                and len(msg.attachments) > 0
            )

        try:
            msg = await self.bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "Tempo esgotado. Use `/fig` novamente.",
                ephemeral=True
            )
            return

        attachment = msg.attachments[0]
        filename = attachment.filename.lower()

        if not any(filename.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")):
            await interaction.followup.send(
                "Formato inválido. Envie PNG, JPG, WEBP ou GIF.",
                ephemeral=True
            )
            return

        try:
            data = await attachment.read()

            if filename.endswith(".gif"):
                result = compress_gif(data)
                out_name = "figurinha.gif"
            else:
                result = compress_static_image(data)
                out_name = "figurinha.png"

            size_kb = round(result.getbuffer().nbytes / 1024, 1)

            await interaction.followup.send(
                content=f"Pronto. Arquivo final: **{size_kb} KB**",
                file=discord.File(fp=result, filename=out_name),
                ephemeral=True
            )

        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                f"Erro ao processar o arquivo: `{e}`",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(FigCog(bot))
