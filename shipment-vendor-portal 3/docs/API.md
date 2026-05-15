# REST API Reference (v1)

Base URL: `http(s)://<host>/api/v1`
Auth: JWT bearer token. Get a token from `POST /auth/login`, then send it as
`Authorization: Bearer <token>` on every subsequent request.

All bodies and responses are JSON. Dates use ISO-8601 (`YYYY-MM-DD`).

## Authentication

### `POST /auth/login`

```json
{ "email": "admin@example.com", "password": "admin123" }
```

Response 200:

```json
{ "access_token": "eyJhbGc...", "role": "admin", "name": "Admin User" }
```

### `GET /me`

Returns the current user's profile.

```json
{ "id": 1, "name": "Admin User", "email": "admin@example.com", "role": "admin" }
```

## Shipments

### `GET /shipments`

Query params: `page`, `per_page` (max 200), `status`, `delay_status`, `q` (search PO/OEM).

Response:

```json
{
  "items": [ { "id": 1, "customer_po_number": "CPO-1001", "..." : "..." } ],
  "page": 1, "pages": 4, "total": 92
}
```

### `GET /shipments/{id}`
Returns the full shipment object (every column).

### `POST /shipments`
Body: any subset of shipment columns. Date columns must be `YYYY-MM-DD`.
The server **auto-recomputes** `payment_days`, `readiness_delay_days`,
`sailing_delayed_days`, `cc_delayed_days`, `total_clearance_days`, and
`delay_status` on every create/update.

### `PUT|PATCH /shipments/{id}`
Same body shape as POST.

### `DELETE /shipments/{id}`
Returns 204.

## Vendors

### `GET /vendors`
Returns the list of all vendors.

## RFQs & Quotations

### `GET /rfqs`
List of all RFQ headers.

### `GET /rfqs/{id}/quotations`
Returns the RFQ header plus all quotations submitted by vendors. Useful for a
mobile or external comparison view.

```json
{
  "rfq": { "id": 5, "rfq_number": "RFQ-2026-001", "...": "..." },
  "items": [
    { "id": 1, "vendor": "Blue Ocean Logistics", "unit_price": 9800,
      "total_price": 4900000, "currency": "INR", "delivery_days": 28,
      "is_selected": false, "submitted_at": "2026-05-10T12:30:00" }
  ]
}
```

## Curl example

```bash
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r .access_token)

curl -s http://localhost:5000/api/v1/shipments?per_page=5 \
  -H "Authorization: Bearer $TOKEN" | jq
```

## Error format

```json
{ "error": "invalid_credentials" }
```

| HTTP | meaning             |
|------|---------------------|
| 400  | bad request         |
| 401  | missing/invalid JWT |
| 403  | role not allowed    |
| 404  | not found           |
| 422  | validation failed   |
