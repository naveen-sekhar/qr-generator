#!/usr/bin/env python3
"""
Generate a QR code from a URL.

Usage:
  python generate_qr.py "https://example.com" -o mycode.png
  python generate_qr.py
    (then follow the prompt)

Requires:
  pip install qrcode[pil]
"""

import argparse
import os
import sys
from datetime import datetime
from urllib.parse import urlparse

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
except ImportError:
    print("The 'qrcode' package is required. Install it with:\n  pip install qrcode[pil]")
    sys.exit(1)


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    return url


def is_likely_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def sanitize_filename(text: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in text)


def ensure_png_extension(path: str) -> str:
    root, ext = os.path.splitext(path)
    return path if ext.lower() == ".png" else root + ".png"


def _make_styled_image(qr, fill_color: str, back_color: str, style: str):
    """Try to build a styled PIL image; fall back to plain if not available."""
    try:
        from qrcode.image.styledpil import StyledPilImage
        from qrcode.image.styles.moduledrawers import (
            SquareModuleDrawer,
            GappedSquareModuleDrawer,
            CircleModuleDrawer,
            RoundedModuleDrawer,
            VerticalBarsDrawer,
            HorizontalBarsDrawer,
        )
        drawer_map = {
            "square": SquareModuleDrawer,
            "gapped": GappedSquareModuleDrawer,
            "circle": CircleModuleDrawer,
            "rounded": RoundedModuleDrawer,
            "vbars": VerticalBarsDrawer,
            "hbars": HorizontalBarsDrawer,
        }
        drawer_cls = drawer_map.get(style, SquareModuleDrawer)
        return qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=drawer_cls(),
            fill_color=fill_color,
            back_color=back_color,
        )
    except Exception:
        # Fallback to default rendering
        return qr.make_image(fill_color=fill_color, back_color=back_color)


def _paste_logo_center(pil_img, logo_path: str, logo_pct: int = 20):
    """Paste a logo at the center of the QR image. logo_pct is 5-40 (percent of width)."""
    try:
        if not logo_path or not os.path.isfile(logo_path):
            return pil_img
        try:
            from PIL import Image
        except Exception:
            return pil_img
        logo = Image.open(logo_path).convert("RGBA")
        qr_w, qr_h = pil_img.size
        pct = max(5, min(int(logo_pct or 20), 40)) / 100.0
        target_w = max(1, int(qr_w * pct))
        target_h = max(1, int(logo.height * (target_w / logo.width)))
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        pos = ((qr_w - target_w) // 2, (qr_h - target_h) // 2)
        pil_img.paste(logo, pos, mask=logo)
        return pil_img
    except Exception:
        return pil_img


def generate_qr(
    url: str,
    output_path: str,
    box_size: int = 10,
    border: int = 4,
    *,
    fill_color: str = "black",
    back_color: str = "white",
    style: str = "square",
    logo_path: str | None = None,
    logo_size: int = 20,
) -> str:
    qr = qrcode.QRCode(
        version=None,  # auto-fit
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Try styled image first (for non-default styles), otherwise plain.
    if style and style != "square":
        img = _make_styled_image(qr, fill_color=fill_color, back_color=back_color, style=style)
    else:
        img = qr.make_image(fill_color=fill_color, back_color=back_color)

    # Ensure we have a PIL.Image object
    pil_img = img.get_image() if hasattr(img, "get_image") else img

    # Optional logo overlay
    if logo_path:
        pil_img = _paste_logo_center(pil_img, logo_path, logo_pct=logo_size)

    pil_img.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate a QR code PNG from a URL.")
    parser.add_argument("url", nargs="?", help="URL to encode (e.g., https://example.com)")
    parser.add_argument("-o", "--output", help="Output PNG file path (default auto-generated)")
    parser.add_argument("--box-size", type=int, default=10, help="Size of each QR box (default: 10)")
    parser.add_argument("--border", type=int, default=4, help="Border size in boxes (default: 4)")
    # New styling options
    parser.add_argument("--fg", default="black", help="Foreground (module) color, e.g. black or #000000")
    parser.add_argument("--bg", default="white", help="Background color, e.g. white or #FFFFFF")
    parser.add_argument(
        "--style",
        choices=["square", "circle", "rounded", "gapped", "vbars", "hbars"],
        default="square",
        help="Module style (default: square)",
    )
    parser.add_argument("--logo", help="Path to a center logo image (PNG with transparency recommended)")
    parser.add_argument("--logo-size", type=int, default=20, help="Logo size as % of QR width (5-40, default: 20)")
    args = parser.parse_args()

    url = args.url
    if not url:
        url = input("Enter URL to encode: ").strip()

    url = normalize_url(url)
    if not is_likely_valid_url(url):
        print("Error: Please provide a valid URL (e.g., https://example.com).")
        sys.exit(1)

    if args.output:
        output_path = ensure_png_extension(args.output.strip())
    else:
        host = urlparse(url).netloc or "qr"
        safe_host = sanitize_filename(host)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"qr_{safe_host}_{ts}.png"

    try:
        saved = generate_qr(
            url,
            output_path,
            box_size=args.box_size,
            border=args.border,
            fill_color=args.fg,
            back_color=args.bg,
            style=args.style,
            logo_path=args.logo,
            logo_size=args.logo_size,
        )
        print(f"QR code generated and saved to: {os.path.abspath(saved)}")
    except Exception as e:
        print(f"Failed to generate QR code: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()