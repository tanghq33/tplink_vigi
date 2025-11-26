# TP-Link VIGI Camera Integration for Home Assistant
[![version](https://img.shields.io/github/manifest-json/v/tanghq33/tplink_vigi?filename=custom_components%2Ftplink_vigi%2Fmanifest.json&color=slateblue)](https://github.com/tanghq33/tplink_vigi/releases/latest)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?logo=HomeAssistantCommunityStore&logoColor=white)](https://github.com/hacs/integration)

Home Assistant custom integration for TP-Link VIGI security cameras that enables real-time event monitoring and image capture through webhook-based notifications.

> [!NOTE]
> This integration uses **local push notifications** from your VIGI cameras. No cloud dependency required - cameras push events directly to your Home Assistant instance.

## Features

✨ **Real-time Event Detection** - Instant notifications for motion, person, vehicle, and line crossing events  
📸 **Automatic Image Capture** - Captures and displays the latest event snapshot from your cameras  
🔔 **Binary Sensor Platform** - Motion detection sensors with configurable auto-reset functionality  
🖼️ **Image Entity Platform** - Displays the most recent event image with metadata (timestamp, file size)  
🌐 **Webhook-based Architecture** - Uses Home Assistant's webhook system for local push notifications  
⚙️ **Easy Configuration** - Simple UI-based setup through Home Assistant's config flow  
🔧 **Customizable Settings** - Configurable auto-reset delay (1-60 seconds) for motion sensors  

## Components

### Binary Sensors
For each camera, a binary sensor is created that:
- Detects motion and other events from your VIGI camera
- Automatically resets to "off" state after a configurable delay (default: 1 second)
- Provides event metadata including event type, timestamp, and detection details
- Entity ID format: `binary_sensor.<camera_name>`

### Image Entities
For each camera, an image entity is created that:
- Displays the latest event snapshot captured by the camera
- Updates automatically when new events occur
- Provides image metadata (last updated time, file size)
- Entity ID format: `image.<camera_name>_last_image`

### Supported Event Types
- **Motion Detection** - General motion events
- **Person Detection** - Human detection events
- **Vehicle Detection** - Vehicle detection events
- **Line Crossing Detection** - Virtual line crossing events

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL: `https://github.com/tanghq33/tplink_vigi`
5. Select category: "Integration"
6. Click "Add"
7. Search for "TP-Link VIGI" in HACS
8. Click "Download"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/tanghq33/tplink_vigi/releases)
2. Extract the `custom_components/tplink_vigi` directory to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

Your directory structure should look like this:
```
config/
├── custom_components/
│   └── tplink_vigi/
│       ├── __init__.py
│       ├── binary_sensor.py
│       ├── config_flow.py
│       ├── const.py
│       ├── image.py
│       ├── manifest.json
│       ├── strings.json
│       └── translations/
│           └── en.json
```

## Configuration

### Adding a Camera

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for "**TP-Link VIGI**"
4. Enter the following information:
   - **Device Name**: A friendly name for your camera (e.g., "Front Door Camera")
   - **Auto-reset delay**: Time in seconds before the motion sensor resets to "off" (1-60 seconds, default: 1)
5. Click **SUBMIT**
6. The integration will display a **webhook URL** - copy this URL

### Configuring Your VIGI Camera

After adding the camera in Home Assistant, you need to configure your VIGI camera to send events to the webhook URL:

1. Log in to your VIGI camera's web interface
2. Navigate to **Settings** → **Event** → **Alarm Server**
3. Add a new webhook:
   - **IP/Domain**: IP or domain of your Home Assistant instance
   - **URL**: `/api/webhook/<webhook_id>`
   - **Protocol**: HTTP/HTTPS
   - **Port**: 8123
   - **Attach image**: Yes
4. Save the settings

#### Webhook URL Format
```
https://your-home-assistant-url/api/webhook/<webhook_id>
```

Example:
```
https://homeassistant.local:8123/api/webhook/front_door_camera
```

> [!IMPORTANT]
> Make sure your VIGI camera can reach your Home Assistant instance over the network. If you're using HTTPS, ensure your SSL certificate is valid or configure your camera to accept self-signed certificates.

### Editing Camera Settings

You can modify camera settings after initial setup:

1. Go to **Settings** → **Devices & Services**
2. Find the **TP-Link VIGI** integration
3. Click **CONFIGURE** on the camera you want to edit
4. Modify the settings:
   - **Auto-reset delay**: Adjust the time before the motion sensor resets
5. Click **SUBMIT**

> [!NOTE]
> The webhook URL cannot be changed after initial setup. If you need a different webhook ID, you'll need to remove and re-add the camera.

## Usage Examples

### Automation: Send Notification on Motion Detection

```yaml
automation:
  - alias: "Front Door Motion Detected"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_camera
        to: "on"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Motion Detected"
          message: "Motion detected at the front door at {{ now().strftime('%H:%M:%S') }}"
          data:
            image: "/api/image_proxy/image.front_door_camera_last_image"
```


## Troubleshooting

### Camera Not Sending Events

1. **Check network connectivity**: Ensure your camera can reach your Home Assistant instance
2. **Verify webhook URL**: Make sure the webhook URL is correctly configured in your camera
3. **Check camera settings**: Ensure event notifications are enabled and properly configured
4. **Review Home Assistant logs**: Check for any error messages in **Settings** → **System** → **Logs**

### Webhook URL Not Working

1. **Check external access**: If your Home Assistant is behind a firewall or NAT, ensure the webhook URL is accessible from your camera
2. **Verify SSL certificate**: If using HTTPS, ensure your SSL certificate is valid
3. **Check webhook ID format**: Webhook IDs must contain only lowercase letters, numbers, and underscores

### Motion Sensor Not Resetting

1. **Check auto-reset delay**: Ensure the auto-reset delay is configured correctly
2. **Review logs**: Check Home Assistant logs for any errors related to the reset timer
3. **Restart integration**: Try reloading the integration from **Settings** → **Devices & Services**

### Images Not Updating

1. **Check camera configuration**: Ensure your camera is configured to send images with event notifications
2. **Verify content type**: The camera should send images as multipart/form-data
3. **Check image size**: Very large images may cause issues - consider reducing image quality in camera settings

## Technical Details

### Webhook Payload

The integration expects webhook payloads in the following format:

**Headers:**
- Content-Type: `multipart/form-data`

**Form Data:**
- `event_type`: Event type (motion, person, vehicle, line_crossing)
- `image`: Image file (optional, but recommended)
- Additional fields from your camera (will be stored in sensor attributes)

### Entity Attributes

**Binary Sensor Attributes:**
- `event_type`: Type of event detected
- `last_triggered`: Timestamp of last event
- `webhook_id`: Webhook ID for this camera
- Additional attributes from webhook payload

**Image Entity Attributes:**
- `image_last_updated`: Timestamp when image was last updated
- `image_size`: Size of the image in bytes

### Device Information

Each camera creates a device in Home Assistant with:
- **Name**: Camera name
- **Manufacturer**: TP-Link

## Supported VIGI Camera Models

This integration should work with any TP-Link VIGI camera that supports webhook notifications, including:

- VIGI C340-W
- VIGI C540-W
- And other VIGI models with webhook support

> [!NOTE]
> If you've successfully tested this integration with a specific VIGI model, please let me know by opening an issue so I can add it to the list!

## Support

- **Issues**: [GitHub Issues](https://github.com/tanghq33/tplink_vigi/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tanghq33/tplink_vigi/discussions)

## License

This project is open source and available under the MIT License.

## Disclaimer

This is a custom integration and is not officially affiliated with or supported by TP-Link. Use at your own risk.

## Credits

Created and maintained by [@tanghq33](https://github.com/tanghq33)

---

**If you find this integration useful, please consider giving it a ⭐ on GitHub!**
