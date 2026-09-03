package com.winlator.inputcontrols;

import android.content.Context;
import android.hardware.input.InputManager;
import android.view.InputDevice;
import android.view.KeyEvent;

/**
 * Detects real USB/Bluetooth keyboards without requiring key bindings.
 * Android HID implementations are inconsistent about SOURCE_KEYBOARD and
 * KEYBOARD_TYPE, so either physical keyboard signal is accepted.
 */
public final class ExternalKeyboardManager implements InputManager.InputDeviceListener {
    private final InputManager inputManager;
    private volatile boolean externalKeyboardConnected;

    public ExternalKeyboardManager(Context context) {
        inputManager = (InputManager) context.getSystemService(Context.INPUT_SERVICE);
        refresh();
        if (inputManager != null) inputManager.registerInputDeviceListener(this, null);
    }

    public void close() {
        if (inputManager != null) inputManager.unregisterInputDeviceListener(this);
    }

    public boolean isExternalKeyboardConnected() {
        return externalKeyboardConnected;
    }

    public static boolean isExternalKeyboard(KeyEvent event) {
        if (event == null) return false;
        return isExternalKeyboard(event.getDevice());
    }

    public static boolean isExternalKeyboard(InputDevice device) {
        if (device == null || device.isVirtual()) return false;
        int sources = device.getSources();
        // Some Android HID drivers expose SOURCE_KEYBOARD; others expose a
        // non-NONE keyboard type without the source bit. Accept either.
        return (sources & InputDevice.SOURCE_KEYBOARD) == InputDevice.SOURCE_KEYBOARD ||
               device.getKeyboardType() != InputDevice.KEYBOARD_TYPE_NONE;
    }

    private void refresh() {
        externalKeyboardConnected = false;
        if (inputManager == null) return;
        for (int id : inputManager.getInputDeviceIds()) {
            if (isExternalKeyboard(InputDevice.getDevice(id))) {
                externalKeyboardConnected = true;
                return;
            }
        }
    }

    @Override public void onInputDeviceAdded(int deviceId) { refresh(); }
    @Override public void onInputDeviceRemoved(int deviceId) { refresh(); }
    @Override public void onInputDeviceChanged(int deviceId) { refresh(); }
}
