from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.models.task import TaskCreate, TaskUpdate
from app.services.auth_service import get_current_user
from app.database import query

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("")
def list_tasks(
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    personnel_id: Optional[int] = Query(None),
    week_start: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    filters = ["t.is_active = TRUE"]
    params = []
    if project_id:
        filters.append("t.project_id = %s"); params.append(project_id)
    if status:
        filters.append("t.status = %s"); params.append(status)
    if personnel_id:
        filters.append("t.primary_personnel_id = %s"); params.append(personnel_id)
    if week_start:
        filters.append("t.week_start = %s"); params.append(week_start)

    where = " AND ".join(filters)
    sql = f"""
        SELECT t.id, t.title, t.scope, t.status, t.deadline, t.week_start,
               p.full_name, pr.name
        FROM tasks t
        JOIN personnel p ON t.primary_personnel_id = p.id
        LEFT JOIN projects pr ON t.project_id = pr.id
        WHERE {where}
        ORDER BY t.deadline ASC NULLS LAST, t.id DESC
    """
    rows = query(sql, params or None, fetch="all")
    return [
        {"id": r[0], "title": r[1], "scope": r[2], "status": r[3],
         "deadline": str(r[4]) if r[4] else None,
         "week_start": str(r[5]) if r[5] else None,
         "assignee": r[6], "project": r[7]}
        for r in (rows or [])
    ]

@router.get("/{task_id}")
def get_task(task_id: int, user=Depends(get_current_user)):
    row = query(
        """SELECT t.id, t.title, t.description, t.scope, t.status, t.deadline,
                  t.start_date, t.target_amount_bif, p.full_name, pr.name
           FROM tasks t
           JOIN personnel p ON t.primary_personnel_id = p.id
           LEFT JOIN projects pr ON t.project_id = pr.id
           WHERE t.id=%s AND t.is_active=TRUE""",
        (task_id,), fetch="one"
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    logs = query(
        """SELECT tl.old_status, tl.new_status, tl.note, tl.source, tl.logged_at, p.full_name
           FROM task_logs tl
           LEFT JOIN personnel p ON tl.personnel_id = p.id
           WHERE tl.task_id=%s ORDER BY tl.logged_at DESC""",
        (task_id,), fetch="all"
    )
    return {
        "id": row[0], "title": row[1], "description": row[2],
        "scope": row[3], "status": row[4],
        "deadline": str(row[5]) if row[5] else None,
        "start_date": str(row[6]) if row[6] else None,
        "target_amount_bif": float(row[7]) if row[7] else None,
        "assignee": row[8], "project": row[9],
        "logs": [
            {"old_status": l[0], "new_status": l[1], "note": l[2],
             "source": l[3], "logged_at": str(l[4]), "by": l[5]}
            for l in (logs or [])
        ],
    }

@router.post("", status_code=201)
def create_task(body: TaskCreate, user=Depends(get_current_user)):
    row = query(
        """INSERT INTO tasks
               (project_id, primary_personnel_id, scope, title, description,
                start_date, deadline, target_amount_bif, week_start, status, created_by_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'planned', %s)
           RETURNING id""",
        (body.project_id, body.primary_personnel_id, body.scope, body.title,
         body.description, body.start_date, body.deadline,
         body.target_amount_bif, body.week_start, user["personnel_id"]),
        fetch="one",
    )
    task_id = row[0]
    query(
        """INSERT INTO task_logs (task_id, personnel_id, old_status, new_status, note, source)
           VALUES (%s, %s, NULL, 'planned', 'Task created', 'web')""",
        (task_id, user["personnel_id"]),
    )
    return {"id": task_id, "message": "Task created"}

@router.patch("/{task_id}")
def update_task(task_id: int, body: TaskUpdate, user=Depends(get_current_user)):
    existing = query(
        "SELECT id, status FROM tasks WHERE id=%s AND is_active=TRUE", (task_id,), fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = existing[1]
    updates, params = [], []
    if body.title is not None:
        updates.append("title=%s"); params.append(body.title)
    if body.description is not None:
        updates.append("description=%s"); params.append(body.description)
    if body.status is not None:
        updates.append("status=%s"); params.append(body.status)
    if body.deadline is not None:
        updates.append("deadline=%s"); params.append(body.deadline)

    if updates:
        params.append(task_id)
        query(f"UPDATE tasks SET {', '.join(updates)} WHERE id=%s", params)

    query(
        """INSERT INTO task_logs (task_id, personnel_id, old_status, new_status, note, source)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (task_id, user["personnel_id"],
         old_status, body.status or old_status,
         body.note or "Task updated", body.source or "web"),
    )
    return {"id": task_id, "message": "Task updated"}

@router.delete("/{task_id}")
def archive_task(task_id: int, user=Depends(get_current_user)):
    result = query(
        "UPDATE tasks SET is_active=FALSE WHERE id=%s AND is_active=TRUE RETURNING id",
        (task_id,), fetch="one"
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task archived"}