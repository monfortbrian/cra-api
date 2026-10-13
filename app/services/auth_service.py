from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.database import query

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode["exp"] = int(expire.timestamp())   # ← THIS is the fix
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        personnel_id = payload.get("sub")
        role = payload.get("role")
        if personnel_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"personnel_id": int(personnel_id), "role": role}
    except JWTError as e:
        print(f"JWT decode error: {e}")   # shows in uvicorn terminal
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*roles):
    def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker