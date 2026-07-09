import psutil
import platform
import socket
import docker
from datetime import datetime
from fastapi import Depends, HTTPException, status, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

SECRET_KEY = "change-this-to-a-long-random-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 5

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

fake_user_db = {
    "richy": {
        "username": "richy",
        "hashed_password": pwd_context.hash("richy"),
    }
}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str):
    user = fake_user_db.get(username)

    if not user:
        return None

    if not verify_password(password, user["hashed_password"]):
        return None

    return user


def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_current_user(required_permission: str):

    def validate_entitled(token: str = Depends(oauth2_scheme)):
        
        try:        
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


            permissions = payload["permissions"]

            if required_permission and required_permission not in permissions:
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden"
                )
            return payload
        
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as ex:
            return {
                "error": ex
            }


    return validate_entitled
        