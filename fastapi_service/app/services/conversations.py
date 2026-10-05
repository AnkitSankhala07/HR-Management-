from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection

now = lambda: datetime.now(timezone.utc).replace(tzinfo=None)


def create(conn: Connection, user_id: int, title: str) -> int:
    t = now()
    res = conn.execute(text("INSERT INTO ai_conversations (user_id, title, created_at, updated_at) VALUES (:u, :t, :n, :n)"), {"u": user_id, "t": title[:100], "n": t})
    conn.commit()
    return int(res.lastrowid)


def owned(conn: Connection, user_id: int, cid: int) -> bool:
    return bool(conn.execute(text("SELECT 1 FROM ai_conversations WHERE id=:c AND user_id=:u"), {"c": cid, "u": user_id}).first())


def add(conn: Connection, cid: int, role: str, content: str):
    conn.execute(text("INSERT INTO ai_messages (conversation_id, role, content, created_at) VALUES (:c, :r, :t, :n)"), {"c": cid, "r": role, "t": content, "n": now()})
    conn.execute(text("UPDATE ai_conversations SET updated_at=:n WHERE id=:c"), {"c": cid, "n": now()})
    conn.commit()


def list_(conn: Connection, user_id: int):
    return [dict(r) for r in conn.execute(text("SELECT id, title, updated_at FROM ai_conversations WHERE user_id=:u ORDER BY updated_at DESC LIMIT 50"), {"u": user_id}).mappings()]


def messages(conn: Connection, cid: int):
    return [dict(r) for r in conn.execute(text("SELECT role, content, created_at FROM ai_messages WHERE conversation_id=:c ORDER BY id"), {"c": cid}).mappings()]


def delete(conn: Connection, cid: int):
    conn.execute(text("DELETE FROM ai_messages WHERE conversation_id=:c"), {"c": cid})
    conn.execute(text("DELETE FROM ai_conversations WHERE id=:c"), {"c": cid})
    conn.commit()
