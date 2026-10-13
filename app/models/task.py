from pydantic import BaseModel
from typing import Optional, Literal
from datetime import date

ScopeType = Literal['project_deliverable','recouvrement','tender','stock_ops','it_systems','admin','other']
StatusType = Literal['planned','in_progress','completed','delayed','failed','cancelled']

class TaskCreate(BaseModel):
    project_id: Optional[int] = None
    primary_personnel_id: int
    scope: ScopeType
    title: str
    description: Optional[str] = None
    start_date: date
    deadline: date
    target_amount_bif: Optional[float] = None
    week_start: Optional[date] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StatusType] = None
    deadline: Optional[date] = None
    note: Optional[str] = None
    source: Optional[Literal['web','telegram','n8n_auto','system']] = 'web'