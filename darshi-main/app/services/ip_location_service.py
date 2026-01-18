"""
IP Location Service - Get geolocation info from IP addresses

Uses ip-api.com (free, no API key needed, 45 requests/minute limit)
Falls back gracefully if service is unavailable.
"""

import httpx
from typing import Optional, Dict
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ip-api.com is free, no API key needed, 45 requests/minute
IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,lat,lon,timezone,isp,proxy,hosting"


async def get_location_from_ip(ip: str) -> Optional[Dict]:
    """
    Get geolocation info from IP address.
    
    Args:
        ip: IP address (IPv4 or IPv6)
    
    Returns:
        Dict with location info or None if lookup fails:
        {
            "city": str,
            "region": str,
            "country": str,
            "country_code": str,
            "lat": float,
            "lng": float,
            "timezone": str,
            "isp": str,
            "vpn_detected": bool
        }
    """
    # Skip private/local IPs
    if _is_private_ip(ip):
        logger.debug(f"Skipping private IP: {ip}")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(IP_API_URL.format(ip=ip))
            
            if response.status_code != 200:
                logger.warning(f"IP geolocation failed with status {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get("status") != "success":
                logger.warning(f"IP geolocation failed: {data.get('message', 'Unknown error')}")
                return None
            
            # proxy/hosting fields indicate VPN/datacenter
            vpn_detected = data.get("proxy", False) or data.get("hosting", False)
            
            result = {
                "city": data.get("city"),
                "region": data.get("regionName"),
                "country": data.get("country"),
                "country_code": data.get("countryCode"),
                "lat": data.get("lat"),
                "lng": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp"),
                "vpn_detected": vpn_detected
            }
            
            logger.info(f"IP {ip} geolocated to {result['city']}, {result['country']}")
            return result
            
    except httpx.TimeoutException:
        logger.warning(f"IP geolocation timed out for {ip}")
        return None
    except Exception as e:
        logger.error(f"IP geolocation error: {e}")
        return None


def _is_private_ip(ip: str) -> bool:
    """Check if IP is private/local (not routable on internet)."""
    # Handle localhost
    if ip in ("127.0.0.1", "::1", "localhost"):
        return True
    
    # Handle common private ranges
    private_prefixes = (
        "10.",
        "172.16.", "172.17.", "172.18.", "172.19.",
        "172.20.", "172.21.", "172.22.", "172.23.",
        "172.24.", "172.25.", "172.26.", "172.27.",
        "172.28.", "172.29.", "172.30.", "172.31.",
        "192.168.",
        "fc00:", "fd00:",  # IPv6 private
        "fe80:",  # IPv6 link-local
    )
    
    return ip.startswith(private_prefixes)


def get_client_ip(request) -> str:
    """
    Extract real client IP from request, handling proxies.
    
    Checks headers in order:
    1. CF-Connecting-IP (Cloudflare)
    2. X-Real-IP (Nginx)
    3. X-Forwarded-For (first IP)
    4. Direct client connection
    """
    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    
    # Nginx proxy
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Standard proxy header (take first IP)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For: client, proxy1, proxy2
        return forwarded.split(",")[0].strip()
    
    # Direct connection
    if request.client:
        return request.client.host
    
    return "unknown"
