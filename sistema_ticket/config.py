import json
import os

TICKET_CONFIG_FILE = "json/ticket_config.json"


DEFAULT_TICKET_DESCRIPTION = (
    "Espaço para ajustes na nossa convivência. O diálogo é a nossa base.\n\n"
    "**Regras rápidas:**\n"
    "• Respeito acima de tudo.\n"
    "• O que é dito aqui, morre aqui.\n"
    "• Se for urgente, priorize a call.\n\n"
    "Clique no botão abaixo para abrir um espaço de conversa."
)


DEFAULT_CONFIG = {
    "panel_channel_id": 1494508908826464438,
    "manager_role_id": 1491166369859764314,
    "log_channel_id": 1491930461750952108,
    "panel_title": "💌 Report Love",
    "panel_description": (
        "Abra um espaço de conversa para resolver algo com calma.\n\n"
        "Use o menu abaixo para abrir um ticket."
    ),
    "panel_image_url": "",
    "ticket_name": "<:tell:1493022801362423931> Report Love",
    "ticket_description": DEFAULT_TICKET_DESCRIPTION,
    "ticket_image_url": "",
    "ticket_icon": "💗",
    "select_placeholder": "Escolha uma opção",
}


def load_config() -> dict:
    if not os.path.exists(TICKET_CONFIG_FILE):
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        with open(TICKET_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {}

    except Exception:
        data = {}

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)
    save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    os.makedirs(os.path.dirname(TICKET_CONFIG_FILE), exist_ok=True)

    with open(TICKET_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)
