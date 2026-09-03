from pathlib import Path

ROOT = Path('app/src/main/java/com/winlator')

# Make Android's active network information visible inside the Wine/PRoot
# environment. The important part for LAN games is that we expose the real
# IPv4/prefix/gateway/DNS and keep Android Wi-Fi multicast/broadcast reception
# enabled while a container is running.
p = ROOT / 'core/NetworkHelper.java'
s = p.read_text(encoding='utf-8')

if 'public List<String> getDNSAddresses()' not in s:
    anchor = '''    public List<IFAddress> getIFAddresses() {'''
    addition = '''    public List<String> getDNSAddresses() {
        ArrayList<String> result = new ArrayList<>();
        Network activeNetwork = connectivityManager.getActiveNetwork();
        if (activeNetwork == null) return result;
        LinkProperties linkProperties = connectivityManager.getLinkProperties(activeNetwork);
        if (linkProperties == null) return result;
        for (InetAddress address : linkProperties.getDnsServers()) {
            if (address != null && !address.isLoopbackAddress()) result.add(address.getHostAddress());
        }
        return result;
    }

    public String getGatewayAddress() {
        Network activeNetwork = connectivityManager.getActiveNetwork();
        if (activeNetwork == null) return null;
        LinkProperties linkProperties = connectivityManager.getLinkProperties(activeNetwork);
        if (linkProperties == null) return null;
        for (android.net.RouteInfo route : linkProperties.getRoutes()) {
            InetAddress gateway = route.getGateway();
            if (gateway instanceof Inet4Address && !gateway.isAnyLocalAddress()) return gateway.getHostAddress();
        }
        return null;
    }

    public int getIPv4PrefixLength() {
        Network activeNetwork = connectivityManager.getActiveNetwork();
        if (activeNetwork == null) return -1;
        LinkProperties linkProperties = connectivityManager.getLinkProperties(activeNetwork);
        if (linkProperties == null) return -1;
        for (LinkAddress address : linkProperties.getLinkAddresses()) {
            if (address.getAddress() instanceof Inet4Address) return address.getPrefixLength();
        }
        return -1;
    }

    public String getIPv4BroadcastAddress() {
        String ip = getIPv4Address();
        int prefix = getIPv4PrefixLength();
        if (ip == null || prefix < 0 || prefix > 32) return null;
        try {
            byte[] bytes = InetAddress.getByName(ip).getAddress();
            int value = ((bytes[0] & 255) << 24) | ((bytes[1] & 255) << 16) | ((bytes[2] & 255) << 8) | (bytes[3] & 255);
            int mask = prefix == 0 ? 0 : (int)(0xffffffffL << (32 - prefix));
            int broadcast = value | ~mask;
            return ((broadcast >>> 24) & 255) + "." + ((broadcast >>> 16) & 255) + "." + ((broadcast >>> 8) & 255) + "." + (broadcast & 255);
        } catch (Exception ignored) {
            return null;
        }
    }

'''
    if anchor not in s: raise SystemExit('NetworkHelper anchor not found')
    s = s.replace(anchor, addition + anchor, 1)
    p.write_text(s, encoding='utf-8')

p = ROOT / 'xenvironment/components/NetworkInfoUpdateComponent.java'
s = p.read_text(encoding='utf-8')

if 'import android.net.wifi.WifiManager;' not in s:
    s = s.replace('import android.net.ConnectivityManager;\n', 'import android.net.ConnectivityManager;\nimport android.net.Network;\nimport android.net.NetworkCapabilities;\nimport android.net.wifi.WifiManager;\n', 1)

if 'private WifiManager.MulticastLock multicastLock;' not in s:
    s = s.replace('    private BroadcastReceiver broadcastReceiver;\n', '    private BroadcastReceiver broadcastReceiver;\n    private ConnectivityManager.NetworkCallback networkCallback;\n    private WifiManager.MulticastLock multicastLock;\n', 1)

old_start = '''        broadcastReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                updateIFAddrsFile(networkHelper.getIFAddresses());
                updateEtcHostsFile(networkHelper.getIPv4Address());
                updateNetworkResolverFiles(networkHelper);
            }
        };

        IntentFilter filter = new IntentFilter();
        filter.addAction(ConnectivityManager.CONNECTIVITY_ACTION);
        context.registerReceiver(broadcastReceiver, filter);'''
new_start = '''        acquireWifiMulticastLock(context);
        updateNetworkFiles(networkHelper);

        networkCallback = new ConnectivityManager.NetworkCallback() {
            @Override public void onAvailable(Network network) { updateNetworkFiles(networkHelper); }
            @Override public void onLost(Network network) { updateNetworkFiles(networkHelper); }
            @Override public void onLinkPropertiesChanged(Network network, android.net.LinkProperties linkProperties) { updateNetworkFiles(networkHelper); }
            @Override public void onCapabilitiesChanged(Network network, NetworkCapabilities capabilities) { updateNetworkFiles(networkHelper); }
        };
        try {
            ConnectivityManager cm = environment.getContext().getSystemService(ConnectivityManager.class);
            if (cm != null) cm.registerDefaultNetworkCallback(networkCallback);
        } catch (Exception ignored) {}
'''
if old_start in s:
    s = s.replace(old_start, new_start, 1)
else:
    marker = '        updateEtcHostsFile(networkHelper.getIPv4Address());'
    if 'registerDefaultNetworkCallback(networkCallback)' not in s and marker in s:
        s = s.replace(marker, marker + '\n        acquireWifiMulticastLock(context);\n        updateNetworkFiles(networkHelper);\n\n        networkCallback = new ConnectivityManager.NetworkCallback() {\n            @Override public void onAvailable(Network network) { updateNetworkFiles(networkHelper); }\n            @Override public void onLost(Network network) { updateNetworkFiles(networkHelper); }\n            @Override public void onLinkPropertiesChanged(Network network, android.net.LinkProperties lp) { updateNetworkFiles(networkHelper); }\n            @Override public void onCapabilitiesChanged(Network network, NetworkCapabilities caps) { updateNetworkFiles(networkHelper); }\n        };\n        try { ConnectivityManager cm = environment.getContext().getSystemService(ConnectivityManager.class); if (cm != null) cm.registerDefaultNetworkCallback(networkCallback); } catch (Exception ignored) {}', 1)

if 'unregisterNetworkCallback(networkCallback)' not in s:
    old_stop = '''    public void stop() {
        if (broadcastReceiver != null) {
            environment.getContext().unregisterReceiver(broadcastReceiver);
            broadcastReceiver = null;
        }
    }'''
    new_stop = '''    public void stop() {
        ConnectivityManager cm = environment.getContext().getSystemService(ConnectivityManager.class);
        if (cm != null && networkCallback != null) {
            try { cm.unregisterNetworkCallback(networkCallback); } catch (Exception ignored) {}
            networkCallback = null;
        }
        if (broadcastReceiver != null) {
            try { environment.getContext().unregisterReceiver(broadcastReceiver); } catch (Exception ignored) {}
            broadcastReceiver = null;
        }
        if (multicastLock != null && multicastLock.isHeld()) {
            try { multicastLock.release(); } catch (Exception ignored) {}
        }
        multicastLock = null;
    }'''
    if old_stop in s: s = s.replace(old_stop, new_stop, 1)

if 'private void updateNetworkFiles(NetworkHelper networkHelper)' not in s:
    anchor = '    private void updateIFAddrsFile(List<NetworkHelper.IFAddress> ifAddresses) {'
    addition = '''    private void updateNetworkFiles(NetworkHelper networkHelper) {
        updateIFAddrsFile(networkHelper.getIFAddresses());
        updateEtcHostsFile(networkHelper.getIPv4Address());
        // The resolver helper below updates /etc/resolv.conf from Android DNS data.
        updateNetworkResolverFiles(networkHelper);

        File tmp = environment.getRootFS().getTmpDir();
        String ip = networkHelper.getIPv4Address();
        String gateway = networkHelper.getGatewayAddress();
        String broadcast = networkHelper.getIPv4BroadcastAddress();
        String prefix = Integer.toString(networkHelper.getIPv4PrefixLength());
        FileUtils.writeString(new File(tmp, "network-ip"), ip != null ? ip + "\\n" : "");
        FileUtils.writeString(new File(tmp, "network-gateway"), gateway != null ? gateway + "\\n" : "");
        FileUtils.writeString(new File(tmp, "network-broadcast"), broadcast != null ? broadcast + "\\n" : "");
        FileUtils.writeString(new File(tmp, "network-prefix"), prefix + "\\n");
        FileUtils.writeString(new File(tmp, "network-status"), networkHelper.isConnected() ? "connected\\n" : "disconnected\\n");
    }

    private void updateNetworkResolverFiles(NetworkHelper networkHelper) {
        // Keep Wine/PRoot DNS resolution aligned with Android's active network.
        StringBuilder content = new StringBuilder();
        for (String dns : networkHelper.getDNSAddresses()) {
            if (dns != null && !dns.isEmpty()) content.append("nameserver ").append(dns).append("\\n");
        }
        if (content.length() == 0) content.append("nameserver 1.1.1.1\\n");
        File resolver = new File(environment.getRootFS().getRootDir(), "etc/resolv.conf");
        FileUtils.writeString(resolver, content.toString());
    }

    private void acquireWifiMulticastLock(Context context) {
        try {
            WifiManager wifiManager = (WifiManager)context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wifiManager != null) {
                multicastLock = wifiManager.createMulticastLock("Winlator-LAN");
                multicastLock.setReferenceCounted(false);
                multicastLock.acquire();
            }
        } catch (Exception ignored) {}
    }

'''
    if anchor not in s: raise SystemExit('NetworkInfoUpdateComponent file anchor not found')
    s = s.replace(anchor, addition + anchor, 1)

p.write_text(s, encoding='utf-8')
print('Android LAN networking fixed: active-network callbacks, real IPv4/prefix/gateway/broadcast/DNS files and Wi-Fi multicast lock enabled.')
