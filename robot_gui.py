"""
robot_gui.py - Interactive Animated Desktop Robot Avatar & GUI for Nova
Features real-time vector graphics on Tkinter Canvas, expressive cyber-eyes,
lip-sync mouth animation, heart-eyes, cursor tracking, draggable window,
and full desktop controls.
"""

import math
import time
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

class RobotGUI:
    def __init__(self, on_command_submitted: Optional[Callable[[str], None]] = None,
                 on_mic_clicked: Optional[Callable[[], None]] = None,
                 on_settings_saved: Optional[Callable[[dict], None]] = None,
                 on_memory_requested: Optional[Callable[[], None]] = None,
                 initial_config: Optional[dict] = None):
        self.on_command_submitted = on_command_submitted
        self.on_mic_clicked = on_mic_clicked
        self.on_settings_saved = on_settings_saved
        self.on_memory_requested = on_memory_requested
        self.config = initial_config if initial_config else {}
        
        # Main Window
        self.root = tk.Tk()
        self.root.title("Nova - AI Robot Companion")
        self.root.geometry("440x650+1000+150")
        self.root.configure(bg="#0c0f1d")
        self.root.attributes("-topmost", True)
        self.is_topmost = True
        
        # Color Palettes (Themeable)
        self.themes = {
            "Cyan": {"primary": "#00f0ff", "secondary": "#0088ff", "blush": "#ff4081", "visor": "#050b14"},
            "Pink": {"primary": "#ff3399", "secondary": "#ff66cc", "blush": "#ff99cc", "visor": "#14050f"},
            "Emerald": {"primary": "#00ff88", "secondary": "#00cc66", "blush": "#ff5588", "visor": "#03140a"},
            "Gold": {"primary": "#ffcc00", "secondary": "#ff9900", "blush": "#ff4466", "visor": "#140f03"},
            "Purple": {"primary": "#bf55ec", "secondary": "#8e44ad", "blush": "#ff69b4", "visor": "#0f0514"}
        }
        self.current_theme = "Cyan"
        self.colors = self.themes[self.current_theme]
        
        # Robot States
        self.state = "idle"       # "idle", "listening", "thinking", "speaking", "happy", "love", "dancing", "sleepy"
        self.prev_state = "idle"
        
        # Animation Parameters
        self.anim_t = 0.0
        self.blink_progress = 0.0 # 0.0 = open, 1.0 = fully closed
        self.is_blinking = False
        self.next_blink_time = time.time() + random.uniform(2.5, 4.5)
        self.mouth_openness = 0.0  # 0.0 = closed/smile, 1.0 = wide open
        self.target_mouth_openness = 0.0
        self.head_tilt = 0.0
        self.mouse_x = 220
        self.mouse_y = 120
        self.particles = []       # For heart/sparkle particles
        
        # Window Dragging state
        self.drag_x = 0
        self.drag_y = 0
        
        # Build UI layout
        self._build_layout()
        
        # Bind Mouse & Window Events
        self.root.bind("<B1-Motion>", self._on_drag)
        self.root.bind("<Button-1>", self._on_drag_start)
        self.root.bind("<Motion>", self._on_mouse_move)
        self.root.bind("<space>", lambda e: self._trigger_mic())
        
        # Start Animation Loop (~40 FPS)
        self.is_running = True
        self.root.after(25, self._animation_tick)

    def _build_layout(self):
        # 1. Top Header Bar
        header_frame = tk.Frame(self.root, bg="#12172b", height=42)
        header_frame.pack(fill="x", side="top")
        
        # Title with live status icon
        self.title_lbl = tk.Label(header_frame, text="⚡ NOVA AI ROBOT", font=("Segoe UI", 11, "bold"),
                                  fg="#00f0ff", bg="#12172b")
        self.title_lbl.pack(side="left", padx=14, pady=8)
        
        # Status Badge
        self.status_badge = tk.Label(header_frame, text="● READY", font=("Segoe UI", 9, "bold"),
                                     fg="#00ff88", bg="#12172b")
        self.status_badge.pack(side="left", padx=5)

        # Settings & API Key button
        self.settings_btn = tk.Button(header_frame, text="⚙️ API / Setup", font=("Segoe UI", 8),
                                      bg="#1c233f", fg="#00f0ff", relief="flat", bd=0,
                                      activebackground="#29345e", activeforeground="#ffffff",
                                      command=self._open_settings_modal)
        self.settings_btn.pack(side="right", padx=4, pady=6)

        self.memory_btn = tk.Button(header_frame, text="🧠 Memory", font=("Segoe UI", 8),
                                    bg="#1c233f", fg="#00f0ff", relief="flat", bd=0,
                                    activebackground="#29345e", activeforeground="#ffffff",
                                    command=self._request_memory_manager)
        self.memory_btn.pack(side="right", padx=4, pady=6)

        # Pin / Always on Top button
        self.pin_btn = tk.Button(header_frame, text="📌 On Top", font=("Segoe UI", 8),
                                 bg="#1c233f", fg="#ffffff", relief="flat", bd=0,
                                 activebackground="#29345e", activeforeground="#ffffff",
                                 command=self._toggle_topmost)
        self.pin_btn.pack(side="right", padx=4, pady=6)

        # Theme menu button
        theme_btn = tk.Menubutton(header_frame, text="🎨 Theme", font=("Segoe UI", 8),
                                  bg="#1c233f", fg="#ffffff", relief="flat")
        theme_menu = tk.Menu(theme_btn, tearoff=0, bg="#1c233f", fg="#ffffff", activebackground="#00f0ff", activeforeground="#000000")
        for t_name in self.themes.keys():
            theme_menu.add_command(label=t_name, command=lambda tn=t_name: self._change_theme(tn))
        theme_btn.config(menu=theme_menu)
        theme_btn.pack(side="right", padx=4, pady=6)

        # 2. Main Robot Canvas (Avatar)
        self.canvas_width = 440
        self.canvas_height = 250
        self.canvas = tk.Canvas(self.root, width=self.canvas_width, height=self.canvas_height,
                               bg="#0c0f1d", highlightthickness=0)
        self.canvas.pack(fill="x", pady=5)
        
        # 3. Speech Subtitle / Dialogue Bubble
        bubble_outer = tk.Frame(self.root, bg="#13192f", bd=1, relief="solid")
        bubble_outer.pack(fill="x", padx=16, pady=4)
        
        self.speaker_lbl = tk.Label(bubble_outer, text="Nova:", font=("Segoe UI", 9, "bold"),
                                    fg="#00f0ff", bg="#13192f")
        self.speaker_lbl.pack(anchor="w", padx=10, pady=(6, 2))
        
        self.dialogue_lbl = tk.Label(bubble_outer, 
                                     text="Hi! I'm Nova, your laptop robot! Click the mic or talk to me! (♥‿♥)",
                                     font=("Segoe UI", 10), fg="#e2e8f0", bg="#13192f",
                                     wraplength=390, justify="left")
        self.dialogue_lbl.pack(fill="x", padx=10, pady=(0, 8))

        # 4. Quick Action Chips (Buttons)
        chips_frame = tk.Frame(self.root, bg="#0c0f1d")
        chips_frame.pack(fill="x", padx=14, pady=4)
        
        actions = [
            ("🔋 Battery", "how is my battery"),
            ("📸 Screen", "take a screenshot"),
            ("🎵 Music", "play lofi beats on youtube"),
            ("✨ Joke", "tell me a joke"),
            ("💃 Dance", "do a dance"),
            ("❤️ Love", "i love you"),
            ("🖥️ Desktop", "show desktop"),
        ]
        
        row1 = tk.Frame(chips_frame, bg="#0c0f1d")
        row1.pack(fill="x", pady=2)
        row2 = tk.Frame(chips_frame, bg="#0c0f1d")
        row2.pack(fill="x", pady=2)
        
        for i, (label, cmd) in enumerate(actions):
            parent = row1 if i < 4 else row2
            btn = tk.Button(parent, text=label, font=("Segoe UI", 8),
                            bg="#182038", fg="#94a3b8", relief="flat", bd=0, padx=7, pady=2,
                            activebackground="#00f0ff", activeforeground="#000000",
                            command=lambda c=cmd: self._submit_command(c))
            btn.pack(side="left", padx=3)

        # 5. Microphone and Voice Trigger Bar
        mic_bar = tk.Frame(self.root, bg="#0c0f1d")
        mic_bar.pack(fill="x", padx=16, pady=8)
        
        self.mic_btn = tk.Button(mic_bar, text="🎙️  HOLD OR CLICK TO SPEAK",
                                 font=("Segoe UI", 11, "bold"),
                                 bg="#00f0ff", fg="#050b14", relief="flat", bd=0, height=2,
                                 activebackground="#66f7ff", activeforeground="#050b14",
                                 command=self._trigger_mic)
        self.mic_btn.pack(fill="x")
        
        hint_lbl = tk.Label(mic_bar, text="Tip: You can also press Spacebar to talk, or type below:",
                            font=("Segoe UI", 8), fg="#64748b", bg="#0c0f1d")
        hint_lbl.pack(anchor="center", pady=(3, 0))

        # 6. Silent Text Command Input Bar
        input_bar = tk.Frame(self.root, bg="#151b31", bd=1, relief="solid")
        input_bar.pack(fill="x", padx=16, pady=8, side="bottom")
        
        self.entry_box = tk.Entry(input_bar, font=("Segoe UI", 10), bg="#151b31", fg="#ffffff",
                                  insertbackground="#00f0ff", relief="flat", bd=0)
        self.entry_box.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        self.entry_box.bind("<Return>", lambda e: self._on_entry_submit())
        
        send_btn = tk.Button(input_bar, text="➤ Send", font=("Segoe UI", 9, "bold"),
                             bg="#0088ff", fg="#ffffff", relief="flat", bd=0, padx=12,
                             activebackground="#33a1ff", activeforeground="#ffffff",
                             command=self._on_entry_submit)
        send_btn.pack(side="right", padx=6, pady=4)

    # ==========================
    # WINDOW CONTROLS & EVENTS
    # ==========================
    def _request_memory_manager(self):
        if self.on_memory_requested:
            self.on_memory_requested()

    def show_memory_manager(self, memories):
        """Display stored memories and provide per-memory/all-memory forget controls."""
        modal = tk.Toplevel(self.root)
        modal.title("🧠 Nova Memory")
        modal.geometry("520x430")
        modal.configure(bg="#12172b")
        modal.attributes("-topmost", True)

        tk.Label(modal, text="🧠 NOVA MEMORY", font=("Segoe UI", 13, "bold"),
                 fg="#00f0ff", bg="#12172b").pack(pady=(14, 4))
        tk.Label(modal, text="Important project details and explicit 'remember this' items are stored locally.",
                 font=("Segoe UI", 8), fg="#94a3b8", bg="#12172b", wraplength=470).pack(pady=(0, 10))

        frame = tk.Frame(modal, bg="#0c0f1d")
        frame.pack(fill="both", expand=True, padx=16, pady=6)
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        listbox = tk.Listbox(frame, bg="#0c0f1d", fg="#e2e8f0",
                             selectbackground="#0088ff", selectforeground="#ffffff",
                             font=("Segoe UI", 9), bd=0, yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def refresh():
            listbox.delete(0, "end")
            current = self._memory_rows()
            for m in current:
                source = "Explicit" if m.get("source") in ("explicit", "user") else "Project detail"
                listbox.insert("end", f"#{m['id']}  [{source}] {m['content']}")
            return current

        def forget_selected():
            selection = listbox.curselection()
            if not selection:
                return
            current = self._memory_rows()
            if selection[0] >= len(current):
                return
            memory_id = current[selection[0]]["id"]
            if hasattr(self, "on_memory_deleted") and self.on_memory_deleted:
                self.on_memory_deleted(memory_id)
                refresh()

        def forget_all():
            if not hasattr(self, "on_memory_cleared") or not self.on_memory_cleared:
                return
            if messagebox.askyesno("Forget all memories", "Delete every stored Nova memory?", parent=modal):
                self.on_memory_cleared()
                refresh()

        buttons = tk.Frame(modal, bg="#12172b")
        buttons.pack(fill="x", padx=16, pady=(6, 14))
        tk.Button(buttons, text="🗑️ Forget Selected", font=("Segoe UI", 9, "bold"),
                  bg="#8b2d3b", fg="#ffffff", relief="flat", bd=0, padx=12, pady=7,
                  command=forget_selected).pack(side="left")
        tk.Button(buttons, text="🧹 Forget All", font=("Segoe UI", 9, "bold"),
                  bg="#5f2530", fg="#ffffff", relief="flat", bd=0, padx=12, pady=7,
                  command=forget_all).pack(side="left", padx=6)
        tk.Button(buttons, text="Close", font=("Segoe UI", 9),
                  bg="#1c233f", fg="#ffffff", relief="flat", bd=0, padx=18, pady=7,
                  command=modal.destroy).pack(side="right")
        refresh()

    def _memory_rows(self):
        # Main injects this callable at runtime to avoid coupling GUI to the database layer.
        if hasattr(self, "memory_provider") and self.memory_provider:
            return self.memory_provider()
        return []

    def _open_settings_modal(self):
        """Opens settings & Gemini API configuration window."""
        modal = tk.Toplevel(self.root)
        modal.title("⚙️ Nova Settings & API Setup")
        modal.geometry("420x500")
        modal.configure(bg="#12172b")
        modal.attributes("-topmost", True)
        modal.resizable(False, False)

        tk.Label(modal, text="⚙️ NOVA CONFIGURATION", font=("Segoe UI", 12, "bold"),
                 fg="#00f0ff", bg="#12172b").pack(pady=(14, 6))

        # 1. API Key Section
        api_frame = tk.Frame(modal, bg="#12172b")
        api_frame.pack(fill="x", padx=16, pady=6)
        
        tk.Label(api_frame, text="Google Gemini API Key:", font=("Segoe UI", 9, "bold"),
                 fg="#e2e8f0", bg="#12172b").pack(anchor="w")
        
        key_entry = tk.Entry(api_frame, font=("Segoe UI", 10), bg="#1c233f", fg="#ffffff",
                             insertbackground="#00f0ff", relief="flat", bd=0)
        current_key = self.config.get("gemini_api_key", "")
        if current_key:
            key_entry.insert(0, current_key)
        key_entry.pack(fill="x", pady=4, ipady=3)

        paste_btn = tk.Button(api_frame, text="📋 Paste from Clipboard", font=("Segoe UI", 8),
                              bg="#29345e", fg="#ffffff", relief="flat", bd=0,
                              command=lambda: (key_entry.delete(0, tk.END), key_entry.insert(0, modal.clipboard_get())))
        paste_btn.pack(anchor="e", pady=(0, 4))

        # 2. MongoDB Atlas memory
        mongo_frame = tk.Frame(modal, bg="#12172b")
        mongo_frame.pack(fill="x", padx=16, pady=(4, 6))
        tk.Label(mongo_frame, text="MongoDB Atlas Connection String:", font=("Segoe UI", 9, "bold"),
                 fg="#e2e8f0", bg="#12172b").pack(anchor="w")
        mongo_entry = tk.Entry(mongo_frame, font=("Segoe UI", 9), bg="#1c233f", fg="#ffffff",
                                insertbackground="#00f0ff", relief="flat", bd=0, show="•")
        current_mongo = self.config.get("mongodb_uri", "")
        if current_mongo:
            mongo_entry.insert(0, current_mongo)
        mongo_entry.pack(fill="x", pady=4, ipady=3)
        tk.Label(mongo_frame, text="Paste your mongodb+srv://... URI. Nova stores memories and chat history in Atlas.",
                 font=("Segoe UI", 7), fg="#64748b", bg="#12172b", wraplength=350).pack(anchor="w")

        db_entry = tk.Entry(mongo_frame, font=("Segoe UI", 9), bg="#1c233f", fg="#ffffff",
                             insertbackground="#00f0ff", relief="flat", bd=0)
        db_entry.insert(0, self.config.get("mongodb_database", "nova"))
        db_entry.pack(fill="x", pady=(5, 2), ipady=2)

        # 3. Wake Word Toggle
        wake_var = tk.BooleanVar(value=self.config.get("wake_word_enabled", True))
        chk_wake = tk.Checkbutton(modal, text="🎙️ Hands-Free: Listen for 'Hello Nova'",
                                  variable=wake_var, font=("Segoe UI", 9),
                                  fg="#e2e8f0", bg="#12172b", selectcolor="#1c233f",
                                  activebackground="#12172b", activeforeground="#00f0ff")
        chk_wake.pack(anchor="w", padx=16, pady=4)

        # 3. Windows Auto-Start Toggle
        start_var = tk.BooleanVar(value=self.config.get("auto_start_with_windows", False))
        chk_start = tk.Checkbutton(modal, text="⚡ Auto-Start Nova when Laptop Turns On",
                                   variable=start_var, font=("Segoe UI", 9),
                                   fg="#e2e8f0", bg="#12172b", selectcolor="#1c233f",
                                   activebackground="#12172b", activeforeground="#00f0ff")
        chk_start.pack(anchor="w", padx=16, pady=4)

        # Status note
        status_lbl = tk.Label(modal, text="Tip: Gemini link enables infinite general knowledge!",
                              font=("Segoe UI", 8), fg="#94a3b8", bg="#12172b")
        status_lbl.pack(pady=6)

        # 4. Save Button
        def _save():
            new_key = key_entry.get().strip()
            self.config["gemini_api_key"] = new_key
            self.config["mongodb_uri"] = mongo_entry.get().strip()
            self.config["mongodb_database"] = db_entry.get().strip() or "nova"
            self.config["wake_word_enabled"] = wake_var.get()
            self.config["auto_start_with_windows"] = start_var.get()
            
            if self.on_settings_saved:
                self.on_settings_saved(self.config)
                
            modal.destroy()
            self.set_dialogue("Nova", "Settings updated! I am ready! (♥‿♥)")
            self.set_state("love")

        save_btn = tk.Button(modal, text="💾 Save & Activate", font=("Segoe UI", 10, "bold"),
                             bg="#00f0ff", fg="#050b14", relief="flat", bd=0, height=2,
                             activebackground="#66f7ff", activeforeground="#050b14",
                             command=_save)
        save_btn.pack(fill="x", padx=16, pady=10)

    def _toggle_topmost(self):
        self.is_topmost = not self.is_topmost
        self.root.attributes("-topmost", self.is_topmost)
        self.pin_btn.config(text="📌 Pinned" if self.is_topmost else "📍 Float")

    def _change_theme(self, theme_name: str):
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.colors = self.themes[theme_name]
            self.title_lbl.config(fg=self.colors["primary"])
            self.speaker_lbl.config(fg=self.colors["primary"])
            self.mic_btn.config(bg=self.colors["primary"])

    def _on_drag_start(self, event):
        # Allow dragging window from header or canvas
        if event.widget in (self.canvas, self.title_lbl, self.status_badge):
            self.drag_x = event.x
            self.drag_y = event.y

    def _on_drag(self, event):
        if event.widget in (self.canvas, self.title_lbl, self.status_badge):
            x = self.root.winfo_x() + (event.x - self.drag_x)
            y = self.root.winfo_y() + (event.y - self.drag_y)
            self.root.geometry(f"+{x}+{y}")

    def _on_mouse_move(self, event):
        # Eye pupil tracking coordinates
        self.mouse_x = event.x
        self.mouse_y = event.y

    def _on_entry_submit(self):
        text = self.entry_box.get().strip()
        if text:
            self.entry_box.delete(0, tk.END)
            self._submit_command(text)

    def _submit_command(self, command_text: str):
        self.set_dialogue("You", command_text)
        if self.on_command_submitted:
            # Run in worker thread to prevent blocking UI
            threading.Thread(target=self.on_command_submitted, args=(command_text,), daemon=True).start()

    def _trigger_mic(self):
        if self.on_mic_clicked:
            threading.Thread(target=self.on_mic_clicked, daemon=True).start()

    # ==========================
    # PUBLIC API FOR CONTROLLER
    # ==========================
    def set_dialogue(self, speaker: str, text: str):
        """Updates live dialogue bubble."""
        def _update():
            self.speaker_lbl.config(text=f"{speaker}:")
            self.dialogue_lbl.config(text=text)
        self.root.after(0, _update)

    def set_state(self, new_state: str):
        """Sets robot emotion/state: idle, listening, thinking, speaking, happy, love, dancing, sleepy"""
        def _update():
            self.state = new_state.lower()
            badges = {
                "idle": ("● READY", "#00ff88"),
                "listening": ("🎙️ LISTENING...", "#ffcc00"),
                "thinking": ("🧠 THINKING...", "#bf55ec"),
                "speaking": ("🗣️ SPEAKING...", "#00f0ff"),
                "happy": ("✨ HAPPY!", "#00ff88"),
                "love": ("💖 LOVE (♥‿♥)", "#ff3399"),
                "dancing": ("💃 DANCING 🎶", "#ff9900"),
                "sleepy": ("💤 SLEEPING...", "#64748b")
            }
            badge_text, badge_color = badges.get(self.state, ("● ACTIVE", "#00f0ff"))
            self.status_badge.config(text=badge_text, fg=badge_color)
            
            # Spawn burst of particles on love or dancing
            if self.state in ("love", "dancing", "happy"):
                for _ in range(12):
                    self._spawn_particle()
        self.root.after(0, _update)

    def pulse_mouth(self, amplitude: float):
        """Called by VoiceEngine during speech to animate mouth opening."""
        self.target_mouth_openness = min(1.0, max(0.1, amplitude))

    def _spawn_particle(self):
        """Adds floating heart/sparkle particle."""
        cx = self.canvas_width / 2 + random.uniform(-60, 60)
        cy = self.canvas_height / 2 + random.uniform(-30, 30)
        p_type = "heart" if self.state == "love" else "sparkle"
        self.particles.append({
            "x": cx, "y": cy,
            "vx": random.uniform(-1.5, 1.5),
            "vy": random.uniform(-2.5, -0.8),
            "life": 1.0,
            "type": p_type,
            "color": self.colors["blush"] if p_type == "heart" else self.colors["primary"]
        })

    # ==========================
    # 40 FPS ANIMATION ENGINE
    # ==========================
    def _animation_tick(self):
        if not self.is_running:
            return
            
        self.anim_t += 0.05
        now = time.time()
        
        # 1. Natural Blinking Logic
        if not self.is_blinking and now >= self.next_blink_time and self.state != "sleepy":
            self.is_blinking = True
            self.blink_progress = 0.0

        if self.is_blinking:
            self.blink_progress += 0.18
            if self.blink_progress >= 1.0:
                self.is_blinking = False
                self.blink_progress = 0.0
                self.next_blink_time = now + random.uniform(2.5, 5.0)

        # 2. Mouth smoothing interpolation
        self.mouth_openness += (self.target_mouth_openness - self.mouth_openness) * 0.35
        if self.state != "speaking":
            self.target_mouth_openness = 0.0

        # 3. Dancing head sway
        if self.state == "dancing":
            self.head_tilt = math.sin(self.anim_t * 2.5) * 8
        else:
            self.head_tilt += (0.0 - self.head_tilt) * 0.1

        # 4. Redraw Canvas Face
        self._render_robot_face()
        
        # Schedule next tick (~40 FPS)
        self.root.after(25, self._animation_tick)

    def _render_robot_face(self):
        self.canvas.delete("all")
        
        # Center of robot head
        cx = self.canvas_width / 2
        # Smooth floating bobbing animation
        float_y = math.sin(self.anim_t * 1.5) * 6
        cy = 135 + float_y + self.head_tilt
        
        primary = self.colors["primary"]
        secondary = self.colors["secondary"]
        blush_col = self.colors["blush"]
        visor_col = self.colors["visor"]

        # --- A. ANTENNA & GLOW ORB ---
        ant_top_x = cx + math.sin(self.anim_t * 2) * 3
        ant_top_y = cy - 102
        self.canvas.create_line(cx, cy - 70, ant_top_x, ant_top_y, fill="#2a3556", width=3)
        
        # Pulsing Antenna Crystal
        pulse_rad = 7 + math.sin(self.anim_t * 3.5) * 2.5
        ant_color = "#ffcc00" if self.state == "listening" else (
            "#bf55ec" if self.state == "thinking" else primary
        )
        self.canvas.create_oval(ant_top_x - pulse_rad, ant_top_y - pulse_rad,
                                ant_top_x + pulse_rad, ant_top_y + pulse_rad,
                                fill=ant_color, outline="#ffffff", width=1)

        # Soundwave rings when listening
        if self.state == "listening":
            wave_rad = 14 + (self.anim_t * 12) % 18
            self.canvas.create_oval(ant_top_x - wave_rad, ant_top_y - wave_rad,
                                    ant_top_x + wave_rad, ant_top_y + wave_rad,
                                    outline="#ffcc00", width=1.5)

        # --- B. ROBOT HEAD SHELL & EARS ---
        # Left & Right cute ear pods
        ear_w, ear_h = 16, 32
        self.canvas.create_oval(cx - 128, cy - ear_h/2, cx - 110, cy + ear_h/2,
                                fill="#1c233f", outline=primary, width=2)
        self.canvas.create_oval(cx + 110, cy - ear_h/2, cx + 128, cy + ear_h/2,
                                fill="#1c233f", outline=primary, width=2)

        # Main Outer Robot Helmet (Rounded Pill)
        self._draw_round_rect(cx - 120, cy - 75, cx + 120, cy + 75, radius=45,
                              fill="#161c32", outline="#29345e", width=2)

        # Inner Glowing Screen / Visor
        self._draw_round_rect(cx - 105, cy - 62, cx + 105, cy + 62, radius=36,
                              fill=visor_col, outline=primary, width=2)

        # --- C. CUTE BLUSH CHEEKS ---
        # Glow cheeks
        cheek_alpha_rad = 12 if self.state in ("love", "happy") else 8
        self.canvas.create_oval(cx - 75 - cheek_alpha_rad, cy + 22 - cheek_alpha_rad/2,
                                cx - 75 + cheek_alpha_rad, cy + 22 + cheek_alpha_rad/2,
                                fill=blush_col, outline="")
        self.canvas.create_oval(cx + 75 - cheek_alpha_rad, cy + 22 - cheek_alpha_rad/2,
                                cx + 75 + cheek_alpha_rad, cy + 22 + cheek_alpha_rad/2,
                                fill=blush_col, outline="")

        # --- D. EXPRESSIVE CYBER-EYES ---
        eye_spacing = 46
        eye_y = cy - 8
        
        # Calculate pupil shift towards cursor
        dx = (self.mouse_x - (cx - eye_spacing)) * 0.05
        dy = (self.mouse_y - eye_y) * 0.05
        dx = max(-7, min(7, dx))
        dy = max(-5, min(5, dy))

        if self.state == "sleepy":
            # Sleepy curved line eyes: ( - . - )
            self.canvas.create_arc(cx - eye_spacing - 20, eye_y - 8, cx - eye_spacing + 20, eye_y + 12,
                                  start=0, extent=180, style="arc", outline=primary, width=4)
            self.canvas.create_arc(cx + eye_spacing - 20, eye_y - 8, cx + eye_spacing + 20, eye_y + 12,
                                  start=0, extent=180, style="arc", outline=primary, width=4)
        elif self.state == "love":
            # Pulsing Neon Hearts Eyes! (♥‿♥)
            heart_scale = 1.0 + math.sin(self.anim_t * 5) * 0.12
            self._draw_heart(cx - eye_spacing, eye_y, size=18 * heart_scale, color=blush_col)
            self._draw_heart(cx + eye_spacing, eye_y, size=18 * heart_scale, color=blush_col)
        elif self.state == "thinking":
            # Scanning radar / rotating data eyes
            self._draw_thinking_eye(cx - eye_spacing, eye_y, primary)
            self._draw_thinking_eye(cx + eye_spacing, eye_y, primary)
        else:
            # Normal / Happy / Speaking eyes with smooth blink
            blink_h = (1.0 - math.sin(self.blink_progress * math.pi)) if self.is_blinking else 1.0
            
            # Left Eye
            self._draw_cyber_eye(cx - eye_spacing + dx, eye_y + dy, blink_h, primary)
            # Right Eye
            self._draw_cyber_eye(cx + eye_spacing + dx, eye_y + dy, blink_h, primary)

        # --- E. ANIMATED MOUTH ---
        mouth_y = cy + 30
        if self.state == "speaking":
            # Dynamic talking mouth
            open_h = 4 + self.mouth_openness * 16
            open_w = 16 + self.mouth_openness * 8
            self.canvas.create_oval(cx - open_w/2, mouth_y - open_h/2,
                                    cx + open_w/2, mouth_y + open_h/2,
                                    fill=primary, outline="#ffffff", width=1)
        elif self.state in ("happy", "love", "dancing"):
            # Big happy smile
            self.canvas.create_arc(cx - 18, mouth_y - 12, cx + 18, mouth_y + 10,
                                  start=190, extent=160, style="arc", outline=primary, width=3)
        elif self.state == "sleepy":
            # Small sleepy dot/line
            self.canvas.create_line(cx - 6, mouth_y, cx + 6, mouth_y, fill=primary, width=2)
        else:
            # Gentle pleasant smile
            self.canvas.create_arc(cx - 14, mouth_y - 8, cx + 14, mouth_y + 6,
                                  start=200, extent=140, style="arc", outline=primary, width=2.5)

        # --- F. PARTICLES (Hearts / Sparkles) ---
        self._update_and_draw_particles()

    def _draw_cyber_eye(self, x, y, blink_h, color):
        """Draws glowing rounded anime/cyber eye with highlights."""
        rx, ry = 18, max(1.5, 24 * blink_h)
        # Eye body
        self.canvas.create_oval(x - rx, y - ry, x + rx, y + ry, fill=color, outline="")
        
        # Cute white specular shine highlight
        if blink_h > 0.5:
            self.canvas.create_oval(x - rx*0.5, y - ry*0.65, x - rx*0.1, y - ry*0.25,
                                    fill="#ffffff", outline="")
            self.canvas.create_oval(x + rx*0.2, y + ry*0.1, x + rx*0.45, y + ry*0.35,
                                    fill="#ffffff", outline="")

    def _draw_thinking_eye(self, x, y, color):
        """Draws scanning techno eye."""
        r = 18
        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=color, width=2)
        angle = self.anim_t * 6
        x2 = x + math.cos(angle) * r
        y2 = y + math.sin(angle) * r
        self.canvas.create_line(x, y, x2, y2, fill=color, width=2)
        self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#ffffff", outline="")

    def _draw_heart(self, x, y, size=18, color="#ff4081"):
        """Draws a cute heart shape for love mode."""
        s = size / 2.0
        # Polygon points approximating heart
        pts = [
            x, y + s * 0.9,
            x - s * 1.0, y - s * 0.1,
            x - s * 0.9, y - s * 0.9,
            x - s * 0.3, y - s * 1.0,
            x, y - s * 0.4,
            x + s * 0.3, y - s * 1.0,
            x + s * 0.9, y - s * 0.9,
            x + s * 1.0, y - s * 0.1,
        ]
        self.canvas.create_polygon(pts, fill=color, outline="#ffffff", width=1, smooth=True)

    def _draw_round_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        """Draws anti-aliased styled rounded rectangle on Tkinter canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def _update_and_draw_particles(self):
        """Renders and animates active particles."""
        alive_particles = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 0.03
            
            if p["life"] > 0:
                alive_particles.append(p)
                if p["type"] == "heart":
                    self._draw_heart(p["x"], p["y"], size=10 * p["life"], color=p["color"])
                else:
                    sz = 4 * p["life"]
                    self.canvas.create_oval(p["x"]-sz, p["y"]-sz, p["x"]+sz, p["y"]+sz,
                                            fill=p["color"], outline="")
        self.particles = alive_particles

    def run(self):
        """Starts Tkinter main loop."""
        self.root.mainloop()

    def destroy(self):
        """Clean shutdown."""
        self.is_running = False
        try:
            self.root.destroy()
        except Exception:
            pass
