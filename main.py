import os
import sys
import json
import time
import threading
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from system_controller import SystemController
from voice_engine import VoiceEngine
from ai_brain import AIBrain
from robot_gui import RobotGUI

class NovaRobotApp:
    def __init__(self):
        print("========================================")
        print("   ⚡ INITIALIZING NOVA DESKTOP ROBOT   ")
        print("========================================")
        
        # Load Config
        self.config_path = Path(__file__).resolve().parent / "config.json"
        self.config = self._load_config()

        # 1. Initialize Subsystems
        self.sys_control = SystemController()
        self.brain = AIBrain(self.sys_control, config_path=str(self.config_path))
        
        # 2. Initialize GUI with settings support
        self.gui = RobotGUI(
            on_command_submitted=self.handle_command,
            on_mic_clicked=self.handle_mic_click,
            on_settings_saved=self.handle_settings_saved,
            on_memory_requested=self.open_memory_manager,
            initial_config=self.config
        )
        
        # 3. Initialize Voice Engine with GUI animation & wake callbacks
        self.gui.memory_provider = self.brain.memory.list
        self.gui.on_memory_deleted = self.forget_memory
        self.gui.on_memory_cleared = self.brain.memory.clear

        self.voice = VoiceEngine(
            on_speech_recognized=self.handle_command,
            on_state_change=self.on_voice_state_change,
            on_audio_pulse=self.gui.pulse_mouth,
            on_wake=self.on_wake_word_heard
        )
        
        # Set initial voice and wake-word setting
        self.voice.set_voice(self.config.get("voice", "en-US-AnaNeural"))
        self.voice.wake_word_enabled = self.config.get("wake_word_enabled", True)
        self.config["wake_words"] = ["hello nova"]
        self.voice.wake_words = ["hello nova"]

        # 4. Start background listening loop for the single wake phrase if enabled
        if self.voice.wake_word_enabled:
            self.voice.start_listening_loop()

    def handle_command(self, user_text: str):
        """Processes any command (from voice or text input)."""
        clean_text = user_text.strip()
        if not clean_text:
            return
            
        print(f"[App] Processing command: '{clean_text}'")
        self.gui.set_dialogue("You", clean_text)
        self.gui.set_state("thinking")
        
        # Process through AI Brain with timer callback
        result = self.brain.process(clean_text, on_timer_callback=self.on_timer_completed)
        reply = result.get("reply", "Done!")
        emotion = result.get("emotion", "happy")
        
        print(f"[App] Nova reply: '{reply}' (Emotion: {emotion})")
        self.gui.set_dialogue("Nova", reply)
        self.gui.set_state(emotion)
        
        # Speak the response
        self.voice.speak(reply)

    def on_timer_completed(self, label: str):
        """Called in background when a set timer finishes."""
        alarm_msg = f"Ding ding ding! ⏰ Your timer for {label} is up! (♥‿♥)"
        print(f"[App] {alarm_msg}")
        self.gui.set_dialogue("Nova", alarm_msg)
        self.gui.set_state("happy")
        self.voice.speak(alarm_msg)

    def handle_mic_click(self):
        """Request command capture from the ONE microphone worker."""
        print("[App] User clicked Speak button.")
        self.gui.set_state("listening")
        self.gui.set_dialogue("Nova", "Listening to your voice... Speak now! 🎙️")
        self.voice.request_command()

    def _load_config(self) -> dict:
        """Reads config.json with defaults."""
        defaults = {
            "gemini_api_key": "",
            "wake_word_enabled": True,
            "wake_words": ["hello nova"],
            "voice": "en-US-AnaNeural",
            "auto_start_with_windows": False
        }
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                defaults.update(data)
            except Exception:
                pass
        return defaults

    def on_wake_word_heard(self):
        """Called immediately when user says 'Hello Nova'."""
        print("[App] Wake word detected!")
        self.gui.set_state("listening")
        self.gui.set_dialogue("Nova", "I'm listening! Speak your command... 🎙️")

    def open_memory_manager(self):
        """Open Nova's persistent memory viewer/forget controls."""
        self.gui.show_memory_manager(self.brain.memory.list())

    def forget_memory(self, memory_id: int):
        self.brain.memory.delete(memory_id)

    def handle_settings_saved(self, new_config: dict):
        """Called when user saves settings modal in GUI."""
        print("[App] Settings updated by user.")
        self.config = new_config
        
        # 0. Update MongoDB Atlas memory connection
        mongo_uri = new_config.get("mongodb_uri", "").strip()
        mongo_db = new_config.get("mongodb_database", "nova").strip() or "nova"
        self.brain.memory.reconnect(mongo_uri, mongo_db)

        # 1. Update Gemini API key in Brain
        new_key = new_config.get("gemini_api_key", "").strip()
        if new_key:
            ok, msg = self.brain.set_api_key(new_key, save=True)
            print(f"[App] {msg}")

        # 2. Update Wake Word continuous listening
        wake_on = new_config.get("wake_word_enabled", True)
        self.voice.wake_word_enabled = wake_on
        if wake_on and not self.voice.is_listening:
            self.voice.start_listening_loop()
        elif not wake_on and self.voice.is_listening:
            self.voice.stop_listening_loop()

        # 3. Update Windows Auto-Start
        if new_config.get("auto_start_with_windows", False):
            self.sys_control.enable_auto_start()
        else:
            self.sys_control.disable_auto_start()

        # 4. Persist to config.json
        try:
            self.config_path.write_text(json.dumps(new_config, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[App] Error saving config: {e}")

    def on_voice_state_change(self, state: str):
        """Synchronizes voice engine events with GUI avatar state."""
        # Only override if not in a special expressive state like love/dancing
        if self.gui.state not in ("love", "dancing", "sleepy"):
            self.gui.set_state(state)

    def run(self):
        """Starts application loop."""
        try:
            self.gui.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown of all threads and audio."""
        print("[App] Shutting down Nova...")
        try:
            self.voice.stop_listening_loop()
            self.voice.stop_speaking()
        except Exception:
            pass
        sys.exit(0)

if __name__ == "__main__":
    app = NovaRobotApp()
    app.run()
