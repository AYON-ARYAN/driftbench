Add pagination to the album collection endpoint.

`GET /albums` should accept two optional query parameters:

- `limit` — maximum number of albums to return. Integer, 1 to 100. Defaults to 20.
- `offset` — number of albums to skip. Integer, 0 or greater. Defaults to 0.

Results stay ordered by `id` ascending. Requests with an out-of-range or
non-integer `limit` or `offset` must be rejected with HTTP 400 and the existing
error body shape. The shape of an individual album object must not change.
