"""Syncthing REST API client for aicontext P2P sync (macOS only)."""

from __future__ import annotations

import json
import logging
import os
import shutil
import ssl
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

SYNCTHING_CONFIG_PATH = os.path.expanduser(
    "~/Library/Application Support/Syncthing/config.xml"
)
SYNCTHING_API = "https://127.0.0.1:8384"

# Syncthing uses a self-signed certificate; skip verification for localhost.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
EXCHANGE_FOLDER_ID = "aicontext-exchange"
EXCHANGE_FOLDER_LABEL = "AIContext Exchange"


# ── Prerequisites ─────────────────────────────────────────────────────────

def check_installed() -> bool:
    """Check if syncthing binary is on PATH."""
    return shutil.which("syncthing") is not None


def check_running() -> bool:
    """Check if Syncthing is running by hitting its health endpoint."""
    try:
        req = urllib.request.Request(f"{SYNCTHING_API}/rest/noauth/health")
        with urllib.request.urlopen(req, timeout=3, context=_SSL_CTX):
            return True
    except Exception:
        return False


def read_api_key() -> str | None:
    """Read the Syncthing API key from its config.xml."""
    if not os.path.exists(SYNCTHING_CONFIG_PATH):
        return None
    try:
        tree = ET.parse(SYNCTHING_CONFIG_PATH)
        elem = tree.find(".//gui/apikey")
        if elem is not None and elem.text:
            return elem.text.strip()
    except Exception:
        pass
    return None


# ── REST helpers ──────────────────────────────────────────────────────────

def _api(method: str, path: str, api_key: str, data=None):
    """Make a Syncthing REST API request. Returns parsed JSON or None."""
    url = f"{SYNCTHING_API}{path}"
    headers = {"X-API-Key": api_key}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw.strip() else None


# ── Device & folder management ────────────────────────────────────────────

def get_device_id(api_key: str) -> str:
    """Get this device's Syncthing device ID."""
    status = _api("GET", "/rest/system/status", api_key)
    return status["myID"]


def add_device(api_key: str, peer_id: str, introducer: bool = True) -> None:
    """Add a peer device to Syncthing config.

    With introducer=True, Syncthing auto-shares devices across the group,
    so adding a 3rd device only requires pairing with one existing device.
    """
    _api("PUT", f"/rest/config/devices/{peer_id}", api_key, {
        "deviceID": peer_id,
        "addresses": ["dynamic"],
        "introducer": introducer,
    })


def ensure_folder(api_key: str, exchange_dir: str) -> dict:
    """Ensure the exchange folder exists in Syncthing. Returns folder config."""
    try:
        return _api("GET", f"/rest/config/folders/{EXCHANGE_FOLDER_ID}", api_key)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    # Folder doesn't exist — create it
    my_id = get_device_id(api_key)
    folder = {
        "id": EXCHANGE_FOLDER_ID,
        "label": EXCHANGE_FOLDER_LABEL,
        "path": exchange_dir,
        "type": "sendreceive",
        "devices": [{"deviceID": my_id}],
        "rescanIntervalS": 60,
        "fsWatcherEnabled": True,
    }
    _api("PUT", f"/rest/config/folders/{EXCHANGE_FOLDER_ID}", api_key, folder)
    return folder


def share_folder_with(api_key: str, exchange_dir: str, peer_id: str) -> None:
    """Add a peer to the shared exchange folder."""
    folder = ensure_folder(api_key, exchange_dir)
    shared_ids = {d["deviceID"] for d in folder.get("devices", [])}
    if peer_id in shared_ids:
        return
    folder["devices"].append({"deviceID": peer_id})
    _api("PUT", f"/rest/config/folders/{EXCHANGE_FOLDER_ID}", api_key, folder)


def remove_folder(api_key: str) -> None:
    """Remove the exchange folder from Syncthing config (for uninstall)."""
    try:
        _api("DELETE", f"/rest/config/folders/{EXCHANGE_FOLDER_ID}", api_key)
    except urllib.error.HTTPError:
        pass


# ── Sync mode (LAN vs web) ───────────────────────────────────────────────

def set_sync_mode(api_key: str, web: bool) -> None:
    """Configure Syncthing for LAN-only or web (internet) sync.

    LAN-only (default): disables global discovery and relay servers.
    Web: enables global discovery and relay servers for internet sync.
    """
    options = _api("GET", "/rest/config/options", api_key)
    options["globalAnnounceEnabled"] = web
    options["relaysEnabled"] = web
    options["localAnnounceEnabled"] = True
    _api("PUT", "/rest/config/options", api_key, options)


def get_sync_mode(api_key: str) -> str:
    """Return 'web' if global announce or relays are enabled, else 'lan'."""
    options = _api("GET", "/rest/config/options", api_key)
    if options.get("globalAnnounceEnabled") or options.get("relaysEnabled"):
        return "web"
    return "lan"


# ── Status ────────────────────────────────────────────────────────────────

def get_status(api_key: str) -> dict:
    """Get sync status: paired devices and connection state.

    Returns dict with keys:
        my_id: str
        devices: list of {id, name, connected, address, last_seen}
    """
    my_id = get_device_id(api_key)
    connections = _api("GET", "/rest/system/connections", api_key) or {}
    conn_map = connections.get("connections", {})

    # Get folder config to find which devices share the exchange folder
    try:
        folder = _api("GET", f"/rest/config/folders/{EXCHANGE_FOLDER_ID}", api_key)
    except urllib.error.HTTPError:
        return {"my_id": my_id, "devices": []}

    shared_ids = {d["deviceID"] for d in folder.get("devices", [])} - {my_id}

    # Get device configs for names
    all_devices = _api("GET", "/rest/config/devices", api_key) or []
    name_map = {d["deviceID"]: d.get("name", "") for d in all_devices}

    devices = []
    for did in sorted(shared_ids):
        conn = conn_map.get(did, {})
        devices.append({
            "id": did,
            "name": name_map.get(did, ""),
            "connected": conn.get("connected", False),
            "address": conn.get("address", ""),
            "last_seen": conn.get("lastHandshakeNs", 0),
        })

    return {"my_id": my_id, "devices": devices}
