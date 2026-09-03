from pathlib import Path
import re

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

method_pattern = re.compile(
    r'    @Override\n'
    r'    public boolean dispatchKeyEvent\(KeyEvent event\) \{.*?\n'
    r'    \}',
    re.DOTALL,
)
method_match = method_pattern.search(s)
if not method_match:
    raise SystemExit('dispatchKeyEvent method not found')

new_method = '''    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        // Physical USB/Bluetooth keyboards are a global input device for the
        // whole Wine/XServer desktop. They must never be routed through the
        // touch/key-assignment overlay. Forward the event directly to XServer.
        if (ExternalKeyboardManager.isExternalKeyboard(event)) {
            return xServer.keyboard.onKeyEvent(event);
        }

        return (!inputControlsView.onKeyEvent(event) && !winHandler.onKeyEvent(event) && xServer.keyboard.onKeyEvent(event)) ||
               (!ExternalController.isGameController(event.getDevice()) && super.dispatchKeyEvent(event));
    }'''
s = s[:method_match.start()] + new_method + s[method_match.end():]
activity.write_text(s, encoding='utf-8')

keyboard = Path('app/src/main/java/com/winlator/xserver/Keyboard.java')
s = keyboard.read_text(encoding='utf-8')

s = s.replace('XKeycode[] keycodeMap = new XKeycode[159];', 'XKeycode[] keycodeMap = new XKeycode[512];', 1)

old = '''            int keyCode = event.getKeyCode();
            XKeycode xKeycode = keyCode >= 0 && keyCode < keycodeMap.length ? keycodeMap[keyCode] : null;

            // Preserve printable Unicode characters from physical keyboards even when
            // Android reports a HID/layout keycode that is absent from the legacy table.
            if (xKeycode == null && event.getDevice() != null &&
                    event.getDevice().getKeyboardType() != android.view.InputDevice.KEYBOARD_TYPE_NONE) {
                int unicode = event.getUnicodeChar();
                if (unicode != 0 && (action == KeyEvent.ACTION_DOWN || action == KeyEvent.ACTION_UP)) {
                    xKeycode = getCustomXKeycodeForKeysym(unicode);
                }
            }
            if (xKeycode == null) return false;
'''
new = '''            int keyCode = event.getKeyCode();
            XKeycode xKeycode = keyCode >= 0 && keyCode < keycodeMap.length ? keycodeMap[keyCode] : null;

            // Physical HID keyboards can report KEYBOARD_TYPE_NONE on Android.
            // Do not use keyboard type as a gate: the device was already proven
            // physical by XServerDisplayActivity. For any unmapped printable key,
            // allocate an X11 custom keysym slot so layouts such as Turkish Q/F,
            // accented characters and OEM/HID keys can still reach Wine.
            if (xKeycode == null && event.getDevice() != null &&
                    !event.getDevice().isVirtual()) {
                int unicode = event.getUnicodeChar();
                if (unicode != 0 && (action == KeyEvent.ACTION_DOWN || action == KeyEvent.ACTION_UP)) {
                    xKeycode = getCustomXKeycodeForKeysym(unicode);
                }
            }
            if (xKeycode == null) return false;
'''
if old not in s:
    raise SystemExit('keyboard dispatch block not found')
s = s.replace(old, new, 1)
keyboard.write_text(s, encoding='utf-8')

manager = Path('patches/ExternalKeyboardManager.java')
s = manager.read_text(encoding='utf-8')
old = '''        int sources = device.getSources();
        // Real USB and Bluetooth keyboards normally expose SOURCE_KEYBOARD.
        // Do not reject KEYBOARD_TYPE_NONE: several Android HID drivers use it.
        return (sources & InputDevice.SOURCE_KEYBOARD) == InputDevice.SOURCE_KEYBOARD;
'''
new = '''        int sources = device.getSources();
        // Android HID implementations are inconsistent: some expose SOURCE_KEYBOARD,
        // while others expose a keyboard type but omit the source bit. Accept either
        // physical-device signal. Virtual IMEs/devices were already rejected above.
        return (sources & InputDevice.SOURCE_KEYBOARD) == InputDevice.SOURCE_KEYBOARD ||
               device.getKeyboardType() != InputDevice.KEYBOARD_TYPE_NONE;
'''
if old not in s:
    raise SystemExit('keyboard detection block not found')
s = s.replace(old, new, 1)
manager.write_text(s, encoding='utf-8')

print('Global physical keyboard bridge hardened: physical HID detection accepts source OR keyboard type, keyboard events bypass key-assignment globally, extended keycodes are safe, and unmapped physical printable keys use X11 custom keysyms.')
