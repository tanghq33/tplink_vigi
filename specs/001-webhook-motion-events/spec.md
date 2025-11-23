# Feature Specification: TPLink Vigi Webhook Motion Detection

**Feature Branch**: `001-webhook-motion-events`
**Created**: 2025-11-20
**Status**: Draft
**Input**: User description: "I am building a home assistant custom integrations that integrate TPLink Vigi cameras, for now it will create a webhook listens the camera send event when motion is detected. The camera will send event and image when motion is detected. The home assistant integration will create a device (which is camera) and it might have multiple entiities, such as binary sensor, and an entity to store last triggered image. One integration = 1 webhook = only 1 camera. If user have multiple camera, it will have to setup one by one. The structure have to be able to easily extend, in the future we might have other feature."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Single Camera for Motion Detection (Priority: P1)

A Home Assistant user wants to receive motion detection alerts from their TPLink Vigi camera. They configure the integration once per camera, and the system automatically creates the necessary entities to track motion events and view captured images.

**Why this priority**: This is the core MVP functionality. Without the ability to configure a camera and receive motion events, the integration provides no value. This represents the minimum viable feature that delivers immediate utility to users.

**Independent Test**: Can be fully tested by configuring one camera through the Home Assistant UI, triggering motion on the camera, and verifying that the motion sensor changes state and the image entity updates with the captured image.

**Acceptance Scenarios**:

1. **Given** a user has a TPLink Vigi camera on their network, **When** they add the integration through Home Assistant's configuration UI, **Then** the system automatically generates a random UUID as the webhook ID and displays the complete webhook URL for the user to configure on their camera
2. **Given** a configured integration, **When** the user opens the integration options to edit configuration, **Then** the webhook URL is displayed so they can copy it again if needed
3. **Given** a camera is configured with the webhook URL, **When** the camera detects motion and sends a JSON body without image, **Then** the binary sensor entity changes to "detected" state within 2 seconds
4. **Given** a camera is configured with the webhook URL, **When** the camera detects motion and sends a multipart form with image, **Then** both the binary sensor changes to "detected" and the image entity updates with the captured image
5. **Given** multiple motion events occur over time, **When** viewing the entities, **Then** only the most recent motion event and most recent image are displayed (previous events are replaced)
6. **Given** motion stops, **When** a configurable timeout period elapses, **Then** the binary sensor returns to "clear" state
7. **Given** a configured camera, **When** the user views the device in Home Assistant, **Then** they see the camera device with all associated entities (motion sensor, last image)

---

### User Story 2 - Configure Multiple Cameras Independently (Priority: P2)

A user with multiple TPLink Vigi cameras wants to monitor motion from all cameras. They configure each camera as a separate integration instance, with each camera having its own webhook endpoint and entities.

**Why this priority**: Many users have multiple cameras for comprehensive coverage. While each camera requires individual setup, this enables full multi-camera monitoring which is essential for real-world security deployments.

**Independent Test**: Can be tested by adding two or more integration instances, each with a different camera, verifying that each camera's webhook is unique, and confirming that motion events from each camera update only their respective entities without cross-interference.

**Acceptance Scenarios**:

1. **Given** a user has already configured one camera, **When** they add another camera through a new integration instance, **Then** a new unique webhook URL is generated for the second camera
2. **Given** multiple cameras are configured, **When** motion occurs on camera A, **Then** only camera A's binary sensor activates (not camera B's sensor)
3. **Given** two cameras with the same physical model, **When** viewing the device list, **Then** each camera device is clearly identifiable with unique names or identifiers
4. **Given** multiple configured cameras, **When** the user removes one integration instance, **Then** only that camera's entities are removed without affecting other cameras

---

### User Story 3 - View Motion Event History and Images (Priority: P3)

A user wants to review past motion detection events and access previously captured images to understand activity patterns or investigate security concerns.

**Why this priority**: While receiving real-time alerts is critical (P1), reviewing historical data provides additional value for security and monitoring use cases. This enhances the utility of the integration but is not required for basic operation.

**Independent Test**: Can be tested by triggering multiple motion events over time, then accessing the entity history to verify that all motion events are recorded with timestamps and that previous images are accessible through entity attributes or a defined storage mechanism.

**Acceptance Scenarios**:

1. **Given** motion has been detected multiple times, **When** the user views the binary sensor's history, **Then** they see a timeline of all detection events with timestamps
2. **Given** multiple images have been captured, **When** the user accesses the image entity attributes, **Then** they can see metadata about the last captured image (timestamp, file size)
3. **Given** historical motion events exist, **When** the user queries the entity state, **Then** the timestamp of the last motion event is accessible as an entity attribute

---

### Edge Cases

1. **Network interruption before image transmission**: Log warning message and continue operation. The binary sensor will still update to "detected" state even if image fails to transmit. The image entity will retain the previous image.

2. **Malformed data or unexpected payload format**: Log warning message with details of the malformed data and continue operation. Do not crash or disable the integration. Subsequent valid requests should be processed normally.

3. **Multiple rapid motion events (within 1 second)**: Not applicable - the camera hardware prevents sending events more frequently than once per second.

4. **Camera offline then comes back online**: No special handling required. The webhook is passive and only responds when the camera sends requests. When the camera comes back online and sends events, they will be processed normally.

5. **Integration deleted but camera continues sending webhook requests**: The webhook endpoint MUST be unregistered immediately when the integration is deleted. Subsequent requests to the unregistered webhook should return appropriate HTTP error codes and be ignored.

6. **Image exceeds expected size limits**: Log warning message indicating the image size and continue processing the motion event. The binary sensor updates normally; the image entity may show a placeholder or the previous image if the large image cannot be processed.

7. **Home Assistant restarts during active motion event**: The last captured image is preserved and displayed when Home Assistant restarts. The motion event state is cleared on restart (binary sensor returns to "clear" state). This is acceptable behavior as the event is likely no longer active.

8. **Unauthorized webhook requests**: No authentication or authorization verification is implemented in the initial version. All requests to the webhook endpoint are processed. Security may be added in future iterations if needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a configuration flow that allows users to set up one camera per integration instance
- **FR-002**: System MUST automatically generate a random UUID as the webhook ID when a new integration instance is created
- **FR-003**: Webhook ID MUST NOT be editable by users after generation
- **FR-004**: System MUST construct the webhook URL using the generated UUID and display it to the user during initial configuration
- **FR-005**: System MUST display the webhook URL when users access the integration options or edit configuration
- **FR-006**: System MUST create a Home Assistant device representing the camera
- **FR-007**: System MUST create a binary sensor entity that reflects motion detection state (detected/clear)
- **FR-008**: System MUST create an entity that stores and displays the last captured motion image
- **FR-009**: System MUST accept incoming webhook POST requests with JSON body format (motion event without image)
- **FR-010**: System MUST accept incoming webhook POST requests with multipart form format (motion event with image)
- **FR-011**: System MUST update the binary sensor state to "detected" when a motion event is received
- **FR-012**: System MUST update the image entity with the new image when an image is received with a motion event
- **FR-013**: System MUST keep only the most recent motion event, replacing previous events when new events arrive
- **FR-014**: System MUST keep only the most recent captured image, replacing previous images when new images arrive
- **FR-015**: System MUST automatically reset the binary sensor to "clear" after a configurable timeout period when no further motion is detected
- **FR-016**: System MUST handle multiple independent integration instances for multiple cameras without interference
- **FR-017**: System MUST persist camera configuration across Home Assistant restarts
- **FR-018**: System MUST immediately unregister the webhook endpoint when an integration instance is deleted
- **FR-019**: System MUST support clean removal of integration instances including webhook deregistration and entity cleanup
- **FR-020**: System MUST log all webhook events with appropriate log levels (errors for failures, warnings for data issues, debug for normal operations)
- **FR-021**: System MUST log warnings and continue operation when network interruptions occur during image transmission
- **FR-022**: System MUST log warnings and continue operation when malformed data or unexpected payloads are received
- **FR-023**: System MUST log warnings and continue operation when images exceed expected size limits
- **FR-024**: System MUST provide user-friendly device and entity naming that identifies each camera clearly
- **FR-025**: System MUST store webhook endpoint configuration in a way that allows future feature extensions
- **FR-026**: Binary sensor state changes MUST trigger Home Assistant automations as expected
- **FR-027**: Image entity updates MUST make the image accessible through standard Home Assistant image display mechanisms

### Key Entities

- **Camera Device**: Represents a single TPLink Vigi camera in Home Assistant. Contains metadata about the camera including friendly name, unique identifier (auto-generated UUID), and webhook URL. Parent container for all camera-related entities.

- **Motion Binary Sensor**: An on/off sensor entity that indicates current motion detection status. State is "on" (detected) when motion event received, "off" (clear) after timeout. Includes attributes for last detection timestamp. Only the most recent motion event state is retained.

- **Motion Image**: An entity that stores and displays only the most recent image captured during a motion event. Previous images are replaced when new images arrive. Contains the image data, timestamp of capture, and image metadata (resolution, file size).

- **Webhook Endpoint**: A unique URL endpoint constructed using an auto-generated UUID for each camera configuration. Receives HTTP POST requests from the camera in two formats: JSON body (motion event without image) or multipart form (motion event with image). The webhook ID cannot be changed by users after creation.

- **Configuration Entry**: User configuration data for each integration instance including camera name, auto-generated webhook UUID, webhook timeout duration, and any camera-specific settings. The webhook URL is viewable but not editable in the configuration interface.

### Webhook Payload Format Specification

**JSON Format (Motion Event Without Image)**:
```json
{
    "ip": "192.168.70.3",
    "mac": "20-23-51-cd-9f-ae",
    "protocol": "HTTP",
    "device_name": "Backyard",
    "event_list": [{
        "dateTime": "20251123180936",
        "event_type": ["PEOPLE"]
    }]
}
```

**Multipart Form Format (Motion Event With Image)**:
- Content-Type: `multipart/form-data`
- Field 1 name: `"event"` - Contains JSON event data (same structure as JSON format above)
- Field 2 name: Variable (datetime string, e.g., `"20251123180936"`) - Contains image bytes (bytearray)
- Image format: JPEG (starts with `\xff\xd8\xff\xdb` signature)

**Implementation Notes**:
- The multipart parser MUST look for a field named `"event"` for JSON data
- Any other field in the multipart payload MUST be treated as image data
- Image field name is variable (uses the event datetime), so implementation MUST NOT hard-code the field name
- Both fields contain bytearray data that needs proper decoding

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete the configuration of a single camera in under 3 minutes including copying the webhook URL to the camera settings
- **SC-002**: Motion events trigger binary sensor state changes within 2 seconds of camera sending the webhook request
- **SC-003**: Image entities update with new images within 3 seconds of receiving the image data from the camera
- **SC-004**: The system successfully handles at least 10 simultaneous camera integrations without performance degradation
- **SC-005**: Binary sensor state resets to "clear" within 5 seconds after the configured timeout period when no new motion occurs
- **SC-006**: 100% of valid webhook requests from configured cameras result in appropriate entity updates
- **SC-007**: Users can successfully configure additional cameras without errors in under 3 minutes per additional camera
- **SC-008**: The integration persists all configuration and state through Home Assistant restarts with 100% reliability
- **SC-009**: Invalid or malformed webhook requests are rejected and logged without crashing the integration or affecting valid requests
- **SC-010**: Users can identify and distinguish between multiple cameras through device and entity names without confusion

### Assumptions

- TPLink Vigi cameras support configurable webhook endpoints for motion events
- Cameras can send HTTP POST requests in two formats: JSON body (without image) or multipart form (with image)
- The camera's webhook format (JSON vs multipart) is configurable on the camera side by the user
- Cameras cannot send motion events more frequently than once per second due to hardware limitations
- Users have network access to configure their cameras to send webhooks to the Home Assistant instance
- Home Assistant instance is accessible to the cameras on the network (same LAN or proper port forwarding configured)
- Standard Home Assistant binary sensor and image entity types are appropriate for this use case
- Users understand they need to configure each camera individually and are comfortable with the one-integration-per-camera model
- Storing only the most recent event and image is acceptable for the initial version (full history may be added in future versions)
- Webhook authentication/authorization is not required for the initial version and may be added if security needs arise
- Future extensions will include additional entity types (e.g., sensor for event counts, switch for enabling/disabling detection)
