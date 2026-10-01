@AGENTS.md

The rules in `AGENTS.md` are authoritative for this backend. In addition:

- Treat authentication, role checks, input validation, and database transaction behavior as part of every API change.
- When changing an endpoint contract, update the corresponding frontend client/types and relevant Postman documentation or tests in the same change.
- Check migration dependencies and the configured database before creating or applying migrations.
- Run the narrowest relevant test first, then the broader test suite when the environment is available.