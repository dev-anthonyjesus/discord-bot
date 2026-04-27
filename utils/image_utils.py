"""Utilitários de imagem: redimensionamento, compressão de PNG/GIF."""
import io
import os
import subprocess
import tempfile

from PIL import Image, ImageFilter, ImageSequence

from utils.constants import FIG_DIM, GIFSICLE_PATH, MAX_FIG_SIZE


# ── Canvas / redimensionamento ────────────────────────────────────────────────

def fit_on_canvas(image: Image.Image, scale: float = 1.0) -> Image.Image:
    """Coloca a imagem em um canvas FIG_DIM com fundo desfocado."""
    img = image.convert("RGBA")
    target_w, target_h = FIG_DIM

    # fundo preenchido e desfocado
    bg_ratio = max(target_w / img.width, target_h / img.height)
    bg_w = max(1, int(img.width * bg_ratio))
    bg_h = max(1, int(img.height * bg_ratio))
    background = img.resize((bg_w, bg_h), Image.Resampling.LANCZOS)
    left = (bg_w - target_w) // 2
    top  = (bg_h - target_h) // 2
    background = background.crop((left, top, left + target_w, top + target_h))
    background = background.filter(ImageFilter.GaussianBlur(12))

    dark = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 70))
    background = Image.alpha_composite(background, dark)

    # imagem principal centralizada
    fg_ratio = min(target_w / img.width, target_h / img.height) * scale
    fg_w = max(1, int(img.width * fg_ratio))
    fg_h = max(1, int(img.height * fg_ratio))
    foreground = img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
    x = (target_w - fg_w) // 2
    y = (target_h - fg_h) // 2
    background.paste(foreground, (x, y), foreground)
    return background


def resize_frame_keep_aspect(frame: Image.Image, scale: float) -> Image.Image:
    frame = frame.convert("RGBA")
    new_w = max(1, int(frame.width * scale))
    new_h = max(1, int(frame.height * scale))
    return frame.resize((new_w, new_h), Image.Resampling.LANCZOS)


# ── Quantização de paleta GIF preservando transparência ──────────────────────

def quantize_preserving_transparency(img: Image.Image, colors: int) -> Image.Image:
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
    palette = pal.getpalette() or [0, 0, 0] * 256
    if len(palette) < 768:
        palette += [0] * (768 - len(palette))
    pal.putpalette(palette)
    pal.paste(transparent_index, mask=transparent_mask)
    pal.info["transparency"] = transparent_index
    return pal


# ── Compressão de imagem estática (PNG) ──────────────────────────────────────

def compress_static_image(data: bytes) -> io.BytesIO:
    original = Image.open(io.BytesIO(data))

    for scale in [1.0, 0.9, 0.8, 0.7, 0.6]:
        processed = fit_on_canvas(original, scale=scale)
        output = io.BytesIO()
        processed.save(output, format="PNG", optimize=True, compress_level=9)
        output.seek(0)
        if output.getbuffer().nbytes <= MAX_FIG_SIZE:
            return output

    raise ValueError("Não consegui comprimir a imagem para 512 KB.")


# ── Helpers internos de gifsicle ─────────────────────────────────────────────

def _gifsicle_available() -> bool:
    return os.path.exists(GIFSICLE_PATH)


def _run_gifsicle(entrada: str, saida: str, extra_args: list[str] | None = None) -> None:
    cmd = [GIFSICLE_PATH, "-O3", *(extra_args or []), entrada, "-o", saida]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Erro ao rodar gifsicle.")


# ── Compressão de GIF (qualidade) ────────────────────────────────────────────

def compress_gif_quality(data: bytes) -> io.BytesIO:
    if not _gifsicle_available():
        raise RuntimeError(f"gifsicle.exe não encontrado em: {GIFSICLE_PATH}")

    with tempfile.TemporaryDirectory() as tmp:
        input_path  = os.path.join(tmp, "input.gif")
        work_path   = os.path.join(tmp, "work.gif")
        output_path = os.path.join(tmp, "output.gif")

        with open(input_path, "wb") as f:
            f.write(data)

        tentativas_diretas = [
            ["--colors", "256"],
            ["--colors", "256", "--lossy=20"],
            ["--colors", "256", "--lossy=40"],
            ["--colors", "192", "--lossy=40"],
            ["--colors", "160", "--lossy=60"],
        ]

        for tentativa in tentativas_diretas:
            try:
                _run_gifsicle(input_path, output_path, tentativa)
                if os.path.exists(output_path) and os.path.getsize(output_path) <= MAX_FIG_SIZE:
                    with open(output_path, "rb") as f:
                        return io.BytesIO(f.read())
            except Exception as e:
                print(f"[AVISO] qualidade direta falhou: {e}")

        original = Image.open(io.BytesIO(data))
        loop = original.info.get("loop", 0)
        original_frames = []
        original_durations = []
        for frame in ImageSequence.Iterator(original):
            original_frames.append(frame.copy().convert("RGBA"))
            original_durations.append(frame.info.get("duration", 80))

        if not original_frames:
            raise ValueError("Não consegui ler os frames do GIF.")

        melhor_bytes: bytes | None = None
        melhor_tamanho: int | None = None

        for scale in [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]:
            frames    = [resize_frame_keep_aspect(f, scale) for f in original_frames]
            durations = list(original_durations)

            for colors in [256, 192, 160]:
                paletted = [quantize_preserving_transparency(f, colors) for f in frames]
                paletted[0].save(
                    work_path,
                    format="GIF",
                    save_all=True,
                    append_images=paletted[1:],
                    optimize=False,
                    loop=loop,
                    duration=durations,
                    disposal=2,
                    transparency=255,
                )
                for lossy in [20, 40, 60]:
                    try:
                        _run_gifsicle(work_path, output_path, [f"--lossy={lossy}"])
                        if os.path.exists(output_path):
                            tamanho = os.path.getsize(output_path)
                            if melhor_tamanho is None or tamanho < melhor_tamanho:
                                melhor_tamanho = tamanho
                                with open(output_path, "rb") as f:
                                    melhor_bytes = f.read()
                            if tamanho <= MAX_FIG_SIZE:
                                with open(output_path, "rb") as f:
                                    return io.BytesIO(f.read())
                    except Exception as e:
                        print(f"[AVISO] qualidade resize falhou: {e}")

        if melhor_bytes is not None:
            raise ValueError(
                f"Não consegui chegar em 512 KB sem pesar demais a compressão. "
                f"Menor tamanho: {round(melhor_tamanho / 1024, 1)} KB."
            )
        raise ValueError("Não consegui processar esse GIF.")


# ── Compressão de GIF (forçada — mais agressiva) ─────────────────────────────

def compress_gif_force(data: bytes) -> io.BytesIO:
    if not _gifsicle_available():
        raise RuntimeError(f"gifsicle.exe não encontrado em: {GIFSICLE_PATH}")

    with tempfile.TemporaryDirectory() as tmp:
        input_path  = os.path.join(tmp, "input.gif")
        work_path   = os.path.join(tmp, "work.gif")
        output_path = os.path.join(tmp, "output.gif")

        with open(input_path, "wb") as f:
            f.write(data)

        tentativas_diretas = [
            ["--colors", "128", "--lossy=80"],
            ["--colors", "96",  "--lossy=120"],
            ["--colors", "64",  "--lossy=160"],
            ["--colors", "48",  "--lossy=200"],
            ["--colors", "32",  "--lossy=240"],
        ]

        for tentativa in tentativas_diretas:
            try:
                _run_gifsicle(input_path, output_path, tentativa)
                if os.path.exists(output_path) and os.path.getsize(output_path) <= MAX_FIG_SIZE:
                    with open(output_path, "rb") as f:
                        return io.BytesIO(f.read())
            except Exception as e:
                print(f"[AVISO] força direta falhou: {e}")

        original = Image.open(io.BytesIO(data))
        loop = original.info.get("loop", 0)
        original_frames = []
        original_durations = []
        for frame in ImageSequence.Iterator(original):
            original_frames.append(frame.copy().convert("RGBA"))
            original_durations.append(frame.info.get("duration", 80))

        if not original_frames:
            raise ValueError("Não consegui ler os frames do GIF.")

        melhor_bytes: bytes | None = None
        melhor_tamanho: int | None = None

        for scale in [0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30]:
            for frame_step in [1, 2, 3, 4, 5]:
                frames, durations = [], []
                for i, frame in enumerate(original_frames):
                    if i % frame_step != 0:
                        continue
                    dur = original_durations[i] if i < len(original_durations) else 80
                    frames.append(resize_frame_keep_aspect(frame, scale))
                    durations.append(max(80, dur * frame_step))

                if not frames:
                    continue

                for colors in [128, 96, 64, 48, 32, 16]:
                    paletted = [quantize_preserving_transparency(f, colors) for f in frames]
                    paletted[0].save(
                        work_path,
                        format="GIF",
                        save_all=True,
                        append_images=paletted[1:],
                        optimize=False,
                        loop=loop,
                        duration=durations,
                        disposal=2,
                        transparency=255,
                    )
                    for lossy in [80, 120, 160, 200, 240, 300]:
                        try:
                            _run_gifsicle(work_path, output_path, [f"--lossy={lossy}"])
                            if os.path.exists(output_path):
                                tamanho = os.path.getsize(output_path)
                                if melhor_tamanho is None or tamanho < melhor_tamanho:
                                    melhor_tamanho = tamanho
                                    with open(output_path, "rb") as f:
                                        melhor_bytes = f.read()
                                if tamanho <= MAX_FIG_SIZE:
                                    with open(output_path, "rb") as f:
                                        return io.BytesIO(f.read())
                        except Exception as e:
                            print(f"[AVISO] força agressiva falhou: {e}")

        if melhor_bytes is not None:
            raise ValueError(
                f"Não consegui chegar em 512 KB. Menor tamanho: "
                f"{round(melhor_tamanho / 1024, 1)} KB."
            )
        raise ValueError("Não consegui processar esse GIF.")
