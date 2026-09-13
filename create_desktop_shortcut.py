"""
create_desktop_shortcut.py - Places a one-click shortcut on the Windows Desktop
"""

import os
from pathlib import Path

def get_desktop_dir():
    # Try OneDrive Desktop first if present, else standard Desktop
    candidates = [
        Path.home() / "OneDrive" / "Desktop",
        Path.home() / "Desktop"
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

def make_shortcut():
    desktop = get_desktop_dir()
    project_dir = Path(__file__).resolve().parent
    shortcut_bat = desktop / "Nova Robot.bat"
    content = f"""@echo off
cd /d "{project_dir}"
call run_robot.bat
"""
    try:
        shortcut_bat.write_text(content, encoding="utf-8")
        print(f"Created Desktop Launcher: {shortcut_bat}")
    except Exception as e:
        print(f"Notice creating shortcut: {e}")

if __name__ == "__main__":
    make_shortcut()
