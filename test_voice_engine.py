"""Static smoke tests for Nova's single-stream VoiceEngine design."""

from voice_engine import VoiceEngine


def main():
    assert VoiceEngine._extract_command("Hello Nova") == ""
    assert VoiceEngine._extract_command("Hello Nova, open Chrome") == "open chrome"
    assert VoiceEngine._extract_command("hello nova what time is it") == "what time is it"
    assert VoiceEngine._extract_command("Hey Nova, open Chrome") is None
    assert VoiceEngine._extract_command("Someone said hello nova yesterday") is None
    print("VoiceEngine wake-word extraction tests passed.")


if __name__ == "__main__":
    main()
