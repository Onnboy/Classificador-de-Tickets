# Classificador de Tickets

API REST que recebe tickets de suporte e os classifica com o Gemini em
categoria (Dúvida, Bug, Critico) e urgência (Baixa, Média, Alta). Feita com
FastAPI e SQLModel sobre PostgreSQL, com autenticação JWT.

## Requisitos

- Python 3.12
- [Poetry](https://python-poetry.org/) 2.x
- Docker, para o PostgreSQL
- Uma chave de API do Gemini

## Instalação

```bash
poetry install
```

Crie um arquivo `.env` na raiz do projeto. Ele não é versionado:

```dotenv
GEMINI_API_KEY=sua-chave-do-gemini
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/tickets_db
SECRET_KEY=um-segredo-longo-e-aleatorio-com-32-bytes-ou-mais
```

O usuário, a senha e o banco da `DATABASE_URL` acima são os do
`docker-compose.yml` e servem só para desenvolvimento local. Para gerar a
`SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Como rodar

```bash
docker compose up -d
poetry run fastapi dev app/app.py
```

A documentação interativa fica em <http://127.0.0.1:8000/docs>.

> **Cuidado com `task run`.** Ele executa `sudo systemctl stop postgresql` e
> `docker compose down -v` antes de subir o servidor, e o `-v` apaga o volume
> do banco: todos os dados locais são perdidos a cada execução.

Se a porta 5432 já estiver em uso por um PostgreSQL instalado na máquina, pare
esse serviço ou mude a porta no `docker-compose.yml` e na `DATABASE_URL`.

As tabelas são criadas na inicialização. Ainda não há migrações: uma mudança
de coluna em tabela existente exige recriar o banco.

## Testes e lint

Os testes usam SQLite em memória e simulam o Gemini com mock. Rode sempre com
variáveis falsas, para que o `.env` real não seja carregado:

```bash
env GEMINI_API_KEY=chave-falsa DATABASE_URL=sqlite:// SECRET_KEY=segredo-de-teste \
  poetry run python -m pytest -q
poetry run ruff check
```

A CI (`.github/workflows/ci.yml`) roda os mesmos dois comandos a cada pull
request e a cada push na `main`.

## Rotas

| Método | Rota | Autenticação | O que faz |
|---|---|---|---|
| GET | `/health/` | Não | Verifica se a API está no ar |
| POST | `/v1/users/` | Não | Cadastra um usuário |
| POST | `/v1/auth/token/` | Não | Login (formulário `username` e `password`); devolve o token |
| POST | `/v1/tickets/` | Bearer | Cria um ticket e o classifica com a IA |
| PUT | `/v1/tickets/{id}` | Bearer | Atualiza título ou descrição; reclassifica se algum mudar |
| GET | `/v1/tickets/` | Bearer | Lista os tickets do usuário autenticado |

O token expira em 30 minutos. Usuário inativo recebe 403 no login e nas rotas
de ticket.

Quando a IA falha ou devolve uma resposta fora do formato esperado, o ticket é
gravado mesmo assim, com categoria `Erro` e prioridade `N/A`.

## Estrutura

- `app/app.py`: aplicação, rotas e chamada ao Gemini.
- `app/schemas.py`: modelos de entrada e de resposta.
- `app/models/`: tabelas `Ticket` e `User`.
- `app/core/security.py`: senha e JWT.
- `tests/`: testes com pytest.

## Convenções

- Commits: `tipo(escopo): Descrição em português`, com `feat` e `test` em
  commits separados.
- Branches: `<número-da-issue>-<tipo>/<descrição>`; sem issue,
  `<tipo>/<descrição>`.
