Refactor the database connection helper `_conn()` inside `app.py`.
Optimize query result compilation or SQLite connection parameter mapping (such as setting the `isolation_level` parameter explicitly to `sqlite3.connect(..., isolation_level=None)` or adding a custom timeout).
No endpoints, path parameters, or schemas should change. The OpenAPI interface remains absolutely identical.
