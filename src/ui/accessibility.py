"""Small accessibility checks for the custom Streamlit colour palette."""
from __future__ import annotations


THEME_PAIRS = {
    "light_text": ("#172033", "#ffffff"),
    "light_muted": ("#536174", "#ffffff"),
    "light_info": ("#172033", "#e8f3ff"),
    "light_warning": ("#172033", "#fff6db"),
    "light_danger": ("#172033", "#ffe9ec"),
    "light_success": ("#172033", "#e7f6ed"),
    "light_status_pass": ("#176b35", "#ffffff"),
    "light_status_fail": ("#b42318", "#ffffff"),
    "light_status_warn": ("#765500", "#ffffff"),
    "dark_text": ("#edf3fb", "#202b3d"),
    "dark_muted": ("#bdc9d8", "#202b3d"),
    "dark_info": ("#edf3fb", "#153653"),
    "dark_warning": ("#edf3fb", "#4a3c13"),
    "dark_danger": ("#edf3fb", "#4a2028"),
    "dark_success": ("#edf3fb", "#153d2b"),
    "dark_status_pass": ("#7ee2a8", "#202b3d"),
    "dark_status_fail": ("#ff9b9b", "#202b3d"),
    "dark_status_warn": ("#ffd166", "#202b3d"),
}


def _rgb(hex_colour: str) -> tuple[float, float, float]:
    value = hex_colour.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected six-digit hex colour, got {hex_colour}")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def relative_luminance(hex_colour: str) -> float:
    channels = []
    for channel in _rgb(hex_colour):
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def palette_contrast_report() -> dict[str, float]:
    return {
        name: round(contrast_ratio(foreground, background), 2)
        for name, (foreground, background) in THEME_PAIRS.items()
    }
