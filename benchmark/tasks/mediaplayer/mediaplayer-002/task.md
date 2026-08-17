Add `limit` and `offset` query parameters to the `GET /tracks` collection endpoint.
- `limit` (optional integer, minimum: 1, maximum: 100, default: 20)
- `offset` (optional integer, minimum: 0, default: 0)
Verify that the returned array is appropriately sliced, and invalid non-integer inputs return 400 Bad Request.
