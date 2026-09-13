# ⚡ Nova - AI Desktop Robot Companion

Nova is an interactive, cute, voice-controlled AI desktop robot companion built for Windows. She lives in your laptop, responds to voice and text commands like Siri, displays animated expressions with lively cyber-eyes and cute reactions, and automates your entire laptop.

---

## ✨ Key Features

1. **Hands-Free "Hello Nova" Wake-Word**:
   - **Continuous Listening**: Nova continuously listens in the background. Just say:
     - *"Hello Nova, open chrome"*
     - *"Hey Nova, what time is it?"*
     - *"Hello Nova"* (She wakes up and responds: *"Yes! I'm listening!"*)
   - **Automatic Windows Startup**: Optional one-click setting to have Nova start automatically whenever your laptop powers on.

2. **Google Gemini AI API Integration**:
   - Link your **Google Gemini API Key** right inside the app via the **`⚙️ API / Setup`** button.
   - When linked, Nova has **infinite intelligence**: answers complex questions, writes notes, explains concepts, and translates natural conversational requests into laptop actions!
   - Works 100% locally out-of-the-box even without an API key.

3. **Cute Animated Robot Avatar**:
   - Floating, draggable desktop companion window with "Always on Top" pin.
   - Real-time animated vector face (smooth 40 FPS):
     - Expressive cyber-eyes with natural blinking and cursor tracking.
     - Blushing glowing cheeks `(✿◡‿◡)`.
     - Reactive animated mouth synced with spoken audio.
     - Pulsing antenna with soundwave ripples when listening.
     - Emotional states: **Idle**, **Listening**, **Thinking**, **Speaking**, **Happy**, **Heart-Eyes (Love)** `(♥‿♥)`, **Dancing**, and **Sleepy**.
     - Particle effects: Floating hearts and sparkles.
     - 5 Color Themes: Cyber Cyan, Neon Pink, Emerald Green, Golden Solar, and Electric Purple.

4. **Voice Interaction (Siri-like)**:
   - **Voice Input (STT)**: Microphone listening with ambient noise suppression. Speak hands-free or click the glowing button / press **Spacebar**.
   - **Natural Neural Voice (TTS)**: Ultra-smooth speech powered by Edge-TTS (with automatic offline fallback to Windows native SAPI5 voices).
   - **Silent Text Mode**: Type commands in the bottom entry bar anytime.

5. **Complete Laptop Control & Automation**:
   - **Launch Apps**: *"open chrome"*, *"open notepad"*, *"open calculator"*, *"open vs code"*, *"open spotify"*, *"open task manager"*.
   - **Control Audio & Media**: *"volume up"*, *"volume down"*, *"mute"*, *"pause music"*, *"next song"*.
   - **Screen & Display**: *"take a screenshot"* (saved automatically to Pictures), *"show desktop"*, *"minimize all"*, *"lock laptop"*, *"sleep laptop"*.
   - **Camera & Selfies**: *"take a selfie"* or *"look at me"* (uses webcam to snap a photo).
   - **System Health Diagnostics**: *"how is my battery?"*, *"system performance"*, *"cpu usage"*, *"ram usage"*.
   - **Web & Entertainment**: *"play lofi on youtube"*, *"search google for [query]"*, *"open reddit"*, *"open github"*.
   - **File Explorer**: *"open downloads"*, *"open documents"*, *"open pictures"*, *"open c drive"*.
   - **Keyboard Typing**: *"type hello world"*, *"press enter"*.
   - **Cute Small Talk & Fun**: *"tell me a joke"*, *"sing a song"*, *"do a dance"*, *"i love you"*, *"give me a compliment"*.

---

## 🚀 How to Run

### Method 1: Double-Click
Double-click `run_robot.bat`.

### Method 2: Command Line
```powershell
cd C:\Users\LENOVO\.gemini\antigravity\scratch\desktop-robot
python main.py
```

---

## 🎙️ Sample Voice Commands to Try
| Category | Example Command | What Nova Does |
| :--- | :--- | :--- |
| **Apps** | *"open chrome"* / *"open calculator"* | Launches the application instantly |
| **Music** | *"play sunflower on youtube"* | Opens YouTube and plays the track |
| **System** | *"how is my battery?"* | Speaks your battery % and charging status |
| **Audio** | *"volume up"* / *"mute"* | Adjusts or mutes Windows sound |
| **Capture** | *"take a screenshot"* | Captures full screen & saves to Pictures with heart-eyes! |
| **Display** | *"show desktop"* | Minimizes all windows (Win + D) |
| **Fun** | *"tell me a joke"* / *"sing a song"* | Tells a funny joke or robot rhyme |
| **Cute** | *"i love you"* / *"you are so cute"* | Eyes turn into pulsing pink hearts `(♥‿♥)` |
| **Security** | *"lock laptop"* | Locks Windows workstation |

## Persistent Memory & Conversation History (MongoDB Atlas)

Nova uses **MongoDB Atlas** for persistent long-term memories and conversation history. The data survives closing/restarting Nova.

### Configure Atlas
1. Create a MongoDB Atlas cluster and database user.
2. Add your computer's IP address under Atlas Network Access.
3. Copy the `mongodb+srv://...` connection string.
4. Open Nova's **⚙️ API / Setup** window and paste the connection string into **MongoDB Atlas Connection String**.
5. Keep the database name as `nova` (or choose another database name) and click **Save & Activate**.

You can also set the `MONGODB_URI` environment variable instead of putting credentials in `config.json`.

### What Nova stores
- **Explicit memories:** `Hello Nova, remember this: my robot uses ESP32`
- **Important project details:** Nova conservatively saves clear project/technology facts.
- **Conversation history:** recent user and Nova messages are persisted and loaded after restart so Nova can continue context.

### Memory controls
- Open **🧠 Memory** to view saved long-term memories.
- Select a memory and click **🗑️ Forget Selected** to remove it from Atlas.
- Click **🧹 Forget All** to remove all long-term memories.
- Voice/text commands also support `forget ...` and `forget everything`.

Conversation history is separate from long-term memory, so forgetting a memory does not erase the conversation archive.

### Security
Do not commit a real Atlas connection string or Gemini API key to GitHub. Prefer environment variables for production use.
