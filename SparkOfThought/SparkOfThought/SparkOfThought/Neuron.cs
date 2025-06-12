using System;
using System.Windows.Controls;
using System.Windows.Media; // Explicitly use System.Windows.Media.Color
using System.Windows.Shapes;
using VelcroPhysics.Dynamics;
using VelcroPhysics.Factories;
using VelcroPhysics.Collision.Shapes;
using System.Windows; // For SystemParameters
using Microsoft.Xna.Framework; // For Vector2

namespace SparkOfThought
{
    public class Neuron
    {
        public Body Body { get; private set; } // VelcroPhysics 物理体
        public string Word { get; set; }
        public Ellipse UiEllipse { get; private set; } // WPF 圆形UI
        public TextBlock UiTextBlock { get; private set; } // WPF 文字UI
        public Grid UiContainer { get; private set; } // 容器，用于组织圆形和文字

        private Config _config; // 持有配置引用，方便计算

        public Neuron(World world, string word, System.Windows.Media.Color color, Config config) // Explicitly use System.Windows.Media.Color
        {
            _config = config;
            Word = word;

            // 1. 随机生成初始目标质量
            double initialTargetMass = RandomProvider.NextDouble(_config.MinInitialMass, _config.MaxInitialMass);

            // 2. 根据目标质量和密度计算初始半径 (米单位)
            // 公式: Mass = Density * Area = Density * PI * R^2  => R = Sqrt(Mass / (Density * PI))
            float initialRadiusMeter = (float)Math.Sqrt(initialTargetMass / (_config.NeuronDensity * Math.PI));

            // 3. 将米单位半径转换为像素单位，并限制在配置的像素半径范围内
            double initialRadiusPx = initialRadiusMeter * _config.PixelsPerMeter;
            initialRadiusPx = Math.Max(_config.MinInitialRadius, Math.Min(_config.MaxInitialRadius, initialRadiusPx));

            // 4. 根据调整后的像素半径，重新计算米单位半径
            initialRadiusMeter = (float)(initialRadiusPx / _config.PixelsPerMeter);

            // 5. 根据最终确定的米单位半径和密度，计算实际的初始质量 (虽然VelcroPhysics内部会根据密度和形状计算，但这个值可以用于调试或验证)
            double actualInitialMass = _config.NeuronDensity * Math.PI * initialRadiusMeter * initialRadiusMeter;
            // 确保实际质量也在配置的质量范围内
            actualInitialMass = Math.Max(_config.MinNeuronMass, Math.Min(_config.MaxNeuronMass, actualInitialMass));


            // 创建物理体
            // VelcroPhysics的CreateCircle方法第三个参数是密度 (density)
            Body = BodyFactory.CreateCircle(world, initialRadiusMeter, (float)_config.NeuronDensity);
            Body.BodyType = BodyType.Dynamic;
            Body.Friction = 0f;
            Body.Restitution = 1.0f; // 完全弹性碰撞

            // 随机初始位置
            Body.Position = new Vector2(
                (float)(RandomProvider.NextDouble(initialRadiusPx, SystemParameters.PrimaryScreenWidth - initialRadiusPx) / _config.PixelsPerMeter),
                (float)(RandomProvider.NextDouble(initialRadiusPx, SystemParameters.PrimaryScreenHeight - initialRadiusPx) / _config.PixelsPerMeter)
            );

            // 随机初始速度
            float initialSpeedX = (float)RandomProvider.NextDouble(-_config.InitialSpeedMagnitude, _config.InitialSpeedMagnitude);
            float initialSpeedY = (float)RandomProvider.NextDouble(-_config.InitialSpeedMagnitude, _config.InitialSpeedMagnitude);
            Body.LinearVelocity = new Vector2(initialSpeedX, initialSpeedY);

            // 创建WPF UI元素
            UiEllipse = new Ellipse
            {
                Fill = new SolidColorBrush(color), // Use the passed System.Windows.Media.Color
                Stroke = Brushes.White,
                StrokeThickness = 2,
                Width = initialRadiusPx * 2, // 使用最终确定的像素半径设置UI大小
                Height = initialRadiusPx * 2
            };

            UiTextBlock = new TextBlock
            {
                Text = Word,
                Foreground = Brushes.White,
                FontWeight = FontWeights.Bold,
                TextAlignment = TextAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                TextWrapping = TextWrapping.Wrap // 允许文字换行
            };

            UiContainer = new Grid();
            UiContainer.Children.Add(UiEllipse);
            UiContainer.Children.Add(UiTextBlock);

            // 初始更新UI
            UpdateUi();
        }

        // 更新UI位置和大小
        public void UpdateUi()
        {
            if (Body == null || UiContainer == null) return;

            // Ensure FixtureList is not empty and shape is CircleShape
            if (Body.FixtureList.Count == 0 || !(Body.FixtureList[0].Shape is CircleShape circleShape))
            {
                // This indicates an issue with the body's fixture, maybe log an error or try to re-create it.
                // For now, return to prevent NullReferenceException.
                System.Diagnostics.Debug.WriteLine("Error: Neuron body does not have a CircleShape fixture or FixtureList is empty.");
                return;
            }

            // 获取当前物理体半径 (VelcroPhysics以米为单位，转换为像素)
            float currentRadiusMeter = circleShape.Radius;
            double currentRadiusPx = currentRadiusMeter * _config.PixelsPerMeter;

            // 更新圆形大小
            UiEllipse.Width = currentRadiusPx * 2;
            UiEllipse.Height = currentRadiusPx * 2;

            // 更新字体大小 (与半径等比缩放)
            // 根据圆的直径和文字长度调整字体大小，确保不溢出
            double desiredFontSize = currentRadiusPx * _config.FontScaleFactor;
            UiTextBlock.FontSize = Math.Max(8, desiredFontSize); // 确保最小字体可读性

            // 更新容器大小以匹配圆形
            UiContainer.Width = UiEllipse.Width;
            UiContainer.Height = UiEllipse.Height;

            // 更新UI元素在Canvas上的位置 (VelcroPhysics中心点，WPF左上角)
            Canvas.SetLeft(UiContainer, Body.Position.X * _config.PixelsPerMeter - currentRadiusPx);
            Canvas.SetTop(UiContainer, Body.Position.Y * _config.PixelsPerMeter - currentRadiusPx);
        }

        // 更新神经元质量和半径，并刷新其VelcroPhysics Fixture
        public void UpdateMassAndRadius(double newMass)
        {
            if (Body == null) return;

            // 限制质量在配置范围内
            newMass = Math.Max(_config.MinNeuronMass, Math.Min(_config.MaxNeuronMass, newMass));

            // 根据新的质量和密度计算新的半径 (米单位)
            // R = Sqrt(Mass / (Density * PI))
            float newRadiusMeter = (float)Math.Sqrt(newMass / (_config.NeuronDensity * Math.PI));

            // 移除旧的Fixture
            if (Body.FixtureList.Count > 0)
            {
                Fixture oldFixture = Body.FixtureList[0];
                Body.DestroyFixture(oldFixture); // Use Body.DestroyFixture
            }
            // 创建新的Fixture for the Body
            // This is the correct way to add a new fixture to an existing body.
            Body.CreateFixture(new CircleShape(newRadiusMeter, (float)_config.NeuronDensity));

            Body.ResetMassData(); // 重新计算Body的质量属性，如惯性
        }
    }

    // 随机数提供者 (线程安全)
    public static class RandomProvider
    {
        private static Random _random = new Random();
        private static object _lock = new object();

        public static double NextDouble(double min, double max)
        {
            lock (_lock)
            {
                return min + (_random.NextDouble() * (max - min));
            }
        }
    }
}