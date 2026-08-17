Refactor the internal database connection helper `_conn()` in `app.py`.
Add an optimized cache or pooling parameter (such as setting the `timeout` parameter to `sqlite3.connect(..., timeout=10.0)`). 
No endpoints or schema parameters must change. The OpenAPI interface remains absolutely identical.
