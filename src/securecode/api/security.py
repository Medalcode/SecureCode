import os
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2 import Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Configuración centralizada de Argon2id.
# Valores recomendados por OWASP y argon2-cffi por defecto:
# - memory_cost: 64 MiB (balance seguridad/performance)
# - time_cost: 3 iteraciones (seguridad razonable sin cuellos de botella)
# - parallelism: 2 hilos (configurado balanceando seguridad y rendimiento)
# Estos valores son consistentes con la versión de argon2-cffi instalada.
# No cambien estos valores sin evaluar: reducir memory_cost debilita el hashing;
# aumentarlo sin necesidad real afecta performance en producción.
ARGON2ID_SETTINGS = {
    "memory_cost": 64 * 1024,  # 64 MiB
    "time_cost": 3,
    "parallelism": 2,
    "hash_len": 32,
    "type": Type.ID,
}

# Password Hasher (instancia singleton: reutilización segura porque no conserva
# estado mutable por solicitud. Argon2id genera una sal aleatoria al crear hashes,
# por lo que la misma contraseña puede producir hashes diferentes, pero todos deben
# verificarse correctamente.)
ph = PasswordHasher(
    memory_cost=ARGON2ID_SETTINGS["memory_cost"],
    time_cost=ARGON2ID_SETTINGS["time_cost"],
    parallelism=ARGON2ID_SETTINGS["parallelism"],
    hash_len=ARGON2ID_SETTINGS["hash_len"],
    type=ARGON2ID_SETTINGS["type"],
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False

# JWT Configuration
def get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise ValueError("JWT_SECRET_KEY environment variable is not set")
    if len(secret) < 32:
        raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
    return secret

def get_jwt_algorithm() -> str:
    algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
    if algorithm != "HS256":
        raise ValueError("Unsupported JWT algorithm: only HS256 is allowed")
    return algorithm

def get_jwt_expire_minutes() -> int:
    return int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

def create_access_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=get_jwt_expire_minutes())
    
    # We include sub, iat, exp, jti conceptually, but PyJWT handles exp explicitly.
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(UTC)
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
