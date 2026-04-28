import json
import os

from sistema_economia.config import ECONOMIA_FILE


def garantir_pasta_json() -> None:
    pasta = os.path.dirname(ECONOMIA_FILE)

    if pasta:
        os.makedirs(pasta, exist_ok=True)


def load_db() -> dict:
    if not os.path.exists(ECONOMIA_FILE):
        return {}

    try:
        with open(ECONOMIA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_db(data: dict) -> None:
    garantir_pasta_json()

    with open(ECONOMIA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_user(user_id: int) -> dict:
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


def get_user_info(user_id: int) -> dict:
    data = get_user(user_id)
    return data[str(user_id)]


def add_moedas(user_id: int, valor: int) -> None:
    data = get_user(user_id)
    data[str(user_id)]["moedas"] += valor
    save_db(data)


def remove_moedas(user_id: int, valor: int) -> bool:
    data = get_user(user_id)
    uid = str(user_id)

    if data[uid]["moedas"] < valor:
        return False

    data[uid]["moedas"] -= valor
    save_db(data)
    return True


def get_moedas(user_id: int) -> int:
    data = get_user(user_id)
    return int(data[str(user_id)].get("moedas", 0))


def add_mimos(user_id: int, valor: int) -> None:
    data = get_user(user_id)
    data[str(user_id)]["mimos"] += valor
    save_db(data)


def remove_mimos(user_id: int, valor: int) -> bool:
    data = get_user(user_id)
    uid = str(user_id)

    if data[uid]["mimos"] < valor:
        return False

    data[uid]["mimos"] -= valor
    save_db(data)
    return True


def get_mimos(user_id: int) -> int:
    data = get_user(user_id)
    return int(data[str(user_id)].get("mimos", 0))


def set_user_field(user_id: int, field: str, value) -> None:
    data = get_user(user_id)
    data[str(user_id)][field] = value
    save_db(data)


def update_user(user_id: int, updates: dict) -> None:
    data = get_user(user_id)
    data[str(user_id)].update(updates)
    save_db(data)


# Compatibilidade com nomes antigos.
# Assim, se algum outro arquivo ainda chamar load_economia/save_economia,
# ele não quebra.

load_economia = load_db
save_economia = save_db
get_user_economia = get_user
