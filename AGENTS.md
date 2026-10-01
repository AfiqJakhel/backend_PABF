# Backend Project Instructions

## Scope

- This is the Flask API for SIMAS UNAND in `backend_PABF/`.
- The application is created by `app.create_app()` and started by `run.py`.
- Keep the existing separation of concerns: routes register endpoints, controllers handle request/response flow, services contain business logic, repositories contain persistence queries, and models define SQLAlchemy entities.

## Stack and conventions

- Use Python with Flask, Flask-SQLAlchemy, Flask-Migrate/Alembic, Flask-JWT-Extended, Flask-CORS, and PyMySQL as defined in `requirements.txt`.
- Preserve the existing JSON response shape (`success`, `message`, and `data`) for API responses unless a deliberate contract change is required.
- Protect authenticated endpoints with the existing JWT middleware/decorators and enforce role access at the backend boundary, not only in the frontend.
- Validate request input before database operations and return appropriate HTTP status codes with clear Indonesian messages consistent with nearby controllers.
- Read configuration from environment variables through `config.py`. Never commit credentials, production secrets, or local `.env` values.
- Store uploaded files only under the configured upload directory and validate filenames, types, and sizes before writing them.
- Keep database schema changes in `migrations/versions/`; do not manually edit an existing applied migration. Import new models through `app/models/__init__.py` so Alembic can discover them.

## Validation

- Activate the project virtual environment before running Python commands.
- Run `python -m pytest` for tests and use `flask db upgrade` only against the intended configured database.
- For a route change, exercise the affected endpoint and its authentication/authorization cases when practical.
- Run `python run.py` only when a live development server is needed; do not commit generated runtime files or uploaded data.

## Change discipline

- Inspect neighboring controllers, services, repositories, models, and tests before adding a new pattern.
- Keep route prefixes and API contracts synchronized with the frontend and Postman collections.
- Prefer small, focused changes. Do not refactor unrelated modules while fixing one endpoint.