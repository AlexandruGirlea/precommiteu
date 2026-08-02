# Regenerate the README scan demo:
#   vhs docs/demo.tape
#
# Expects `precommiteu` and `llama-server` on PATH and $PRECOMMITEU_MODELS_DIR
# pointing at a bundle containing base.gguf and gdpr/detector-adapter.gguf.
#
# The scan below is real and unedited. PlaybackSpeed compresses the wall-clock
# wait; TypingSpeed and Sleep are pre-multiplied to stay legible after it.

Output docs/assets/img/scan-demo.gif

Set Shell bash
# Menlo has no ligatures: "--regulations" must not render as an em dash.
Set FontFamily "Menlo"
Set FontSize 16
Set Width 1240
Set Height 500
Set Padding 22
Set Framerate 12
Set PlaybackSpeed 5
Set TypingSpeed 250ms
Set WaitTimeout 10m
Set Theme "Catppuccin Mocha"

Hide
Type "rm -rf /tmp/shopmate && mkdir -p /tmp/shopmate/app" Enter
Type "cp tests/fixtures/risky_code/models.py tests/fixtures/risky_code/user_store.py /tmp/shopmate/app/" Enter
Type "cd /tmp/shopmate" Enter
Type "export PS1='❯ '" Enter
Type "clear" Enter
Show

Sleep 4s
Type "precommiteu scan app --regulations gdpr"
Sleep 3s
Enter
Wait+Screen@10m /Findings:/
Sleep 20s
