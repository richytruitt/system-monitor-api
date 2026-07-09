import psutil
import platform
import socket
import docker
import os
from app import auth_helpers
from datetime import datetime
from fastapi import Depends, HTTPException, status, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Raspberry Pi Metadata API")

app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
)

docker_client = docker.from_env()


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth_helpers.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_helpers.create_access_token(
        data={
            "sub": user["username"],
            "role": "admin",
            "display_name": "Richy Truitt",
            "permissions": [
                "read:system",
                "read:docker",
                "read:dockers"
            ]
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/")
def root():
    return {"status": "ok", "service": "pi-metadata-api"}


@app.get("/system")
def system_info(current_user=Depends(auth_helpers.authenticate_current_user("read:system"))):
    return {
        "hostname": os.getenv("HOST_HOSTNAME"),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total_mb": round(psutil.virtual_memory().total / 1024 / 1024, 2),
            "used_percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total_gb": round(psutil.disk_usage("/").total / 1024 / 1024 / 1024, 2),
            "used_percent": psutil.disk_usage("/").percent,
        },
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    }


@app.get("/docker/containers")
def docker_containers(current_user=Depends(auth_helpers.authenticate_current_user("read:docker"))):
    try:
        containers = docker_client.containers.list(all=True)

        return [
            {
                "name": c.name,
                "image": c.image.tags,
                "status": c.status,
                "id": c.short_id,
                "ports": c.attrs.get("NetworkSettings", {}).get("Ports"),
            }
            for c in containers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docker/images")
def docker_images(current_user=Depends(auth_helpers.authenticate_current_user("read:dockers"))):
    try:
        images = docker_client.images.list()

        return [
            {
                "id": image.short_id,
                "tags": image.tags,
                "created": image.attrs.get("Created"),
                "size_mb": round(image.attrs.get("Size", 0) / 1024 / 1024, 2),
            }
            for image in images
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {
        "healthy": True,
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": psutil.virtual_memory().percent,
    }