from pathlib import Path

activity = Path('app/src/main/java/com/winlator/XServerDisplayActivity.java')
s = activity.read_text(encoding='utf-8')

if 'import com.winlator.inputcontrols.ExternalKeyboardManager;' not in s:
    anchor = 'import com.winlator.inputcontrols.ExternalController;\n'
    if anchor not in s:
        raise SystemExit('ExternalController import anchor not found')
    s = s.replace(anchor, anchor + 'import com.winlator.inputcontrols.ExternalKeyboardManager;\n', 1)

if 'private ExternalKeyboardManager externalKeyboardManager;' not in s:
    anchor = '    private boolean capturePointerOnExternalMouse = true;\n'
    if anchor not in s:
        raise SystemExit('activity field anchor not found')
    s = s.replace(anchor, anchor + '    private ExternalKeyboardManager externalKeyboardManager;\n', 1)

if 'externalKeyboardManager = new ExternalKeyboardManager(this);' not in s:
    anchor = '        inputControlsManager = new InputControlsManager(this);\n'
    if anchor not in s:
        raise SystemExit('inputControlsManager init anchor not found')
    s = s.replace(anchor, '        externalKeyboardManager = new ExternalKeyboardManager(this);\n' + anchor, 1)

if 'externalKeyboardManager.close();' not in s:
    anchor = '        winHandler.stop();\n'
    if anchor not in s:
        raise SystemExit('onDestroy stop anchor not found')
    s = s.replace(anchor, '        if (externalKeyboardManager != null) externalKeyboardManager.close();\n' + anchor, 1)

# Physical keyboards must never enter InputControlsView's key-binding/capture flow.
old = '''    public boolean dispatchKeyEvent(KeyEvent event) {
        // Physical USB/Bluetooth keyboards are native input devices. Never send their keys
        // through the touchscreen/gamepad binding layer. Consume the event here even when
        // Wine does not recognize a particular Android key code, so InputControlsView can
        // never fall back into key-assignment/capture mode.
        if (ExternalKeyboardManager.isExternalKeyboard(event)) {
            xServer.keyboard.onKeyEvent(event);
            return true;
        }

        return (!inputControlsView.onKeyEvent(event) && !winHandler.onKeyEvent(event) && xServer.keyboard.onKeyEvent(event)) ||
               (!ExternalController.isGameController(event.getDevice()) && super.dispatchKeyEvent(event));
    }'''
new = '''    public boolean dispatchKeyEvent(KeyEvent event) {
        if (ExternalKeyboardManager.isExternalKeyboard(event)) {
            // Always consume physical USB/Bluetooth keyboard events here. They bypass
            // InputControlsView entirely, so no key-assignment UI can be triggered.
            xServer.keyboard.onKeyEvent(event);
            return true;
        }

        return (!inputControlsView.onKeyEvent(event) && !winHandler.onKeyEvent(event) && xServer.keyboard.onKeyEvent(event)) ||
               (!ExternalController.isGameController(event.getDevice()) && super.dispatchKeyEvent(event));
    }'''
if old not in s:
    raise SystemExit('dispatchKeyEvent block not found')
s = s.replace(old, new, 1)
activity.write_text(s, encoding='utf-8')

keyboard = Path('app/src/main/java/com/winlator/xserver/Keyboard.java')
s = keyboard.read_text(encoding='utf-8')

# The upstream table has 159 entries, while Android can report larger HID keycodes.
# Enlarge it and safely handle all Android keycodes without ever returning control to
# InputControlsView. Existing XKeycode mappings are preserved.
s = s.replace('XKeycode[] keycodeMap = new XKeycode[159];', 'XKeycode[] keycodeMap = new XKeycode[512];', 1)

old = '''            int keyCode = event.getKeyCode();
            XKeycode xKeycode = keycodeMap[keyCode];
            if (xKeycode == null) return false;

            if (action == KeyEvent.ACTION_DOWN) {'''
new = '''            int keyCode = event.getKeyCode();
            XKeycode xKeycode = keyCode >= 0 && keyCode < keycodeMap.length ? keycodeMap[keyCode] : null;

            // For a physical keyboard, preserve printable Unicode characters even when
            // Android reports a keycode that is not present in Winlator's legacy table.
            // getCustomXKeycodeForKeysym() provides a real X11 key slot for the character.
            if (xKeycode == null && event.getDevice() != null &&
                    event.getDevice().getKeyboardType() != android.view.InputDevice.KEYBOARD_TYPE_NONE) {
                int unicode = event.getUnicodeChar();
                if (unicode != 0 && (action == KeyEvent.ACTION_DOWN || action == KeyEvent.ACTION_UP)) {
                    xKeycode = getCustomXKeycodeForKeysym(unicode);
                }
            }
            if (xKeycode == null) return false;

            if (action == KeyEvent.ACTION_DOWN) {'''
if old not in s:
    raise SystemExit('keyboard dispatch block not found')
s = s.replace(old, new, 1)

keyboard.write_text(s, encoding='utf-8')
print('Physical USB/Bluetooth keyboard path fixed: all reported keycodes are consumed, legacy table expanded, printable unmapped HID keys use dynamic X11 key slots, and key-assignment fallback is disabled.')
