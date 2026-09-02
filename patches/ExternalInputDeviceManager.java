package com.winlator.inputcontrols;

import android.content.Context;
import android.hardware.input.InputManager;
import android.view.InputDevice;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Automatically discovers and classifies physical Android input devices. */
public final class ExternalInputDeviceManager implements InputManager.InputDeviceListener {
    public enum Role { KEYBOARD, MOUSE, GAMEPAD, UNKNOWN }

    public static final class DeviceInfo {
        public final int id;
        public final String name;
        public final int vendorId;
        public final int productId;
        public final int sources;
        public final Role role;

        DeviceInfo(InputDevice d, Role role) {
            this.id = d.getId();
            this.name = d.getName() == null ? "" : d.getName();
            this.vendorId = d.getVendorId();
            this.productId = d.getProductId();
            this.sources = d.getSources();
            this.role = role;
        }

        public String signature() {
            return vendorId + ":" + productId + ":" + sources + ":" + name;
        }
    }

    private final InputManager inputManager;
    private final Map<Integer, DeviceInfo> devices = new HashMap<>();

    public ExternalInputDeviceManager(Context context) {
        inputManager = (InputManager)context.getSystemService(Context.INPUT_SERVICE);
        refresh();
        if (inputManager != null) inputManager.registerInputDeviceListener(this, null);
    }

    public void close() {
        if (inputManager != null) inputManager.unregisterInputDeviceListener(this);
    }

    public synchronized void refresh() {
        devices.clear();
        if (inputManager == null) return;
        for (int id : inputManager.getInputDeviceIds()) addDevice(id);
    }

    public synchronized List<DeviceInfo> getDevices() {
        return Collections.unmodifiableList(new ArrayList<>(devices.values()));
    }

    public synchronized DeviceInfo getDevice(int id) { return devices.get(id); }

    private void addDevice(int id) {
        InputDevice d = inputManager.getInputDevice(id);
        if (d != null) devices.put(id, new DeviceInfo(d, classify(d)));
    }

    private static Role classify(InputDevice d) {
        final int sources = d.getSources();
        if ((sources & InputDevice.SOURCE_MOUSE) == InputDevice.SOURCE_MOUSE ||
            (sources & InputDevice.SOURCE_TOUCHPAD) == InputDevice.SOURCE_TOUCHPAD) return Role.MOUSE;
        if ((sources & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD ||
            (sources & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK) return Role.GAMEPAD;
        if (d.getKeyboardType() != InputDevice.KEYBOARD_TYPE_NONE ||
            (sources & InputDevice.SOURCE_KEYBOARD) == InputDevice.SOURCE_KEYBOARD) return Role.KEYBOARD;
        return Role.UNKNOWN;
    }

    @Override public void onInputDeviceAdded(int deviceId) { synchronized (this) { addDevice(deviceId); } }
    @Override public void onInputDeviceRemoved(int deviceId) { synchronized (this) { devices.remove(deviceId); } }
    @Override public void onInputDeviceChanged(int deviceId) { synchronized (this) { addDevice(deviceId); } }
}
