# Classificador de Tickets

API FastAPI que recebe tickets e os classifica com o Gemini. SQLModel sobre PostgreSQL (docker-compose), autenticação JWT, Poetry, Python 3.12.

## Estrutura

- `app/app.py`: aplicação, rotas (prefixo `/v1`) e chamadas ao Gemini.
- `app/schemas.py`: modelos de entrada e de resposta.
- `app/models/`: tabelas `Ticket` e `User`.
- `app/core/security.py`: senha e JWT.
- `tests/`: pytest com `TestClient`, SQLite em memória e Gemini simulado com mock.

## Comandos

Testes, sempre com variáveis falsas no lugar do `.env`:

```bash
env GEMINI_API_KEY=chave-falsa DATABASE_URL=sqlite:// SECRET_KEY=segredo-de-teste \
  .venv/bin/python -m pytest -q
```

Lint e formatação: `.venv/bin/ruff check` e `.venv/bin/ruff format`.

## Regras

- Não rode `task run`: ele executa `sudo systemctl stop postgresql` e `docker compose down -v`, que apaga o volume do banco.
- Não rode `task test` nem `pytest` sem as variáveis acima: o `.env` real seria carregado, e um teste sem mock chamaria a API paga do Gemini.
- Todo teste que passe por uma rota que classifica ticket precisa de mock em `client.aio.models.generate_content`.
- Um schema usado como `response_model` não deve carregar validadores de entrada: dados antigos do banco que não passam na regra viram erro 500. Use um modelo de resposta separado.
- Com o sandbox ativo, rode `git push`, `git fetch`, `git pull` e `gh` como comandos simples, um por chamada, sem encadear com `&&` nem `cd`. Encadeados, eles rodam dentro do sandbox, onde o `gh` não alcança o keyring e acusa token inválido. Nesse caso o token está válido: não rode `gh auth login`.

## Convenções

- Commits: `tipo(escopo): Descrição em português`, com `feat` e `test` em commits separados.
- Branches: `<número-da-issue>-<tipo>/<descrição>`; sem issue, `<tipo>/<descrição>`.
- Ruff: linha de 79 colunas e aspas simples.
