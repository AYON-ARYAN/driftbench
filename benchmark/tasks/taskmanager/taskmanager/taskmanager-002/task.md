Secure the `POST /tasks` endpoint so that it requires Bearer Token authorization.
- Token format must be exactly `Bearer agent-secret-token`.
- If the `Authorization` header is missing, incorrect, or malformed, return `401 Unauthorized` with a JSON body `{"error": "unauthorized", "message": "invalid credentials"}`.
- If the token is valid, proceed with creating the task as usual and return 201 Created.
