映象回响/
├── assets/             # 存放所有游戏资源
│   ├── images/         # 存放16张核心美图（原始或处理后的）
│   │   ├── stage1_1.png    # 根据设定去寻找/制作的图片
│   │   ├── stage1_2.png
│   │   └── ... (共16张)
│   │   ├── background_vertical.png # 竖屏背景图
│   │   └── background_horizontal.png # 横屏背景图
│   ├── masks/          # 存放擦除蒙版纹理、无法擦除区域纹理等
│   │   ├── dust_mask.png   # 示例蒙版纹理
│   │   ├── fog_mask.png
│   │   ├── veil_mask.png
│   │   ├── structure_mask.png # Stage 5 剥离蒙版
│   │   ├── structure_overlay.png # Stage 5 叠加效果
│   │   └── ...
│   ├── effects/        # 存放粒子纹理、光晕纹理等特效相关图片
│   │   ├── sparkle.png
│   │   ├── glow.png
│   │   ├── anomaly_flash.png # Stage 3.2 异常点特效
│   │   ├── puzzle_fragment_flash.png # Stage 3.3 碎片轮廓闪烁
│   │   ├── core_activation.png # Stage 4.3 核心激活特效
│   │   ├── self_sculpt_complete.png # Stage 5.3 自我塑形完成特效
│   │   ├── resonance_pulse_blue.png # Stage 6.1 共振特效
│   │   ├── connection_established.png # Stage 6.2 连接特效
│   │   └── ...
│   ├── audio/          # 存放音乐和音效文件
│   │   ├── bgm_stage1.ogg  # 背景音乐
│   │   ├── sfx_click.wav   # 互动音效
│   │   ├── sfx_erase_looping.wav # 循环擦除音效 (需要手动停止)
│   │   ├── sfx_puzzle_pickup.wav # 拼图拾起音效
│   │   ├── sfx_puzzle_drop.wav # 拼图放下音效
│   │   ├── sfx_puzzle_snap.wav # 拼图吸附音效
│   │   ├── sfx_puzzle_complete.wav # 拼图完成音效
│   │   ├── sfx_ui_click.wav # UI点击音效
│   │   ├── sfx_ui_hover.wav # UI悬停音效 (画廊用到)
│   │   ├── sfx_ui_back.wav # 返回音效 (画廊用到)
│   │   ├── sfx_gallery_enter.wav # 进入画廊音效
│   │   ├── sfx_gallery_exit.wav # 退出画廊音效
│   │   ├── sfx_gallery_hint.wav # 画廊提示音
│   │   ├── sfx_game_complete.wav # 游戏完成音效 (Stage 6.2)
│   │   ├── sfx_ai_subtle_1.wav # 示例AI声音音效
│   │   └── ... # 包含所有在 settings.py 中定义的 AI_SOUND_EFFECTS 文件
│   ├── fonts/          # 存放游戏文本字体文件
│   │   └── YourFont.ttf # 游戏使用的字体文件
│   └── ui/             # 存放UI元素的图片资源（按钮、文本框背景等）
│       ├── button_next.png
│       ├── hint_gallery.png
│       └── ... # TODO: 根据UI设计添加其他按钮、进度条、画廊元素等图片资源
├── data/               # 存放游戏数据文件
│   └── image_config.json # JSON 文件，存储每张图的互动配置（点击点、擦除区、拼图、混合玩法序列等）
├── src/                # 存放主要的 Python 代码文件
│   ├── main.py         # 游戏主入口，初始化 Pygame，运行主循环
│   ├── settings.py     # 所有可调参数和配置
│   ├── game_manager.py # 游戏状态管理、阶段加载、流程控制
│   ├── ui_manager.py   # UI 元素的绘制和互动处理（文本框、按钮、进度条）
│   ├── image_renderer.py # 负责图片的加载、缩放、裁剪、显示和各种艺术化效果的实现
│   ├── input_handler.py  # 处理鼠标、键盘事件（包括Esc退出）
│   ├── interaction_modules/ # 存放不同互动玩法的具体实现模块
│   │   ├── click_reveal.py # Click Reveal 逻辑
│   │   ├── clean_erase.py  # Clean Erase 逻辑 (含RenderTexture模拟实现)
│   │   ├── drag_puzzle.py  # Drag Puzzle 逻辑
│   │   ├── puzzle_piece.py # 拼图碎片类
│   │   └── hybrid_interaction.py # 混合玩法协调逻辑
│   ├── narrative_manager.py # 管理叙事文本的加载、逐字显示和触发
│   ├── audio_manager.py  # 管理背景音乐和音效播放，包括AI声音
│   ├── gallery_manager.py  # 画廊界面的逻辑和显示
│   └── save_manager.py   # 游戏进度保存和加载 (使用JSON)
├── README.md           # 项目说明文档
└── 《映象回响》设计文档.md # 本设计文档