from pathlib import Path
import re

ROOT = Path('app/src/main/java/com/winlator')

# Harden the generated Wi-Fi panel. Android 10+ does not allow an app to silently
# force-connect to arbitrary Wi-Fi networks. WifiNetworkSuggestion is the supported
# path, but the old implementation did not clear stale app suggestions or handle
# WPA3/OWE. This patch also gives the UI a deterministic fallback to system Wi-Fi
# settings when Android refuses the request.
p = ROOT / 'WifiNetworkFragment.java'
s = p.read_text(encoding='utf-8')

start = s.find('    private void submitSuggestion(String ssid, String password, String capabilities) {')
end = s.find('    private String getIPv4() {', start)
if start < 0 or end < 0:
    raise SystemExit('Wi-Fi submitSuggestion block not found')

new_method = '''    private void submitSuggestion(String ssid, String password, String capabilities) {
        try {
            // Suggestions belong to this application. Remove our previous request
            // before adding a fresh one so a stale password/network entry cannot win.
            try { wifiManager.removeNetworkSuggestions(wifiManager.getNetworkSuggestions()); }
            catch (Exception ignored) {}

            WifiNetworkSuggestion.Builder b = new WifiNetworkSuggestion.Builder().setSsid(ssid);
            String caps = capabilities != null ? capabilities.toUpperCase(java.util.Locale.US) : "";
            boolean wpa3 = caps.contains("SAE");
            boolean enhancedOpen = caps.contains("OWE");
            boolean secured = caps.contains("WPA") || caps.contains("WEP") || caps.contains("SAE");

            if (wpa3 && password.length() > 0) {
                b.setWpa3Passphrase(password);
            } else if (secured && password.length() > 0) {
                // WPA/WPA2 mixed networks are accepted through WPA2 here.
                b.setWpa2Passphrase(password);
            } else if (enhancedOpen) {
                b.setIsEnhancedOpen(true);
            } else if (secured) {
                Toast.makeText(requireContext(), "Bu ağ parola istiyor. Parolayı girin.", Toast.LENGTH_LONG).show();
                return;
            }

            List<WifiNetworkSuggestion> suggestions = new ArrayList<>();
            suggestions.add(b.build());
            int result = wifiManager.addNetworkSuggestions(suggestions);
            if (result == WifiManager.STATUS_NETWORK_SUGGESTIONS_SUCCESS) {
                Toast.makeText(requireContext(), "Bağlantı isteği gönderildi. Android ağı bağlayınca durum otomatik güncellenecek.", Toast.LENGTH_LONG).show();
                refreshView();
            } else {
                Toast.makeText(requireContext(), "Android Wi-Fi bağlantı isteğini kabul etmedi (" + result + "). Wi-Fi Ayarları açılıyor.", Toast.LENGTH_LONG).show();
                startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS));
            }
        } catch (SecurityException e) {
            Toast.makeText(requireContext(), "Wi-Fi izni verilmedi. Wi-Fi Ayarları açılıyor.", Toast.LENGTH_LONG).show();
            startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS));
        } catch (Exception e) {
            Toast.makeText(requireContext(), "Wi-Fi bağlantısı başlatılamadı: " + e.getMessage(), Toast.LENGTH_LONG).show();
            startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS));
        }
    }

'''
s = s[:start] + new_method + s[end:]
p.write_text(s, encoding='utf-8')

# Ensure all permissions needed by the Wi-Fi UI and multicast LAN support exist.
manifest = Path('app/src/main/AndroidManifest.xml')
ms = manifest.read_text(encoding='utf-8')
permissions = [
    'android.permission.INTERNET',
    'android.permission.ACCESS_NETWORK_STATE',
    'android.permission.ACCESS_WIFI_STATE',
    'android.permission.CHANGE_WIFI_STATE',
]
for perm in permissions:
    tag = '<uses-permission android:name="' + perm + '" />'
    if tag not in ms:
        ms = tag + '\n' + ms
manifest.write_text(ms, encoding='utf-8')
print('Wi-Fi connection handling hardened: stale suggestions cleared, WPA3/OWE supported, refusal falls back to Android Wi-Fi settings, required network permissions ensured.')
