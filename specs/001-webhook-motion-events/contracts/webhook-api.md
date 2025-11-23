# Webhook API Contract: TPLink Vigi Motion Detection

**Feature**: 001-webhook-motion-events
**Date**: 2025-11-20
**Version**: 1.0.0

## Overview

This document defines the API contract for TPLink Vigi camera webhooks. Cameras POST motion detection events to Home Assistant webhook endpoints, optionally including captured images.

## Base URL

```
{home_assistant_url}/api/webhook/{webhook_id}
```

**Parameters:**
- `home_assistant_url`: Base URL of Home Assistant instance (e.g., `http://192.168.1.50:8123`)
- `webhook_id`: Auto-generated UUID identifier for specific camera (e.g., `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)

**Example:**
```
http://192.168.1.50:8123/api/webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

## Authentication

**None** - Webhook IDs act as bearer tokens. No additional authentication required in initial version.

**Security Note**: Webhook UUIDs provide sufficient entropy (2^122 possibilities) to prevent guessing. Future versions may add HMAC signatures or API keys if needed.

## Endpoints

### POST /api/webhook/{webhook_id}

Receive motion detection event from camera, optionally with captured image.

---

#### Request Format 1: JSON Body (No Image)

**Content-Type**: `application/json`

**Headers:**
```
POST /api/webhook/{webhook_id} HTTP/1.1
Host: {home_assistant_url}
Content-Type: application/json
Content-Length: {length}
```

**Body Schema:**
```json
{
    "device_name": "string",  // Optional, camera's self-reported name
    "ip": "string",            // Optional, camera IP address
    "mac": "string",           // Optional, camera MAC address
    "event_list": [            // Required, array of events
        {
            "dateTime": "string",      // Optional, format: YYYYMMDDHHmmss
            "event_type": ["string"]   // Optional, array of event type names
        }
    ]
}
```

**Field Descriptions:**

| Field | Type | Required | Format/Validation | Description |
|-------|------|----------|-------------------|-------------|
| `device_name` | string | No | Any string | Camera's self-reported device name |
| `ip` | string | No | IPv4 address | Camera's IP address on the network |
| `mac` | string | No | MAC address | Camera's MAC address (format: AA:BB:CC:DD:EE:FF) |
| `event_list` | array | Yes | Non-empty | List of motion events (typically single element) |
| `event_list[].dateTime` | string | No | YYYYMMDDHHmmss | Timestamp when event occurred on camera |
| `event_list[].event_type` | array | No | Array of strings | Types of motion detected (e.g., ["motion"], ["person", "vehicle"]) |

**Example Request:**
```http
POST /api/webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890 HTTP/1.1
Host: 192.168.1.50:8123
Content-Type: application/json
Content-Length: 189

{
    "device_name": "Front Door Camera",
    "ip": "192.168.1.100",
    "mac": "AA:BB:CC:DD:EE:FF",
    "event_list": [
        {
            "dateTime": "20231120150530",
            "event_type": ["motion"]
        }
    ]
}
```

**Success Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{}
```

---

#### Request Format 2: Multipart Form (With Image)

**Content-Type**: `multipart/form-data; boundary={boundary}`

**Headers:**
```
POST /api/webhook/{webhook_id} HTTP/1.1
Host: {home_assistant_url}
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary
Content-Length: {length}
```

**Body Structure:**

The multipart body contains two parts:

1. **data** part (JSON event metadata)
2. **image** part (binary image data)

**Multipart Schema:**
```
------WebKitFormBoundary
Content-Disposition: form-data; name="event"
Content-Type: application/json

{JSON event data - same schema as Request Format 1}

------WebKitFormBoundary
Content-Disposition: form-data; name="20251123180936"
Content-Type: image/jpeg

{binary image data}

------WebKitFormBoundary--
```

**Part Specifications:**

**Part 1: event**
- **name**: "event" (fixed field name)
- **Content-Type**: application/json
- **Content**: Same JSON schema as Request Format 1 (bytearray that needs UTF-8 decoding)
- **Required**: Yes

**Part 2: image**
- **name**: Variable - datetime string (e.g., "20251123180936") matching the event dateTime
- **Content-Type**: image/jpeg (typically)
- **filename**: Not included by camera
- **Content**: Binary image data as bytearray (JPEG format, starts with `\xff\xd8\xff\xdb`)
- **Size**: Recommended ≤5MB (warning logged if exceeded)
- **Required**: No

**Example Request:**
```http
POST /api/webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890 HTTP/1.1
Host: 192.168.1.50:8123
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary
Content-Length: 245621

------WebKitFormBoundary
Content-Disposition: form-data; name="event"
Content-Type: application/json

{
    "ip": "192.168.70.3",
    "mac": "20-23-51-cd-9f-ae",
    "protocol": "HTTP",
    "device_name": "Backyard",
    "event_list": [
        {
            "dateTime": "20251123180936",
            "event_type": ["PEOPLE"]
        }
    ]
}

------WebKitFormBoundary
Content-Disposition: form-data; name="20251123180936"
Content-Type: image/jpeg

<binary JPEG image data as bytearray - starts with \xff\xd8\xff\xdb>

------WebKitFormBoundary--
```

**Success Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{}
```

---

## Response Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| 200 OK | Success | Webhook processed successfully |
| 400 Bad Request | Invalid Request | Malformed JSON or multipart data |
| 404 Not Found | Unknown Webhook | Webhook ID not registered or integration deleted |
| 413 Payload Too Large | Image Too Large | Image exceeds server limits (typically >10MB) |
| 500 Internal Server Error | Processing Error | Unexpected error during processing |

**Error Response Format:**
```json
{
    "error": "string",        // Error message
    "details": "string"       // Additional error details (optional)
}
```

**Error Examples:**

**400 Bad Request - Malformed JSON:**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
    "error": "Invalid JSON",
    "details": "Expecting property name enclosed in double quotes"
}
```

**404 Not Found - Unknown Webhook:**
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
    "error": "Webhook not found",
    "details": "Webhook ID 'xyz' is not registered"
}
```

---

## Error Handling

### Client-Side (Camera) Behavior

**Recommended Retry Logic:**
- **200 OK**: Success, no retry needed
- **4xx errors**: Log error, do not retry (client error)
- **5xx errors**: Retry with exponential backoff (max 3 attempts)
- **Network timeout**: Retry with exponential backoff (max 3 attempts)

**Retry Schedule Example:**
- 1st retry: 5 seconds
- 2nd retry: 15 seconds
- 3rd retry: 45 seconds
- Give up after 3 failed attempts

### Server-Side (Home Assistant) Behavior

Per specification edge cases:

1. **Malformed Data (FR-022)**: Log warning with details, return 400 Bad Request
2. **Missing event_list**: Log warning, return 400 Bad Request
3. **Network Interruption During Image (FR-021)**: Log warning, process event without image, return 200 OK
4. **Oversized Image (FR-023)**: Log warning with size, continue processing, return 200 OK
5. **Unknown Webhook ID**: Return 404 Not Found
6. **Processing Exception**: Log error with traceback, return 500 Internal Server Error

---

## Validation Rules

### JSON Format Validation

**Required Fields:**
- `event_list`: Must be present and non-empty array

**Optional Fields (defaults applied):**
- `device_name`: Defaults to "Unknown"
- `ip`: Defaults to "Unknown"
- `mac`: Defaults to "Unknown"
- `event_list[].dateTime`: Defaults to current server time
- `event_list[].event_type`: Defaults to ["unknown"]

**Type Validation:**
- `event_list`: Must be array
- `event_list[].event_type`: Must be array of strings
- `device_name`, `ip`, `mac`: Must be strings if provided

**Format Validation:**
- `dateTime`: Must match YYYYMMDDHHmmss pattern (e.g., "20231120150530")
- Invalid datetime → log warning, use current server time

### Multipart Format Validation

**Part Names:**
- "data" part: Required
- "image" part: Optional

**Content-Type Validation:**
- "data" part: Must be application/json
- "image" part: Should be image/jpeg or image/png (not strictly enforced)

**Size Limits:**
- Overall payload: No hard limit (server default, typically 10-100MB)
- Image size: Warning logged if >5MB, but processing continues

---

## Idempotency

**Not Guaranteed**: Each webhook POST is processed independently. Duplicate requests (same event sent twice) will:
- Trigger duplicate state updates (acceptable - most recent state retained)
- Replace previous image with duplicate image (acceptable)
- Generate duplicate log entries (acceptable)

**Recommendation**: Cameras should avoid sending duplicate events for the same motion detection occurrence.

---

## Rate Limiting

**Not Enforced**: No explicit rate limiting in initial version.

**Hardware Limitation**: TPLink Vigi cameras cannot send events more frequently than once per second (camera hardware constraint per spec assumption).

**Future Consideration**: If rate limiting needed, implement per-webhook-id throttling (e.g., max 10 requests per minute).

---

## Security Considerations

### Current Security Model

- **Webhook ID as Bearer Token**: UUID provides 2^122 bits of entropy
- **No Additional Authentication**: No HMAC, API keys, or signatures
- **Network Security**: Relies on network-level security (firewall, VLANs)

### Threat Model

**Acceptable Risks (Initial Version):**
- Unauthorized POST to webhook (if UUID leaked) → log entry created, false motion detection
- Network eavesdropping → image and metadata visible in transit

**Mitigations (Initial Version):**
- Use HTTPS for Home Assistant instance (recommended but not required)
- Keep webhook UUIDs secret (don't publish publicly)
- Use network segmentation (cameras on isolated VLAN)

**Future Enhancements (If Needed):**
- HMAC signature validation (using shared secret)
- API key header (X-API-Key)
- Rate limiting per webhook_id
- IP whitelisting per camera

---

## Examples

### Example 1: Simple Motion Event (JSON)

**Request:**
```bash
curl -X POST \
  'http://192.168.1.50:8123/api/webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890' \
  -H 'Content-Type: application/json' \
  -d '{
    "device_name": "Back Yard Camera",
    "ip": "192.168.1.101",
    "mac": "11:22:33:44:55:66",
    "event_list": [
        {
            "dateTime": "20231120160730",
            "event_type": ["motion"]
        }
    ]
}'
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{}
```

**Home Assistant Result:**
- Binary sensor: `back_yard_camera_motion` → ON
- State attributes: `event_type: ["motion"]`, `event_time: "2023-11-20T16:07:30"`
- Auto-reset scheduled after 5 seconds (default)

---

### Example 2: Motion Event With Image (Multipart)

**Request:**
```bash
curl -X POST \
  'http://192.168.1.50:8123/api/webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890' \
  -F 'data={"device_name":"Front Door Camera","ip":"192.168.1.100","mac":"AA:BB:CC:DD:EE:FF","event_list":[{"dateTime":"20231120150530","event_type":["motion","person"]}]};type=application/json' \
  -F 'image=@snapshot.jpg;type=image/jpeg'
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{}
```

**Home Assistant Result:**
- Binary sensor: `front_door_camera_motion` → ON
- State attributes: `event_type: ["motion", "person"]`, `event_time: "2023-11-20T15:05:30"`
- Image entity: `front_door_camera_last_image` → Updated with snapshot.jpg bytes
- Image attributes: `image_last_updated: "2023-11-20T15:05:30"`, `image_size: 245621`

---

### Example 3: Minimal Event (No Optional Fields)

**Request:**
```bash
curl -X POST \
  'http://192.168.1.50:8123/api/webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890' \
  -H 'Content-Type: application/json' \
  -d '{
    "event_list": [{}]
}'
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{}
```

**Home Assistant Result:**
- Binary sensor → ON
- State attributes use defaults: `device_name: "Unknown"`, `event_type: ["unknown"]`, `event_time: null`

---

## Testing

### Manual Testing with curl

**Test JSON format:**
```bash
curl -X POST 'http://localhost:8123/api/webhook/{your-webhook-id}' \
  -H 'Content-Type: application/json' \
  -d '{"event_list":[{"dateTime":"20231120120000","event_type":["motion"]}]}'
```

**Test multipart format:**
```bash
# Note: Camera uses field name "event" for JSON and datetime string for image field name
curl -X POST 'http://localhost:8123/api/webhook/{your-webhook-id}' \
  -F 'event={"ip":"192.168.70.3","mac":"20-23-51-cd-9f-ae","protocol":"HTTP","device_name":"Test Camera","event_list":[{"dateTime":"20251123180936","event_type":["PEOPLE"]}]};type=application/json' \
  -F '20251123180936=@test_image.jpg;type=image/jpeg'
```

**Test invalid webhook:**
```bash
curl -X POST 'http://localhost:8123/api/webhook/invalid-uuid-12345' \
  -H 'Content-Type: application/json' \
  -d '{"event_list":[{}]}'
# Expected: 404 Not Found
```

**Test malformed JSON:**
```bash
curl -X POST 'http://localhost:8123/api/webhook/{your-webhook-id}' \
  -H 'Content-Type: application/json' \
  -d '{invalid json'
# Expected: 400 Bad Request
```

---

## Changelog

**Version 1.0.0** (2025-11-20):
- Initial webhook API contract
- JSON body format support
- Multipart form format support
- UUID-based webhook IDs
- No authentication (UUID as bearer token)
- 5MB image size recommendation with warning
