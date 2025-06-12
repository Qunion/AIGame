using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

namespace SparkOfThought
{
    public class Config
    {
        public List<string> Words { get; set; } = new List<string>
        {
            "创新", "灵感", "智慧", "连接", "探索", "发现", "知识", "思想", "火花", "洞察",
            "成长", "突破", "视角", "迭代", "重构", "机遇", "挑战", "未来", "梦想", "勇气"
        };

        public double MinInitialMass { get; set; } = 1.0;
        public double MaxInitialMass { get; set; } = 5.0;

        public double MinInitialRadius { get; set; } = 20.0; // 初始半径，实际半径会根据质量动态调整
        public double MaxInitialRadius
        {
            get; set; = 50.0;

        public double InitialSpeedMagnitude { get; set; } = 50.0; // 神经元初始随机速度的最大值

        public double MinTransferAmount { get; set; } = 0.1; // 每次碰撞质量转移的最小值
        public double MaxTransferAmount { get; set; } = 0.5; // 每次碰撞质量转移的最大值

        public double MinNeuronMass { get; set; } = 0.5; // 神经元最小质量阈值
        public double MaxNeuronMass { get; set; } = 10.0; // 神经元最大质量

        public double MouseMass { get; set; } = 1.0; // 鼠标的初始质量，0表示无质量
        public double MouseImpulseScale { get; set; } = 0.1; // 鼠标施加冲量的额外缩放因子

        public double FontScaleFactor { get; set; } = 0.5; // 字体大小相对于半径的缩放因子

        public double PixelsPerMeter { get; set; } = 50.0; // 物理世界单位到像素的转换比例

        public double NeuronDensity { get; set; } = 1.0; // 神经元的物理密度 (用于质量-半径计算)

        public int FrameRate { get; set; } = 60; // 物理模拟和UI更新的帧率

        private static string ConfigFilePath => "config.json";

        public static async Task<Config> LoadAsync()
        {
            if (File.Exists(ConfigFilePath))
            {
                try
                {
                    string jsonString = await File.ReadAllTextAsync(ConfigFilePath);
                    var options = new JsonSerializerOptions { WriteIndented = true };
                    // 使用 ?? new Config() 确保即使反序列化结果为 null 也返回一个默认实例，解决 CS8603 警告
                    return JsonSerializer.Deserialize<Config>(jsonString, options) ?? new Config();
                }
                catch (JsonException ex)
                {
                    // Log or handle error if JSON is malformed
                    System.Diagnostics.Debug.WriteLine($"Error loading config: {ex.Message}");
                    return new Config(); // Return default if loading fails
                }
            }
            else
            {
                var defaultConfig = new Config();
                await defaultConfig.SaveAsync(); // Create default config file
                return defaultConfig;
            }
        }

        public async Task SaveAsync()
        {
            var options = new JsonSerializerOptions { WriteIndented = true };
            string jsonString = JsonSerializer.Serialize(this, options);
            await File.WriteAllTextAsync(ConfigFilePath, jsonString);
        }
    }
}