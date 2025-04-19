映象回响/
├── assets/             # 存放所有游戏资源
│   ├── images/         # 存放16张核心美图（原始或处理后的）
│   │   ├── stage1_1.png    # 根据设定去寻找/制作的图片
│   │   ├── stage1_2.png
│   │   └── ... (共16张)
│   ├── masks/          # 存放擦除蒙版纹理、无法擦除区域纹理等
│   │   ├── dust_mask.png   # 示例蒙版纹理
│   │   ├── fog_mask.png
│   │   ├── veil_mask.png
│   │   ├── structure_mask.png
│   │   ├── structure_overlay.png
│   │   └── ...
│   ├── effects/        # 存放粒子纹理、光晕纹理等特效相关图片
│   │   ├── sparkle.png
│   │   ├── glow.png
│   │   └── ...
│   ├── audio/          # 存放音乐和音效文件
│   │   ├── bgm_stage1.ogg  # 背景音乐
│   │   ├── sfx_click.wav   # 互动音效
│   │   ├── sfx_erase.wav
│   │   ├── sfx_puzzle_snap.wav
│   │   ├── sfx_complete.wav
│   │   ├── sfx_ai_subtle_1.wav # 示例AI声音音效
│   │   └── ...
│   ├── fonts/          # 存放游戏文本字体文件
│   │   └── YourFont.ttf # 游戏使用的字体文件
│   └── ui/             # 存放UI元素的图片资源（按钮、文本框背景等）
│       ├── button_next.png
│       ├── hint_gallery.png
│       └── ...
├── data/               # 存放游戏数据文件
│   └── image_config.json # JSON 文件，存储每张图的互动配置（点击点、擦除区、拼图、混合玩法序列等）
├── src/                # 存放主要的 Python 代码文件
│   ├── main.py         # 游戏主入口，初始化 Pygame，运行主循环
│   ├── settings.py     # 所有可调参数和配置
│   ├── game_manager.py # 游戏状态管理、阶段加载、流程控制
│   ├── ui_manager.py   # UI 元素的绘制和互动处理（文本框、按钮、进度条）
│   ├── image_renderer.py # 负责图片的加载、显示和各种艺术化效果的实现，处理缩放和裁剪
│   ├── input_handler.py  # 处理鼠标、键盘事件（包括Esc退出）
│   ├── interaction_modules/ # 存放不同互动玩法的具体实现模块
│   │   ├── click_reveal.py # 点击显影逻辑
│   │   ├── clean_erase.py  # 清洁擦除逻辑 (含RenderTexture模拟实现)
│   │   ├── drag_puzzle.py  # 拖拽拼图逻辑
│   │   └── hybrid_interaction.py # 混合玩法协调逻辑
│   ├── narrative_manager.py # 管理叙事文本的加载、逐字显示和触发
│   ├── audio_manager.py  # 管理背景音乐和音效播放，包括AI声音
│   ├── gallery_manager.py  # 画廊界面的逻辑和显示
│   └── save_manager.py   # 游戏进度保存和加载 (使用JSON)
├── README.md           # 项目说明文档
└── 《映象回响》设计文档.md # 本设计文档（你正在看的这份）