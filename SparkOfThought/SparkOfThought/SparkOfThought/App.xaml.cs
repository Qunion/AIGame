using System.Windows;

namespace SparkOfThought
{
    /// <summary>
    /// Interaction logic for App.xaml
    /// </summary>
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);

            // 设置程序在所有窗口关闭后不自动退出
            // 这样可以在后台通过托盘图标管理
            ShutdownMode = ShutdownMode.OnExplicitShutdown;

            // 这里可以启动托盘图标
            // For now, we'll just show the main window.
            // A full tray icon implementation would replace StartupUri and manage window visibility.
        }
    }
}