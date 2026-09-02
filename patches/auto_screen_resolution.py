from pathlib import Path

p = Path('app/src/main/java/com/winlator/XServerDisplayActivity.java')
s = p.read_text(encoding='utf-8')
s = s.replace('import android.os.Bundle;\n', 'import android.os.Bundle;\nimport android.os.Build;\nimport android.graphics.Rect;\nimport android.util.DisplayMetrics;\n')
old = 'screenInfo = new ScreenInfo(container.getScreenSize());'
new = 'screenInfo = autoDetectScreenInfo();'
if old not in s:
    raise SystemExit('container screenInfo assignment not found')
s = s.replace(old, new, 1)
old2 = 'screenInfo = new ScreenInfo(shortcut.getExtra("screenSize", container.getScreenSize()));'
new2 = '''String shortcutScreenSize = shortcut.getExtra("screenSize", "");
                screenInfo = shortcutScreenSize != null && !shortcutScreenSize.isEmpty() && !shortcutScreenSize.equalsIgnoreCase("auto")
                        ? new ScreenInfo(shortcutScreenSize) : autoDetectScreenInfo();'''
if old2 not in s:
    raise SystemExit('shortcut screenInfo assignment not found')
s = s.replace(old2, new2, 1)
marker = '    @Override\n    public void onCreate(Bundle savedInstanceState) {'
helper = '''    /** Automatically match the device display aspect ratio without forcing games to render at native 2K/3K resolution. */
    private ScreenInfo autoDetectScreenInfo() {
        int width;
        int height;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Rect bounds = getWindowManager().getCurrentWindowMetrics().getBounds();
            width = bounds.width();
            height = bounds.height();
        }
        else {
            DisplayMetrics metrics = new DisplayMetrics();
            getWindowManager().getDefaultDisplay().getRealMetrics(metrics);
            width = metrics.widthPixels;
            height = metrics.heightPixels;
        }

        if (width <= 0 || height <= 0) return new ScreenInfo(Container.DEFAULT_SCREEN_SIZE);

        boolean landscape = width >= height;
        int displayLong = Math.max(width, height);
        int displayShort = Math.min(width, height);
        float aspect = (float)displayLong / (float)Math.max(1, displayShort);

        int renderLong = displayLong >= 1800 ? 1600 : 1280;
        int renderShort = Math.round(renderLong / aspect);
        renderShort = Math.max(ScreenInfo.MIN_HEIGHT, Math.min(renderShort, 1080));

        renderLong = Math.max(ScreenInfo.MIN_WIDTH, (renderLong / 8) * 8);
        renderShort = Math.max(ScreenInfo.MIN_HEIGHT, (renderShort / 8) * 8);

        return landscape ? new ScreenInfo(renderLong, renderShort) : new ScreenInfo(renderShort, renderLong);
    }

'''
if marker not in s:
    raise SystemExit('onCreate marker not found')
s = s.replace(marker, helper + marker, 1)
p.write_text(s, encoding='utf-8')
print('Automatic screen resolution/aspect detection patch applied')
