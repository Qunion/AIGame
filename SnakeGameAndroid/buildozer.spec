[app]

# (必需) 应用的标题，会显示在手机上
title = 贪吃蛇 Kivy

# (必需) 应用的包名，格式通常是 com.yourdomain.yourapp
package.name = snakesnake

# (必需) 应用的包域名
package.domain = org.kivy.games

# (必需) 主程序入口文件
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,spec,json,wav,ogg,mp3 # 确保包含所有资源类型

# (必需) 应用版本号
version = 0.1

# (必需) 应用运行所需的库，kivy是必须的
# 如果用到其他库（比如后面可能需要的 numpy 用于计算），也要加在这里
requirements = python3,kivy,pillow

# (推荐) 应用图标文件 (需要你提供一个 icon.png 在项目根目录)
icon.filename = %(source.dir)s/assets/images/icon.png

# (推荐) 应用启动画面图片 (需要你提供一个 presplash.png 在项目根目录)
# presplash.filename = %(source.dir)s/assets/images/presplash.png

# (必需) 应用屏幕方向设置为横屏
orientation = landscape

# (可选) 如果应用需要访问网络（比如未来可能加排行榜），需要这个权限
# android.permissions = INTERNET

# (可选) 如果需要震动反馈
# android.permissions = VIBRATE

# (必需) 指定目标 Android API Level (与你安装的 SDK Platforms 对应)
# 建议使用较新的稳定版本，比如 33 (Android 13) 或 34 (Android 14)
android.api = 33
android.minapi = 21 # 最低支持的 API Level (Android 5.0)

# (推荐) 全屏模式，隐藏状态栏和导航栏
fullscreen = 1

# (重要) 包含你的资源文件
source.include_patterns = assets/*, assets/images/*, assets/sounds/*

# (可选) Buildozer 使用的 Android NDK 版本 (应与你安装的版本匹配)
# 如果你有多个 NDK 版本，可以指定一个，比如 25.1.8937393
# android.ndk = 25c # 或者具体的版本号 25.1.8937393

# (可选) JDK 路径，通常 Buildozer 能自动找到，如果不行可以手动指定
# android.jdk_path = C:/Program Files/Java/jdk-18.0.2.1/

# (可选) SDK 路径，通常 Buildozer 能自动找到，如果不行可以手动指定
# android.sdk_path = C:/Users/admin/AppData/Local/Android/Sdk/

# (可选) NDK 路径，通常 Buildozer 能自动找到，如果不行可以手动指定
# android.ndk_path = C:/Users/admin/AppData/Local/Android/Sdk/ndk/25.1.8937393/


[buildozer]

# (可选) 日志级别 (0 = error, 1 = warning, 2 = info, 3 = debug)
log_level = 2

# (可选) 警告模式 (0 = no warnings, 1 = show warnings)
warn_on_root = 1
