"""
system_controller.py - Comprehensive Windows Laptop Controller for Nova Robot
Provides voice and programmatic control over apps, audio, display, system stats,
files, web browsing, and keyboard/mouse automation.
"""

import os
import sys
import time
import ctypes
import threading
import subprocess
import webbrowser
import datetime
from pathlib import Path
import psutil
import pyautogui

# Safety settings for pyautogui
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

class SystemController:
    def __init__(self):
        self.home_dir = Path.home()
        self.screenshots_dir = self.home_dir / "Pictures" / "NovaScreenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Common Windows application mappings
        # Check standard Windows directories for executables
        program_files = Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
        program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))
        local_app_data = Path(os.environ.get("LOCALAPPDATA", str(self.home_dir / "AppData" / "Local")))

        chrome_candidates = [
            program_files / "Google" / "Chrome" / "Application" / "chrome.exe",
            program_files_x86 / "Google" / "Chrome" / "Application" / "chrome.exe",
            local_app_data / "Google" / "Chrome" / "Application" / "chrome.exe"
        ]
        chrome_exe = next((str(p) for p in chrome_candidates if p.exists()), None)
        self.chrome_exe = chrome_exe

        vscode_candidates = [
            local_app_data / "Programs" / "Microsoft VS Code" / "Code.exe",
            program_files / "Microsoft VS Code" / "Code.exe"
        ]
        vscode_exe = next((str(p) for p in vscode_candidates if p.exists()), "code")

        # Startup folder for Windows auto-start
        self.startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        self.startup_bat = self.startup_dir / "NovaRobotStartup.bat"

        # Active background timers {id: thread}
        self.active_timers = {}

        self.app_map = {
            "chrome": ([f'"{chrome_exe}"', "start chrome"] if chrome_exe else ["start chrome"]),
            "google chrome": ([f'"{chrome_exe}"', "start chrome"] if chrome_exe else ["start chrome"]),
            "edge": ["start msedge"],
            "browser": ["start msedge", f'"{chrome_exe}"'],
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "calc": ["calc.exe"],
            "vs code": [f'"{vscode_exe}"', "code"],
            "vscode": [f'"{vscode_exe}"', "code"],
            "code": [f'"{vscode_exe}"', "code"],
            "spotify": ["start spotify:", "explorer.exe shell:AppsFolder\\SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify", "https://open.spotify.com"],
            "spotify music": ["start spotify:", "https://open.spotify.com"],
            "youtube": ["https://www.youtube.com"],
            "utube": ["https://www.youtube.com"],
            "u tube": ["https://www.youtube.com"],
            "clock": ["start ms-clock:"],
            "timer": ["start ms-clock:"],
            "alarm": ["start ms-clock:"],
            "whatsapp": ["start whatsapp:", "https://web.whatsapp.com"],
            "discord": ["start discord", "discord.exe"],
            "command prompt": ["cmd.exe"],
            "cmd": ["cmd.exe"],
            "terminal": ["wt.exe", "powershell.exe"],
            "powershell": ["powershell.exe"],
            "settings": ["start ms-settings:"],
            "file explorer": ["explorer.exe"],
            "explorer": ["explorer.exe"],
            "paint": ["mspaint.exe"],
            "camera": ["start microsoft.windows.camera:"],
            "word": ["winword.exe", "start winword"],
            "excel": ["excel.exe", "start excel"],
            "powerpoint": ["powerpnt.exe", "start powerpnt"],
            "task manager": ["taskmgr.exe"],
            "netflix": ["https://www.netflix.com"],
            "gmail": ["https://mail.google.com"],
        }
        
        # Quick folder mappings
        self.folder_map = {
            "downloads": self.home_dir / "Downloads",
            "documents": self.home_dir / "Documents",
            "pictures": self.home_dir / "Pictures",
            "desktop": self.home_dir / "Desktop",
            "videos": self.home_dir / "Videos",
            "music": self.home_dir / "Music",
            "c drive": Path("C:\\"),
        }

    # ==========================
    # APP & WINDOW CONTROLS
    # ==========================
    def open_app(self, app_name: str) -> tuple[bool, str]:
        """Opens a requested application."""
        clean_name = app_name.lower().strip()

        # Always open these websites directly in Google Chrome when Chrome
        # is installed. This avoids the Windows "Select an app to open this
        # https link" dialog caused by an unset/broken default browser.
        if clean_name in {"youtube", "utube", "u tube"}:
            return self.open_url_in_chrome("https://www.youtube.com")

        if clean_name in {"gmail"}:
            return self.open_url_in_chrome("https://mail.google.com")
        
        # Check direct mapping
        commands = self.app_map.get(clean_name)
        if not commands:
            for key, val in self.app_map.items():
                if key in clean_name or clean_name in key:
                    commands = val
                    clean_name = key
                    break
                    
        if commands:
            for cmd in commands:
                try:
                    if cmd.startswith("http"):
                        webbrowser.open(cmd)
                        return True, f"Opening {clean_name} in your browser!"
                    elif cmd.startswith("start "):
                        subprocess.Popen(cmd, shell=True)
                        return True, f"Opening {clean_name}!"
                    else:
                        subprocess.Popen(cmd, shell=True)
                        return True, f"Opening {clean_name}!"
                except Exception:
                    continue

        # Fallback: attempt to launch executable or search Windows
        try:
            subprocess.Popen(f"start {clean_name}", shell=True)
            return True, f"Attempting to launch {clean_name}!"
        except Exception as e:
            return False, f"Could not find or open {clean_name}: {e}"

    def close_window(self) -> tuple[bool, str]:
        """Closes the current active window (Alt + F4)."""
        try:
            pyautogui.hotkey('alt', 'f4')
            return True, "Closed active window!"
        except Exception as e:
            return False, f"Failed to close window: {e}"

    def minimize_all(self) -> tuple[bool, str]:
        """Minimizes all windows to reveal desktop (Win + D)."""
        try:
            pyautogui.hotkey('win', 'd')
            return True, "Showing your desktop!"
        except Exception as e:
            return False, f"Failed to minimize windows: {e}"

    def open_folder(self, folder_name: str) -> tuple[bool, str]:
        """Opens standard user folders."""
        clean = folder_name.lower().strip()
        target = None
        for key, path in self.folder_map.items():
            if key in clean:
                target = path
                break
                
        if target and target.exists():
            try:
                os.startfile(str(target))
                return True, f"Opening {clean} folder!"
            except Exception as e:
                return False, f"Could not open folder: {e}"
        return False, f"Folder {folder_name} not found."

    # ==========================
    # SYSTEM AUDIO & MEDIA
    # ==========================
    def volume_up(self, steps: int = 5) -> tuple[bool, str]:
        """Increases volume."""
        try:
            for _ in range(steps):
                pyautogui.press('volumeup')
            return True, "Turned volume up!"
        except Exception as e:
            return False, f"Volume adjustment error: {e}"

    def volume_down(self, steps: int = 5) -> tuple[bool, str]:
        """Decreases volume."""
        try:
            for _ in range(steps):
                pyautogui.press('volumedown')
            return True, "Turned volume down!"
        except Exception as e:
            return False, f"Volume adjustment error: {e}"

    def mute_toggle(self) -> tuple[bool, str]:
        """Mutes or unmutes system audio."""
        try:
            pyautogui.press('volumemute')
            return True, "Toggled audio mute!"
        except Exception as e:
            return False, f"Mute toggle error: {e}"

    def media_play_pause(self) -> tuple[bool, str]:
        """Toggles media play/pause."""
        try:
            pyautogui.press('playpause')
            return True, "Toggled media playback!"
        except Exception as e:
            return False, f"Media toggle error: {e}"

    def media_next(self) -> tuple[bool, str]:
        """Plays next media track."""
        try:
            pyautogui.press('nexttrack')
            return True, "Skipping to next track!"
        except Exception as e:
            return False, f"Next track error: {e}"

    def media_prev(self) -> tuple[bool, str]:
        """Plays previous media track."""
        try:
            pyautogui.press('prevtrack')
            return True, "Going to previous track!"
        except Exception as e:
            return False, f"Previous track error: {e}"

    # ==========================
    # SCREENSHOTS & CAMERA
    # ==========================
    def take_screenshot(self) -> tuple[bool, str, str]:
        """Captures full screen and saves to NovaScreenshots with multi-layer fallback."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Nova_Screenshot_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        
        # Method 1: PyAutoGUI
        try:
            pyautogui.screenshot(str(filepath))
            if filepath.exists() and filepath.stat().st_size > 0:
                return True, "Screenshot captured and saved to Pictures! (♥‿♥)", str(filepath)
        except Exception as e:
            print(f"[SystemController] PyAutoGUI screenshot notice: {e}")

        # Method 2: PIL ImageGrab
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True)
            img.save(str(filepath))
            if filepath.exists() and filepath.stat().st_size > 0:
                return True, "Screenshot captured and saved to Pictures! (♥‿♥)", str(filepath)
        except Exception as e:
            print(f"[SystemController] PIL ImageGrab notice: {e}")

        # Method 3: PowerShell Script
        try:
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms,System.Drawing
            $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
            $graphics = [System.Drawing.Graphics]::FromImage($bmp)
            $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
            $bmp.Save('{str(filepath).replace(chr(92), chr(47))}')
            $graphics.Dispose()
            $bmp.Dispose()
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=5)
            if filepath.exists() and filepath.stat().st_size > 0:
                return True, "Screenshot captured and saved to Pictures! (♥‿♥)", str(filepath)
        except Exception as e:
            print(f"[SystemController] PowerShell screenshot notice: {e}")

        return False, "Could not capture screen (session may be locked or restricted).", ""

    def take_webcam_snapshot(self) -> tuple[bool, str, str]:
        """Takes a photo with the webcam if available."""
        try:
            import cv2
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return False, "Could not access webcam.", ""
            
            # Let camera warm up
            time.sleep(0.3)
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"Nova_Selfie_{timestamp}.jpg"
                filepath = self.screenshots_dir / filename
                cv2.imwrite(str(filepath), frame)
                return True, "Say cheese! Photo taken and saved to Pictures!", str(filepath)
            else:
                return False, "Failed to capture webcam frame.", ""
        except Exception as e:
            return False, f"Webcam error: {e}", ""

    def open_url_in_chrome(self, url: str) -> tuple[bool, str]:
        """Open a URL directly in Google Chrome, without a browser chooser."""
        try:
            if self.chrome_exe and Path(self.chrome_exe).exists():
                subprocess.Popen([self.chrome_exe, url])
                return True, "Opened it directly in Google Chrome!"

            # Chrome may be discoverable through the Windows App Paths/
            # command alias even when the executable was not found above.
            subprocess.Popen(["cmd", "/c", "start", "", "chrome", url], shell=False)
            return True, "Opened it directly in Google Chrome!"
        except Exception as e:
            return False, f"Could not open Google Chrome: {e}"

    # ==========================
    # WEB & SEARCH
    # ==========================
    def google_search(self, query: str) -> tuple[bool, str]:
        """Searches Google for the given query."""
        try:
            from urllib.parse import quote_plus
            url = f"https://www.google.com/search?q={quote_plus(query)}"
            if self.chrome_exe and Path(self.chrome_exe).exists():
                subprocess.Popen([self.chrome_exe, url])
            else:
                webbrowser.open_new_tab(url)
            return True, f"Searching Google for: {query}"
        except Exception as e:
            return False, f"Search failed: {e}"

    def play_on_youtube(self, query: str) -> tuple[bool, str]:
        """Searches or plays video/music on YouTube."""
        try:
            encoded = query.replace(" ", "+")
            url = f"https://www.youtube.com/results?search_query={encoded}"
            success, _ = self.open_url_in_chrome(url)
            if success:
                return True, f"Opening '{query}' on YouTube in Google Chrome!"
            webbrowser.open_new_tab(url)
            return True, f"Opening '{query}' on YouTube!"
        except Exception as e:
            return False, f"YouTube error: {e}"

    def open_website(self, domain_or_name: str) -> tuple[bool, str]:
        """Opens a website."""
        clean = domain_or_name.strip()
        if not clean.startswith("http://") and not clean.startswith("https://"):
            if "." in clean:
                url = f"https://{clean}"
            else:
                url = f"https://www.{clean}.com"
        else:
            url = clean
        try:
            webbrowser.open(url)
            return True, f"Opening {url}!"
        except Exception as e:
            return False, f"Failed to open website: {e}"

    # ==========================
    # SYSTEM STATS & POWER
    # ==========================
    def get_battery_info(self) -> tuple[bool, str]:
        """Returns battery percentage and charging state."""
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return True, "Your laptop is running on desktop/AC power with no battery detected."
            
            percent = int(battery.percent)
            plugged = "plugged in and charging" if battery.power_plugged else "discharging on battery"
            
            if battery.secsleft != psutil.POWER_TIME_UNLIMITED and battery.secsleft > 0 and not battery.power_plugged:
                hours = battery.secsleft // 3600
                mins = (battery.secsleft % 3600) // 60
                time_str = f" About {hours} hours and {mins} minutes remaining."
            else:
                time_str = ""
                
            return True, f"Your battery is at {percent}%, and it is currently {plugged}.{time_str}"
        except Exception as e:
            return False, f"Could not read battery info: {e}"

    def get_system_health(self) -> tuple[bool, str]:
        """Returns CPU, RAM, and Disk utilization."""
        try:
            cpu = psutil.cpu_percent(interval=0.2)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")
            
            disk_free_gb = disk.free / (1024 ** 3)
            ram_percent = ram.percent
            
            status = (
                f"System status: CPU usage is {cpu}%, "
                f"RAM usage is {ram_percent}% ({ram.used // (1024**2)} MB used), "
                f"and your C: drive has {disk_free_gb:.1f} GB of free space."
            )
            return True, status
        except Exception as e:
            return False, f"Could not read system stats: {e}"

    def lock_laptop(self) -> tuple[bool, str]:
        """Locks the Windows workstation."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return True, "Locking your laptop. See you soon!"
        except Exception as e:
            return False, f"Failed to lock laptop: {e}"

    def sleep_laptop(self) -> tuple[bool, str]:
        """Puts the laptop to sleep."""
        try:
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return True, "Going to sleep mode now. Sweet dreams!"
        except Exception as e:
            return False, f"Sleep error: {e}"

    # ==========================
    # KEYBOARD & TYPING
    # ==========================
    def type_text(self, text: str) -> tuple[bool, str]:
        """Types text into the currently active cursor/window."""
        try:
            pyautogui.write(text, interval=0.03)
            return True, f"Typed: '{text}'"
        except Exception as e:
            return False, f"Typing error: {e}"

    def press_key(self, key_name: str) -> tuple[bool, str]:
        """Presses a specific key (e.g. enter, space, esc, backspace)."""
        try:
            pyautogui.press(key_name.lower().strip())
            return True, f"Pressed {key_name}!"
        except Exception as e:
            return False, f"Keypress error: {e}"

    # ==========================
    # WINDOWS AUTO-START (HKCU RUN)
    # ==========================
    def is_auto_start_enabled(self) -> bool:
        """Checks if HKCU Run registry value exists for Nova."""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, "NovaRobot")
                return True
        except Exception:
            return False

    def enable_auto_start(self) -> tuple[bool, str]:
        """Adds Nova launcher command to HKCU Run registry."""
        try:
            import winreg
            proj_dir = Path(__file__).resolve().parent
            run_cmd = f'"{sys.executable}" "{proj_dir / "main.py"}"'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "NovaRobot", 0, winreg.REG_SZ, run_cmd)
            return True, "Nova will now start automatically whenever your laptop turns on!"
        except Exception as e:
            return False, f"Could not enable auto-start: {e}"

    def disable_auto_start(self) -> tuple[bool, str]:
        """Removes Nova from HKCU Run registry."""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, "NovaRobot")
                except FileNotFoundError:
                    pass
            return True, "Disabled auto-start on laptop boot."
        except Exception as e:
            return False, f"Could not disable auto-start: {e}"

    # ==========================
    # TIMERS & ALARMS
    # ==========================
    def open_clock(self) -> tuple[bool, str]:
        """Opens Windows native Clock / Timer application."""
        try:
            subprocess.Popen("start ms-clock:", shell=True)
            return True, "Opening Windows Clock and Timer!"
        except Exception as e:
            return False, f"Could not open Clock: {e}"

    def start_timer(self, total_seconds: int, label: str = "Timer", on_complete=None) -> tuple[bool, str]:
        """Runs a background countdown timer and notifies on finish."""
        if total_seconds <= 0:
            return self.open_clock()
            
        timer_id = f"timer_{int(time.time()*1000)}"
        
        def _worker():
            time.sleep(total_seconds)
            # Beep system chime
            try:
                ctypes.windll.user32.MessageBeep(0x00000040)  # Asterisk chime
            except Exception:
                pass
            if on_complete:
                on_complete(label, total_seconds)
            self.active_timers.pop(timer_id, None)

        t = threading.Thread(target=_worker, daemon=True)
        self.active_timers[timer_id] = t
        t.start()
        
        if total_seconds >= 60:
            mins = total_seconds // 60
            secs = total_seconds % 60
            time_str = f"{mins} minute{'s' if mins > 1 else ''}" + (f" and {secs} seconds" if secs > 0 else "")
        else:
            time_str = f"{total_seconds} seconds"
            
        return True, f"Timer set for {time_str}! I will notify you when it's done! ⏰"
