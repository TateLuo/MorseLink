package com.bi4mol.morselink.ui.home

import android.health.connect.datatypes.units.Length
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import androidx.annotation.RequiresApi
import androidx.fragment.app.Fragment
import com.bi4mol.morselink.customviews.MorseCodeAnimationView
import com.bi4mol.morselink.databinding.FragmentHomeBinding
import com.bi4mol.morselink.utils.*
import org.eclipse.paho.mqttv5.client.IMqttToken
import org.eclipse.paho.mqttv5.client.MqttCallback
import org.eclipse.paho.mqttv5.client.MqttDisconnectResponse
import org.eclipse.paho.mqttv5.common.MqttException
import org.eclipse.paho.mqttv5.common.MqttMessage
import org.eclipse.paho.mqttv5.common.packet.MqttProperties
import com.bi4mol.morselink.utils.AdaptiveMorseDecoder
import com.bi4mol.morselink.utils.ClientQueryTool

class HomeFragment : Fragment() , ClientQueryTool.ClientCountListener{

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!

    private lateinit var fallingBlockLayout: MorseCodeAnimationView

    // 声明蜂鸣器对象
    private lateinit var buzzer: Buzzer

    // 声明布局中的控件
    private lateinit var textReceivedCode: TextView
    private lateinit var editReceivedCode: TextView
    private lateinit var textReceivedCodeTranslation: TextView
    private lateinit var editReceivedCodeTranslation: TextView
    private lateinit var textSendCode: TextView
    private lateinit var editSendCode: TextView
    private lateinit var textSendCodeTranslation: TextView
    private lateinit var editSendCodeTranslation: TextView
    private lateinit var textClientsOnService: TextView

    private lateinit var btnConnectServer: Button
    private lateinit var btnCleanScreen: Button
    private lateinit var btnTransmitter: Button
    private lateinit var textChannel: TextView
    private lateinit var seekBarChannel: SeekBar

    //配置文件助手
    private lateinit var configManager : ConfigManager

    //查询服务器在线人数工具
    private lateinit var queryTool: ClientQueryTool

    // 解码相关变量
    private var morseCode: String = " "
    private var morseCodeForTranslate: String = ""
    private var receivedMorseCodeForTranslate: String = ""
    private var pressedStartTime: Long = 0
    private var pressedEndTime: Long = 0
    private var pressedIntervalTime: Long = 0
    private var letterIntervalTime: Long = 0
    private var wordIntervalTime: Long = 0
    private var lastPressedTime: Long = 0

    //解码器
    private lateinit var customDecoder: AdaptiveMorseDecoder

    //计时器
    private val timerManager = TimerManager()
    //解码器
    private val morseCodeTranslator = MorseCodeTranslator()
    private val jsonParser = JsonParser()

    private lateinit var mqttHelper: MqttHelper
    private lateinit var receivedMessageAudio: ReceivedMessageAudio

    private var isConnected = false
    private var urlServer = ""
    private var userName = "账号"
    private var password = "密码"
    private var topic = ""

    private var myCall: String = ""
    private var senderCall: String = ""
    private var myChannel: Int = 7141
    private var senderChannel: Int = 7141
    private var buzzerFrequency = 800
    private var sendBuzzerSwitch = true
    private var wpm:Int = 0

    //各个常量
    companion object {
        const val DEFAULT_DASH_TIME = 100L
        const val BUZZER_STOP_DELAY = 50L
        const val BUTTON_ANIMATION_DURATION = 100L
        const val DEFAULT_CHANNEL = 5
    }

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {

        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        val root: View = binding.root

        //调用用各个初始化函数
        initializeConfig()
        initializeUI()
        initializeMQTT()

        //按钮监听
        btnTransmitter.setOnTouchListener { v, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> handleButtonPress(v)
                MotionEvent.ACTION_UP -> handleButtonRelease(v)
                else -> false
            }
        }

        //清理屏幕按钮函数绑定
        btnCleanScreen.setOnClickListener { cleanScreen() }
        //连接服务器按钮函数绑定
        btnConnectServer.setOnClickListener { connectToServer() }

        //初始化在线人数查看器
        queryTool = ClientQueryTool.Builder(requireContext())
            .setBaseUrl(服务器ip)
            .setPort(端口)
            .setCredentials("账号", "密码")
            .setInterval(60000)
            .setListener(this)
            .build()

        return root
    }

    //初始化配置信息
    @RequiresApi(Build.VERSION_CODES.O)
    private fun initializeConfig() {
        configManager = ConfigManager(requireContext())

        letterIntervalTime = configManager.getLetterIntervalDurationTime().toLong()
        wordIntervalTime = configManager.getWordIntervalDurationTime().toLong()
        urlServer = "tcp://" + configManager.getServerUrl() + ":" + configManager.getServerPort()
        topic = configManager.getTopic()
        myCall = configManager.getMyCall()
        myChannel = configManager.getMyChannel()
        buzzerFrequency = configManager.getBuzzFreq()
        sendBuzzerSwitch = configManager.getSendBuzzStatus()
        wpm = configManager.getWPM()

        //初始化解码器
        customDecoder = AdaptiveMorseDecoder(initialWpm = wpm)

        Log.i("s","当前的呼号是$myCall")
        //偷个懒吧，检测下呼号是否设置
        if (myCall == "请设置呼号")
        {
            Toast.makeText(requireContext(),"请先在设置中设置呼号，否则将无法正常通联。若无呼号可编写虚拟呼号", Toast.LENGTH_LONG).show()
        }

    }

    //初始化UI中各个控件对象
    private fun initializeUI() {
        textReceivedCode = binding.textReceivedCode
        editReceivedCode = binding.editReceivedCode
        textReceivedCodeTranslation = binding.textReceivedCodeTranslation
        editReceivedCodeTranslation = binding.editReceivedCodeTranslation
        textSendCode = binding.textSendCode
        editSendCode = binding.editSendCode
        textSendCodeTranslation = binding.textSendCodeTranslation
        editSendCodeTranslation = binding.editSendCodeTranslation
        btnConnectServer = binding.btnConnectServer
        btnCleanScreen = binding.btnCleanScreen
        btnTransmitter = binding.btnTransmitter
        textClientsOnService = binding.textClientsOnService
        textChannel = binding.textChannel
        seekBarChannel = binding.seekBarChannel

        textChannel.setText("当前中心频率: $myChannel kHz")
        seekBarChannel.progress = myChannel


        editReceivedCode.isFocusable = false
        editReceivedCode.isSingleLine = true
        editReceivedCodeTranslation.isFocusable = false
        editReceivedCodeTranslation.isSingleLine = true
        editSendCode.isFocusable = false
        editSendCode.isSingleLine = true
        editSendCodeTranslation.isFocusable = false
        editSendCodeTranslation.isSingleLine = true

        fallingBlockLayout = binding.fallingBlockLayout
        fallingBlockLayout.setCurrentChannel(DEFAULT_CHANNEL)

        buzzer = Buzzer()
        receivedMessageAudio = ReceivedMessageAudio(fallingBlockLayout)

        // 频道滑动条监听
        binding.seekBarChannel.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                // 实时更新键速值
                binding.textChannel.setText("当前中心频率：$progress kHz")
                Log.i("SeekBar", "set text$progress")
                configManager.setMyChannel(progress)
                myChannel = progress

            }

            override fun onStartTrackingTouch(seekBar: SeekBar?) {
                // 用户开始拖动滑块时触发
            }

            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                // 用户停止拖动滑块时触发
            }
        })
    }

    //初始化MQTT对象
    private fun initializeMQTT() {
        mqttHelper = MqttHelper(urlServer, userName, password)
    }

    //mqtt的消息回调
    private fun setCallbackOfMQTT(){
        mqttHelper.setCallback(object : MqttCallback {
            override fun disconnected(disconnectResponse: MqttDisconnectResponse?) {
                Log.e("MQTT", "Disconnected: $disconnectResponse")
                updateConnectButtonText("连接至服务器")
            }

            override fun mqttErrorOccurred(exception: MqttException?) {
                Log.e("MQTT", "Error occurred: ${exception?.message}")
            }

            override fun messageArrived(topic: String?, message: MqttMessage?) {
                handleIncomingMessage(message.toString())
                println("接收到MQTT消息了")
            }

            override fun deliveryComplete(token: IMqttToken?) {
                Log.i("MQTT", "Message delivered: $token")
            }

            override fun connectComplete(reconnect: Boolean, serverURI: String?) {
                Log.i("MQTT", "Connected to $serverURI")
            }

            override fun authPacketArrived(reasonCode: Int, properties: MqttProperties?) {
                Log.i("MQTT", "Auth packet arrived: $reasonCode")
            }
        })
    }

    //连接服务器按钮点击事件
    @RequiresApi(Build.VERSION_CODES.O)
    private fun connectToServer() {
        if (mqttHelper.isConnected()) {
            // 显示断开连接的加载提示
            mqttHelper.disconnect {
                // 断开连接成功后
                updateUIForDisconnected()
            }
        } else {
            mqttHelper.connect(onConnected = {
                // 连接成功后
                setCallbackOfMQTT()
                updateUIForConnected()
                subscribeToTopic()
            }, onError = {
                // 连接失败时
                updateConnectButtonText("连接至服务器")
            })
        }
    }


    //连接成功后更新UI
    @RequiresApi(Build.VERSION_CODES.O)
    private fun updateUIForConnected() {
        isConnected = true
        updateConnectButtonText("断开连接")
        //开始查询在线人数
        queryTool.startPolling()

    }
    //断开连接成功后更新UI
    @RequiresApi(Build.VERSION_CODES.O)
    private fun updateUIForDisconnected() {
        isConnected = false
        updateConnectButtonText("连接至服务器")
        //停止查询在线人数
        queryTool.stopPolling()
    }

    //mqtt订阅主题
    private fun subscribeToTopic() {
        mqttHelper.subscribe(topic, onSubscribed = {
            Log.i("MQTT", "Subscribed to topic $topic")
        }, onError = {
            Log.e("MQTT", "Subscription failed: ${it.message}")
        })
    }

    //更新连接服务器按钮上的文字
    private fun updateConnectButtonText(text: String) {
        requireActivity().runOnUiThread {
            btnConnectServer.text = text
        }
    }

    //处理按钮按下事件
    private fun handleButtonPress(v: View): Boolean {
        //计算距离上一次按键的间隔
        val currentTime = System.currentTimeMillis()
        pressedIntervalTime = currentTime - lastPressedTime
        //如果大于200则直接为零
        if (pressedIntervalTime >50){
            pressedIntervalTime = 10
        }
        stopActiveTimers()
        fallingBlockLayout.startDrawing(DEFAULT_CHANNEL)
        buzzer.startBuzz()
        pressedStartTime = System.currentTimeMillis()
        showButtonPressAnimation(v)
        return true
    }

    //处理按钮松开事件
    private fun handleButtonRelease(v: View): Boolean {
        fallingBlockLayout.stopDrawing(DEFAULT_CHANNEL)
        val currentTime = System.currentTimeMillis()
        pressedEndTime = currentTime - pressedStartTime
        lastPressedTime = currentTime
        // 输入以毫秒为单位的时间间隔
        val (code) = customDecoder.processDuration(pressedEndTime.toDouble())
        morseCode = code.toString()
        morseCodeForTranslate += morseCode
        updateSendCodeUI(morseCode)
        buzzer.stopBuzz()
        showButtonReleaseAnimation(v)
        startLetterTimer()
        publishMorseCode()
        return true
    }

    //显示按钮按下动画
    private fun showButtonPressAnimation(v: View) {
        v.animate().scaleX(0.9f).scaleY(0.9f).setDuration(BUTTON_ANIMATION_DURATION).start()
    }

    //显示按钮松开动画
    private fun showButtonReleaseAnimation(v: View) {
        v.animate().scaleX(1f).scaleY(1f).setDuration(BUTTON_ANIMATION_DURATION).start()
    }

    //开始字母计时器
    private fun startLetterTimer() {
        timerManager.startLetterTimer(letterIntervalTime) {
            onLetterTimeOut()
        }
    }

    //开始单词计时器
    private fun startWordTimer() {
        timerManager.startWordTimer(wordIntervalTime) {
            onWordTimeOut()
        }
    }

    //开始禁用发射计时器
    private  fun onBanTransmit(){
        btnTransmitter.isEnabled = true
        btnTransmitter.setText("点击发报")
    }

    //字母计时器超时处理
    private fun onLetterTimeOut() {
        val translatedText = morseCodeTranslator.morseToText(morseCodeForTranslate)
        updateSendCodeTranslationUI(translatedText)
        morseCodeForTranslate = ""
        updateSendCodeUI("/")
        publishMorseCode("/")
        startWordTimer()
    }

    //单词计时器超时处理
    private fun onWordTimeOut() {
        updateSendCodeUI("//")
        publishMorseCode("//")
        updateSendCodeTranslationUI(" ")
    }

    //mqtt发送消息
    private fun publishMorseCode(code: String = morseCode) {
        println("即将发送的按下时间$pressedEndTime")
        val json = jsonParser.parseDataToJson(
            morseCode = code,
            myCall = myCall,
            pressedTime = pressedEndTime,
            pressedIntervalTime = pressedIntervalTime,
            myChannel = myChannel
        )
        println("即将发送的消息$json")
        mqttHelper.publish(topic, json)
    }

    //更新发送的消息到UI界面
    private fun updateSendCodeUI(code: String) {
        if (isTextOverflowing(editSendCode)) cleanScreen()
        editSendCode.append(code)
    }

    //更新发送解码消息到UI界面
    private fun updateSendCodeTranslationUI(text: String) {
        editSendCodeTranslation.append(text)
    }

    /**
     * 检测单行文本是否超出 TextView 的显示范围
     *
     * @param textView 要检测的 TextView
     * @return true 表示文本超出控件显示范围，false 表示未超出
     */
    private fun isTextOverflowing(textView: TextView): Boolean {
        // 获取控件的宽度（减去左右内边距）
        val textViewWidth = textView.width - textView.paddingStart - textView.paddingEnd

        // 获取文本的实际宽度
        val textWidth = textView.paint.measureText(textView.text.toString())

        // 返回比较结果
        return textWidth > textViewWidth
    }


    //处理mqtt接收的消息
    private fun handleIncomingMessage(message: String) {
        println("接收到的MQTT消息为$message")
        val parsedData = jsonParser.parseJsonData(message)
        senderCall = parsedData.myCall
        senderChannel = parsedData.myChannel
        if (senderCall != myCall) {
            processReceivedMorseCode(parsedData.morseCode, parsedData.pressedTime, parsedData.pressedIntervalTime, senderCall, senderChannel)

        }
    }

    //处理接收到的电码
    private fun processReceivedMorseCode(code: String, pressedTime: Long, intervalTime: Long, senderCall: String, channel: Int) {

        //收到电码则，禁用发射按钮3秒
        btnTransmitter.isEnabled = false
        btnTransmitter.setText("$senderCall 正在发报中，3秒内禁止发射")
        if (timerManager.isTimerRunning(TimerManager.TimerType.GENERIC)) {
            timerManager.stopGenericTimer()
        }
        timerManager.startGenericTimer(3000L){
            onBanTransmit()
        }

        when (code) {

            "/" -> {
                val text = morseCodeTranslator.morseToLetter(receivedMorseCodeForTranslate)
                updateReceivedCodeTranslationUI(text.toString())
                receivedMorseCodeForTranslate = ""
            }
            "//" -> updateReceivedCodeTranslationUI(" ")
            else -> {
                receivedMorseCodeForTranslate += code
                receivedMessageAudio.addMessage(intervalTime, pressedTime, myChannel, senderChannel)
                receivedMessageAudio.startPlaying()
                updateReceivedCodeUI(code)
            }
        }
    }

    //将接收的电码更新到UI
    private fun updateReceivedCodeUI(code: String) {
        if (isTextOverflowing(editReceivedCode)) cleanScreen()
        editReceivedCode.append(code)
    }

    //将接收到的电码翻译更新到UI
    private fun updateReceivedCodeTranslationUI(text: String) {
        editReceivedCodeTranslation.append(text)
    }

    //清理屏幕
    private fun cleanScreen() {
        listOf(editSendCode, editReceivedCode, editSendCodeTranslation, editReceivedCodeTranslation)
            .forEach { it.setText("") }
    }

    //停止所有计时器
    private fun stopActiveTimers() {
        if (timerManager.isTimerRunning(TimerManager.TimerType.LETTER)) {
            timerManager.stopLetterTimer()
        }
        if (timerManager.isTimerRunning(TimerManager.TimerType.WORD)) {
            timerManager.stopWordTimer()
        }
    }

    override fun onClientCountReceived(count: Int) {
        view?.post {
            binding.textClientsOnService.text = "服务器在线人数：$count"
        }
    }

    override fun onError(message: String) {
        view?.post {
            binding.textClientsOnService.text = "查询错误：$message"
            Log.i("ClientQueryTool", "$message")
        }
    }
}
