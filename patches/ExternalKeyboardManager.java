package com.winlator.inputcontrols;

import android.content.Context;
import android.hardware.input.InputManager;
import android.view.InputDevice;
import android.view.KeyEvent;

/**
 * Detects real USB/Bluetooth keyboards without requiring key bindings.
 * Physical keyboards are SOURCE_KEYBOARD devices. Some Android keyboard
 * drivers report KEYBOARD_TYPE_NONE, so detection intentionally does not
 * require an alphabetic/non-alphabetic keyboard type.
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
        // Real USB and Bluetooth keyboards normally expose SOURCE_KEYBOARD.
        // Do not reject KEYBOARD_TYPE_NONE: several Android HID drivers use it.
        return (sources & InputDevice.SOURCE_KEYBOARD) == InputDevice.SOURCE_KEYBOARD;
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
