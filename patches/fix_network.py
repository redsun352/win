from pathlib import Path

ROOT = Path('app/src/main/java/com/winlator')

# Extend the existing NetworkHelper with DNS and gateway discovery from Android's
# active network. Winlator already tracks interface addresses; this makes the
# container inherit usable resolver and gateway information as well.
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
            if (address != null && !address.isLoopbackAddress()) {
                result.add(address.getHostAddress());
            }
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
            if (gateway instanceof Inet4Address && !gateway.isAnyLocalAddress()) {
                return gateway.getHostAddress();
            }
        }
        return null;
    }

'''
    if anchor not in s:
        raise SystemExit('NetworkHelper anchor not found')
    s = s.replace(anchor, addition + anchor, 1)
    p.write_text(s, encoding='utf-8')

# Update the existing environment component so every container gets fresh
# /etc/resolv.conf plus diagnostic DNS/gateway files whenever connectivity changes.
p = ROOT / 'xenvironment/components/NetworkInfoUpdateComponent.java'
s = p.read_text(encoding='utf-8')

if 'updateNetworkResolverFiles(networkHelper);' not in s:
    s = s.replace('''        updateIFAddrsFile(networkHelper.getIFAddresses());
        updateEtcHostsFile(networkHelper.getIPv4Address());''', '''        updateIFAddrsFile(networkHelper.getIFAddresses());
        updateEtcHostsFile(networkHelper.getIPv4Address());
        updateNetworkResolverFiles(networkHelper);''', 1)
    s = s.replace('''                updateIFAddrsFile(networkHelper.getIFAddresses());
                updateEtcHostsFile(networkHelper.getIPv4Address());''', '''                updateIFAddrsFile(networkHelper.getIFAddresses());
                updateEtcHostsFile(networkHelper.getIPv4Address());
                updateNetworkResolverFiles(networkHelper);''', 1)

if 'private void updateNetworkResolverFiles' not in s:
    anchor = '''    private void updateEtcHostsFile(String ipAddress) {'''
    addition = '''    private void updateNetworkResolverFiles(NetworkHelper networkHelper) {
        File etcDir = new File(environment.getRootFS().getRootDir(), "etc");
        if (!etcDir.exists()) etcDir.mkdirs();

        List<String> dnsServers = networkHelper.getDNSAddresses();
        String resolv = "";
        for (String dns : dnsServers) {
            resolv += "nameserver " + dns + "\\n";
        }
        // Android can temporarily report no DNS servers during a network handover.
        // Keep a safe public fallback so Wine applications can still resolve hosts.
        if (resolv.isEmpty()) {
            resolv = "nameserver 1.1.1.1\\n" + "nameserver 8.8.8.8\\n";
        }
        FileUtils.writeString(new File(etcDir, "resolv.conf"), resolv);

        File tmpDir = environment.getRootFS().getTmpDir();
        String gateway = networkHelper.getGatewayAddress();
        FileUtils.writeString(new File(tmpDir, "network-dns"), resolv);
        FileUtils.writeString(new File(tmpDir, "network-gateway"), gateway != null ? gateway + "\\n" : "");
        FileUtils.writeString(new File(tmpDir, "network-status"),
                networkHelper.isConnected() ? "connected\\n" : "disconnected\\n");
    }

'''
    if anchor not in s:
        raise SystemExit('NetworkInfoUpdateComponent anchor not found')
    s = s.replace(anchor, addition + anchor, 1)
    p.write_text(s, encoding='utf-8')

print('Network resolver/gateway integration applied')
