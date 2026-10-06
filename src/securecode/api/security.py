import os
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Password Hasher
ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False

# JWT Configuration
def get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise ValueError("JWT_SECRET_KEY environment variable is not set")
    return secret

def get_jwt_algorithm() -> str:
    return os.environ.get("JWT_ALGORITHM", "HS256")

def get_jwt_expire_minutes() -> int:
    return int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=get_jwt_expire_minutes())
    
    # We include sub, iat, exp, jti conceptually, but PyJWT handles exp explicitly.
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    return jwt.encode(payload, get_jwt_secret(), algorithm=get_jwt_algorithm())

def verify_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, 
            get_jwt_secret(), 
            algorithms=[get_jwt_algorithm()],
            options={"require": ["exp", "sub"]}
        )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
