# Minjet MH7A-48 Home Assistant Integration

Custom Home Assistant integration for Minjet MH7A-48 energy storage systems.

This integration supports:
- Credential login via Minjet cloud API
- Regular REST polling (configurable interval)
- Optional WebSocket updates for near real-time values
- Derived power and energy sensors
- Connection/debug sensors for diagnostics

## Disclaimer

This project is an unofficial community integration and is not affiliated with Minjet.

## Installation

### HACS (Custom repository)

1. Open HACS in Home Assistant.
2. Select the 3-dot menu in the top-right corner.
3. Open `Custom repositories`.
4. Add this repository URL.
5. Select repository type `Integration`.
6. Install `Minjet MH7A-48 Energy Storage`.
7. Restart Home Assistant.

### Manual installation

1. Copy the integration files to:
   `config/custom_components/minjet/`
2. Restart Home Assistant.
3. Add the integration from:
   `Settings -> Devices & Services -> Add Integration`

## Configuration

Configuration is handled via UI (`config_flow`).

Required:
- `username`
- `password`

Optional:
- `enable_websocket` (default: `false`)
- `scan_interval` in seconds (default: `10`, min: `5`, max: `300`)

## Sensors

### Raw sensors
- PV Total Power
- Output Power
- Battery Power Raw
- Battery Percentage
- Temperature 1
- Temperature 2
- Cell Voltage Max
- Cell Voltage Min
- WiFi RSSI
- EM Feedback Value
- Battery Status
- Grid Import Power
- Grid Export Power

### Derived power sensors
- Battery Charge Power
- Battery Discharge Power
- PV to Inverter Power
- Battery to Inverter Power
- PV to Battery Power
- Cell Voltage Delta

### Derived energy sensors
- Solar Energy
- Battery Charge Energy
- Battery Discharge Energy

### Debug sensors
- Connection Mode
- WebSocket Connected
- Device Offline
- Offline Minutes

## Data behavior

- REST data is used as base data.
- If WebSocket is enabled and connected, incoming values are merged into REST data.
- If WebSocket disconnects, the integration falls back to REST-only updates.

## Troubleshooting

Add debug logging in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.minjet: debug
```

Common checks:
- Verify username/password in integration configuration
- Disable WebSocket temporarily if your network blocks WSS traffic
- Increase scan interval if you run into rate-limit/network issues

## Support and issues

- Documentation: https://github.com/snoova/minjet-ha
- Issue tracker: https://github.com/snoova/minjet-ha/issues
