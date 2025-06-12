using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media; // Explicitly use System.Windows.Media.Color for WPF UI
using System.Windows.Threading;
using VelcroPhysics.Dynamics;
// REMOVED: using VelcroPhysics.Dynamics.Contacts; // Contact and Manifold are directly in VelcroPhysics.Dynamics
using VelcroPhysics.Factories;
using VelcroPhysics.Shared;
using VelcroPhysics.Utilities;
using VelcroPhysics.Dynamics.Joints; // Ensure this is present for MouseJoint
using System.Diagnostics;
using Microsoft.Xna.Framework; // For Vector2, which VelcroPhysics uses

// Added explicit using aliases for clarity and to resolve ambiguous references.
using WpfPoint = System.Windows.Point;
using WpfColor = System.Windows.Media.Color;
using VelcroPhysics.Collision.ContactSystem;
using VelcroPhysics.Collision.Narrowphase;

namespace SparkOfThought
{
    public partial class MainWindow : Window
    {
        // 声明字段时初始化，或确保在构造函数中赋值，以解决 CS8618 警告
        private World? _world;
        private List<Neuron> _neurons = new List<Neuron>();
        private Config? _currentConfig;
        private DispatcherTimer? _gameLoopTimer;
        private double _timeStep;

        private MouseJoint? _mouseJoint;
        private Neuron? _draggedNeuron;

        private WpfPoint _previousMousePosition;

        public MainWindow()
        {
            InitializeComponent();
            // 字段已在声明时初始化或标记为可空，因此此处不再需要显式赋值为 null
        }

        private async void Window_Loaded(object sender, RoutedEventArgs e)
        {
            // 加载配置
            _currentConfig = await Config.LoadAsync();
            if (_currentConfig == null) // Basic null check for loaded config
            {
                MessageBox.Show("Failed to load configuration. Using default settings.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                _currentConfig = new Config(); // Fallback to default if load fails
            }

            // 设置窗口为透明和鼠标穿透
            NativeMethods.MakeTransparentAndClickThrough(this);

            // 初始化VelcroPhysics世界
            _world = new World(Vector2.Zero); // 无重力

            // 创建世界边界 (墙体)
            CreateWorldBoundaries();

            // 初始化神经元
            InitializeNeurons();

            // 设置游戏循环计时器
            _timeStep = 1.0f / _currentConfig.FrameRate;
            _gameLoopTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(_timeStep) };
            _gameLoopTimer.Tick += GameLoop_Tick;
            _gameLoopTimer.Start();

            // 监听碰撞事件，用于质量转移
            // The signature for PreSolve is Contact contact, ref Manifold oldManifold
            _world.ContactManager.PreSolve += OnPreSolveCollision;
        }

        // 刷新所有神经元并重新加载配置
        public async void RefreshNeurons()
        {
            _gameLoopTimer?.Stop(); // Stop with null propagation

            // 清理旧的神经元
            if (_neurons != null && _world != null && MainCanvas != null) // Add null check for _neurons list and MainCanvas
            {
                foreach (var neuron in _neurons)
                {
                    _world.RemoveBody(neuron.Body); // Remove body from world
                    MainCanvas.Children.Remove(neuron.UiContainer);
                }
                _neurons.Clear();
            }

            // 重新加载配置
            _currentConfig = await Config.LoadAsync();
            if (_currentConfig == null)
            {
                MessageBox.Show("Failed to reload configuration. Using previous or default settings.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                _currentConfig = new Config(); // Fallback
            }

            // 重新初始化神经元
            InitializeNeurons();

            _gameLoopTimer?.Start(); // Restart with null propagation
        }

        private void CreateWorldBoundaries()
        {
            if (_currentConfig == null || _world == null) return;

            // 物理世界边界（米为单位）
            float screenWidthMeter = (float)(SystemParameters.PrimaryScreenWidth / _currentConfig.PixelsPerMeter);
            float screenHeightMeter = (float)(SystemParameters.PrimaryScreenHeight / _currentConfig.PixelsPerMeter);

            // 上墙
            BodyFactory.CreateEdge(_world, new Vector2(0, 0), new Vector2(screenWidthMeter, 0));
            // 下墙
            BodyFactory.CreateEdge(_world, new Vector2(0, screenHeightMeter), new Vector2(screenWidthMeter, screenHeightMeter));
            // 左墙
            BodyFactory.CreateEdge(_world, new Vector2(0, 0), new Vector2(0, screenHeightMeter));
            // 右墙
            BodyFactory.CreateEdge(_world, new Vector2(screenWidthMeter, 0), new Vector2(screenWidthMeter, screenHeightMeter));
        }

        private void InitializeNeurons()
        {
            if (_currentConfig == null || _world == null) return;

            _neurons.Clear(); // Clear existing neurons before adding new ones
            var availableWords = new List<string>(_currentConfig.Words); // 复制一份，防止删除
            var random = new Random();

            for (int i = 0; i < _currentConfig.Words.Count; i++)
            {
                if (availableWords.Count == 0) break;

                int wordIndex = random.Next(availableWords.Count);
                string word = availableWords[wordIndex];
                availableWords.RemoveAt(wordIndex); // 确保每个词语只使用一次

                // 随机颜色
                WpfColor randomColor = WpfColor.FromRgb( // Using WpfColor alias
                    (byte)random.Next(50, 200),
                    (byte)random.Next(50, 200),
                    (byte)random.Next(50, 200)
                );

                var neuron = new Neuron(_world, word, randomColor, _currentConfig);
                _neurons.Add(neuron);
                MainCanvas?.Children.Add(neuron.UiContainer); // Add with null propagation for MainCanvas
            }
        }

        private void GameLoop_Tick(object? sender, EventArgs e) // Added nullability for sender
        {
            _world?.Step((float)_timeStep); // Step with null propagation

            // 同步UI
            if (_neurons != null)
            {
                foreach (var neuron in _neurons)
                {
                    neuron.UpdateUi();
                }
            }
        }

        // 碰撞前处理 (用于质量转移)
        // Correct signature for PreSolve event
        private void OnPreSolveCollision(Contact contact, ref Manifold oldManifold)
        {
            if (_neurons == null || _currentConfig == null) return;

            // 获取碰撞的两个物理体
            Body bodyA = contact.FixtureA.Body;
            Body bodyB = contact.FixtureB.Body;

            // 查找对应的神经元对象
            Neuron? neuronA = _neurons.FirstOrDefault(n => n.Body == bodyA);
            Neuron? neuronB = _neurons.FirstOrDefault(n => n.Body == bodyB);

            if (neuronA == null || neuronB == null || neuronA == neuronB) return;

            // 随机决定质量转移方向
            bool transferAToB = RandomProvider.NextDouble(0, 1) > 0.5;

            double transferAmount = RandomProvider.NextDouble(_currentConfig.MinTransferAmount, _currentConfig.MaxTransferAmount);

            // 质量转移
            if (transferAToB)
            {
                // 从A转移到B
                double newMassA = neuronA.Body.Mass - transferAmount;
                double newMassB = neuronB.Body.Mass + transferAmount;

                // 确保质量不低于最小值，不高于最大值
                newMassA = Math.Max(_currentConfig.MinNeuronMass, newMassA);
                newMassB = Math.Min(_currentConfig.MaxNeuronMass, newMassB);

                // 应用质量变化
                neuronA.UpdateMassAndRadius(newMassA);
                neuronB.UpdateMassAndRadius(newMassB);
            }
            else
            {
                // 从B转移到A
                double newMassB = neuronB.Body.Mass - transferAmount;
                double newMassA = neuronA.Body.Mass + transferAmount;

                // 确保质量不低于最小值，不高于最大值
                newMassB = Math.Max(_currentConfig.MinNeuronMass, newMassB);
                newMassA = Math.Min(_currentConfig.MaxNeuronMass, newMassA);

                // 应用质量变化
                neuronB.UpdateMassAndRadius(newMassB);
                neuronA.UpdateMassAndRadius(newMassA);
            }
        }

        // 鼠标左键按下
        private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (_currentConfig == null || _world == null || _neurons == null) return;

            WpfPoint currentMousePositionWpf = e.GetPosition(this); // Get System.Windows.Point
            Vector2 mouseWorldPos = ConvertToWorldCoordinates(currentMousePositionWpf);

            // 查找被点击的神经元
            foreach (var neuron in _neurons)
            {
                // 手动进行射线检测 (鼠标点与神经元圆心距离 < 半径)
                // Ensure the FixtureList is not empty before accessing Shape
                if (neuron.Body.FixtureList.Count > 0 && neuron.Body.FixtureList[0].Shape is VelcroPhysics.Collision.Shapes.CircleShape circleShape)
                {
                    float currentRadiusMeter = circleShape.Radius;
                    if (Vector2.Distance(neuron.Body.Position, mouseWorldPos) <= currentRadiusMeter)
                    {
                        _draggedNeuron = neuron;
                        // CreateMouseJoint is a static method of JointFactory
                        // Ensure _world is not null before passing it to CreateMouseJoint
                        _mouseJoint = JointFactory.CreateMouseJoint(_world, _draggedNeuron.Body, mouseWorldPos);

                        // VelcroPhysics.Dynamics.Joints.MouseJoint 属性是正确的，如果报错，通常是包引用问题
                        _mouseJoint.MaxForce = 1000f * (float)_draggedNeuron.Body.Mass; // Cast to float for Vector2 multiplication
                        _mouseJoint.Frequency = 5.0f; // Oscillation frequency
                        _mouseJoint.DampingRatio = 0.9f; // Damping
                        break;
                    }
                }
            }

            _previousMousePosition = currentMousePositionWpf; // Store current mouse position (using WpfPoint alias)
        }

        // 鼠标移动
        private void Window_MouseMove(object sender, MouseEventArgs e)
        {
            if (_currentConfig == null || _neurons == null) return;

            WpfPoint currentMousePosition = e.GetPosition(this); // Using WpfPoint alias
            Vector2 mouseWorldPos = ConvertToWorldCoordinates(currentMousePosition);

            // 使用 'is not null' 进行 null 检查，更符合 C# 8+ 规范
            if (_mouseJoint is not null && _draggedNeuron is not null)
            {
                // If dragging, update MouseJoint's target position
                _mouseJoint.Target = mouseWorldPos;
            }
            else if (e.LeftButton == MouseButtonState.Released)
            {
                // If left mouse button is not pressed, calculate mouse velocity and apply impulse
                float deltaX = (float)(currentMousePosition.X - _previousMousePosition.X);
                float deltaY = (float)(currentMousePosition.Y - _previousMousePosition.Y);

                // Calculate velocity in pixels/second, then convert to meters/second
                Vector2 mouseVelocityPx = new Vector2(deltaX / (float)_timeStep, deltaY / (float)_timeStep);
                Vector2 mouseVelocityMeter = mouseVelocityPx / (float)_currentConfig.PixelsPerMeter; // Convert pixels/sec to meters/sec

                // Find neuron under mouse cursor
                foreach (var neuron in _neurons)
                {
                    if (neuron.Body.FixtureList.Count > 0 && neuron.Body.FixtureList[0].Shape is VelcroPhysics.Collision.Shapes.CircleShape circleShape)
                    {
                        float currentRadiusMeter = circleShape.Radius;
                        if (Vector2.Distance(neuron.Body.Position, mouseWorldPos) <= currentRadiusMeter)
                        {
                            // Apply impulse (Impulse = Mass * Velocity)
                            // The '*' operator for double * Vector2 is not directly supported, convert double to float first.
                            Vector2 impulse = (float)_currentConfig.MouseMass * mouseVelocityMeter * (float)_currentConfig.MouseImpulseScale;
                            // Debug.WriteLine($"Applying impulse: {impulse.Length()}");
                            neuron.Body.ApplyLinearImpulse(impulse, mouseWorldPos);
                            break; // Apply to only the first touched neuron
                        }
                    }
                }
            }

            _previousMousePosition = currentMousePosition; // Update previous frame mouse position (using WpfPoint alias)
        }

        // Mouse Left Button Up
        private void Window_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            // 使用 'is not null' 进行 null 检查
            if (_world is not null && _mouseJoint is not null)
            {
                _world.RemoveJoint(_mouseJoint);
                _mouseJoint = null;
                _draggedNeuron = null;
            }
        }

        // Convert WPF pixel coordinates to VelcroPhysics world coordinates (meters)
        private Vector2 ConvertToWorldCoordinates(WpfPoint screenPoint) // Using WpfPoint alias
        {
            if (_currentConfig == null) return Vector2.Zero; // Should not happen if loaded correctly

            return new Vector2(
                (float)(screenPoint.X / _currentConfig.PixelsPerMeter),
                (float)(screenPoint.Y / _currentConfig.PixelsPerMeter)
            );
        }

        private void Window_Closing(object? sender, System.ComponentModel.CancelEventArgs e) // Added nullability for sender
        {
            _gameLoopTimer?.Stop(); // Stop with null propagation
            _world?.Clear(); // Clear with null propagation
        }
    }
}