"""Alert categories and constants for municipality broadcasting system"""

# Alert Categories with emojis
ALERT_CATEGORIES = {
    # Traffic & Transport
    "traffic_jam": "🚗 Traffic Jam",
    "road_closure": "🚧 Road Closure",
    "accident": "💥 Accident",
    "diversion": "↪️ Traffic Diversion",
    
    # Utilities
    "power_outage": "⚡ Power Outage",
    "water_supply": "💧 Water Supply",
    "gas_supply": "🔥 Gas Supply",
    
    # Safety & Emergency
    "safety_alert": "🚨 Safety Alert",
    "weather_warning": "🌧️ Weather Warning",
    "fire": "🔥 Fire",
    "flood": "🌊 Flood",
    
    # Events
    "festival": "🎉 Festival",
    "market": "🛒 Market/Fair",
    "sports": "⚽ Sports Event",
    "cultural": "🎭 Cultural Event",
    
    # Public Services
    "school": "🏫 School Notice",
    "hospital": "🏥 Hospital Update",
    "office_closure": "🏛️ Office Closure",
    "vaccination": "💉 Health Camp",
    "maintenance": "🔧 Maintenance Work",
    
    # General
    "announcement": "📢 Announcement",
    "community": "👥 Community Update"
}

# Severity levels
ALERT_SEVERITY = {
    "low": {"color": "#28a745", "priority": 1},
    "medium": {"color": "#ffc107", "priority": 2},
    "high": {"color": "#fd7e14", "priority": 3},
    "critical": {"color": "#dc3545", "priority": 4}
}

# Default expiry times (in hours)
DEFAULT_EXPIRY_HOURS = 24
MAX_EXPIRY_HOURS = 168  # 7 days
MIN_EXPIRY_HOURS = 1

# Geofencing - HYPER-LOCAL ONLY
DEFAULT_RADIUS_KM = 5
MAX_RADIUS_KM = 30  # Alerts are city-specific, not regional
MIN_RADIUS_KM = 1
