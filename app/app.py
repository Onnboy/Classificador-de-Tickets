from fastapi import APIRouter, FastAPI, status
from pydantic import BaseModel, Field

app = FastAPI()
router = APIRouter(prefix='/v1')


class Ticket(BaseModel):
    titulo: str = Field(..., min_length=10)
    descricao: str


@app.get('/health')
def read_state():
    return {'estado': 'EM ATIVIDADE'}


@router.post('/tickets/', status_code = status.HTTP_201_CREATED)
def create_ticket(ticket: Ticket):
    return 'Recebido'


app.include_router(router)
