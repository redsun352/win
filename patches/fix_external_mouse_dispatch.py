from pathlib import Path

p = Path('app/src/main/java/com/winlator/XServerDisplayActivity.java')
s = p.read_text(encoding='utf-8')

old = '''    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent event) {
        return !winHandler.onGenericMotionEvent(event) && !touchpadView.onExternalMouseEvent(event) && super.dispatchGenericMotionEvent(event);
    }
'''

new = '''    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent event) {
        // Physical USB/Bluetooth mice must reach TouchpadView before the gamepad handler.
        // Some Android input stacks classify hybrid mouse devices as joystick/gamepad sources,
        // which otherwise consumes the motion event and leaves the Windows pointer frozen.
        final int source = event.getSource();
        final boolean isExternalMouse =
                (source & InputDevice.SOURCE_MOUSE) == InputDevice.SOURCE_MOUSE ||
                (source & InputDevice.SOURCE_TOUCHPAD) == InputDevice.SOURCE_TOUCHPAD;
        if (isExternalMouse && touchpadView.onExternalMouseEvent(event)) return true;
        return !winHandler.onGenericMotionEvent(event) && super.dispatchGenericMotionEvent(event);
    }
'''

if old not in s:
    raise SystemExit('dispatchGenericMotionEvent anchor not found')
if new not in s:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding='utf-8')
print('External mouse dispatch priority fix applied')
