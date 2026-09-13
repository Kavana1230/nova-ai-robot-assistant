"""
voice_engine.py - Nova's single-stream voice engine.

The microphone is owned by ONE background worker.  Wake-word detection,
follow-up command capture, and push-to-talk requests all use that same
microphone stream.  This prevents SpeechRecognition from trying to enter the
same Microphone context from two threads at once.
"""

import asyncio
import queue
import random
import tempfile
import threading
import time
from pathlib import Path

import pygame
import pyttsx3
import speech_recognition as sr


class VoiceEngine:
    def __init__(
        self,
        on_speech_recognized=None,
        on_state_change=None,
        on_audio_pulse=None,
        on_wake=None,
    ):
        self.on_speech_recognized = on_speech_recognized
        self.on_state_change = on_state_change
        self.on_audio_pulse = on_audio_pulse
        self.on_wake = on_wake

        # ---------- Audio playback ----------
        pygame.mixer.init()
        self.temp_dir = Path(tempfile.gettempdir()) / "nova_voice_cache"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # ---------- Speech recognition ----------
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 280
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.7
        self.recognizer.non_speaking_duration = 0.35

        self.microphone = None
        self._init_mic()

        # ---------- TTS ----------
        self.offline_engine = None
        self._tts_lock = threading.RLock()
        self._init_offline_tts()
        self.current_voice = "en-US-AnaNeural"

        # Only this wake phrase is accepted.
        self.wake_words = ["hello nova"]
        self.wake_word_enabled = True

        # ---------- Listener state ----------
        self.is_listening = False
        self.is_speaking = False
        self._stop_listening_flag = threading.Event()
        self._worker_thread = None
        self._worker_lock = threading.Lock()

        # Requests from the GUI are consumed by the same listener thread.
        self._command_request = threading.Event()
        self._wake_followup_request = threading.Event()

        # Protects the single Microphone context.  Only _listen_worker owns it;
        # it is intentionally not used by listen_once() because listen_once no
        # longer opens the microphone itself.
        self._microphone_owner_thread = None

        # ---------- Speech playback queue ----------
        self._speech_queue = queue.Queue()
        self._worker_thread_tts = threading.Thread(
            target=self._speech_worker,
            daemon=True,
            name="Nova-TTS",
        )
        self._worker_thread_tts.start()

    # ============================================================
    # INITIALIZATION
    # ============================================================
    def _init_mic(self):
        """Create and calibrate the microphone once."""
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
            print("[VoiceEngine] Microphone initialized and calibrated.")
        except Exception as e:
            self.microphone = None
            print(f"[VoiceEngine] Warning: Microphone init error: {e}")

    def _init_offline_tts(self):
        try:
            self.offline_engine = pyttsx3.init()
            voices = self.offline_engine.getProperty("voices")
            for voice in voices:
                name = getattr(voice, "name", "") or ""
                if "zira" in name.lower() or "female" in name.lower():
                    self.offline_engine.setProperty("voice", voice.id)
                    break
            self.offline_engine.setProperty("rate", 175)
            self.offline_engine.setProperty("volume", 1.0)
        except Exception as e:
            self.offline_engine = None
            print(f"[VoiceEngine] pyttsx3 fallback init error: {e}")

    def set_voice(self, voice_name: str):
        if voice_name:
            self.current_voice = voice_name

    # ============================================================
    # TEXT TO SPEECH
    # ============================================================
    def speak(self, text: str, block: bool = False):
        if not text or not text.strip():
            return

        self.stop_speaking(clear_queue=True)
        self._speech_queue.put(text.strip())

        if block:
            self._speech_queue.join()

    def stop_speaking(self, clear_queue: bool = True):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        if self.offline_engine:
            try:
                self.offline_engine.stop()
            except Exception:
                pass

        self.is_speaking = False

        if clear_queue:
            while True:
                try:
                    self._speech_queue.get_nowait()
                    self._speech_queue.task_done()
                except queue.Empty:
                    break

    def _speech_worker(self):
        while True:
            text = self._speech_queue.get()
            if text is None:
                self._speech_queue.task_done()
                break
            try:
                self._execute_speak(text)
            finally:
                self._speech_queue.task_done()

    def _execute_speak(self, text: str):
        self.is_speaking = True
        if self.on_state_change:
            self.on_state_change("speaking")

        try:
            if not self._speak_with_edge_tts(text):
                self._speak_with_pyttsx3(text)
        finally:
            self.is_speaking = False
            if self.on_state_change:
                self.on_state_change("idle")

    def _speak_with_edge_tts(self, text: str) -> bool:
        try:
            import edge_tts

            temp_file = self.temp_dir / f"utterance_{int(time.time() * 1000)}.mp3"

            async def generate():
                communicate = edge_tts.Communicate(
                    text,
                    self.current_voice,
                    rate="+5%",
                    pitch="+2Hz",
                )
                await communicate.save(str(temp_file))

            asyncio.run(generate())

            if not temp_file.exists() or temp_file.stat().st_size == 0:
                return False

            pygame.mixer.music.load(str(temp_file))
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy() and self.is_speaking:
                if self.on_audio_pulse:
                    self.on_audio_pulse(random.uniform(0.3, 1.0))
                time.sleep(0.08)

            try:
                pygame.mixer.music.unload()
            except Exception:
                pass

            try:
                temp_file.unlink()
            except Exception:
                pass

            return True

        except Exception as e:
            print(f"[VoiceEngine] Edge-TTS error, falling back: {e}")
            return False

    def _speak_with_pyttsx3(self, text: str):
        try:
            with self._tts_lock:
                if not self.offline_engine:
                    self._init_offline_tts()
                if not self.offline_engine:
                    return

                pulse_active = True

                def pulse():
                    while pulse_active and self.is_speaking:
                        if self.on_audio_pulse:
                            self.on_audio_pulse(random.uniform(0.2, 0.9))
                        time.sleep(0.09)

                pulse_thread = threading.Thread(target=pulse, daemon=True)
                pulse_thread.start()

                self.offline_engine.say(text)
                self.offline_engine.runAndWait()
                pulse_active = False

        except Exception as e:
            print(f"[VoiceEngine] pyttsx3 error: {e}")

    # ============================================================
    # SINGLE MICROPHONE STREAM
    # ============================================================
    def start_listening_loop(self):
        """Start the one and only microphone owner thread."""
        with self._worker_lock:
            if self.is_listening and self._worker_thread and self._worker_thread.is_alive():
                return

            if not self.microphone:
                self._init_mic()

            if not self.microphone:
                print("[VoiceEngine] Cannot start listener: no microphone available.")
                return

            self.is_listening = True
            self._stop_listening_flag.clear()
            self._worker_thread = threading.Thread(
                target=self._listen_worker,
                daemon=True,
                name="Nova-Microphone",
            )
            self._worker_thread.start()

    def stop_listening_loop(self):
        """Stop the microphone owner thread."""
        self.is_listening = False
        self._stop_listening_flag.set()
        self._command_request.clear()
        self._wake_followup_request.clear()

    def request_command(self):
        """Ask the existing microphone worker to capture one command.

        This replaces opening a second `with self.microphone` context from the
        GUI's Speak button.
        """
        if not self.is_listening:
            self.start_listening_loop()

        if self.is_listening:
            print("[VoiceEngine] Command capture requested by UI.")
            self._command_request.set()

    def listen_once(self) -> str:
        """Compatibility API.

        IMPORTANT: this no longer opens the microphone.  It requests the single
        microphone worker to capture a command.  The callback receives the
        result through the normal `on_speech_recognized` path.
        """
        self.request_command()
        return ""

    # ============================================================
    # RECOGNITION HELPERS
    # ============================================================
    @staticmethod
    def _extract_command(text: str):
        """Return command after an exact-ish 'Hello Nova' wake phrase."""
        clean = " ".join(text.lower().strip().split())

        # Wake phrase must be at the beginning. This prevents a random
        # background sentence containing 'hello nova' from triggering Nova.
        prefix = "hello nova"
        if not clean.startswith(prefix):
            return None

        remainder = clean[len(prefix):].strip(" ,.!?;:-")
        return remainder

    def _recognize(self, audio) -> str:
        try:
            return self.recognizer.recognize_google(audio).strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[VoiceEngine] Speech recognition service error: {e}")
            return ""

    def _capture(self, source, timeout: float, phrase_time_limit: float):
        """Capture audio using the already-open source."""
        try:
            return self.recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
            )
        except sr.WaitTimeoutError:
            return None

    # ============================================================
    # MAIN MICROPHONE WORKER
    # ============================================================
    def _listen_worker(self):
        """Own the microphone context for the entire lifetime of the worker."""
        print(
            "[VoiceEngine] Single microphone stream started. "
            "Listening for 'Hello Nova'..."
        )

        try:
            # THIS is the only `with self.microphone as source` in the file.
            # No other thread is allowed to enter the microphone context.
            with self.microphone as source:
                self._microphone_owner_thread = threading.current_thread()

                while not self._stop_listening_flag.is_set():
                    if self.is_speaking:
                        # Never try to transcribe Nova's own TTS output.
                        time.sleep(0.15)
                        continue

                    # A UI push-to-talk request has priority over passive wake
                    # detection. It still uses this same `source` object.
                    if self._command_request.is_set():
                        self._command_request.clear()
                        self._capture_command(source, timeout=6, phrase_time_limit=20)
                        continue

                    if self._wake_followup_request.is_set():
                        self._wake_followup_request.clear()
                        self._capture_command(source, timeout=7, phrase_time_limit=20)
                        continue

                    if self.wake_word_enabled:
                        audio = self._capture(
                            source,
                            timeout=1.5,
                            phrase_time_limit=12,
                        )
                        if audio is None:
                            continue

                        text = self._recognize(audio)
                        if not text:
                            continue

                        print(f"[VoiceEngine] Heard: '{text}'")

                        # IMPORTANT:
                        # The Speak button can be clicked while this passive
                        # microphone capture is already running. In that case
                        # _command_request is set while _capture() is active.
                        # Do NOT discard the recognized speech. Use it as the
                        # requested command.
                        if self._command_request.is_set():
                            self._command_request.clear()
                            print(
                                "[VoiceEngine] UI command captured from "
                                "passive listener."
                            )
                            self._deliver_command(text)
                            continue

                        command = self._extract_command(text)

                        if command is None:
                            # Ignore normal background speech unless it starts
                            # with the exact wake phrase "Hello Nova".
                            continue

                        print("[VoiceEngine] ✨ Wake word 'hello nova' detected!")

                        if self.on_wake:
                            self.on_wake()

                        if command:
                            # One-shot command: "Hello Nova, open Chrome"
                            self._deliver_command(command)
                        else:
                            # Two-step command: "Hello Nova" -> listen again.
                            self.speak("Yes! I'm listening! (◕‿◕)", block=True)
                            if not self._stop_listening_flag.is_set():
                                self._capture_command(
                                    source,
                                    timeout=7,
                                    phrase_time_limit=20,
                                )

                    else:
                        # Optional non-wake mode: still one microphone stream.
                        audio = self._capture(
                            source,
                            timeout=2.5,
                            phrase_time_limit=10,
                        )
                        if audio is None:
                            continue
                        text = self._recognize(audio)
                        if text:
                            self._deliver_command(text)

        except Exception as e:
            print(f"[VoiceEngine] Listener error: {e}")
            if self.on_state_change:
                self.on_state_change("error")
        finally:
            self._microphone_owner_thread = None
            self.is_listening = False
            self._command_request.clear()
            self._wake_followup_request.clear()
            print("[VoiceEngine] Single microphone stream stopped.")

    def _capture_command(self, source, timeout=7, phrase_time_limit=20):
        if self._stop_listening_flag.is_set() or self.is_speaking:
            return

        if self.on_state_change:
            self.on_state_change("listening")

        print("[VoiceEngine] Listening for command...")
        audio = self._capture(
            source,
            timeout=timeout,
            phrase_time_limit=phrase_time_limit,
        )

        if audio is None:
            print("[VoiceEngine] Command listening timed out.")
            if self.on_state_change:
                self.on_state_change("idle")
            return

        if self.on_state_change:
            self.on_state_change("thinking")

        text = self._recognize(audio)
        if text:
            print(f"[VoiceEngine] Recognized: '{text}'")
            self._deliver_command(text)
        else:
            print("[VoiceEngine] Could not understand command.")

        if self.on_state_change:
            self.on_state_change("idle")

    def _deliver_command(self, text: str):
        if self.on_speech_recognized and text.strip():
            self.on_speech_recognized(text.strip())

    # ============================================================
    # CLEANUP
    # ============================================================
    def shutdown(self):
        self.stop_listening_loop()
        self.stop_speaking()
        try:
            self._speech_queue.put_nowait(None)
        except Exception:
            pass
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            pass
