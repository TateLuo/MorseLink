package com.bi4mol.morselink.ui.setting

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.SeekBar
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.bi4mol.morselink.databinding.FragmentSettingBinding
import com.bi4mol.morselink.utils.ConfigManager

class SettingFragment : Fragment() {

    // 使用 ViewBinding 绑定布局
    private var _binding: FragmentSettingBinding? = null
    private val binding get() = _binding!!

    // 配置管理器
    private lateinit var configManager: ConfigManager

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        // 初始化 ViewBinding
        _binding = FragmentSettingBinding.inflate(inflater, container, false)
        val root: View = binding.root

        // 初始化配置管理器
        configManager = ConfigManager(requireContext())

        // 初始化 UI 和设置事件监听器
        setupUI()

        return root
    }

    private fun setupUI() {
        // 从配置文件中读取设置并初始化控件
        binding.editMyCall.setText(configManager.getMyCall()) // 从配置文件读取呼号
        binding.switchAutoKey.isChecked = configManager.getAutokeyStatus() // 自动发送状态
        binding.switchSendBuzz.isChecked = configManager.getSendBuzzStatus() // 发送音频状态
        binding.switchReceiveBuzz.isChecked = configManager.getReceiveBuzzStatus() // 接收音频状态
        binding.switchTranslationVisibility.isChecked = configManager.getTranslationVisibility() // 翻译可见性
        binding.switchVisualizerVisibility.isChecked = configManager.getVisualizerVisibility() // 可视化显示状态
        binding.seekBarBuzzFreq.progress = configManager.getBuzzFreq() // 音频频率
        binding.textBuzzFreq.setText("音频频率：${configManager.getBuzzFreq()} Hz")  // 音频频率
        binding.seekBarWPM.progress = configManager.getWPM() // wpm键速
        binding.textWpm.setText("WPM键速：${configManager.getWPM()} ")  // wpm键速

        // 设置事件监听器

        // 保存按钮
        binding.btnSave.setOnClickListener {
            saveSettings()
        }

        // 取消按钮
        binding.btnCancel.setOnClickListener {
            resetSettings()
        }

        // 音频频率滑动条监听
        binding.seekBarBuzzFreq.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                // 实时更新频率值
                //Toast.makeText(requireContext(), "当前频率: $progress Hz", Toast.LENGTH_SHORT).show()
                binding.textBuzzFreq.setText("当前音频频率：$progress Hz")
            }

            override fun onStartTrackingTouch(seekBar: SeekBar?) {
                // 用户开始拖动滑块时触发
            }

            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                // 用户停止拖动滑块时触发
            }
        })

        // wpm键速滑动条监听
        binding.seekBarWPM.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                // 实时更新键速值
                binding.textWpm.setText("WPM键速：$progress")
            }

            override fun onStartTrackingTouch(seekBar: SeekBar?) {
                // 用户开始拖动滑块时触发
            }

            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                // 用户停止拖动滑块时触发
            }
        })
    }

    // 保存设置
    private fun saveSettings() {
        val myCall = binding.editMyCall.text.toString() // 获取呼号
        println("当前填写呼号$myCall")
        val autoKeyEnabled = binding.switchAutoKey.isChecked
        val sendBuzzEnabled = binding.switchSendBuzz.isChecked
        val receiveBuzzEnabled = binding.switchReceiveBuzz.isChecked
        val translationVisible = binding.switchTranslationVisibility.isChecked
        val visualizerVisible = binding.switchVisualizerVisibility.isChecked
        val buzzFrequency = binding.seekBarBuzzFreq.progress
        val wpm = binding.seekBarWPM.progress

        // 将设置保存到配置文件
        configManager.setMyCall(myCall) // 保存呼号
        configManager.setAutokeyStatus(autoKeyEnabled)
        configManager.setSendBuzzStatus(sendBuzzEnabled)
        configManager.setReceiveBuzzStatus(receiveBuzzEnabled)
        configManager.setTranslationVisibility(translationVisible)
        configManager.setVisualizerVisibility(visualizerVisible)
        configManager.setBuzzFreq(buzzFrequency)
        configManager.setWPM(wpm)

        // 提示用户设置已保存
        Toast.makeText(requireContext(), "设置已保存", Toast.LENGTH_LONG).show()
    }

    // 重置设置
    private fun resetSettings() {
        // 恢复默认值
        binding.editMyCall.setText(configManager.getMyCall()) // 从配置文件重新读取呼号
        binding.switchAutoKey.isChecked = configManager.getAutokeyStatus()
        binding.switchSendBuzz.isChecked = configManager.getSendBuzzStatus()
        binding.switchReceiveBuzz.isChecked = configManager.getReceiveBuzzStatus()
        binding.switchTranslationVisibility.isChecked = configManager.getTranslationVisibility()
        binding.switchVisualizerVisibility.isChecked = configManager.getVisualizerVisibility()
        binding.seekBarBuzzFreq.progress = configManager.getBuzzFreq()

        Toast.makeText(requireContext(), "设置已重置为默认值", Toast.LENGTH_SHORT).show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        // 清除绑定，避免内存泄漏
        _binding = null
    }
}
