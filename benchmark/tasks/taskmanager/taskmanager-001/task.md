Add an endpoint `GET /users/{user_id}` to retrieve user details.
It should:
- Take `user_id` as a path parameter (integer).
- Query the `users` SQLite table.
- Return `200 OK` with user JSON `{"id": id, "name": name, "email": email}` if found.
- Return `404 Not Found` with an appropriate JSON detail if the user ID is not registered in the system.
