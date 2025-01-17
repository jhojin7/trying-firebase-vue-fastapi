# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import firebase_admin
from firebase_admin import credentials, auth
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uuid
from datetime import datetime

# Initialize Firebase Admin
cred = credentials.Certificate("path/to/your/firebase-credentials.json")
firebase_admin.initialize_app(cred)

# Initialize FastAPI
app = FastAPI()
security = HTTPBearer()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cloudflare Workers KV configuration
ACCOUNT_ID = "your_account_id"
NAMESPACE_ID = "your_namespace_id"
API_TOKEN = "your_api_token"
KV_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}"


# Models
class TodoCreate(BaseModel):
    text: str
    completed: bool = False


class TodoUpdate(BaseModel):
    completed: Optional[bool] = None
    text: Optional[str] = None


class Todo(BaseModel):
    id: str
    text: str
    completed: bool
    user_id: str
    created_at: str


# Authentication middleware
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        return decoded_token["uid"]
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication")


# KV Helper functions
async def kv_get(key: str):
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{KV_URL}/values/{key}", headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        if response.status_code == 404:
            return None
        return response.json()


async def kv_put(key: str, value: dict):
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{KV_URL}/values/{key}",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            json=value,
        )
        return response.json()


async def kv_delete(key: str):
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{KV_URL}/values/{key}", headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        return response.json()


# Routes
@app.get("/api/todos", response_model=List[Todo])
async def get_todos(user_id: str = Depends(get_current_user)):
    todos = await kv_get(f"todos_{user_id}")
    return todos or []


@app.post("/api/todos", response_model=Todo)
async def create_todo(todo: TodoCreate, user_id: str = Depends(get_current_user)):
    todos = await kv_get(f"todos_{user_id}") or []

    new_todo = Todo(
        id=str(uuid.uuid4()),
        text=todo.text,
        completed=todo.completed,
        user_id=user_id,
        created_at=datetime.now().isoformat(),
    )

    todos.append(new_todo.dict())
    await kv_put(f"todos_{user_id}", todos)
    return new_todo


@app.put("/api/todos/{todo_id}", response_model=Todo)
async def update_todo(
    todo_id: str, todo_update: TodoUpdate, user_id: str = Depends(get_current_user)
):
    todos = await kv_get(f"todos_{user_id}") or []
    todo_idx = next((i for i, t in enumerate(todos) if t["id"] == todo_id), None)

    if todo_idx is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    if todo_update.completed is not None:
        todos[todo_idx]["completed"] = todo_update.completed
    if todo_update.text is not None:
        todos[todo_idx]["text"] = todo_update.text

    await kv_put(f"todos_{user_id}", todos)
    return todos[todo_idx]


@app.delete("/api/todos/{todo_id}")
async def delete_todo(todo_id: str, user_id: str = Depends(get_current_user)):
    todos = await kv_get(f"todos_{user_id}") or []
    todos = [t for t in todos if t["id"] != todo_id]
    await kv_put(f"todos_{user_id}", todos)
    return {"message": "Todo deleted"}
