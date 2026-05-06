from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "llm-wiki-gravity-chamber.png"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: str, outline: str | None = None, radius: int = 18) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=1 if outline else 0)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, *, size: int = 24, color: str = "#162033", bold: bool = False) -> None:
    draw.text(xy, value, fill=color, font=font(size, bold=bold))


def main() -> int:
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), "#f7f8fb")
    draw = ImageDraw.Draw(image)

    # Header
    rounded(draw, (52, 44, 1548, 172), "#172033", radius=22)
    text(draw, (92, 74), "LLM Wiki Prompt Packet", size=40, color="#ffffff", bold=True)
    text(draw, (94, 125), "Local-first memory, evidence retrieval, Obsidian persistence, and agent evaluation", size=23, color="#d7e1f3")

    # Flow strip
    steps = [
        ("1", "Install", "wire repo or vault"),
        ("2", "Retrieve", "source truth first"),
        ("3", "Save", "Obsidian by default"),
        ("4", "Evaluate", "flywheel artifacts"),
        ("5", "Improve", "harness catches gaps"),
    ]
    x = 68
    for idx, title, subtitle in steps:
        rounded(draw, (x, 210, x + 270, 342), "#ffffff", outline="#d6dbe7", radius=16)
        rounded(draw, (x + 20, 230, x + 68, 278), "#276ef1", radius=12)
        text(draw, (x + 36, 238), idx, size=22, color="#ffffff", bold=True)
        text(draw, (x + 86, 230), title, size=27, color="#111827", bold=True)
        text(draw, (x + 86, 270), subtitle, size=19, color="#526070")
        x += 298

    # Terminal panel
    rounded(draw, (68, 392, 1018, 814), "#0c1222", radius=18)
    text(draw, (104, 424), "PowerShell", size=20, color="#8bd5ff", bold=True)
    terminal_lines = [
        "PS> py scripts/llm_wiki_packet.py evidence --plane local --deep",
        "ok  fixtures/click/src/click/core.py",
        "ok  wiki/syntheses/Click Deprecation Handling Source-Backed Synthesis.md",
        "",
        "PS> python .agent-improvement/scripts/repo_local_harness.py report",
        "success_rate: 1.0",
        "success_count: 2",
        "failure_count: 0",
        "",
        "PS> py -m pytest tests/test_llm_wiki_packet.py ...",
        "58 passed",
    ]
    y = 468
    for line in terminal_lines:
        color = "#80ffbf" if line.startswith("ok") or "passed" in line or "success_" in line else "#dce6f4"
        text(draw, (104, y), line, size=22, color=color)
        y += 30

    # Obsidian card
    rounded(draw, (1060, 392, 1532, 814), "#ffffff", outline="#d6dbe7", radius=18)
    text(draw, (1100, 426), "Obsidian Wiki Layer", size=30, color="#111827", bold=True)
    card_lines = [
        ("Provider", "obsidian"),
        ("Behavior", "agent-cli-obsidian"),
        ("Transport", "mcpvault or direct-file"),
        ("Saved note", "Click deprecation synthesis"),
        ("Hot cache", "refreshed"),
        ("Harness", "2/2 passing"),
    ]
    y = 492
    for label, value in card_lines:
        text(draw, (1100, y), label, size=19, color="#667085", bold=True)
        text(draw, (1245, y), value, size=21, color="#182230")
        y += 46
    rounded(draw, (1100, 746, 1492, 786), "#eaf8ef", outline="#b7e2c3", radius=12)
    text(draw, (1120, 754), "Research gets saved, not lost.", size=19, color="#18623b", bold=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
