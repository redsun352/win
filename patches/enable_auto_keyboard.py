from pathlib import Path
import re

activity = Path('app/src/main/java/com/winlator/XServerDisplayActivity.java')
s = activity.read_text(encoding='utf-8')

if 'import com.winlator.inputcontrols.ExternalKeyboardManager;' not in s:
    anchor = 'import com.winlator.inputcontrols.ExternalController;\n'
    if anchor not in s: raise SystemExit('ExternalController import anchor not found')
    s = s.replace(anchor, anchor + 'import com.winlator.inputcontrols.ExternalKeyboardManager;\n', 1)
if 'private ExternalKeyboardManager externalKeyboardManager;' not in s:
    anchor = '    private boolean capturePointerOnExternalMouse = true;\n'
    if anchor not in s: raise SystemExit('activity field anchor not found')
    s = s.replace(anchor, anchor + '    private ExternalKeyboardManager externalKeyboardManager;\n', 1)
if 'externalKeyboardManager = new ExternalKeyboardManager(this);' not in s:
    anchor = '        inputControlsManager = new InputControlsManager(this);\n'
    if anchor not in s: raise SystemExit('inputControlsManager init anchor not found')
    s = s.replace(anchor, '        externalKeyboardManager = new ExternalKeyboardManager(this);\n' + anchor, 1)
if 'externalKeyboardManager.close();' not in s:
    anchor = '        winHandler.stop();\n'
    if anchor not in s: raise SystemExit('onDestroy stop anchor not found')
    s = s.replace(anchor, '        if (externalKeyboardManager != null) externalKeyboardManager.close();\n' + anchor, 1)

method_pattern = re.compile(r'    @Override\n    public boolean dispatchKeyEvent\(KeyEvent event\) \{.*?\n    \}', re.DOTALL)
m = method_pattern.search(s)
if not m: raise SystemExit('dispatchKeyEvent method not found')
new_method = '''    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        // Physical USB/Bluetooth keyboard events are global: bypass the touch
        // controls/key-assignment layer and send them directly to XServer/Wine.
        if (ExternalKeyboardManager.isExternalKeyboard(event)) {
            return xServer.keyboard.onKeyEvent(event);
        }
        return (!inputControlsView.onKeyEvent(event) && !winHandler.onKeyEvent(event) && xServer.keyboard.onKeyEvent(event)) ||
               (!ExternalController.isGameController(event.getDevice()) && super.dispatchKeyEvent(event));
    }'''
s = s[:m.start()] + new_method + s[m.end():]
activity.write_text(s, encoding='utf-8')

keyboard = Path('app/src/main/java/com/winlator/xserver/Keyboard.java')
s = keyboard.read_text(encoding='utf-8')
s, n = re.subn(r'XKeycode\[\] keycodeMap = new XKeycode\[\d+\];', 'XKeycode[] keycodeMap = new XKeycode[512];', s, count=1)
if n != 1: raise SystemExit('keycode map declaration not found')

# Make Android keycode lookup bounds-safe and support printable physical HID keys
# regardless of Android's reported keyboard type.
lookup = re.compile(r'            int keyCode = event\.getKeyCode\(\);\n            XKeycode xKeycode = keycodeMap\[keyCode\];\n            if \(xKeycode == null\) return false;')
replacement = '''            int keyCode = event.getKeyCode();
            XKeycode xKeycode = (keyCode >= 0 && keyCode < keycodeMap.length) ? keycodeMap[keyCode] : null;
            if (xKeycode == null && event.getDevice() != null && !event.getDevice().isVirtual()) {
                int unicode = event.getUnicodeChar();
                if (unicode != 0) xKeycode = getCustomXKeycodeForKeysym(unicode);
            }
            if (xKeycode == null) return false;'''
s, n = lookup.subn(replacement, s, count=1)
if n != 1: raise SystemExit('keyboard lookup block not found')
keyboard.write_text(s, encoding='utf-8')

print('Winlator 11.1 global physical keyboard patch applied successfully')