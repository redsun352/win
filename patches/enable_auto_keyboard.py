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
        raise SystemExit('onDestroy/exit stop anchor not found')
    s = s.replace(anchor, '        if (externalKeyboardManager != null) externalKeyboardManager.close();\n' + anchor, 1)

old = '''    public boolean dispatchKeyEvent(KeyEvent event) {
        return (!inputControlsView.onKeyEvent(event) && !winHandler.onKeyEvent(event) && xServer.keyboard.onKeyEvent(event)) ||
               (!ExternalController.isGameController(event.getDevice()) && super.dispatchKeyEvent(event));
    }'''
new = '''    public boolean dispatchKeyEvent(KeyEvent event) {
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
if old not in s:
    raise SystemExit('dispatchKeyEvent block not found; source may have changed')
s = s.replace(old, new, 1)
activity.write_text(s, encoding='utf-8')

keyboard = Path('app/src/main/java/com/winlator/xserver/Keyboard.java')
s = keyboard.read_text(encoding='utf-8')
old = '''            int keyCode = event.getKeyCode();
            XKeycode xKeycode = keycodeMap[keyCode];
            if (xKeycode == null) return false;'''
new = '''            int keyCode = event.getKeyCode();
            // Android has key codes outside the compact table used by Winlator.
            // Ignore unknown codes safely instead of indexing past the table.
            XKeycode xKeycode = keyCode >= 0 && keyCode < keycodeMap.length ? keycodeMap[keyCode] : null;
            if (xKeycode == null) return false;'''
if old in s:
    s = s.replace(old, new, 1)
keyboard.write_text(s, encoding='utf-8')

print('Automatic USB/Bluetooth keyboard support applied: physical keyboard events are always consumed by the native keyboard path; no key assignment fallback.')
