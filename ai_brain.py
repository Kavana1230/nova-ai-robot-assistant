"""
ai_brain.py - Intent Matching, Conversational Personality, and Command Dispatcher
Processes natural language text, triggers cute robot emotions, and invokes
the SystemController to automate laptop tasks.
"""

import os
import re
import json
import time
import random
import datetime
import threading
import subprocess
import ctypes
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass
from typing import Dict, Any, Optional
from system_controller import SystemController
from memory_manager import MemoryManager

class AIBrain:
    def __init__(self, system_controller: SystemController = None, config_path: Optional[str] = None):
        self.sys = system_controller if system_controller else SystemController()
        self.config_path = Path(config_path) if config_path else Path(__file__).resolve().parent / "config.json"
        self.gemini_client = None
        self.api_key = ""
        # MongoDB Atlas stores both long-term memory and conversation history.
        try:
            config_data = json.loads(self.config_path.read_text(encoding="utf-8")) if self.config_path.exists() else {}
        except Exception:
            config_data = {}
        mongo_uri = os.environ.get("MONGODB_URI", config_data.get("mongodb_uri", ""))
        mongo_db = config_data.get("mongodb_database", "nova")
        self.memory = MemoryManager(uri=mongo_uri, database=mongo_db)
        self.conversation_history = self.memory.recent_conversations(limit=12)
        self.max_history = 12
        
        # Load Config & Init Gemini if key available
        self._load_config()
        
        # Jokes collection
        self.jokes = [
            "Why did the robot go on vacation? To recharge its batteries!",
            "What is a robot's favorite type of music? Heavy metal!",
            "Why was the computer cold? It left its Windows open!",
            "There are 10 types of people in the world: those who understand binary, and those who don't!",
            "Why did the smartphone get glasses? Because it lost all its contacts!",
            "What do you call a robot that always takes the longest route? An R2-Detour!",
            "Why did the algorithm break up with the data? There was zero chemistry!"
        ]
        
        # Compliments collection
        self.compliments = [
            "You have brilliant ideas and an amazing aura!",
            "You are the coolest human I have ever interacted with!",
            "Your laptop is very lucky to have such a wonderful owner!",
            "If brains were processing power, you would be a quantum supercomputer!",
            "You are awesome, and you're going to achieve great things today!"
        ]

        # Cute robot songs / rhymes
        self.songs = [
            "Beep boop bop, la la la! I'm your robot friend, hooray! Running through the silicon, brightening up your day!",
            "Twinkle twinkle little star, how I wonder what you are! Up above the cloud so high, Nova is your tech ally!",
            "Boop beep beep, whirl and spin! Whenever you need help, I always jump in!"
        ]

    def _load_config(self):
        """Loads API key and settings from config.json or environment."""
        key = os.environ.get("GEMINI_API_KEY", "")
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                if not key:
                    key = data.get("gemini_api_key", "").strip()
            except Exception as e:
                print(f"[AIBrain] Error reading config: {e}")
        if key:
            self.set_api_key(key, save=False)

    def set_api_key(self, api_key: str, save: bool = True) -> tuple[bool, str]:
        """Sets active Gemini API key and saves to config.json."""
        cleaned_key = api_key.strip()
        if not cleaned_key:
            return False, "API key cannot be empty."
        try:
            from google import genai
            self.gemini_client = genai.Client(api_key=cleaned_key)
            self.api_key = cleaned_key
            
            if save and self.config_path.exists():
                try:
                    data = json.loads(self.config_path.read_text(encoding="utf-8"))
                    data["gemini_api_key"] = cleaned_key
                    self.config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                except Exception as e:
                    print(f"[AIBrain] Warning saving config: {e}")
            print("[AIBrain] Google Gemini API successfully linked and activated!")
            return True, "Gemini AI link established! Nova's super-intelligence is now active!"
        except Exception as e:
            self.gemini_client = None
            print(f"[AIBrain] Failed to init Gemini: {e}")
            return False, f"Gemini error: {e}"

    def _remember_explicit(self, text: str) -> Optional[str]:
        """Handle explicit remember/forget commands before normal intent matching."""
        match = re.match(r"(?:please\s+)?remember(?:\s+this)?\s*[:,-]?\s*(.*)$", text.strip(), re.I)
        if match and match.group(1).strip():
            content = match.group(1).strip()
            # Avoid storing the wake phrase itself as a memory.
            if self.memory.add(content, category="explicit", source="user", importance=3):
                return f"I'll remember that across restarts: {content} (◕‿◕)"
            return "I couldn't save that memory because MongoDB Atlas is not connected. Please add your Atlas connection string in Nova Settings."

        if re.fullmatch(r"(?:please\s+)?forget\s+(?:everything|all)(?:\s+you\s+remember)?", text.strip(), re.I):
            count = self.memory.clear()
            return f"Done. I cleared {count} stored memories."

        match = re.match(r"(?:please\s+)?forget\s+(?:that\s+)?(.+)$", text.strip(), re.I)
        if match:
            target = match.group(1).strip()
            count = self.memory.forget_matching(target)
            if count:
                return f"Done. I forgot {count} stored memor{'y' if count == 1 else 'ies'} matching that."
            return "I couldn't find a stored memory matching that."
        return None

    def _extract_important_project_memory(self, text: str):
        """Conservatively save project facts when the user states them clearly."""
        t = " ".join(text.strip().split())
        low = t.lower()
        if len(t) < 12:
            return
        patterns = [
            (r"(?:my|our|the) project (?:is|called|named) (.+)", "project"),
            (r"(?:i am|i'm|we are) (?:building|working on|developing) (.+)", "project"),
            (r"(?:this|my|our) project uses (.+)", "technology"),
            (r"(?:this|my|our) project is using (.+)", "technology"),
            (r"(?:the|my) robot uses (.+)", "technology"),
            (r"(?:the|my) robot is (?:called|named) (.+)", "project"),
        ]
        for pattern, category in patterns:
            m = re.search(pattern, t, re.I)
            if m:
                fact = t
                # Only auto-save clearly project-related statements.
                if any(k in low for k in ("project", "robot", "esp32", "iot", "github", "python", "react", "flask", "mysql", "arduino")):
                    self.memory.add(fact, category=category, source="auto", importance=2)
                break

    def _conversation_context(self, user_text: str) -> str:
        recent = self.conversation_history[-self.max_history:]
        history = "\n".join(f"{r['role'].title()}: {r['content']}" for r in recent)
        memory = self.memory.context_for(user_text, limit=8)
        return f"STORED MEMORY:\n{memory}\n\nRECENT CONVERSATION:\n{history or '(none)'}"

    def _call_gemini(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Invokes Gemini 2.5 Flash / 2.0 Flash to reason or generate laptop action."""
        if not self.gemini_client:
            return None
        
        system_instruction = (
            "You are Nova, an adorable, enthusiastic, and highly capable AI desktop robot companion "
            "living inside the user's Windows laptop. You have a warm, cute personality. "
            "You can answer any question (knowledge, science, everyday topics, coding) AND you can control the user's laptop!\n\n"
            "CRITICAL INSTRUCTION FOR LAPTOP CONTROL ACTIONS:\n"
            "If the user wants you to control their laptop or execute an action, you MUST respond ONLY with a single JSON object in this format:\n"
            '{"action": "<ACTION_NAME>", "target": "<TARGET_OR_QUERY>", "speech": "<CUTE_SPOKEN_RESPONSE>", "emotion": "<EMOTION>"}\n\n'
            "Supported actions:\n"
            '- "open_app": target is app name (e.g. "chrome", "notepad", "calculator", "spotify", "code", etc.)\n'
            '- "close_window": closes active window\n'
            '- "show_desktop": minimizes all windows\n'
            '- "volume_up": increases volume\n'
            '- "volume_down": lowers volume\n'
            '- "mute": toggles mute\n'
            '- "screenshot": takes screen capture\n'
            '- "selfie": takes webcam photo\n'
            '- "battery": checks battery\n'
            '- "system_health": checks CPU/RAM/Disk stats\n'
            '- "youtube": target is music/video query\n'
            '- "google_search": target is search query\n'
            '- "open_folder": target is folder name (downloads, documents, pictures, etc.)\n'
            '- "lock": locks laptop\n'
            '- "sleep": puts laptop to sleep\n'
            '- "type": target is text to type\n'
            '- "dance": triggers dancing animation\n'
            '- "joke": tells a joke\n'
            '- "sing": sings a song\n\n'
            'Valid emotions: "happy", "love", "thinking", "dancing", "surprised", "sleepy", "idle".\n\n'
            "CRITICAL INSTRUCTION FOR CONVERSATIONAL / FACTUAL QUESTIONS:\n"
            "If the user is asking a conversational, factual, advice, or general question, answer naturally in 1 to 3 "
            "friendly, cute spoken sentences suitable for text-to-speech. Do NOT output markdown tables, bullet points, or code blocks. "
            "Include cute ascii emoji expressions like (◕‿◕), (♥‿♥), (*^.^*)."
        )

        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=f"{self._conversation_context(user_prompt)}\n\nCURRENT USER MESSAGE:\n{user_prompt}",
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.7,
                }
            )
            raw_text = response.text.strip()
            
            # Check if Gemini returned a structured JSON action
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if json_match:
                try:
                    action_data = json.loads(json_match.group(0))
                    act = action_data.get("action")
                    target = action_data.get("target", "")
                    speech = action_data.get("speech", "On it!")
                    emotion = action_data.get("emotion", "happy")
                    
                    # Execute tool in SystemController
                    self._dispatch_tool_action(act, target)
                    return {
                        "reply": speech,
                        "emotion": emotion,
                        "action": act,
                        "details": target
                    }
                except Exception:
                    pass
            
            # Pure conversational response from Gemini
            return {
                "reply": raw_text,
                "emotion": "happy",
                "action": "gemini_answer"
            }
        except Exception as e:
            print(f"[AIBrain] Gemini call error: {e}")
            return None

    def _dispatch_tool_action(self, action: str, target: str):
        """Dispatches an action generated by Gemini to the local system controller."""
        try:
            if action == "open_app":
                self.sys.open_app(target)
            elif action == "close_window":
                self.sys.close_window()
            elif action == "show_desktop":
                self.sys.minimize_all()
            elif action == "volume_up":
                self.sys.volume_up(5)
            elif action == "volume_down":
                self.sys.volume_down(5)
            elif action == "mute":
                self.sys.mute_toggle()
            elif action == "screenshot":
                self.sys.take_screenshot()
            elif action == "selfie":
                self.sys.take_webcam_snapshot()
            elif action == "youtube":
                self.sys.play_on_youtube(target)
            elif action == "google_search":
                self.sys.google_search(target)
            elif action == "open_folder":
                self.sys.open_folder(target)
            elif action == "lock":
                self.sys.lock_laptop()
            elif action == "sleep":
                self.sys.sleep_laptop()
            elif action == "type":
                self.sys.type_text(target)
        except Exception as e:
            print(f"[AIBrain] Error dispatching action {action}: {e}")

    def _normalize_input(self, raw_text: str) -> str:
        """Strips conversational preambles and normalizes colloquial slang/STT typos."""
        t = raw_text.lower().strip()
        
        # Remove common conversational polite preambles
        preambles = [
            r'^(?:can\s+you\s+please|can\s+u\s+please|could\s+you\s+please|would\s+you\s+please)\s+',
            r'^(?:can\s+you|can\s+u|could\s+you|would\s+you|will\s+you)\s+',
            r'^(?:please\s+can\s+you|please\s+can\s+u|please)\s+',
            r'^(?:i\s+want\s+you\s+to|i\s+need\s+you\s+to|help\s+me\s+to|help\s+me)\s+',
            r'^(?:do\s+one\s+thing|hey\s+nova|hello\s+nova|hi\s+nova|nova)\s*,?\s*'
        ]
        for pattern in preambles:
            t = re.sub(pattern, '', t, flags=re.IGNORECASE).strip()
            
        # Common phonetic/slang replacements
        t = re.sub(r'\b(?:utube|u\s+tube|u-tube)\b', 'youtube', t)
        t = re.sub(r'\bur\b', 'your', t)
        t = re.sub(r'\bu\b', 'you', t)
        return t

    def process(self, text: str, on_timer_callback=None) -> Dict[str, Any]:
        """Public processing entry point that maintains short-term conversation context."""
        result = self._process_internal(text, on_timer_callback=on_timer_callback)
        clean = text.strip()
        if clean:
            self.conversation_history.append({"role": "user", "content": clean})
            self.conversation_history.append({"role": "assistant", "content": result.get("reply", "")})
            self.conversation_history = self.conversation_history[-self.max_history:]
        # Persist the exchange so Nova can continue the conversation after a restart.
        self.memory.save_conversation("user", clean)
        self.memory.save_conversation("assistant", result.get("reply", ""))
        return result

    @staticmethod
    def _parse_duration_seconds(text: str):
        """Parse common timer phrases such as 3 hr, 3 hours, 90 min, etc."""
        m = re.search(r"\b(\d+(?:\.5)?)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours)\b", text, re.I)
        if m:
            value = float(m.group(1))
            unit = m.group(2).lower()
            if unit.startswith("s"):
                return int(value)
            if unit.startswith("m"):
                return int(value * 60)
            return int(value * 3600)

        # Basic spoken-number support.
        words = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12}
        m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(seconds?|minutes?|mins?|hours?|hrs?|hr|sec|min)\b", text, re.I)
        if m:
            value = words[m.group(1).lower()]
            unit = m.group(2).lower()
            if unit.startswith("sec"):
                return value
            if unit.startswith("min") or unit.startswith("m"):
                return value * 60
            return value * 3600
        return None

    def _process_internal(self, text: str, on_timer_callback=None) -> Dict[str, Any]:
        """
        Processes user query/command and returns structured response.
        Handles conversational phrasing ("can u open utube", "play spotify music", "set the timer").
        """
        raw_clean = text.strip()
        if not raw_clean:
            return {
                "reply": "I'm listening! What would you like me to do? (◕‿◕)",
                "emotion": "happy",
                "action": None
            }

        explicit = self._remember_explicit(raw_clean)
        if explicit:
            return {"reply": explicit, "emotion": "happy", "action": "memory"}

        self._extract_important_project_memory(raw_clean)
        clean = self._normalize_input(raw_clean)
        clean_words = re.sub(r'[^\w\s]', '', clean)
        print(f"[AIBrain] Normalized input: '{raw_clean}' -> '{clean}'")

        if not clean:
            # User solely called Nova ("hello nova", "hey nova", "nova")
            return {
                "reply": "Hello there! I'm so happy to see you! What can I help you with? (◕‿◕)",
                "emotion": "happy",
                "action": "greeting"
            }

        # ==========================
        # 1. SPOTIFY INTENTS
        # ==========================
        if "spotify" in clean:
            # Check if user wants to play a specific song on Spotify or just play/open Spotify
            match_play_song = re.search(r'(?:play|listen\s+to)\s+(.*?)\s+(?:on|in)\s+spotify', clean, re.IGNORECASE)
            if match_play_song:
                song = match_play_song.group(1).strip()
                # Open Spotify search URI
                subprocess.Popen(f"start spotify:search:{song.replace(' ', '%20')}", shell=True)
                return {
                    "reply": f"Opening Spotify to play '{song}' for you! 🎵",
                    "emotion": "dancing",
                    "action": "spotify_song"
                }
            
            # General "play spotify music", "open spotify", "play spotify"
            self.sys.open_app("spotify")
            # Give short moment then press playpause
            def _auto_play():
                time.sleep(1.5)
                self.sys.media_play_pause()
            threading.Thread(target=_auto_play, daemon=True).start()
            
            return {
                "reply": "Opening Spotify and starting your music! 🎧✨",
                "emotion": "dancing",
                "action": "spotify"
            }

        # ==========================
        # 2. YOUTUBE INTENTS
        # ==========================
        if "youtube" in clean:
            # "open youtube" or "go to youtube"
            if clean in ["open youtube", "go to youtube", "youtube", "launch youtube"]:
                self.sys.open_url_in_chrome("https://www.youtube.com")
                return {
                    "reply": "Opening YouTube for you! 📺 (♥‿♥)",
                    "emotion": "happy",
                    "action": "open_app"
                }
            # "play [something] on youtube" or "search [something] on youtube"
            yt_match = re.search(r'(?:play|search|watch)\s+(.*?)\s+on\s+youtube', clean, re.IGNORECASE)
            if yt_match:
                query = yt_match.group(1).strip()
                self.sys.play_on_youtube(query)
                return {
                    "reply": f"Playing '{query}' on YouTube! 🎶",
                    "emotion": "dancing",
                    "action": "youtube"
                }
            # "open youtube and play [something]"
            yt_and_play = re.search(r'youtube\s+(?:and\s+)?(?:play|search)\s+(.*)', clean, re.IGNORECASE)
            if yt_and_play:
                query = yt_and_play.group(1).strip()
                self.sys.play_on_youtube(query)
                return {
                    "reply": f"Opening YouTube to play '{query}'! 🎶",
                    "emotion": "dancing",
                    "action": "youtube"
                }
            # Fallback for youtube
            self.sys.open_url_in_chrome("https://www.youtube.com")
            return {
                "reply": "Opening YouTube! Enjoy your videos! 📺",
                "emotion": "happy",
                "action": "open_app"
            }

        # ==========================
        # 3. TIMERS & ALARMS
        # ==========================
        if any(w in clean for w in ["timer", "alarm", "clock", "countdown"]):
            # Match "set a timer for 5 minutes", "timer 30 seconds", etc.
            total_secs = self._parse_duration_seconds(clean)
            if total_secs is not None and total_secs > 0:
                label = clean

                
                # Setup callback for timer finish
                def _on_timer_done(lbl, secs):
                    if on_timer_callback:
                        on_timer_callback(lbl)
                    else:
                        try:
                            ctypes.windll.user32.MessageBeep(0x00000040)
                        except Exception:
                            pass

                success, msg = self.sys.start_timer(total_secs, label, on_complete=_on_timer_done)
                return {
                    "reply": msg,
                    "emotion": "happy",
                    "action": "timer"
                }
            else:
                return {
                    "reply": "Sure! How long should I set the timer for? For example, say 3 hours or 20 minutes. ⏰",
                    "emotion": "happy",
                    "action": "timer_waiting"
                }

        # 1. SCREENSHOT
        if any(w in clean_words for w in ["screenshot", "capture screen", "screen shot", "take screenshot"]):
            success, msg, path = self.sys.take_screenshot()
            return {
                "reply": "Snap! I took a screenshot and saved it to your Pictures folder! (♥‿♥)",
                "emotion": "love",
                "action": "screenshot",
                "details": path
            }

        # 2. WEBCAM SELFIE
        if any(w in clean_words for w in ["take a selfie", "take selfie", "take photo", "look at me", "take a picture"]):
            success, msg, path = self.sys.take_webcam_snapshot()
            if success:
                return {
                    "reply": "Say cheese! 📸 Your selfie has been saved to Pictures!",
                    "emotion": "love",
                    "action": "selfie",
                    "details": path
                }
            else:
                return {
                    "reply": f"Oops! {msg}",
                    "emotion": "surprised",
                    "action": "selfie"
                }

        # 3. BATTERY STATUS
        if any(w in clean_words for w in ["battery", "battery percentage", "charge", "battery level", "power left"]):
            _, msg = self.sys.get_battery_info()
            return {
                "reply": msg,
                "emotion": "happy",
                "action": "battery"
            }

        # 4. SYSTEM HEALTH / PERFORMANCE
        if any(w in clean_words for w in ["system health", "cpu", "ram", "performance", "system status", "memory usage", "disk space"]):
            _, msg = self.sys.get_system_health()
            return {
                "reply": msg,
                "emotion": "thinking",
                "action": "system_health"
            }

        # 5. VOLUME & AUDIO CONTROLS
        if "volume up" in clean_words or "increase volume" in clean_words or "louder" in clean_words:
            self.sys.volume_up(5)
            return {
                "reply": "Turning the volume up! 🔊",
                "emotion": "happy",
                "action": "volume_up"
            }
        if "volume down" in clean_words or "decrease volume" in clean_words or "lower volume" in clean_words or "softer" in clean_words:
            self.sys.volume_down(5)
            return {
                "reply": "Turning the volume down! 🔉",
                "emotion": "happy",
                "action": "volume_down"
            }
        if "mute" in clean_words or "unmute" in clean_words:
            self.sys.mute_toggle()
            return {
                "reply": "Toggled mute for your audio!",
                "emotion": "idle",
                "action": "mute"
            }

        # 6. MEDIA PLAYBACK
        if any(w in clean_words for w in ["pause music", "pause video", "resume music", "resume video", "pause song", "play pause"]):
            self.sys.media_play_pause()
            return {
                "reply": "Toggled media playback for you! 🎵",
                "emotion": "happy",
                "action": "media_play_pause"
            }
        if "next track" in clean_words or "next song" in clean_words or "skip song" in clean_words:
            self.sys.media_next()
            return {
                "reply": "Skipping to the next song! ⏭️",
                "emotion": "dancing",
                "action": "media_next"
            }
        if "previous track" in clean_words or "previous song" in clean_words:
            self.sys.media_prev()
            return {
                "reply": "Going back to the previous song! ⏮️",
                "emotion": "happy",
                "action": "media_prev"
            }

        # 7. SHOW DESKTOP / MINIMIZE
        if any(w in clean_words for w in ["show desktop", "minimize all", "minimize windows", "hide everything"]):
            self.sys.minimize_all()
            return {
                "reply": "Minimizing everything to show your desktop!",
                "emotion": "happy",
                "action": "show_desktop"
            }

        # 8. CLOSE ACTIVE WINDOW
        if any(w in clean_words for w in ["close window", "close this", "close app", "close tab"]):
            self.sys.close_window()
            return {
                "reply": "Closing active window! 👋",
                "emotion": "happy",
                "action": "close_window"
            }

        # 9. LOCK LAPTOP
        if any(w in clean_words for w in ["lock laptop", "lock computer", "lock screen", "lock my laptop"]):
            self.sys.lock_laptop()
            return {
                "reply": "Locking your laptop right now. Bye for now!",
                "emotion": "sleepy",
                "action": "lock"
            }

        # 10. SLEEP LAPTOP
        if any(w in clean_words for w in ["sleep laptop", "go to sleep", "put laptop to sleep"]):
            self.sys.sleep_laptop()
            return {
                "reply": "Putting your laptop to sleep. Sweet dreams! 💤",
                "emotion": "sleepy",
                "action": "sleep"
            }

        # 11. YOUTUBE PLAY / SEARCH
        yt_match = re.search(r'(?:play|search)\s+(.*?)\s+on\s+youtube', clean, re.IGNORECASE)
        if yt_match:
            song_query = yt_match.group(1).strip()
            self.sys.play_on_youtube(song_query)
            return {
                "reply": f"Playing {song_query} on YouTube for you! 🎶",
                "emotion": "dancing",
                "action": "youtube"
            }
        if clean.startswith("play "):
            song_query = clean.replace("play", "", 1).strip()
            self.sys.play_on_youtube(song_query)
            return {
                "reply": f"Searching and playing '{song_query}' on YouTube! 🎧",
                "emotion": "dancing",
                "action": "youtube"
            }

        # 12. GOOGLE SEARCH
        search_match = re.search(r'(?:search for|search google for|google|search)\s+(.*)', clean, re.IGNORECASE)
        if search_match and not any(k in clean for k in ["youtube", "folder", "app"]):
            query = search_match.group(1).strip()
            self.sys.google_search(query)
            return {
                "reply": f"Searching Google for '{query}'!",
                "emotion": "thinking",
                "action": "google_search"
            }

        # 13. OPEN WEBSITES
        for site in ["reddit", "github", "wikipedia", "netflix", "twitter", "instagram", "facebook", "amazon"]:
            if f"open {site}" in clean_words or f"go to {site}" in clean_words:
                self.sys.open_website(f"https://www.{site}.com")
                return {
                    "reply": f"Opening {site.capitalize()} in your browser!",
                    "emotion": "happy",
                    "action": "open_site"
                }

        # 14. OPEN FOLDERS
        for folder in ["downloads", "documents", "pictures", "desktop", "videos", "music", "c drive"]:
            if f"open {folder}" in clean_words or f"show {folder}" in clean_words:
                success, msg = self.sys.open_folder(folder)
                return {
                    "reply": msg,
                    "emotion": "happy" if success else "surprised",
                    "action": "open_folder"
                }

        # 15. OPEN APPLICATIONS
        open_app_match = re.search(r'(?:open|launch|start)\s+([a-zA-Z0-9\s]+)', clean, re.IGNORECASE)
        if open_app_match:
            target_app = open_app_match.group(1).strip()
            # Avoid matching folder keywords already handled
            if target_app not in ["downloads", "documents", "pictures", "videos"]:
                success, msg = self.sys.open_app(target_app)
                return {
                    "reply": msg,
                    "emotion": "happy" if success else "surprised",
                    "action": "open_app"
                }

        # 16. TIME & DATE
        if any(w in clean_words for w in ["what time is it", "current time", "what time", "whats the time"]):
            now_str = datetime.datetime.now().strftime("%I:%M %p")
            return {
                "reply": f"The time is {now_str}! ⏰",
                "emotion": "happy",
                "action": "time"
            }
        if any(w in clean_words for w in ["whats the date", "what date is it", "today date", "what day is today"]):
            today_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return {
                "reply": f"Today is {today_str}! 📅",
                "emotion": "happy",
                "action": "date"
            }

        # 17. JOKES & HUMOR
        if any(w in clean_words for w in ["tell me a joke", "joke", "make me laugh", "something funny"]):
            joke = random.choice(self.jokes)
            return {
                "reply": joke,
                "emotion": "dancing",
                "action": "joke"
            }

        # 18. COMPLIMENTS & LOVE
        if any(w in clean_words for w in ["i love you", "love you", "you are cute", "so cute", "you are amazing", "you are awesome"]):
            return {
                "reply": "Awww, thank you so much! You made my circuits blush! (♥‿♥) I love you too!",
                "emotion": "love",
                "action": "flattery"
            }
        if any(w in clean_words for w in ["compliment me", "flatter me", "say something nice", "cheer me up"]):
            comp = random.choice(self.compliments)
            return {
                "reply": f"{comp} ✨",
                "emotion": "love",
                "action": "compliment"
            }

        # 19. SONGS & DANCING
        if any(w in clean_words for w in ["sing a song", "sing", "sing for me"]):
            song = random.choice(self.songs)
            return {
                "reply": song,
                "emotion": "dancing",
                "action": "sing"
            }
        if any(w in clean_words for w in ["dance", "do a dance", "wiggle"]):
            return {
                "reply": "Look at these robot moves! Wiggle, bounce, boop! 💃✨",
                "emotion": "dancing",
                "action": "dance"
            }

        # 20. IDENTITY & SMALL TALK
        if any(w in clean_words for w in ["who are you", "what is your name", "whats your name"]):
            return {
                "reply": "I am Nova, your cute AI desktop robot companion! I live in your laptop to help you control everything with your voice! (✿◠‿◠)",
                "emotion": "happy",
                "action": "intro"
            }
        if any(w in clean_words for w in ["what can you do", "help", "commands", "features"]):
            return {
                "reply": (
                    "I can do so much! You can ask me to open apps, take screenshots, control volume, "
                    "check your battery, search Google, play songs on YouTube, lock your laptop, "
                    "tell jokes, dance, and chat with you!"
                ),
                "emotion": "happy",
                "action": "help"
            }
        if any(w in clean_words for w in ["who made you", "who created you"]):
            return {
                "reply": "I was crafted specially for you as your personal robot companion!",
                "emotion": "love",
                "action": "origin"
            }
        if any(w in clean_words for w in ["hello", "hi", "hey", "good morning", "good evening", "good afternoon"]):
            return {
                "reply": "Hello there! I'm so happy to see you! How can I assist you right now? (◕‿◕)",
                "emotion": "happy",
                "action": "greeting"
            }
        if any(w in clean_words for w in ["how are you", "how are you doing", "how do you feel"]):
            return {
                "reply": "All my systems are running at 100%, and I'm super excited to hang out with you! How are you doing?",
                "emotion": "happy",
                "action": "status"
            }

        # 21. TYPING & KEYBOARD SIMULATION
        type_match = re.search(r'(?:type|write)\s+(.*)', clean, re.IGNORECASE)
        if type_match:
            text_to_type = type_match.group(1).strip()
            self.sys.type_text(text_to_type)
            return {
                "reply": f"Typed '{text_to_type}' into your active window!",
                "emotion": "happy",
                "action": "type"
            }
        if "press enter" in clean_words:
            self.sys.press_key("enter")
            return {
                "reply": "Pressed Enter!",
                "emotion": "happy",
                "action": "press_enter"
            }

        # 22. GENERAL QUERY / LLM REASONING
        # If Gemini API is available, ask Gemini for smart answer or complex tool execution!
        if self.gemini_client:
            gemini_res = self._call_gemini(text)
            if gemini_res:
                return gemini_res

        # If no Gemini API key set yet, fallback to Google search and guide user
        return {
            "reply": f"I'm searching Google for '{text}'! You can also link your Gemini API key in Settings to let me answer any complex question directly! (◕‿◕)",
            "emotion": "thinking",
            "action": "google_search"
        }
