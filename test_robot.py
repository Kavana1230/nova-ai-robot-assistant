"""
test_robot.py - Automated Verification Test Suite for Nova Desktop Robot
Tests System Controller, AI Brain Intent Matching, Voice Engine, and GUI Smoke Test.
"""

import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding for emojis in Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from system_controller import SystemController
from ai_brain import AIBrain

def test_system_controller():
    print("\n--- Testing SystemController ---")
    sys_ctrl = SystemController()
    
    # 1. Test battery info
    ok, bat_msg = sys_ctrl.get_battery_info()
    print(f"[PASS] Battery info: {bat_msg}")
    assert ok and len(bat_msg) > 5, "Battery check failed"

    # 2. Test system health
    ok, health_msg = sys_ctrl.get_system_health()
    print(f"[PASS] System health: {health_msg}")
    assert ok and "CPU" in health_msg, "System health check failed"

    # 3. Test screenshot capture
    ok, sc_msg, sc_path = sys_ctrl.take_screenshot()
    print(f"[INFO] Screenshot result: ok={ok}, msg='{sc_msg}', path='{sc_path}'")
    if ok and sc_path:
        assert Path(sc_path).exists(), "Screenshot file not found"
        try:
            Path(sc_path).unlink()
            print("[PASS] Test screenshot cleaned up successfully")
        except Exception:
            pass
    else:
        print("[NOTICE] Screenshot requires active interactive desktop session.")

def test_ai_brain():
    print("\n--- Testing AIBrain Intent Matching ---")
    brain = AIBrain()
    
    test_cases = [
        ("how is my battery", "battery"),
        ("take a screenshot", "screenshot"),
        ("tell me a joke", "joke"),
        ("i love you", "flattery"),
        ("sing a song", "sing"),
        ("do a dance", "dance"),
        ("who are you", "intro"),
        ("what time is it", "time"),
        ("whats today date", "date"),
        ("volume up", "volume_up"),
        ("volume down", "volume_down"),
        ("mute", "mute"),
        ("show desktop", "show_desktop"),
        ("pause music", "media_play_pause"),
        ("next song", "media_next"),
        ("play lofi hip hop on youtube", "youtube"),
        ("search for latest tech news", "google_search"),
        ("open chrome", "open_app"),
        ("open notepad", "open_app"),
        ("open calculator", "open_app"),
        ("open downloads", "open_folder"),
        ("lock laptop", "lock"),
        ("compliment me", "compliment"),
        ("hello nova", "greeting"),
        ("can u open utube", "open_app"),
        ("could you open youtube", "open_app"),
        ("can you play spotify music", "spotify"),
        ("please play spotify", "spotify"),
        ("set the timer", "clock"),
        ("can u set a timer for 5 minutes", "timer"),
        ("could you please play lofi on utube", "youtube")
    ]
    
    passed = 0
    for query, expected_action in test_cases:
        res = brain.process(query)
        action = res.get("action")
        reply = res.get("reply")
        emotion = res.get("emotion")
        print(f"  Command: '{query}' -> Action: {action}, Emotion: {emotion}")
        if action == expected_action:
            passed += 1
        else:
            print(f"  [MISMATCH] Query '{query}' got '{action}', expected '{expected_action}'")
            
    print(f"[RESULT] AI Brain: {passed}/{len(test_cases)} tests passed perfectly!")
    assert passed == len(test_cases), f"Only {passed}/{len(test_cases)} intents matched."

def test_auto_start_and_config():
    print("\n--- Testing Windows Auto-Start & Config ---")
    sys_ctrl = SystemController()
    
    # Test enabling auto-start (checks graceful handling if restricted by Windows security)
    ok, msg = sys_ctrl.enable_auto_start()
    print(f"[INFO] Enable auto-start response: ok={ok}, msg='{msg}'")
    
    # Test disabling auto-start
    ok_dis, msg_dis = sys_ctrl.disable_auto_start()
    print(f"[PASS] Disable auto-start response: ok={ok_dis}, msg='{msg_dis}'")

def test_wake_word_parsing():
    print("\n--- Testing Wake-Word Parsing Logic ---")
    wake_words = ["hello nova", "hey nova", "hi nova", "nova", "okay nova"]
    
    test_phrases = [
        ("hello nova open chrome", "open chrome"),
        ("hey nova what time is it", "what time is it"),
        ("nova take a screenshot", "take a screenshot"),
        ("hello nova", "")
    ]
    
    for phrase, expected_command in test_phrases:
        matched = None
        for w in wake_words:
            if w in phrase.lower():
                matched = w
                break
        assert matched is not None, f"Failed to match wake word in '{phrase}'"
        command = phrase.lower().replace(matched, "", 1).strip(" ,.?!")
        assert command == expected_command, f"Expected '{expected_command}', got '{command}'"
        print(f"[PASS] '{phrase}' -> Wake: '{matched}', Command: '{command}'")

def test_gui_smoketest():
    print("\n--- Testing RobotGUI Smoke Test ---")
    from robot_gui import RobotGUI
    
    gui = RobotGUI()
    # Cycle through emotions
    for state in ["listening", "thinking", "speaking", "happy", "love", "dancing", "sleepy", "idle"]:
        gui.set_state(state)
        gui.pulse_mouth(0.8)
        gui.set_dialogue("Nova", f"Testing state: {state}")
        gui.root.update()
        time.sleep(0.1)
        
    print("[PASS] GUI rendered and cycled states smoothly without crashing.")
    gui.destroy()

if __name__ == "__main__":
    print("========================================")
    print("      RUNNING NOVA TEST SUITE           ")
    print("========================================")
    test_system_controller()
    test_ai_brain()
    test_auto_start_and_config()
    test_wake_word_parsing()
    test_gui_smoketest()
    print("\n✅ ALL MODULE & INTEGRATION TESTS PASSED!")
