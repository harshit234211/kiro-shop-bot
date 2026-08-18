import random
from typing import Dict, Any, Tuple
import database as db
from logger import logger

def generate_ff_sensitivity(telegram_id: int, order_id: str, brand: str, model: str, variant: str = "Standard") -> Tuple[Dict[str, Any], str]:
    """
    Generates a unique random Free Fire sensitivity setup with 1-200 ranges.
    Saves the delivery record to the database and returns the data dict + formatted markdown string.
    """
    general = random.randint(1, 200)
    red_dot = random.randint(1, 200)
    scope_2x = random.randint(1, 200)
    scope_4x = random.randint(1, 200)
    sniper = random.randint(1, 200)
    free_look = random.randint(1, 200)
    fire_button = random.randint(35, 65)
    dpi = random.randint(360, 800)
    pointer_speed = random.randint(1, 10)

    # Save to database
    db.save_sensi_delivery(
        telegram_id=telegram_id,
        order_id=order_id,
        brand=brand,
        model=model,
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
        "brand": brand,
        "model": model,
        "variant": variant,
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
        f"🎯 *Kiro Sensi Delivered*\n\n"
        f"📱 *Phone:* `{model}`\n\n"
        f"⚡ *General:* `{general}` (1-200)\n"
        f"🔴 *Red Dot:* `{red_dot}` (1-200)\n"
        f"🎯 *2x Scope:* `{scope_2x}` (1-200)\n"
        f"🔭 *4x Scope:* `{scope_4x}` (1-200)\n"
        f"🎯 *Sniper Scope:* `{sniper}` (1-200)\n"
        f"👀 *Free Look:* `{free_look}` (1-200)\n\n"
        f"🔥 *Fire Button Size:* `{fire_button}%`\n"
        f"📏 *Recommended DPI:* `{dpi}`\n"
        f"⚡ *Pointer Speed:* `{pointer_speed}/10`\n\n"
        f"🎮 *Play 3-5 matches for best headshot results!*"
    )

    logger.info(f"Generated FF Sensitivity (1-200 range) for Order {order_id} ({model})")
    return data, formatted_msg

def generate_sensi_profile(order_id: str, telegram_id: int, brand: str, model: str, variant: str = "Standard") -> Dict[str, Any]:
    """Alias wrapper returning sensitivity data dictionary."""
    data, _ = generate_ff_sensitivity(telegram_id=telegram_id, order_id=order_id, brand=brand, model=model, variant=variant)
    return data
