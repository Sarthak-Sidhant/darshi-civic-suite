#!/bin/bash
# Debug script - run this on production server

echo "=== DEBUGGING MUNICIPALITY ADMIN ACCESS ==="
echo ""

echo "1. Checking user in database..."
docker exec -i darshi-postgres psql -U postgres -d darshi -c "SELECT username, email, role, municipality_id, is_active FROM users WHERE username = 'ranchi_admin';"

echo ""
echo "2. Testing login API..."
LOGIN_RESP=$(curl -s -X POST "http://localhost:8080/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ranchi_admin&password=securepass123")

echo "$LOGIN_RESP"

TOKEN=$(echo "$LOGIN_RESP" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed - no token received"
  exit 1
fi

echo ""
echo "3. Decoding token payload..."
PAYLOAD=$(echo "$TOKEN" | cut -d'.' -f2)
# Add padding
PADDING=$((4 - ${#PAYLOAD} % 4))
if [ $PADDING -ne 4 ]; then
  PAYLOAD="${PAYLOAD}$(printf '=%.0s' $(seq 1 $PADDING))"
fi
echo "$PAYLOAD" | base64 -d 2>/dev/null | jq . || echo "$PAYLOAD" | base64 -d 2>/dev/null

echo ""
echo "4. Testing municipality dashboard API..."
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/municipality/dashboard"

echo ""
echo "=== END DEBUG ==="
