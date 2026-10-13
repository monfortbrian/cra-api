from fastapi import APIRouter, HTTPException
from app.models.auth import LoginRequest, TokenResponse
from app.services.auth_service import verify_password, hash_password, create_token
from app.database import query

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    row = query(
        "SELECT id, password_hash, web_role FROM personnel WHERE email=%s AND is_active=TRUE",
        (req.email,), fetch="one"
    )
    if not row or not row[1] or not verify_password(req.password, row[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": str(row[0]), "role": row[2]})
    return {"access_token": token}

@router.post("/set-password")
def set_password(email: str, password: str):
    hashed = hash_password(password)
    result = query(
        "UPDATE personnel SET password_hash=%s WHERE email=%s RETURNING id",
        (hashed, email), fetch="one"
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Password set", "id": result[0]}