"""Utilitário: enviar/atualizar painéis persistentes por canal."""
import json
import os
import logging

import nextcord
from nextcord.ext import commands

from utils.constants import PANEL_FILE

log = logging.getLogger(__name__)


def load_panels() -> dict:
    if not os.path.exists(PANEL_FILE):
        return {}
    try:
        with open(PANEL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_panels(data: dict) -> None:
    with open(PANEL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


async def send_or_update_panel(
    bot: commands.Bot,
    channel_id: int,
    panel_key: str,
    embed: nextcord.Embed,
    view=None,
) -> None:
    panels  = load_panels()
    channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)

    message_id = panels.get(panel_key)
    if message_id:
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed, view=view)
            return
        except Exception:
            pass

    msg = await channel.send(embed=embed, view=view)
    panels[panel_key] = msg.id
    save_panels(panels)
