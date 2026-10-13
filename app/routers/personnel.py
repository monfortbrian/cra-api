from fastapi import APIRouter, Depends
from app.services.auth_service import get_current_user
from app.database import query

router = APIRouter(prefix="/personnel", tags=["personnel"])

@router.get("")
def list_personnel(user=Depends(get_current_user)):
    rows = query(
        """SELECT id, full_name, short_name, job_title, web_role, telegram_id, phone, email
           FROM personnel WHERE is_active=TRUE ORDER BY full_name""",
        fetch="all"
    )
    return [
        {"id": r[0], "full_name": r[1], "short_name": r[2],
         "job_title": r[3], "web_role": r[4],
         "telegram_id": r[5], "phone": r[6], "email": r[7]}
        for r in (rows or [])
    ]

@router.get("/projects")
def list_projects(user=Depends(get_current_user)):
    rows = query(
        "SELECT id, name, code FROM projects WHERE is_active=TRUE ORDER BY name",
        fetch="all"
    )
    return [{"id": r[0], "name": r[1], "code": r[2]} for r in (rows or [])]