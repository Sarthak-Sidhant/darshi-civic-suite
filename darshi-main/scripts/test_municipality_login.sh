#!/bin/bash
# Test script to verify municipality admin login and token

echo "=== Testing Municipality Admin Login ==="

# 1. Login and get token
echo "1. Logging in as ranchi_admin..."
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8080/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ranchi_admin&password=securepass123")

echo "Login Response: $LOGIN_RESPONSE"

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ FAILED: No token received"
  exit 1
fi

echo "✅ Token received: ${TOKEN:0:50}..."

# 2. Decode token to check claims (base64 decode the payload)
echo ""
echo "2. Decoding token payload..."
PAYLOAD=$(echo $TOKEN | cut -d'.' -f2)
# Add padding if needed
PADDING=$((4 - ${#PAYLOAD} % 4))
if [ $PADDING -ne 4 ]; then
  PAYLOAD="${PAYLOAD}$(printf '=%.0s' $(seq 1 $PADDING))"
fi
DECODED=$(echo $PAYLOAD | base64 -d 2>/dev/null)
echo "Token Claims: $DECODED"

# 3. Test municipality dashboard access
echo ""
echo "3. Testing /api/v1/municipality/dashboard access..."
DASHBOARD_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/municipality/dashboard")

HTTP_CODE=$(echo "$DASHBOARD_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY=$(echo "$DASHBOARD_RESPONSE" | sed '/HTTP_CODE/d')

echo "HTTP Status: $HTTP_CODE"
echo "Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ SUCCESS: Dashboard accessible"
else
  echo "❌ FAILED: Dashboard returned $HTTP_CODE"
fi
