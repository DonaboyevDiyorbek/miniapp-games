import hashlib, hmac, json, time
from urllib.parse import parse_qsl


def validate(init_data: str, bot_token: str, max_age: int = 86400):
    """Telegram Mini App initData ni tekshiradi. To'g'ri bo'lsa {"id","name"}, aks holda None."""
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
        got = pairs.pop("hash")
        check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, got):
            return None
        if time.time() - int(pairs.get("auth_date", "0")) > max_age:
            return None
        u = json.loads(pairs["user"])
        name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("username") or "Player"
        return {"id": int(u["id"]), "name": name[:40]}
    except Exception:
        return None
