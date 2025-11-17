#!/bin/bash

# TP-Link VIGI Webhook Test Script
# Usage: ./test_webhook.sh WEBHOOK_ID [HOME_ASSISTANT_URL]
#
# Examples:
#   ./test_webhook.sh front_door_camera
#   ./test_webhook.sh front_door_camera http://192.168.1.100:8123

# Check if webhook ID is provided
if [ -z "$1" ]; then
    echo "Error: Webhook ID is required"
    echo "Usage: $0 WEBHOOK_ID [HOME_ASSISTANT_URL]"
    echo ""
    echo "Examples:"
    echo "  $0 front_door_camera"
    echo "  $0 front_door_camera http://192.168.1.100:8123"
    exit 1
fi

WEBHOOK_ID="$1"
HA_URL="${2:-http://homeassistant.local:8123}"

# Generate current timestamp in the format VIGI cameras use (YYYYMMDDHHmmss)
TIMESTAMP=$(date +"%Y%m%d%H%M%S")

echo "========================================="
echo "TP-Link VIGI Webhook Test"
echo "========================================="
echo "Webhook ID:  $WEBHOOK_ID"
echo "HA URL:      $HA_URL"
echo "Webhook URL: $HA_URL/api/webhook/$WEBHOOK_ID"
echo "Timestamp:   $TIMESTAMP"
echo "========================================="
echo ""

# Send test webhook
curl -X POST "$HA_URL/api/webhook/$WEBHOOK_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_name\": \"Test Camera\",
    \"ip\": \"192.168.1.100\",
    \"mac\": \"AA:BB:CC:DD:EE:FF\",
    \"event_list\": [{
      \"dateTime\": \"$TIMESTAMP\",
      \"event_type\": [\"motion\", \"person\"]
    }]
  }" \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo "========================================="
echo "Expected Results:"
echo "- HTTP Status: 200"
echo "- Binary sensor turns ON in Home Assistant"
echo "- Attributes show: motion, person"
echo "- Auto-resets to OFF after 5 seconds"
echo "========================================="
