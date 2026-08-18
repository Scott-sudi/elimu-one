"""Génère les icônes Flutter à partir du dossier ELIMU (logo officiel)."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

APP = Path(__file__).resolve().parents[1]
SCHOOL_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = Path(__file__).resolve().parents[4]
_candidates = [
    REPO_ROOT / "ELIMU",
    SCHOOL_ROOT / "images" / "mes_icons",
]
SRC_DIR = next(
    (p for p in _candidates if (p / "android-chrome-512x512.png").exists()),
    SCHOOL_ROOT / "images" / "mes_icons",
)



def save_resized(img: Image.Image, size: int, dest: Path) -> None:
    out = img.resize((size, size), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, "PNG")
    print(f"OK {dest.relative_to(APP)}")


def main() -> None:
    src512 = Image.open(SRC_DIR / "android-chrome-512x512.png").convert("RGBA")
    src192 = Image.open(SRC_DIR / "android-chrome-192x192.png").convert("RGBA")
    apple = Image.open(SRC_DIR / "apple-touch-icon.png").convert("RGBA")

    web = APP / "web"
    (web / "icons").mkdir(exist_ok=True)
    src192.save(web / "icons" / "Icon-192.png")
    src512.save(web / "icons" / "Icon-512.png")
    src192.save(web / "icons" / "Icon-maskable-192.png")
    src512.save(web / "icons" / "Icon-maskable-512.png")
    Image.open(SRC_DIR / "favicon-32x32.png").convert("RGBA").save(web / "favicon.png")
    shutil.copy2(SRC_DIR / "favicon.ico", web / "favicon.ico")
    apple.save(web / "icons" / "apple-touch-icon.png")
    print("web icons done")

    android_sizes = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    res = APP / "android" / "app" / "src" / "main" / "res"
    for folder, size in android_sizes.items():
        save_resized(src512, size, res / folder / "ic_launcher.png")

    ios_icon_dir = APP / "ios" / "Runner" / "Assets.xcassets" / "AppIcon.appiconset"
    ios_sizes = {
        "Icon-App-20x20@1x.png": 20,
        "Icon-App-20x20@2x.png": 40,
        "Icon-App-20x20@3x.png": 60,
        "Icon-App-29x29@1x.png": 29,
        "Icon-App-29x29@2x.png": 58,
        "Icon-App-29x29@3x.png": 87,
        "Icon-App-40x40@1x.png": 40,
        "Icon-App-40x40@2x.png": 80,
        "Icon-App-40x40@3x.png": 120,
        "Icon-App-60x60@2x.png": 120,
        "Icon-App-60x60@3x.png": 180,
        "Icon-App-76x76@1x.png": 76,
        "Icon-App-76x76@2x.png": 152,
        "Icon-App-83.5x83.5@2x.png": 167,
        "Icon-App-1024x1024@1x.png": 1024,
    }
    if ios_icon_dir.exists():
        for name, size in ios_sizes.items():
            save_resized(src512, size, ios_icon_dir / name)
    else:
        print("iOS AppIcon dir missing, skip")

    win_icon = APP / "windows" / "runner" / "resources"
    if win_icon.exists():
        icos = [
            src512.resize((s, s), Image.Resampling.LANCZOS)
            for s in (16, 32, 48, 64, 128, 256)
        ]
        icos[0].save(
            win_icon / "app_icon.ico",
            format="ICO",
            sizes=[(i.width, i.height) for i in icos],
        )
        print("OK windows/runner/resources/app_icon.ico")

    print("DONE")


if __name__ == "__main__":
    main()
