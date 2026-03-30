DOMAIN = "minjet"

API_BASE = "https://app.minjet-energy.com/prod-api"
LOGIN_ENDPOINT = f"{API_BASE}/login"
DEVICE_LIST_ENDPOINT = f"{API_BASE}/device/queryUserDeviceList"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ENABLE_WEBSOCKET = "enable_websocket"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 10
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300
DEFAULT_ENABLE_WEBSOCKET = False
