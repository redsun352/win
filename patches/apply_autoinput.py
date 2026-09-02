from pathlib import Path
import re

ROOT = Path('app/src/main/java/com/winlator')

def patch(path, old, new):
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if new in s:
        return
    if old not in s:
        raise SystemExit(f'Patch anchor not found: {path}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')

# XServer: expose a button-state setter for robust held-button/drag handling.
patch('xserver/XServer.java', '''    public void injectPointerButtonPress(Pointer.Button buttonCode) {
        try (XLock lock = lock(Lockable.WINDOW_MANAGER, Lockable.INPUT_DEVICE)) {
            pointer.setButton(buttonCode, true);
        }
    }
''', '''    public void injectPointerButtonPress(Pointer.Button buttonCode) {
        try (XLock lock = lock(Lockable.WINDOW_MANAGER, Lockable.INPUT_DEVICE)) {
            pointer.setButton(buttonCode, true);
        }
    }

    public void injectPointerButtonState(Pointer.Button buttonCode, boolean pressed) {
        try (XLock lock = lock(Lockable.WINDOW_MANAGER, Lockable.INPUT_DEVICE)) {
            pointer.setButton(buttonCode, pressed);
        }
    }
''')

# TouchpadView: add physical button state and replace the existing external mouse handler.
p = ROOT / 'widget/TouchpadView.java'
s = p.read_text(encoding='utf-8')
if 'externalMouseButtonState' not in s:
    s = s.replace('private boolean moveCursorToTouchpoint;', '''private boolean moveCursorToTouchpoint;
    private int externalMouseButtonState = 0;''', 1)

start = s.find('    public boolean onExternalMouseEvent(MotionEvent event) {')
end = s.find('\n    public float[] computeDeltaPoint', start)
if start < 0 or end < 0:
    raise SystemExit('TouchpadView external mouse handler anchor not found')
handler = '''    public boolean onExternalMouseEvent(MotionEvent event) {
        if (!isEnabled() || event == null) return false;
        final int source = event.getSource();
        final boolean isMouse =
                (source & InputDevice.SOURCE_MOUSE) == InputDevice.SOURCE_MOUSE ||
                (source & InputDevice.SOURCE_TOUCHPAD) == InputDevice.SOURCE_TOUCHPAD;
        if (!isMouse) return false;

        final int action = event.getActionMasked();
        final int actionButton = event.getActionButton();
        switch (action) {
            case MotionEvent.ACTION_BUTTON_PRESS:
                setExternalMouseButton(actionButton, true);
                syncExternalMouseButtons(event.getButtonState());
                return true;
            case MotionEvent.ACTION_BUTTON_RELEASE:
                setExternalMouseButton(actionButton, false);
                syncExternalMouseButtons(event.getButtonState());
                return true;
            case MotionEvent.ACTION_HOVER_MOVE:
                syncExternalMouseButtons(event.getButtonState());
                float[] transformedPoint = XForm.transformPoint(xform, event.getX(), event.getY());
                xServer.injectPointerMove((int)transformedPoint[0], (int)transformedPoint[1]);
                return true;
            case MotionEvent.ACTION_MOVE:
                syncExternalMouseButtons(event.getButtonState());
                if (xServer.isRelativeMouseMovement()) {
                    float dx = event.getX() * sensitivity;
                    float dy = event.getY() * sensitivity;
                    if (Math.abs(dx) > CURSOR_ACCELERATION_THRESHOLD) dx *= CURSOR_ACCELERATION;
                    if (Math.abs(dy) > CURSOR_ACCELERATION_THRESHOLD) dy *= CURSOR_ACCELERATION;
                    if (dx != 0 || dy != 0)
                        xServer.injectPointerMoveDelta(Mathf.roundPoint(dx), Mathf.roundPoint(dy));
                } else {
                    float[] movePoint = XForm.transformPoint(xform, event.getX(), event.getY());
                    xServer.injectPointerMove((int)movePoint[0], (int)movePoint[1]);
                }
                return true;
            case MotionEvent.ACTION_SCROLL:
                float scrollY = event.getAxisValue(MotionEvent.AXIS_VSCROLL);
                if (scrollY <= -0.01f) {
                    int count = Math.max(1, Mathf.roundPoint(Math.abs(scrollY)));
                    for (int i = 0; i < count; i++) {
                        xServer.injectPointerButtonPress(Pointer.Button.BUTTON_SCROLL_DOWN);
                        xServer.injectPointerButtonRelease(Pointer.Button.BUTTON_SCROLL_DOWN);
                    }
                } else if (scrollY >= 0.01f) {
                    int count = Math.max(1, Mathf.roundPoint(Math.abs(scrollY)));
                    for (int i = 0; i < count; i++) {
                        xServer.injectPointerButtonPress(Pointer.Button.BUTTON_SCROLL_UP);
                        xServer.injectPointerButtonRelease(Pointer.Button.BUTTON_SCROLL_UP);
                    }
                }
                return true;
        }
        return false;
    }

    private void setExternalMouseButton(int button, boolean pressed) {
        // Android MotionEvent button bit values are stable: primary=1, secondary=2, tertiary=4.
        switch (button) {
            case 1:
                xServer.injectPointerButtonState(Pointer.Button.BUTTON_LEFT, pressed);
                externalMouseButtonState = pressed ? externalMouseButtonState | 1 : externalMouseButtonState & ~1;
                break;
            case 2:
                xServer.injectPointerButtonState(Pointer.Button.BUTTON_RIGHT, pressed);
                externalMouseButtonState = pressed ? externalMouseButtonState | 2 : externalMouseButtonState & ~2;
                break;
            case 4:
                xServer.injectPointerButtonState(Pointer.Button.BUTTON_MIDDLE, pressed);
                externalMouseButtonState = pressed ? externalMouseButtonState | 4 : externalMouseButtonState & ~4;
                break;
        }
    }

    private void syncExternalMouseButtons(int state) {
        final int primary = 1;
        final int secondary = 2;
        final int tertiary = 4;
        if ((state & primary) != 0 && (externalMouseButtonState & primary) == 0) setExternalMouseButton(primary, true);
        else if ((state & primary) == 0 && (externalMouseButtonState & primary) != 0) setExternalMouseButton(primary, false);
        if ((state & secondary) != 0 && (externalMouseButtonState & secondary) == 0) setExternalMouseButton(secondary, true);
        else if ((state & secondary) == 0 && (externalMouseButtonState & secondary) != 0) setExternalMouseButton(secondary, false);
        if ((state & tertiary) != 0 && (externalMouseButtonState & tertiary) == 0) setExternalMouseButton(tertiary, true);
        else if ((state & tertiary) == 0 && (externalMouseButtonState & tertiary) != 0) setExternalMouseButton(tertiary, false);
    }
'''
s = s[:start] + handler + s[end:]
old_capture = '''    @Override
    public boolean onCapturedPointer(View view, MotionEvent event) {
        if (event.getAction() == MotionEvent.ACTION_MOVE) {'''
if old_capture in s:
    s = s.replace(old_capture, '''    @Override
    public boolean onCapturedPointer(View view, MotionEvent event) {
        if (event.getActionMasked() == MotionEvent.ACTION_MOVE) {
            syncExternalMouseButtons(event.getButtonState());''', 1)
p.write_text(s, encoding='utf-8')

# Activity: add the physical-device registry and hook it into the EXISTING lifecycle.
p = ROOT / 'XServerDisplayActivity.java'
s = p.read_text(encoding='utf-8')
if 'import com.winlator.inputcontrols.ExternalInputDeviceManager;' not in s:
    s = s.replace('import com.winlator.inputcontrols.ExternalController;', 'import com.winlator.inputcontrols.ExternalController;\nimport com.winlator.inputcontrols.ExternalInputDeviceManager;', 1)
if 'private ExternalInputDeviceManager externalInputDeviceManager;' not in s:
    s = s.replace('private TouchpadView touchpadView;', 'private TouchpadView touchpadView;\n    private ExternalInputDeviceManager externalInputDeviceManager;', 1)
if 'externalInputDeviceManager = new ExternalInputDeviceManager(this);' not in s:
    s = s.replace('super.onCreate(savedInstanceState);', 'super.onCreate(savedInstanceState);\n        externalInputDeviceManager = new ExternalInputDeviceManager(this);', 1)
if 'externalInputDeviceManager.close();' not in s:
    match = re.search(r'(\n\s*@Override\s*\n\s*protected void onDestroy\(\)\s*\{)', s)
    if not match:
        raise SystemExit('Existing XServerDisplayActivity.onDestroy() not found')
    insert_at = match.end()
    s = s[:insert_at] + '\n        if (externalInputDeviceManager != null) externalInputDeviceManager.close();' + s[insert_at:]
p.write_text(s, encoding='utf-8')

print('AutoInput patch applied successfully')
