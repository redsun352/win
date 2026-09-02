from pathlib import Path

p = Path('app/src/main/java/com/winlator/widget/TouchpadView.java')
s = p.read_text(encoding='utf-8')

old = '''            case MotionEvent.ACTION_MOVE:\n                syncExternalMouseButtons(event.getButtonState());\n                if (xServer.isRelativeMouseMovement()) {\n                    float dx = event.getX() * sensitivity;\n                    float dy = event.getY() * sensitivity;\n                    if (Math.abs(dx) > CURSOR_ACCELERATION_THRESHOLD) dx *= CURSOR_ACCELERATION;\n                    if (Math.abs(dy) > CURSOR_ACCELERATION_THRESHOLD) dy *= CURSOR_ACCELERATION;\n                    if (dx != 0 || dy != 0)\n                        xServer.injectPointerMoveDelta(Mathf.roundPoint(dx), Mathf.roundPoint(dy));\n                } else {\n                    float[] movePoint = XForm.transformPoint(xform, event.getX(), event.getY());\n                    xServer.injectPointerMove((int)movePoint[0], (int)movePoint[1]);\n                }\n                return true;\n'''

new = '''            case MotionEvent.ACTION_MOVE:\n                syncExternalMouseButtons(event.getButtonState());\n                // Generic mouse MOVE can carry RELATIVE_X/Y while getX()/getY() may be 0 or\n                // represent absolute coordinates. Prefer the Android relative axes whenever\n                // present; this is required for real USB/Bluetooth mice on the Windows desktop.\n                float dx = event.getAxisValue(MotionEvent.AXIS_RELATIVE_X);\n                float dy = event.getAxisValue(MotionEvent.AXIS_RELATIVE_Y);\n                if (dx != 0.0f || dy != 0.0f) {\n                    dx *= sensitivity;\n                    dy *= sensitivity;\n                    if (Math.abs(dx) > CURSOR_ACCELERATION_THRESHOLD) dx *= CURSOR_ACCELERATION;\n                    if (Math.abs(dy) > CURSOR_ACCELERATION_THRESHOLD) dy *= CURSOR_ACCELERATION;\n                    if (xServer.isRelativeMouseMovement()) {\n                        xServer.injectPointerMoveDelta(Mathf.roundPoint(dx), Mathf.roundPoint(dy));\n                    } else {\n                        xServer.injectPointerMoveDelta(Mathf.roundPoint(dx), Mathf.roundPoint(dy));\n                    }\n                } else if (!xServer.isRelativeMouseMovement()) {\n                    float[] movePoint = XForm.transformPoint(xform, event.getX(), event.getY());\n                    xServer.injectPointerMove((int)movePoint[0], (int)movePoint[1]);\n                }\n                return true;\n'''

if old not in s:
    raise SystemExit('Expected external mouse ACTION_MOVE block not found')
s = s.replace(old, new, 1)

# Captured-pointer events are already relative. Keep their getX()/getY() path, but make sure\n# the external button state is synchronized before movement so drag works.\nold_capture = '''        if (event.getActionMasked() == MotionEvent.ACTION_MOVE) {\n            syncExternalMouseButtons(event.getButtonState());\n            float dx = event.getX() * sensitivity;'''
new_capture = '''        if (event.getActionMasked() == MotionEvent.ACTION_MOVE) {\n            syncExternalMouseButtons(event.getButtonState());\n            float dx = event.getAxisValue(MotionEvent.AXIS_RELATIVE_X);\n            if (dx == 0.0f) dx = event.getX();\n            dx *= sensitivity;'''
if old_capture in s:
    s = s.replace(old_capture, new_capture, 1)
old_dy = '''            float dy = event.getY() * sensitivity;'''
new_dy = '''            float dy = event.getAxisValue(MotionEvent.AXIS_RELATIVE_Y);\n            if (dy == 0.0f) dy = event.getY();\n            dy *= sensitivity;'''
if old_dy in s:
    s = s.replace(old_dy, new_dy, 1)

p.write_text(s, encoding='utf-8')
print('External mouse relative motion fix applied')
