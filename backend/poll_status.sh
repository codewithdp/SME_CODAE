#!/bin/bash
RECON_ID=$1

if [ -z "$RECON_ID" ]; then
  echo "Usage: $0 <reconciliation_id>"
  exit 1
fi

echo "Polling status for reconciliation: $RECON_ID"
echo ""

for i in {1..30}; do
  echo "=== Check $i ==="
  RESPONSE=$(curl -s http://localhost:8000/api/v1/reconciliation/${RECON_ID}/status)

  STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  PROGRESS=$(echo "$RESPONSE" | grep -o '"progress_percentage":[0-9]*' | cut -d':' -f2)
  STEP=$(echo "$RESPONSE" | grep -o '"current_step":"[^"]*"' | cut -d'"' -f4)

  echo "Status: $STATUS | Progress: $PROGRESS% | Step: $STEP"

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    echo ""
    echo "✅ Processing finished!"
    echo ""
    echo "Full response:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    break
  fi

  sleep 3
  echo ""
done
