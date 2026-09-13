"""
Live proof-of-offline-operation endpoint: inspects this machine's
established network connections and reports how many point to a
local/private address (loopback, LAN, RFC1918) versus a public one, so the
frontend can show real evidence that the workbench isn't talking to the
internet at runtime.

Note: this reflects every established connection on the whole machine, not
just this process — other running apps (a browser, cloud sync, OS
telemetry) will show up too. That's intentional for a demo whose claim is
"this laptop is offline," but it means you should close other
internet-connected apps before judges watch this panel.
"""

import ipaddress
import logging

import psutil
from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["monitor"])


def _is_local_address(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_loopback or addr.is_private or addr.is_link_local


@router.get("/monitor")
async def monitor_status():
    """
    Returns {"external_connections": int, "local_connections": int,
    "status": "clean"|"alert"} based on currently ESTABLISHED connections.
    """
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError) as exc:
        logger.warning("Cannot read system network connections: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot read network connections on this OS without elevated permissions.",
        ) from exc

    local_count = 0
    external_count = 0

    for conn in connections:
        if conn.status != psutil.CONN_ESTABLISHED or not conn.raddr:
            continue
        if _is_local_address(conn.raddr.ip):
            local_count += 1
        else:
            external_count += 1

    return {
        "external_connections": external_count,
        "local_connections": local_count,
        "status": "clean" if external_count == 0 else "alert",
    }
