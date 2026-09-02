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
        // Any real HID keyboard is handled exclusively by the native keyboard path.
        // Never let physical keyboard events reach InputControlsView/key-assignment logic.
        if (ExternalKeyboardManager.isExternalKeyboard(event)) {
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

# Expand physical keyboard coverage by translating Android keycodes directly to
# X11 keysyms for the keys that are commonly absent from the compact Winlator map.
# The generated helper is used before the legacy table, so unmapped HID keys do not
# fall into the input-controls assignment path.
helper = '''\n    private XKeycode getPhysicalXKeycode(KeyEvent event) {\n        int keyCode = event.getKeyCode();\n        int keysym = 0;\n        switch (keyCode) {\n            case KeyEvent.KEYCODE_ESCAPE: keysym = 0xff1b; break;\n            case KeyEvent.KEYCODE_TAB: keysym = 0xff09; break;\n            case KeyEvent.KEYCODE_ENTER: keysym = 0xff0d; break;\n            case KeyEvent.KEYCODE_DEL: keysym = 0xff08; break;\n            case KeyEvent.KEYCODE_FORWARD_DEL: keysym = 0xffff; break;\n            case KeyEvent.KEYCODE_MOVE_HOME: keysym = 0xff50; break;\n            case KeyEvent.KEYCODE_MOVE_END: keysym = 0xff57; break;\n            case KeyEvent.KEYCODE_PAGE_UP: keysym = 0xff55; break;\n            case KeyEvent.KEYCODE_PAGE_DOWN: keysym = 0xff56; break;\n            case KeyEvent.KEYCODE_INSERT: keysym = 0xff63; break;\n            case KeyEvent.KEYCODE_DPAD_UP: keysym = 0xff52; break;\n            case KeyEvent.KEYCODE_DPAD_DOWN: keysym = 0xff54; break;\n            case KeyEvent.KEYCODE_DPAD_LEFT: keysym = 0xff51; break;\n            case KeyEvent.KEYCODE_DPAD_RIGHT: keysym = 0xff53; break;\n            case KeyEvent.KEYCODE_SHIFT_LEFT: keysym = 0xffe1; break;\n            case KeyEvent.KEYCODE_SHIFT_RIGHT: keysym = 0xffe2; break;\n            case KeyEvent.KEYCODE_CTRL_LEFT: keysym = 0xffe3; break;\n            case KeyEvent.KEYCODE_CTRL_RIGHT: keysym = 0xffe4; break;\n            case KeyEvent.KEYCODE_ALT_LEFT: keysym = 0xffe9; break;\n            case KeyEvent.KEYCODE_ALT_RIGHT: keysym = 0xffea; break;\n            case KeyEvent.KEYCODE_META_LEFT: keysym = 0xffeb; break;\n            case KeyEvent.KEYCODE_META_RIGHT: keysym = 0xffec; break;\n            case KeyEvent.KEYCODE_CAPS_LOCK: keysym = 0xffe5; break;\n            case KeyEvent.KEYCODE_NUM_LOCK: keysym = 0xff7f; break;\n            case KeyEvent.KEYCODE_SCROLL_LOCK: keysym = 0xff14; break;\n            case KeyEvent.KEYCODE_PRINT_SCREEN: keysym = 0xff61; break;\n            case KeyEvent.KEYCODE_BREAK: keysym = 0xff13; break;\n            case KeyEvent.KEYCODE_F1: keysym = 0xffbe; break;\n            case KeyEvent.KEYCODE_F2: keysym = 0xffbf; break;\n            case KeyEvent.KEYCODE_F3: keysym = 0xffc0; break;\n            case KeyEvent.KEYCODE_F4: keysym = 0xffc1; break;\n            case KeyEvent.KEYCODE_F5: keysym = 0xffc2; break;\n            case KeyEvent.KEYCODE_F6: keysym = 0xffc3; break;\n            case KeyEvent.KEYCODE_F7: keysym = 0xffc4; break;\n            case KeyEvent.KEYCODE_F8: keysym = 0xffc5; break;\n            case KeyEvent.KEYCODE_F9: keysym = 0xffc6; break;\n            case KeyEvent.KEYCODE_F10: keysym = 0xffc7; break;\n            case KeyEvent.KEYCODE_F11: keysym = 0xffc8; break;\n            case KeyEvent.KEYCODE_F12: keysym = 0xffc9; break;\n            case KeyEvent.KEYCODE_SPACE: keysym = 0x20; break;\n            default: break;\n        }\n        if (keysym == 0) return null;\n        return new XKeycode(keysym);\n    }\n'''

if 'private XKeycode getPhysicalXKeycode(KeyEvent event)' not in s:
    marker = '\n}'
    pos = s.rfind(marker)
    if pos < 0: raise SystemExit('Keyboard class end not found')
    s = s[:pos] + helper + s[pos:]

# Prefer the physical-key path before the legacy compact map.
needle = '            int keyCode = event.getKeyCode();\n            // Android has key codes outside the compact table used by Winlator.\n'
if needle in s and 'XKeycode physicalKeycode = getPhysicalXKeycode(event);' not in s:
    replacement = '''            XKeycode physicalKeycode = getPhysicalXKeycode(event);\n            if (physicalKeycode != null) {\n                // Keep the same press/release handling as the legacy path.\n                return handleKeycode(event, physicalKeycode);\n            }\n\n            int keyCode = event.getKeyCode();\n            // Android has key codes outside the compact table used by Winlator.\n'''
    s = s.replace(needle, replacement, 1)

keyboard.write_text(s, encoding='utf-8')
print('Physical keyboard coverage expanded; USB/Bluetooth keyboards bypass key assignment.')
