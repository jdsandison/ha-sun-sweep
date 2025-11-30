# sun_sweep.py  -- Revised version (rows + cinematic sunset + severity floors)

import random
import time


# Expects:
#   data.position (0..100)
#   data.severity (0.5..2.0)

pos = float(data.get("position", 0.0))
severity = float(data.get("severity", 1.0))
transition_fast = 6
transition_slow = 20

# --- Entity IDs ----------------------------------------------------------
row1_tw = ["light.slope_spot", "light.music_corner"]
row2_rgb = ["light.towards_slope", "light.foot_stool"]
row3_rgb = ["light.burner", "light.axel"]
row4_tw = ["light.reading_light", "light.music_stand"]
row5_tw = ["light.breakfast_bar"]
row6_atrium_tw = ["light.table_uplight_white", "light.table_downlight_white"]
row6_atrium_rgb = ["light.table_uplight_colour", "light.table_downlight_colour"]

# --- Row Config ----------------------------------------------------------
row_config = {
    "row1_tw": {"center": 30, "width": 20, "max": 85},
    "row2_rgb": {"center": 40, "width": 22, "max": 85},
    "row3_rgb": {"center": 50, "width": 24, "max": 90},
    "row4_tw": {"center": 60, "width": 28, "max": 85},
    "row5_tw": {"center": 70, "width": 30, "max": 95},
    "row6_atrium": {"center": 85, "width": 32, "max": 100},
}

master_config: dict[str, dict[str, dict[str, int] | list[str]]] = {
    "row1_tw": {
        "dim": {"center": 30, "width": 20, "max": 85},
        "entity": ["light.slope_spot", "light.music_corner"],
    },
    "row2_rgb": {
        "dim": {"center": 40, "width": 22, "max": 85},
        "entity": ["light.towards_slope", "light.foot_stool"],
    },
    "row3_rgb": {
        "dim": {"center": 50, "width": 24, "max": 90},
        "entity": ["light.burner", "light.axel"],
    },
    "row4_tw": {
        "dim": {"center": 60, "width": 28, "max": 85},
        "entity": ["light.reading_light", "light.music_stand"],
    },
    "row5_tw": {
        "dim": {"center": 70, "width": 30, "max": 95},
        "entity": ["light.breakfast_bar"],
    },
    "row6_atrium_tw": {
        "dim": {"center": 85, "width": 32, "max": 100},
        "entity": ["light.table_uplight_white", "light.table_downlight_white"],
    },
    "row6_atrium_rgb": {
        "dim": {"center": 85, "width": 32, "max": 100},
        "entity": ["light.table_uplight_colour", "light.table_downlight_colour"],
    },
}

# --- Helpers -------------------------------------------------------------
def clamp(v, a, b):
    return max(a, min(b, v))


def lerp(a, b, t):
    return a + (b - a) * t


def bell(x, c, w, severity):
    # Parabolic bell; severity reduces curvature (higher -> wider/shallower)
    dx = (x - c) / max(0.0001, w)
    return max(0.0, 1.0 - (dx * dx / max(0.0001, severity)))


def tw_kelvin(pos):
    # Sunrise -> Midday -> Sunset mapping with extra orange near end
    if pos < 50:
        t = pos / 50.0
        kelvin = int(lerp(2200, 5500, t))
    else:
        t = (pos - 50) / 50.0
        kelvin = int(lerp(5500, 2200, t))
    if pos > 85:
        t2 = (pos - 85) / 15.0
        kelvin -= int(500 * t2)
    return clamp(kelvin, 1800, 5500)


def atrium_uplight_sunset(pos):
    if pos <= 85:
        return None
    t = (pos - 85) / 15.0
    if t <= 0.5:
        t2 = t / 0.5
        r = int(lerp(255, 255, t2))
        g = int(lerp(140, 80, t2))
        b = int(lerp(40, 50, t2))
    else:
        t2 = (t - 0.5) / 0.5
        r = int(lerp(255, 120, t2))
        g = int(lerp(80, 40, t2))
        b = int(lerp(50, 150, t2))
    return (clamp(r, 0, 255), clamp(g, 0, 255), clamp(b, 0, 255))


def atrium_downlight_sunset(pos):
    if pos <= 85:
        return None
    t = (pos - 85) / 15.0
    if t <= 0.5:
        t2 = t / 0.5
        r = int(lerp(255, 255, t2))
        g = int(lerp(200, 80, t2))
        b = int(lerp(100, 40, t2))
    else:
        t2 = (t - 0.5) / 0.5
        r = int(lerp(255, 200, t2))
        g = int(lerp(80, 20, t2))
        b = int(lerp(40, 150, t2))
    return (clamp(r, 0, 255), clamp(g, 0, 255), clamp(b, 0, 255))


def atrium_default_rgb(pos):
    k = tw_kelvin(pos)
    if k >= 5000:
        return (180, 200, 255)
    elif k >= 3500:
        return (255, 235, 200)
    else:
        return (255, 200, 150)


def safe_rgb(c, fallback=(255, 200, 150)):
    return c if c is not None else fallback


# --- Compute row envelopes -----------------------------------------------
# Expand widths by severity
for k in list(row_config.keys()):
    cfg = row_config[k]
    row_config[k] = {
        "center": cfg["center"],
        "width": cfg["width"] * severity,
        "max": cfg["max"],
    }

# severity floor: severity 1 -> floor 60 (so bulbs remain visibly warm), severity 2 -> floor 5 (practically off)
floor = int(lerp(60, 5, clamp((severity - 1.0) / (2.0 - 1.0), 0.0, 1.0)))

row_pct = {}
for r, cfg in row_config.items():
    computed = int(bell(pos, cfg["center"], cfg["width"], severity) * cfg["max"])
    row_pct[r] = clamp(max(computed, floor), 0, 100)

# --- Apply lights -------------------------------------------------------
# Row 1 & 4 TW
for ent in row1_tw:
    pct = row_pct["row1_tw"]
    hass.services.call(
        "light",
        "turn_on",
        {
            "entity_id": ent,
            "brightness_pct": pct,
            "color_temp_kelvin": tw_kelvin(pos),
            "transition": transition_fast,
        },
    )

for ent in row4_tw:
    pct = row_pct["row4_tw"]
    hass.services.call(
        "light",
        "turn_on",
        {
            "entity_id": ent,
            "brightness_pct": pct,
            "color_temp_kelvin": tw_kelvin(pos),
            "transition": transition_fast,
        },
    )

# Row 5 TW (kitchen)
for ent in row5_tw:
    pct = row_pct["row5_tw"]
    hass.services.call(
        "light",
        "turn_on",
        {
            "entity_id": ent,
            "brightness_pct": pct,
            "color_temp_kelvin": tw_kelvin(pos),
            "transition": transition_fast,
        },
    )

# Atrium TW -- scale whites down during final sunset zone
if pos <= 85:
    tw_factor = 1.0
else:
    tw_factor = max(0.0, 1.0 - ((pos - 85) / 15.0))

for ent in row6_atrium_tw:
    hass.services.call(
        "light",
        "turn_on",
        {
            "entity_id": ent,
            "brightness_pct": int(row_pct["row6_atrium"] * tw_factor),
            "color_temp_kelvin": tw_kelvin(pos),
            "transition": transition_slow,
        },
    )

# Row 2 & 3 RGB (ambient tint based on tunable white)
for ent in row2_rgb:
    hass.services.call(
        "light",
        "turn_on",
        {
            "entity_id": ent,
            "brightness_pct": row_pct["row2_rgb"],
            "rgb_color": atrium_default_rgb(pos),
            "transition": transition_fast,
        },
    )

for ent in row3_rgb:
    hass.services.call(
        "light",
        "turn_on",
        {
            "entity_id": ent,
            "brightness_pct": row_pct["row3_rgb"],
            "rgb_color": atrium_default_rgb(pos),
            "transition": transition_fast,
        },
    )

# Atrium RGB (cinematic sunset)
up_rgb = atrium_uplight_sunset(pos) or atrium_default_rgb(pos)
down_rgb = atrium_downlight_sunset(pos) or atrium_default_rgb(pos)

hass.services.call(
    "light",
    "turn_on",
    {
        "entity_id": row6_atrium_rgb[0],
        "rgb_color": safe_rgb(up_rgb),
        "brightness_pct": row_pct["row6_atrium"],
        "transition": transition_slow,
    },
)

hass.services.call(
    "light",
    "turn_on",
    {
        "entity_id": row6_atrium_rgb[1],
        "rgb_color": safe_rgb(down_rgb),
        "brightness_pct": int(clamp(row_pct["row6_atrium"] * 0.9, 0, 100)),
        "transition": transition_slow,
    },
)


# --- Boo Dinner Lights Sequence ------------------------------------------

# assuming the suffix rgb are the only lights that can produce colours:
valid_entity_group_list = ["row2_rgb", "row3_rgb", "row6_atrium_rgb"]


def colour_selection() -> tuple:
    """Bright colours signalling Boo's dinner time."""
    bright_colour_list: list[tuple] = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (255, 0, 255),
        (0, 255, 255),
        (255, 128, 0),
        (128, 0, 255),
        (255, 20, 147),
        (0, 255, 127),
    ]
    return random.choice(bright_colour_list)


def boo_dinner_lights(valid_entity_group_list: list[str], time_length: int) -> None:
    for _ in range(time_length):
        for loc_key in valid_entity_group_list:
            entity_list = master_config[loc_key]["entity"]
            for ent in entity_list:
                # need to consider asynchronous nature?
                hass.services.call(
                    "light",
                    "turn_on",
                    {
                        "entity_id": ent,
                        "brightness_pct": 100,
                        "rgb_color": colour_selection(),
                        "transition": transition_fast,
                    },
                )
        time.sleep(1)


# --- Debug ---------------------------------------------------------------
debug = (
    f"pos={pos:.1f}, sev={severity:.2f} | "
    f"r1={row_pct['row1_tw']}%, r2={row_pct['row2_rgb']}%, r3={row_pct['row3_rgb']}%, "
    f"r4={row_pct['row4_tw']}%, r5={row_pct['row5_tw']}%, r6={row_pct['row6_atrium']}% | "
    f"kelvin={tw_kelvin(pos):d}"
)
hass.states.set("input_text.sun_debugger", debug)
