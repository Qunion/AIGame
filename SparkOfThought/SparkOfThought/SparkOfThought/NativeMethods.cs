using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace SparkOfThought
{
    public static class NativeMethods
    {
        // Window styles
        public const int GWL_EXSTYLE = -20;
        public const int WS_EX_LAYERED = 0x00080000;
        public const int WS_EX_TRANSPARENT = 0x00000020;

        // Layered window attributes
        public const int LWA_ALPHA = 0x00000002;
        public const int LWA_COLORKEY = 0x00000001;

        // SetWindowPos flags
        public static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
        public static readonly IntPtr HWND_NOTOPMOST = new IntPtr(-2);
        public static readonly IntPtr HWND_TOP = new IntPtr(0);
        public static readonly IntPtr HWND_BOTTOM = new IntPtr(1);

        public const uint SWP_NOSIZE = 0x0001;
        public const uint SWP_NOMOVE = 0x0002;
        public const uint SWP_NOZORDER = 0x0004;
        public const uint SWP_NOREDRAW = 0x0008;
        public const uint SWP_NOACTIVATE = 0x0010;
        public const uint SWP_FRAMECHANGED = 0x0020;
        public const uint SWP_SHOWWINDOW = 0x0040;
        public const uint SWP_HIDEWINDOW = 0x0080;
        public const uint SWP_NOCOPYBITS = 0x0100;
        public const uint SWP_NOOWNERZORDER = 0x0200;
        public const uint SWP_NOREPOSITION = SWP_NOOWNERZORDER;
        public const uint SWP_NOSENDCHANGING = 0x0400;
        public const uint SWP_DEFERERASE = 0x2000;
        public const uint SWP_ASYNCWINDOWPOS = 0x4000;

        [DllImport("user32.dll")]
        public static extern int GetWindowLong(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll")]
        public static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);

        [DllImport("user32.dll")]
        public static extern bool SetLayeredWindowAttributes(IntPtr hWnd, uint crKey, byte bAlpha, uint dwFlags);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);


        // Helper to make a WPF window transparent and click-through
        public static void MakeTransparentAndClickThrough(Window window)
        {
            var hwnd = new WindowInteropHelper(window).Handle;
            int extendedStyle = GetWindowLong(hwnd, GWL_EXSTYLE);
            SetWindowLong(hwnd, GWL_EXSTYLE, extendedStyle | WS_EX_LAYERED | WS_EX_TRANSPARENT);

            // Set alpha to 255 (fully opaque) but allow transparency based on pixels
            // For WS_EX_TRANSPARENT to work correctly, LWA_ALPHA or LWA_COLORKEY is often needed first.
            // Setting alpha to 255 means no overall window transparency.
            SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA); // 0 is color key, 255 is alpha

            // Position and size the window to cover the primary screen
            // SetWindowPos flags: SWP_NOMOVE (no move), SWP_NOSIZE (no resize), etc.
            // For a "wallpaper" effect, you typically want it to fill the screen and be at the bottom of the Z-order.
            // HWND_BOTTOM makes it appear behind other normal windows.
            // To make it truly like a wallpaper (behind icons), it gets more complex
            // involving finding the desktop window handle. For a demo, HWND_BOTTOM is a good start.
            SetWindowPos(hwnd, HWND_BOTTOM, // HWND_BOTTOM for wallpaper effect. HWND_TOPMOST if you want it over everything
                         (int)SystemParameters.PrimaryScreenWidth / 2 - (int)window.Width / 2, // Centered horizontally
                         (int)SystemParameters.PrimaryScreenHeight / 2 - (int)window.Height / 2, // Centered vertically
                         (int)SystemParameters.PrimaryScreenWidth, // Full screen width
                         (int)SystemParameters.PrimaryScreenHeight, // Full screen height
                         SWP_SHOWWINDOW); // Ensure it's shown

            // For a true "wallpaper" effect that sits *below* desktop icons,
            // the Z-order adjustment is more tricky and often requires finding the
            // "Progman" or "WorkerW" windows and positioning relative to them.
            // For this demo, SWP_SHOWWINDOW and HWND_BOTTOM will make it fill the screen
            // and act as a background that is mouse-through.
        }
    }
}