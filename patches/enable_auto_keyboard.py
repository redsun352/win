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
        // Physical USB/Bluetooth HID keyboards are global: bypass touch
        // controls/key-assignment and forward directly to XServer/Wine.
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

if 'import com.winlator.inputcontrols.ExternalKeyboardManager;' not in s:
    anchor = 'import com.winlator.inputcontrols.ExternalController;\n'
    if anchor not in s: raise SystemExit('Keyboard ExternalController import anchor not found')
    s = s.replace(anchor, anchor + 'import com.winlator.inputcontrols.ExternalKeyboardManager;\n', 1)

# Do not let the generic gamepad filter swallow a Bluetooth HID keyboard that
# Android exposes as GAMEPAD/JOYSTICK. Keyboard classification has priority.
s = s.replace(
    'if (ExternalController.isGameController(event.getDevice())) return false;',
    'if (ExternalController.isGameController(event.getDevice()) && !ExternalKeyboardManager.isExternalKeyboard(event)) return false;',
    1
)

s, n = re.subn(r'XKeycode\[\] keycodeMap = new XKeycode\[\d+\];', 'XKeycode[] keycodeMap = new XKeycode[512];', s, count=1)
if n != 1: raise SystemExit('keycode map declaration not found')

if 'private final java.util.HashMap<Integer, XKeycode> externalKeyMap' not in s:
    anchor = '    private final XServer xServer;\n'
    if anchor not in s: raise SystemExit('xServer field anchor not found')
    s = s.replace(anchor, anchor + '    private final java.util.HashMap<Integer, XKeycode> externalKeyMap = new java.util.HashMap<>();\n', 1)

lookup = re.compile(r'            int keyCode = event\.getKeyCode\(\);\n            XKeycode xKeycode = .*?\n            if \(xKeycode == null\) return false;', re.DOTALL)
replacement = '''            int keyCode = event.getKeyCode();
            int physicalKeyId = ((event.getDeviceId() & 0xFFFF) << 16) ^ (event.getScanCode() & 0xFFFF);
            XKeycode xKeycode = (keyCode >= 0 && keyCode < keycodeMap.length) ? keycodeMap[keyCode] : null;

            // Bluetooth HID keyboards on some Android builds expose valid
            // physical events but report KEYCODE_UNKNOWN or a keycode that is
            // absent from Winlator's table. Recover printable keys from the
            // Unicode character and remember the allocated X key for ACTION_UP.
            if (xKeycode == null && event.getDevice() != null && !event.getDevice().isVirtual()) {
                if (action == KeyEvent.ACTION_DOWN) {
                    int unicode = event.getUnicodeChar();
                    if (unicode != 0) {
                        xKeycode = getCustomXKeycodeForKeysym(unicode);
                        externalKeyMap.put(physicalKeyId, xKeycode);
                    }
                }
                else if (action == KeyEvent.ACTION_UP) {
                    xKeycode = externalKeyMap.remove(physicalKeyId);
                }
            }
            if (xKeycode == null) return false;'''
s, n = lookup.subn(replacement, s, count=1)
if n != 1: raise SystemExit('keyboard lookup block not found')
keyboard.write_text(s, encoding='utf-8')

print('Bluetooth HID keyboard routing + XInput priority patch applied successfully')