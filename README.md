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
DATABASE_URL=postgresql://user:password@localhost:5433/tickets_db
SECRET_KEY=um-segredo-longo-e-aleatorio-com-32-bytes-ou-mais
```

O usuário, a senha e o banco da `DATABASE_URL` acima são os do
`docker-compose.yml` e servem só para desenvolvimento local. Para gerar a
`SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

Opcional: `DB_ECHO=true` faz o SQLAlchemy logar todo SQL executado, com os
valores das consultas. Fica desligado por padrão; use só para depurar.

## Como rodar

```bash
docker compose up -d
poetry run alembic upgrade head
poetry run fastapi dev app/app.py
```

O `alembic upgrade head` cria as tabelas num banco vazio e aplica as migrações
que faltam num banco existente. Rode-o de novo sempre que puxar uma mudança
que traga migração nova.

Ou, com o mesmo efeito, `poetry run task run`: ele sobe o banco, espera o
healthcheck do PostgreSQL ficar saudável, aplica as migrações e inicia o
servidor. Os dados ficam no volume `postgres_data` e são preservados entre
execuções.

A documentação interativa fica em <http://127.0.0.1:8000/docs>.

O container do PostgreSQL publica a porta 5433 na máquina (`"5433:5432"` no
`docker-compose.yml`), para não conflitar com um PostgreSQL instalado no
sistema na 5432. A `DATABASE_URL` precisa usar a mesma porta.

## Migrações

O schema do banco é controlado pelo [Alembic](https://alembic.sqlalchemy.org/),
com as migrações em `migrations/versions/`. A aplicação não cria tabelas ao
subir: quem cria e altera é o `alembic upgrade head`.

Ao mudar um modelo em `app/models/`, gere a migração, revise o arquivo gerado
e aplique:

```bash
poetry run alembic revision --autogenerate -m "descreve a mudança"
poetry run alembic upgrade head
```

O autogenerate não detecta tudo (por exemplo, renomear coluna vira remover e
adicionar), por isso a revisão manual é obrigatória. O teste
`tests/test_migracoes.py` aplica as migrações num SQLite e as compara com os
modelos: modelo alterado sem migração quebra a CI.

### Banco criado antes do Alembic

Um banco criado pelo antigo `create_all` já tem as tabelas, mas não tem a
tabela `alembic_version`. Antes do primeiro `task run` (ou `alembic upgrade
head`) depois desta mudança, ele precisa ser marcado como migrado (`stamp`) ou
recriado; senão o upgrade tenta criar as tabelas de novo e falha com
`relation "user" already exists`.

Para preservar os dados, primeiro compare o banco com os modelos. A comparação
só lê o banco; o `alembic check` não serve aqui, porque exige um banco já
marcado e falha com `Target database is not up to date`:

```bash
poetry run python -c 'from alembic.autogenerate import compare_metadata; from alembic.migration import MigrationContext; from sqlalchemy import create_engine; from sqlmodel import SQLModel; from app.config import settings; import app.models.user, app.models.ticket; c = create_engine(settings.DATABASE_URL).connect(); print(compare_metadata(MigrationContext.configure(c), SQLModel.metadata) or "sem diferenças")'
```

Só se a saída for `sem diferenças`, marque e confirme:

```bash
poetry run alembic stamp head
poetry run alembic check    # No new upgrade operations detected.
```

O `stamp` só grava a revisão em `alembic_version`; para desfazê-lo, use
`poetry run alembic stamp base`. Se os dados forem descartáveis, recrie o
banco em vez disso:

```bash
docker compose down -v
poetry run task run
```

## Testes e lint

Os testes usam SQLite em memória e simulam o Gemini com mock. Rode sempre com
variáveis falsas, para que o `.env` real não seja carregado:

```bash
env GEMINI_API_KEY=chave-falsa DATABASE_URL=sqlite:// SECRET_KEY=segredo-de-teste \
  poetry run python -m pytest -q
poetry run ruff check
poetry run ruff format --check
```

A CI (`.github/workflows/ci.yml`) roda os mesmos comandos a cada pull request
e a cada push na `main`.

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
- `migrations/`: migrações do Alembic (`env.py` e `versions/`).
- `tests/`: testes com pytest.

## Convenções

- Commits: `tipo(escopo): Descrição em português`, com `feat` e `test` em
  commits separados.
- Branches: `<número-da-issue>-<tipo>/<descrição>`; sem issue,
  `<tipo>/<descrição>`.
