import random
import uuid
from typing import Dict, Any, Tuple
import database as db
from logger import logger

# Configuration dictionary (can be updated via admin commands or config file)
SENSI_CONFIG = {
    "ranges": {
        "general": (150, 200),
        "red_dot": (140, 200),
        "scope_2x": (130, 195),
        "scope_4x": (110, 190),
        "sniper": (70, 150),
        "free_look": (100, 200),
        "dpi": (320, 600),
        "fire_button": (35, 60),
        "pointer_speed": (50, 100)
    },
    "profile_types": [
        "🎯 Balanced",
        "🔥 Headshot",
        "⚡ Fast Drag",
        "🎮 Smooth",
        "🎯 Precision",
        "🚀 Aggressive",
        "🧊 Stable"
    ],
    "brand_multipliers": {
        "Apple": {"sensi_bias": 1.0, "dpi_max": 480},
        "Samsung": {"sensi_bias": 1.02, "dpi_max": 520},
        "Vivo": {"sensi_bias": 1.05, "dpi_max": 580},
        "Xiaomi": {"sensi_bias": 1.04, "dpi_max": 560},
        "Redmi": {"sensi_bias": 1.04, "dpi_max": 560},
        "POCO": {"sensi_bias": 1.05, "dpi_max": 580},
        "Realme": {"sensi_bias": 1.03, "dpi_max": 550},
        "OPPO": {"sensi_bias": 1.02, "dpi_max": 540},
        "OnePlus": {"sensi_bias": 1.04, "dpi_max": 570},
        "Infinix": {"sensi_bias": 1.0, "dpi_max": 500},
        "Tecno": {"sensi_bias": 1.0, "dpi_max": 500},
        "Lava": {"sensi_bias": 1.0, "dpi_max": 500},
        "Google Pixel": {"sensi_bias": 0.98, "dpi_max": 480},
        "Asus": {"sensi_bias": 1.06, "dpi_max": 600},
        "Nothing": {"sensi_bias": 1.02, "dpi_max": 520},
        "Honor": {"sensi_bias": 1.01, "dpi_max": 510},
        "Huawei": {"sensi_bias": 1.01, "dpi_max": 510},
        "Lenovo": {"sensi_bias": 1.01, "dpi_max": 510},
        "Motorola": {"sensi_bias": 1.0, "dpi_max": 500},
        "Nokia": {"sensi_bias": 0.99, "dpi_max": 480},
        "iQOO": {"sensi_bias": 1.05, "dpi_max": 580}
    }
}

def generate_ff_sensitivity(telegram_id: int, order_id: str, brand: str, model: str = None, variant: str = "Standard") -> Tuple[Dict[str, Any], str]:
    """
    Generates a smart, balanced Free Fire sensitivity profile using device categories and weighted algorithms.
    """
    brand_key = brand.replace("📱 ", "").strip()
    device_name = model if model and model != "Standard" else brand_key
    
    # Get config ranges & multipliers
    ranges = SENSI_CONFIG["ranges"]
    mult = SENSI_CONFIG["brand_multipliers"].get(brand_key, {"sensi_bias": 1.0, "dpi_max": 550})
    bias = mult["sensi_bias"]
    
    profile_type = random.choice(SENSI_CONFIG["profile_types"])
    profile_id = f"KI-{brand_key[:4].upper()}-{uuid.uuid4().hex[:5].upper()}"

    # Smart DPI calculation (High DPI -> Slightly lower sensitivity)
    dpi = random.randint(ranges["dpi"][0], min(ranges["dpi"][1], mult["dpi_max"]))
    dpi_factor = 1.0 - ((dpi - ranges["dpi"][0]) / (ranges["dpi"][1] - ranges["dpi"][0])) * 0.08

    # Weighted Base General Sensitivity
    gen_min, gen_max = ranges["general"]
    base_gen = random.randint(gen_min, gen_max) * bias * dpi_factor
    general = max(1, min(200, int(base_gen)))

    # Weighted Red Dot, Scopes based on General
    red_min, red_max = ranges["red_dot"]
    red_dot = max(1, min(200, int(general * random.uniform(0.92, 1.0))))

    scope2_min, scope2_max = ranges["scope_2x"]
    scope_2x = max(1, min(200, int(red_dot * random.uniform(0.88, 0.96))))

    scope4_min, scope4_max = ranges["scope_4x"]
    scope_4x = max(1, min(200, int(scope_2x * random.uniform(0.85, 0.94))))

    snip_min, snip_max = ranges["sniper"]
    sniper = max(1, min(200, int(random.randint(snip_min, snip_max) * random.uniform(0.8, 1.0))))

    fl_min, fl_max = ranges["free_look"]
    free_look = max(1, min(200, random.randint(fl_min, fl_max)))

    fire_button = random.randint(ranges["fire_button"][0], ranges["fire_button"][1])
    pointer_speed = random.randint(ranges["pointer_speed"][0], ranges["pointer_speed"][1])

    # Save delivery to database
    db.save_sensi_delivery(
        telegram_id=telegram_id,
        order_id=order_id,
        brand=brand_key,
        model=device_name,
        variant=variant,
        general=general,
        red_dot=red_dot,
        scope_2x=scope_2x,
        scope_4x=scope_4x,
        sniper=sniper,
        free_look=free_look,
        fire_button=fire_button,
        dpi=dpi,
        pointer_speed=pointer_speed
    )

    data = {
        "order_id": order_id,
        "profile_id": profile_id,
        "brand": brand_key,
        "model": device_name,
        "profile_type": profile_type,
        "general": general,
        "red_dot": red_dot,
        "scope_2x": scope_2x,
        "scope_4x": scope_4x,
        "sniper": sniper,
        "free_look": free_look,
        "fire_button": fire_button,
        "dpi": dpi,
        "pointer_speed": pointer_speed
    }

    formatted_msg = (
        f"🎯 *Kiro Sensi Generated*\n\n"
        f"📱 *Device:* `{device_name}`\n\n"
        f"⚡ *Sensitivity*\n"
        f"• General: `{general}`\n"
        f"• Red Dot: `{red_dot}`\n"
        f"• 2X Scope: `{scope_2x}`\n"
        f"• 4X Scope: `{scope_4x}`\n"
        f"• Sniper Scope: `{sniper}`\n"
        f"• Free Look: `{free_look}`\n\n"
        f"📐 *Device Settings*\n"
        f"• DPI: `{dpi}`\n"
        f"• Fire Button: `{fire_button}%`\n"
        f"• Pointer Speed: `{pointer_speed}%`\n\n"
        f"🔥 *Profile Type:* {profile_type}\n"
        f"🎲 *Profile ID:* `{profile_id}`\n\n"
        f"⚠️ *Note:* Settings are randomized recommendations. Actual performance depends on device, touch response, FPS, and personal control."
    )

    logger.info(f"Generated Smart FF Sensitivity Profile [{profile_id}] for {device_name}")
    return data, formatted_msg

def generate_sensi_profile(order_id: str, telegram_id: int, brand: str, model: str = None, variant: str = "Standard") -> Dict[str, Any]:
    """Alias wrapper returning sensitivity data dictionary."""
    data, _ = generate_ff_sensitivity(telegram_id=telegram_id, order_id=order_id, brand=brand, model=model, variant=variant)
    return data
