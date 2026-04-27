"""Utilitários centralizados de banco de dados (JSON simples)."""
import json
import os

from utils.constants import DB_FILE


def load_db() -> dict:
    """Carrega o banco de dados completo."""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_db(data: dict) -> None:
    """Salva o banco de dados completo."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_user(user_id: int) -> dict:
    """
    Retorna o banco completo garantindo que o usuário existe com
    todos os campos padrão. Persiste automaticamente.
    """
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


def add_moedas(user_id: int, valor: int) -> None:
    data = get_user(user_id)
    data[str(user_id)]["moedas"] += valor
    save_db(data)


def add_mimos(user_id: int, valor: int) -> None:
    data = get_user(user_id)
    data[str(user_id)]["mimos"] += valor
    save_db(data)


def remove_mimos(user_id: int, valor: int) -> None:
    data = get_user(user_id)
    uid = str(user_id)
    data[uid]["mimos"] = max(0, data[uid]["mimos"] - valor)
    save_db(data)
