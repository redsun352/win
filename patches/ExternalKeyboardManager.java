package com.winlator.inputcontrols;

import android.content.Context;
import android.hardware.input.InputManager;
import android.view.InputDevice;
import android.view.KeyEvent;

/**
 * Detects physical USB and Bluetooth keyboards without requiring key bindings.
 * Android delivers both kinds of keyboards as SOURCE_KEYBOARD devices.
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
        InputDevice device = event.getDevice();
        return isExternalKeyboard(device);
    }

    public static boolean isExternalKeyboard(InputDevice device) {
        if (device == null) return false;
        int sources = device.getSources();
        if ((sources & InputDevice.SOURCE_KEYBOARD) != InputDevice.SOURCE_KEYBOARD) return false;
        if (device.isVirtual()) return false;
        int keyboardType = device.getKeyboardType();
        return keyboardType == InputDevice.KEYBOARD_TYPE_ALPHABETIC ||
               keyboardType == InputDevice.KEYBOARD_TYPE_NON_ALPHABETIC;
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
