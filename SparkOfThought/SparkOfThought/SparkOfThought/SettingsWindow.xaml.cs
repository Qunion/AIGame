using System;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace SparkOfThought
{
    public partial class SettingsWindow : Window
    {
        private Config _currentConfig;
        private MainWindow _mainWindow; // 引用主窗口，以便通知刷新

        public SettingsWindow(MainWindow mainWindow, Config initialConfig)
        {
            InitializeComponent();
            _mainWindow = mainWindow;
            _currentConfig = initialConfig;
            LoadSettingsToUI();
        }

        private void LoadSettingsToUI()
        {
            WordsListBox.ItemsSource = null; // 清除旧数据源
            WordsListBox.ItemsSource = _currentConfig.Words;

            MinInitialMassTextBox.Text = _currentConfig.MinInitialMass.ToString("F1");
            MaxInitialMassTextBox.Text = _currentConfig.MaxInitialMass.ToString("F1");
            MinInitialRadiusTextBox.Text = _currentConfig.MinInitialRadius.ToString("F1");
            MaxInitialRadiusTextBox.Text = _currentConfig.MaxInitialRadius.ToString("F1");
            InitialSpeedMagnitudeTextBox.Text = _currentConfig.InitialSpeedMagnitude.ToString("F1");
            MinTransferAmountTextBox.Text = _currentConfig.MinTransferAmount.ToString("F1");
            MaxTransferAmountTextBox.Text = _currentConfig.MaxTransferAmount.ToString("F1");
            MinNeuronMassTextBox.Text = _currentConfig.MinNeuronMass.ToString("F1");
            MaxNeuronMassTextBox.Text = _currentConfig.MaxNeuronMass.ToString("F1");
            MouseMassTextBox.Text = _currentConfig.MouseMass.ToString("F1");
            MouseImpulseScaleTextBox.Text = _currentConfig.MouseImpulseScale.ToString("F1");
            FontScaleFactorTextBox.Text = _currentConfig.FontScaleFactor.ToString("F1");
            NeuronDensityTextBox.Text = _currentConfig.NeuronDensity.ToString("F1"); // 加载 NeuronDensity
        }

        private void AddWord_Click(object sender, RoutedEventArgs e)
        {
            string newWord = NewWordTextBox.Text.Trim();
            if (!string.IsNullOrEmpty(newWord) && !_currentConfig.Words.Contains(newWord))
            {
                _currentConfig.Words.Add(newWord);
                WordsListBox.ItemsSource = null; // 刷新ListBox
                WordsListBox.ItemsSource = _currentConfig.Words;
                NewWordTextBox.Clear();
            }
        }

        private void NewWordTextBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter)
            {
                AddWord_Click(sender, e);
            }
        }

        private void RemoveWord_Click(object sender, RoutedEventArgs e)
        {
            var selectedWords = WordsListBox.SelectedItems.Cast<string>().ToList();
            foreach (var word in selectedWords)
            {
                _currentConfig.Words.Remove(word);
            }
            WordsListBox.ItemsSource = null; // 刷新ListBox
            WordsListBox.ItemsSource = _currentConfig.Words;
        }

        private void ConfigValue_TextChanged(object sender, TextChangedEventArgs e)
        {
            // Try to update config values as user types, or just mark dirty
            // For simplicity, we'll parse and apply on Save only to avoid frequent errors
        }

        private async void SaveSettings_Click(object sender, RoutedEventArgs e)
        {
            // 从UI读取并更新Config对象
            if (double.TryParse(MinInitialMassTextBox.Text, out double minIM)) _currentConfig.MinInitialMass = minIM;
            if (double.TryParse(MaxInitialMassTextBox.Text, out double maxIM)) _currentConfig.MaxInitialMass = maxIM;
            if (double.TryParse(MinInitialRadiusTextBox.Text, out double minIR)) _currentConfig.MinInitialRadius = minIR;
            if (double.TryParse(MaxInitialRadiusTextBox.Text, out double maxIR)) _currentConfig.MaxInitialRadius = maxIR;
            if (double.TryParse(InitialSpeedMagnitudeTextBox.Text, out double initialSpeed)) _currentConfig.InitialSpeedMagnitude = initialSpeed;
            if (double.TryParse(MinTransferAmountTextBox.Text, out double minTA)) _currentConfig.MinTransferAmount = minTA;
            if (double.TryParse(MaxTransferAmountTextBox.Text, out double maxTA)) _currentConfig.MaxTransferAmount = maxTA;
            if (double.TryParse(MinNeuronMassTextBox.Text, out double minNM)) _currentConfig.MinNeuronMass = minNM;
            if (double.TryParse(MaxNeuronMassTextBox.Text, out double maxNM)) _currentConfig.MaxNeuronMass = maxNM;
            if (double.TryParse(MouseMassTextBox.Text, out double mouseM)) _currentConfig.MouseMass = mouseM;
            if (double.TryParse(MouseImpulseScaleTextBox.Text, out double mouseIS)) _currentConfig.MouseImpulseScale = mouseIS;
            if (double.TryParse(FontScaleFactorTextBox.Text, out double fontSF)) _currentConfig.FontScaleFactor = fontSF;
            if (double.TryParse(NeuronDensityTextBox.Text, out double neuronD)) _currentConfig.NeuronDensity = neuronD; // 保存 NeuronDensity

            // 保存到文件
            await _currentConfig.SaveAsync();

            // 通知主窗口刷新神经元
            _mainWindow?.RefreshNeurons();

            MessageBox.Show("设置已保存并刷新神经元。", "保存成功", MessageBoxButton.OK, MessageBoxImage.Information);
            this.Close(); // 关闭设置窗口
        }
    }
}