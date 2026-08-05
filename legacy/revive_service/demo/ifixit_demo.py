"""Streamlit demo for live iFixit repair documentation lookup."""

import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import streamlit as st

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from revive_service.repair_documentation import get_repair_documentation

CUSTOM_DEVICE = "Other / custom model"
CUSTOM_BRAND = "Other / custom brand"
DEVICES_BY_BRAND = {
    "Apple": (
        "iPhone 12",
        "iPhone 17 Pro Max",
        "iPad 9",
        "iPad Pro 11-inch",
        "MacBook Air 2020",
    ),
    "Samsung": (
        "Samsung Galaxy S22",
        "Samsung Galaxy S24 Ultra",
        "Samsung Galaxy Z Fold 5",
    ),
    "Google": (
        "Google Pixel 7",
        "Google Pixel 9 Pro",
    ),
    "OnePlus": ("OnePlus 12",),
    "Dell": ("Dell XPS 13",),
    "Microsoft": ("Microsoft Surface Pro 8",),
    "Nintendo": ("Nintendo Switch",),
    "Valve": ("Steam Deck",),
}

CUSTOM_ISSUE = "Other / custom issue"
DEMO_ISSUES = (
    "cracked screen",
    "battery issue",
    "charging issue",
    "camera issue",
    "back glass",
    "speaker issue",
    "microphone issue",
    "power issue",
    "water damage",
    "keyboard issue",
    "trackpad issue",
    "fan issue",
    "overheating issue",
    "storage issue",
    "joystick drift",
    "button issue",
    CUSTOM_ISSUE,
)


def _escape_markdown(value: str) -> str:
    """Escape text used inside a Markdown link label."""
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _valid_http_url(value: Any) -> str | None:
    """Return a safe HTTP(S) URL, if one was supplied."""
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    return None


def _format_item(item: Any) -> str:
    """Format one iFixit tool or part as readable Markdown."""
    if isinstance(item, dict):
        name = item.get("text") or item.get("name") or item.get("title")
        name = str(name).strip() if name else "Unnamed item"
        quantity = item.get("quantity")
        optional = item.get("isoptional") is True
        url = _valid_http_url(item.get("url"))
    elif isinstance(item, str):
        name = item.strip() or "Unnamed item"
        quantity = None
        optional = False
        url = None
    else:
        name = "Unnamed item"
        quantity = None
        optional = False
        url = None

    label = _escape_markdown(name)
    if url:
        label = f"[{label}]({url})"
    if isinstance(quantity, (int, float)) and not isinstance(quantity, bool):
        if quantity > 1:
            label += f" × {quantity:g}"
    if optional:
        label += " (optional)"
    return label


def _render_items(
    label: str,
    items: list[Any],
    *,
    expanded: bool,
) -> None:
    """Render a capped tool or part list in an expandable section."""
    with st.expander(f"{label} required ({len(items)})", expanded=expanded):
        if not items:
            st.caption(f"No {label.lower()} listed by iFixit.")
            return

        for item in items[:10]:
            st.markdown(f"- {_format_item(item)}")

        remaining = len(items) - 10
        if remaining > 0:
            noun = "item" if remaining == 1 else "items"
            st.caption(f"And {remaining} more {noun}.")


def _render_guide(
    guide: dict[str, Any],
    *,
    expand_items: bool,
) -> None:
    """Render one normalized repair guide."""
    exact = guide["exact_device_match"]
    status = "Exact model match" if exact else "Related model"
    st.subheader(guide["title"])
    st.markdown(f"**{status}**")

    image = guide.get("image")
    if image:
        st.image(image, caption=guide["title"], width=420)
    else:
        st.caption("No guide image is available.")

    difficulty, repair_time = st.columns(2)
    difficulty.metric("Difficulty", guide.get("difficulty") or "Not listed")
    repair_time.metric(
        "Repair time",
        guide.get("time_required") or "Not listed",
    )

    tools, parts = st.columns(2)
    with tools:
        _render_items(
            "Tools",
            guide.get("tools", []),
            expanded=expand_items,
        )
    with parts:
        _render_items(
            "Parts",
            guide.get("parts", []),
            expanded=expand_items,
        )

    if guide.get("url"):
        st.link_button("Open guide on iFixit", guide["url"])
    st.divider()


def main() -> None:
    """Render and run the iFixit demonstration page."""
    st.set_page_config(
        page_title="Revive or Recycle — iFixit Demo",
        page_icon="🛠️",
        layout="wide",
    )
    st.title("Revive or Recycle: Repair Documentation")
    st.markdown(
        "Find live repair guides from the public iFixit API. "
        "No iFixit API key is required."
    )

    brand_column, device_column = st.columns(2)
    with brand_column:
        selected_brand = st.selectbox(
            "Brand",
            (*DEVICES_BY_BRAND, CUSTOM_BRAND),
        )

    with device_column:
        if selected_brand == CUSTOM_BRAND:
            device = st.text_input(
                "Device model",
                placeholder="For example: Sony WH-1000XM4",
            )
        else:
            selected_device = st.selectbox(
                "Device",
                (*DEVICES_BY_BRAND[selected_brand], CUSTOM_DEVICE),
            )
            if selected_device == CUSTOM_DEVICE:
                device = st.text_input(
                    "Device model",
                    placeholder="For example: iphone 17pm",
                )
            else:
                device = selected_device

    selected_issue = st.selectbox("Issue", DEMO_ISSUES)
    if selected_issue == CUSTOM_ISSUE:
        issue = st.text_input(
            "Repair issue",
            placeholder="For example: headphone jack issue",
        )
    else:
        issue = selected_issue
    include_related = st.checkbox(
        "Include related device variants",
        value=False,
    )
    submitted = st.button("Find repair guides", type="primary")

    if not submitted:
        st.info("Enter a device and issue, then select “Find repair guides.”")
        return

    if not device.strip() or not issue.strip():
        st.error("Device and issue are both required.")
        return

    with st.spinner("Searching iFixit…"):
        result = get_repair_documentation(
            device=device,
            issue=issue,
            include_related_variants=include_related,
        )

    if device != result["device"]:
        st.caption(f"Entered device: {device}")
        st.caption(f"Normalized device: {result['device']}")
        st.caption(f"Normalized issue: {result['issue']}")
    else:
        st.caption(
            f"Normalized query: {result['device']} · {result['issue']}"
        )
    if result["used_related_variant_fallback"]:
        st.warning(
            "No exact-model guide was found; showing related-model results."
        )

    for error in result["errors"]:
        st.warning(error)

    if not result["matched"]:
        st.error("No matching repair guides were found.")
        return

    st.success(f"Found {len(result['guides'])} matching guide(s).")
    for index, guide in enumerate(result["guides"]):
        _render_guide(guide, expand_items=index == 0)

    st.caption("Repair documentation source: iFixit API v2.0")


if __name__ == "__main__":
    main()
