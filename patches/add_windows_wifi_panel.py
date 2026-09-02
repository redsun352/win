from pathlib import Path

ROOT = Path('app/src/main/java/com/winlator')

# Windows-like network flyout implemented natively in Winlator. It reads the real
# Android Wi-Fi state, displays SSID/signal/IP/gateway/DNS, scans nearby APs and
# uses Android's supported Wi-Fi suggestion API for connection requests.
fragment = r'''package com.winlator;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.LinkProperties;
import android.net.Network;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.net.wifi.WifiNetworkSuggestion;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.Fragment;

import java.net.Inet4Address;
import java.net.InetAddress;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

public class WifiNetworkFragment extends Fragment {
    private static final int REQ_WIFI = 9127;
    private WifiManager wifiManager;
    private ConnectivityManager connectivityManager;
    private LinearLayout root;
    private LinearLayout networksBox;
    private TextView statusText;
    private TextView detailsText;
    private BroadcastReceiver receiver;

    private int dp(float v) {
        return (int)(v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private TextView label(String text, float size) {
        TextView t = new TextView(requireContext());
        t.setText(text);
        t.setTextSize(size);
        t.setTextColor(0xff202124);
        t.setPadding(dp(4), dp(3), dp(4), dp(3));
        return t;
    }

    @Override
    public View onCreateView(@NonNull android.view.LayoutInflater inflater, ViewGroupUnused container, Bundle state) {
        wifiManager = (WifiManager) requireContext().getApplicationContext().getSystemService(Context.WIFI_SERVICE);
        connectivityManager = (ConnectivityManager) requireContext().getSystemService(Context.CONNECTIVITY_SERVICE);

        ScrollView scroll = new ScrollView(requireContext());
        scroll.setBackgroundColor(0xfff3f3f3);
        root = new LinearLayout(requireContext());
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(18), dp(18), dp(24));
        scroll.addView(root);

        LinearLayout titleRow = new LinearLayout(requireContext());
        titleRow.setGravity(Gravity.CENTER_VERTICAL);
        TextView wifiIcon = label("◉", 32);
        wifiIcon.setTextColor(0xff0078d4);
        titleRow.addView(wifiIcon, new LinearLayout.LayoutParams(dp(48), dp(52)));
        LinearLayout titleBox = new LinearLayout(requireContext());
        titleBox.setOrientation(LinearLayout.VERTICAL);
        titleBox.addView(label("Ağ ve İnternet", 24));
        statusText = label("Wi-Fi durumu okunuyor…", 14);
        titleBox.addView(statusText);
        titleRow.addView(titleBox, new LinearLayout.LayoutParams(0, -2, 1));
        Button settings = new Button(requireContext());
        settings.setText("Wi-Fi Ayarları");
        settings.setOnClickListener(v -> startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS)));
        titleRow.addView(settings);
        root.addView(titleRow);

        detailsText = label("", 14);
        detailsText.setPadding(dp(56), 0, dp(4), dp(10));
        root.addView(detailsText);

        TextView heading = label("Kullanılabilir ağlar", 18);
        heading.setTextColor(0xff1f1f1f);
        root.addView(heading);

        networksBox = new LinearLayout(requireContext());
        networksBox.setOrientation(LinearLayout.VERTICAL);
        root.addView(networksBox);

        Button refresh = new Button(requireContext());
        refresh.setText("↻  Ağları yenile");
        refresh.setOnClickListener(v -> refreshNetworks());
        root.addView(refresh);

        receiver = new BroadcastReceiver() {
            @Override public void onReceive(Context c, Intent intent) {
                String a = intent.getAction();
                if (WifiManager.NETWORK_STATE_CHANGED_ACTION.equals(a) ||
                    WifiManager.RSSI_CHANGED_ACTION.equals(a) ||
                    WifiManager.WIFI_STATE_CHANGED_ACTION.equals(a) ||
                    WifiManager.SCAN_RESULTS_AVAILABLE_ACTION.equals(a)) {
                    refreshView();
                    if (WifiManager.SCAN_RESULTS_AVAILABLE_ACTION.equals(a)) populateNetworks();
                }
            }
        };

        if (needsPermission()) requestWifiPermission();
        else refreshNetworks();
        return scroll;
    }

    private boolean needsPermission() {
        if (Build.VERSION.SDK_INT >= 33) {
            return ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.NEARBY_WIFI_DEVICES) != PackageManager.PERMISSION_GRANTED;
        }
        return ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED;
    }

    private void requestWifiPermission() {
        if (Build.VERSION.SDK_INT >= 33) {
            ActivityCompat.requestPermissions(requireActivity(), new String[]{Manifest.permission.NEARBY_WIFI_DEVICES, Manifest.permission.ACCESS_FINE_LOCATION}, REQ_WIFI);
        } else {
            ActivityCompat.requestPermissions(requireActivity(), new String[]{Manifest.permission.ACCESS_FINE_LOCATION}, REQ_WIFI);
        }
    }

    @Override public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQ_WIFI) refreshNetworks();
    }

    @Override public void onStart() {
        super.onStart();
        if (receiver != null) {
            IntentFilter f = new IntentFilter();
            f.addAction(WifiManager.NETWORK_STATE_CHANGED_ACTION);
            f.addAction(WifiManager.RSSI_CHANGED_ACTION);
            f.addAction(WifiManager.WIFI_STATE_CHANGED_ACTION);
            f.addAction(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION);
            ContextCompat.registerReceiver(requireContext(), receiver, f, ContextCompat.RECEIVER_NOT_EXPORTED);
        }
    }

    @Override public void onStop() {
        if (receiver != null) {
            try { requireContext().unregisterReceiver(receiver); } catch (Exception ignored) {}
        }
        super.onStop();
    }

    private void refreshNetworks() {
        refreshView();
        if (wifiManager != null && wifiManager.isWifiEnabled()) {
            try { wifiManager.startScan(); } catch (SecurityException ignored) {}
        }
        populateNetworks();
    }

    private void refreshView() {
        if (wifiManager == null) return;
        boolean enabled = wifiManager.isWifiEnabled();
        statusText.setText(enabled ? "Wi-Fi açık" : "Wi-Fi kapalı");
        if (!enabled) {
            detailsText.setText("Wi-Fi'yi açmak için Wi-Fi Ayarları düğmesine dokunun.");
            return;
        }
        try {
            WifiInfo info = wifiManager.getConnectionInfo();
            String ssid = info != null ? info.getSSID() : null;
            if (ssid == null || "<unknown ssid>".equals(ssid)) ssid = "Bağlı değil";
            int rssi = info != null ? info.getRssi() : -127;
            int bars = rssi == -127 ? 0 : WifiManager.calculateSignalLevel(rssi, 5);
            StringBuilder b = new StringBuilder();
            b.append(ssid).append("  ").append(signalGlyph(bars));
            String ip = getIPv4();
            String gateway = getGateway();
            String dns = getDns();
            if (ip != null) b.append("\nIP: ").append(ip);
            if (gateway != null) b.append("   Ağ geçidi: ").append(gateway);
            if (dns.length() > 0) b.append("\nDNS: ").append(dns);
            detailsText.setText(b.toString());
        } catch (SecurityException e) {
            detailsText.setText("Wi-Fi bilgilerini görmek için izin gerekli.");
        }
    }

    private String signalGlyph(int bars) {
        if (bars <= 0) return "▱";
        if (bars == 1) return "▰▱▱▱";
        if (bars == 2) return "▰▰▱▱";
        if (bars == 3) return "▰▰▰▱";
        return "▰▰▰▰";
    }

    private void populateNetworks() {
        if (networksBox == null || wifiManager == null) return;
        networksBox.removeAllViews();
        List<ScanResult> results;
        try { results = new ArrayList<>(wifiManager.getScanResults()); }
        catch (SecurityException e) { return; }
        Collections.sort(results, new Comparator<ScanResult>() {
            @Override public int compare(ScanResult a, ScanResult b) { return Integer.compare(b.level, a.level); }
        });
        String last = null;
        int shown = 0;
        for (ScanResult r : results) {
            String ssid = r.SSID;
            if (ssid == null || ssid.isEmpty() || ssid.equals(last)) continue;
            last = ssid;
            shown++;
            addNetworkRow(ssid, r.level, r.capabilities);
            if (shown >= 30) break;
        }
        if (shown == 0) networksBox.addView(label("Yakındaki ağ bulunamadı. Wi-Fi taramasını yenileyin.", 14));
    }

    private void addNetworkRow(String ssid, int level, String capabilities) {
        LinearLayout row = new LinearLayout(requireContext());
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(12), dp(10), dp(8), dp(10));
        row.setBackgroundColor(0xffffffff);
        TextView icon = label(signalGlyph(WifiManager.calculateSignalLevel(level, 5)), 18);
        icon.setTextColor(0xff0078d4);
        row.addView(icon, new LinearLayout.LayoutParams(dp(70), -2));
        LinearLayout texts = new LinearLayout(requireContext());
        texts.setOrientation(LinearLayout.VERTICAL);
        texts.addView(label(ssid, 16));
        texts.addView(label(capabilities != null && capabilities.contains("WPA") ? "Güvenli ağ" : "Açık ağ", 12));
        row.addView(texts, new LinearLayout.LayoutParams(0, -2, 1));
        Button connect = new Button(requireContext());
        connect.setText("Bağlan");
        connect.setOnClickListener(v -> connectTo(ssid, capabilities));
        row.addView(connect);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.setMargins(0, dp(4), 0, 0);
        networksBox.addView(row, lp);
    }

    private void connectTo(String ssid, String capabilities) {
        if (Build.VERSION.SDK_INT < 29) {
            startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS));
            return;
        }
        EditText pass = new EditText(requireContext());
        pass.setHint("Wi-Fi parolası (açıksa boş bırakın)");
        pass.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        new androidx.appcompat.app.AlertDialog.Builder(requireContext())
            .setTitle("\"" + ssid + "\" ağına bağlan")
            .setView(pass)
            .setNegativeButton("İptal", null)
            .setPositiveButton("Bağlan", (d, w) -> submitSuggestion(ssid, pass.getText().toString(), capabilities))
            .show();
    }

    private void submitSuggestion(String ssid, String password, String capabilities) {
        try {
            WifiNetworkSuggestion.Builder b = new WifiNetworkSuggestion.Builder().setSsid(ssid);
            boolean secured = capabilities != null && (capabilities.contains("WPA") || capabilities.contains("WEP"));
            if (secured && password.length() > 0) b.setWpa2Passphrase(password);
            List<WifiNetworkSuggestion> suggestions = new ArrayList<>();
            suggestions.add(b.build());
            int result = wifiManager.addNetworkSuggestions(suggestions);
            if (result == WifiManager.STATUS_NETWORK_SUGGESTIONS_SUCCESS) {
                Toast.makeText(requireContext(), "Bağlantı isteği gönderildi. Android onayı gerekebilir.", Toast.LENGTH_LONG).show();
                refreshView();
            } else {
                Toast.makeText(requireContext(), "Android Wi-Fi bağlantı isteğini kabul etmedi (" + result + ").", Toast.LENGTH_LONG).show();
            }
        } catch (Exception e) {
            Toast.makeText(requireContext(), "Wi-Fi bağlantısı başlatılamadı: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private String getIPv4() {
        Network n = connectivityManager.getActiveNetwork();
        LinkProperties lp = n != null ? connectivityManager.getLinkProperties(n) : null;
        if (lp == null) return null;
        for (android.net.LinkAddress la : lp.getLinkAddresses()) {
            InetAddress a = la.getAddress();
            if (a instanceof Inet4Address) return a.getHostAddress();
        }
        return null;
    }

    private String getGateway() {
        Network n = connectivityManager.getActiveNetwork();
        LinkProperties lp = n != null ? connectivityManager.getLinkProperties(n) : null;
        if (lp == null) return null;
        for (android.net.RouteInfo route : lp.getRoutes()) {
            InetAddress a = route.getGateway();
            if (a instanceof Inet4Address && !a.isAnyLocalAddress()) return a.getHostAddress();
        }
        return null;
    }

    private String getDns() {
        Network n = connectivityManager.getActiveNetwork();
        LinkProperties lp = n != null ? connectivityManager.getLinkProperties(n) : null;
        if (lp == null) return "";
        ArrayList<String> out = new ArrayList<>();
        for (InetAddress a : lp.getDnsServers()) if (a != null && !a.isLoopbackAddress()) out.add(a.getHostAddress());
        return android.text.TextUtils.join(", ", out);
    }

    // Kept private because this Fragment uses only programmatic views.
    private static class ViewGroupUnused extends android.view.ViewGroup {
        ViewGroupUnused(Context c) { super(c); }
        @Override protected void onLayout(boolean c, int l, int t, int r, int b) {}
    }
}
'''

# Fix the harmless placeholder ViewGroup type by using the real ViewGroup import/signature.
fragment = fragment.replace('ViewGroupUnused container', 'android.view.ViewGroup container')
fragment = fragment.replace('\n    // Kept private because this Fragment uses only programmatic views.\n    private static class ViewGroupUnused extends android.view.ViewGroup {\n        ViewGroupUnused(Context c) { super(c); }\n        @Override protected void onLayout(boolean c, int l, int t, int r, int b) {}\n    }\n', '\n')

p = ROOT / 'WifiNetworkFragment.java'
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(fragment, encoding='utf-8')

# Add a permanent Wi-Fi & Network entry to the app's navigation drawer.
p = ROOT / 'MainActivity.java'
s = p.read_text(encoding='utf-8')
if 'MENU_WIFI_NETWORK' not in s:
    s = s.replace('public static final byte OPEN_DIRECTORY_REQUEST_CODE = 4;', 'public static final byte OPEN_DIRECTORY_REQUEST_CODE = 4;\n    public static final int MENU_WIFI_NETWORK = 0x7f0f9001;')
    s = s.replace('navigationView.setNavigationItemSelectedListener(this);', 'navigationView.setNavigationItemSelectedListener(this);\n        if (navigationView.getMenu().findItem(MENU_WIFI_NETWORK) == null) {\n            navigationView.getMenu().add(0, MENU_WIFI_NETWORK, 3, "Wi-Fi ve Ağ").setIcon(android.R.drawable.ic_menu_manage);\n        }')
    s = s.replace('case R.id.menu_item_settings:', 'case MENU_WIFI_NETWORK:\n                showFragment(new WifiNetworkFragment());\n                break;\n            case R.id.menu_item_settings:')
    p.write_text(s, encoding='utf-8')

# Android 13+ requires NEARBY_WIFI_DEVICES for Wi-Fi discovery; older versions use fine location.
manifest = Path('app/src/main/AndroidManifest.xml')
ms = manifest.read_text(encoding='utf-8')
if 'android.permission.NEARBY_WIFI_DEVICES' not in ms:
    ms = ms.replace('    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>', '    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>\n    <uses-permission android:name="android.permission.NEARBY_WIFI_DEVICES" android:usesPermissionFlags="neverForLocation"/>\n    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>')
    manifest.write_text(ms, encoding='utf-8')

print('Windows-style Wi-Fi/network panel added')
