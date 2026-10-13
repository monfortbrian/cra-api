from fastapi import APIRouter, Request, HTTPException
from app.config import settings
from app.database import query
import httpx

router = APIRouter(prefix="/webhook", tags=["telegram"])


async def send_message(chat_id: int, text: str):
    if not settings.telegram_bot_token:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


@router.post("/telegram")
async def telegram_webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if settings.app_env != "development" and secret != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    telegram_id = str(message.get("from", {}).get("id", ""))
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return {"ok": True}

    person = query(
        "SELECT id, full_name, web_role FROM personnel WHERE telegram_id=%s AND is_active=TRUE",
        (telegram_id,), fetch="one"
    )
    if not person:
        await send_message(chat_id, "❌ You are not registered in the system.")
        return {"ok": True}

    person_id, full_name, web_role = person

    if text == "/start":
        await send_message(chat_id, f"👋 Hello <b>{full_name}</b>!\n\nCommands:\n/tasks -- your open tasks\n/done [id] - mark done\n/progress [id] - mark in progress\n/report [id] message - add note")

    elif text == "/tasks":
        rows = query(
            """SELECT id, title, status, due_date FROM tasks
               WHERE primary_personnel_id=%s AND is_active=TRUE AND status != 'done'
               ORDER BY due_date ASC NULLS LAST LIMIT 10""",
            (person_id,), fetch="all"
        )
        if not rows:
            await send_message(chat_id, "✅ No pending tasks!")
        else:
            lines = ["<b>Your open tasks:</b>"]
            for r in rows:
                due = str(r[3]) if r[3] else "-"
                lines.append(f"• [<b>{r[0]}</b>] {r[1]}\n  {r[2]} · due {due}")
            await send_message(chat_id, "\n".join(lines))

    elif text.startswith("/done "):
        parts = text.split()
        task_id = parts[1] if len(parts) > 1 else None
        if not task_id:
            await send_message(chat_id, "Usage: /done [task_id]")
        else:
            result = query(
                "UPDATE tasks SET status='done' WHERE id=%s AND primary_personnel_id=%s RETURNING id",
                (task_id, person_id), fetch="one"
            )
            if result:
                query(
                    "INSERT INTO task_logs (task_id, personnel_id, old_status, new_status, note, source) VALUES (%s,%s,'in_progress','completed','Marked done via Telegram','telegram')",
                    (task_id, person_id)
                )
                await send_message(chat_id, f"✅ Task {task_id} marked as done!")
            else:
                await send_message(chat_id, f"❌ Task {task_id} not found or not yours.")

    elif text.startswith("/progress "):
        parts = text.split()
        task_id = parts[1] if len(parts) > 1 else None
        if not task_id:
            await send_message(chat_id, "Usage: /progress [task_id]")
        else:
            result = query(
                "UPDATE tasks SET status='in_progress' WHERE id=%s AND primary_personnel_id=%s RETURNING id",
                (task_id, person_id), fetch="one"
            )
            if result:
                query(
                    "INSERT INTO task_logs (task_id, personnel_id, old_status, new_status, note, source) VALUES (%s,%s,'planned','in_progress','Started via Telegram','telegram')",
                    (task_id, person_id)
                )
                await send_message(chat_id, f"🔄 Task {task_id} in progress!")
            else:
                await send_message(chat_id, f"❌ Task {task_id} not found or not yours.")

    elif text.startswith("/report "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            await send_message(chat_id, "Usage: /report [task_id] [your message]")
        else:
            task_id, note = parts[1], parts[2]
            row = query(
                "SELECT id FROM tasks WHERE id=%s AND primary_personnel_id=%s AND is_active=TRUE",
                (task_id, person_id), fetch="one"
            )
            if row:
                query(
                    "INSERT INTO task_logs (task_id, personnel_id, old_status, new_status, note, source) VALUES (%s,%s,NULL,'in_progress',%s,'telegram')",
                    (task_id, person_id, note)
                )
                await send_message(chat_id, f"📝 Report saved for task {task_id}.")
            else:
                await send_message(chat_id, f"❌ Task {task_id} not found or not yours.")
    else:
        await send_message(chat_id, "Unknown command. Send /start for help.")

    return {"ok": True}
