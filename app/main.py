from fastapi import FastAPI,APIRouter
from pydantic import BaseModel

app = FastAPI()
router = APIRouter(prefix="/v1")

class Ticket(BaseModel):
    titulo: str
    descricao: str

@app.get("/health")
def read_state():
    return {"estado": "EM ATIVIDADE"}

@router.post("/tickets/")
async def create_ticket(ticket: Ticket):
    return "Recebido"

app.include_router(router)