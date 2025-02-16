package com.bi4mol.morselink.utils

import android.content.Context
import android.content.SharedPreferences

// 配置管理器类
class ConfigManager(context: Context) {

    private val sharedPreferences: SharedPreferences = context.getSharedPreferences("config", Context.MODE_PRIVATE)

    init {
        initializeConfig()
    }

    // 初始化默认配置
    private fun initializeConfig() {
        val defaultConfigs = mapOf(
            ConfigKeys.CURRENT_VERSION to "1.0.0",
            ConfigKeys.FIRST_RUN_STATUS to true,
            ConfigKeys.MY_CALL to "请设置呼号",
            ConfigKeys.DOT_TIME to 110,
            ConfigKeys.DASH_TIME to 300,
            ConfigKeys.LETTER_INTERVAL_DURATION_TIME to 150,
            ConfigKeys.WORD_INTERVAL_DURATION_TIME to 320,
            ConfigKeys.SERVER_URL to "在这里请填写自己的服务器ip",
            ConfigKeys.SERVER_PORT to 1883,
            ConfigKeys.LANGUAGE to "any",
            ConfigKeys.BUZZ_FREQ to 800,
            ConfigKeys.AUTOKEY_STATUS to false,
            ConfigKeys.KEYBOARD_KEY to "81,87",
            ConfigKeys.SEND_BUZZ_STATUS to true,
            ConfigKeys.RECEIVE_BUZZ_STATUS to true,
            ConfigKeys.TRANSLATION_VISIBILITY to true,
            ConfigKeys.VISUALIZER_VISIBILITY to true,
            ConfigKeys.SENDER_FONT_SIZE to 15,
            ConfigKeys.MY_CHANNEL to 7000,
            ConfigKeys.MIN_WORD_LENGTH to 4,
            ConfigKeys.MAX_WORD_LENGTH to 4,
            ConfigKeys.MIN_GROUPS to 4,
            ConfigKeys.MAX_GROUPS to 4,
            ConfigKeys.LISTEN_WEIGHT to 0.2f,
            ConfigKeys.TOPIC to "123",
            ConfigKeys.WPM to 25
        )

        defaultConfigs.forEach { (key, value) ->
            if (!sharedPreferences.contains(key)) {
                setValue(key, value)
            }
        }
    }

    // 获取配置项的通用方法，类型安全
    private inline fun <reified T> getValue(key: String, default: T): T {
        return with(sharedPreferences) {
            when (T::class) {
                Boolean::class -> getBoolean(key, default as Boolean)
                Int::class -> getInt(key, default as Int)
                Float::class -> getFloat(key, default as Float)
                Long::class -> getLong(key, default as Long)
                String::class -> getString(key, default as String)
                else -> throw IllegalArgumentException("Unsupported type")
            } as T
        }
    }

    // 设置配置项的通用方法
    private fun setValue(key: String, value: Any?) {
        with(sharedPreferences.edit()) {
            when (value) {
                is Boolean -> putBoolean(key, value)
                is Int -> putInt(key, value)
                is Float -> putFloat(key, value)
                is Long -> putLong(key, value)
                is String -> putString(key, value)
            }
            commit()
        }
    }

    // 获取和设置具体配置项的方法
    fun setMyCall(value: String) = setValue(ConfigKeys.MY_CALL, value)
    fun getMyCall(): String = getValue(ConfigKeys.MY_CALL, "No call sign has been set")

    fun setFirstRunStatus(value: Boolean) = setValue(ConfigKeys.FIRST_RUN_STATUS, value)
    fun getFirstRunStatus(): Boolean = getValue(ConfigKeys.FIRST_RUN_STATUS, true)

    fun setWPM(value: Int) = setValue(ConfigKeys.WPM, value)
    fun getWPM(): Int = getValue(ConfigKeys.WPM, 25)

    fun setCurrentVersion(value: String) = setValue(ConfigKeys.CURRENT_VERSION, value)
    fun getCurrentVersion(): String = getValue(ConfigKeys.CURRENT_VERSION, "1.2.0")

    fun setDotTime(value: Int) = setValue(ConfigKeys.DOT_TIME, value)
    fun getDotTime(): Int = getValue(ConfigKeys.DOT_TIME, 110)

    fun setDashTime(value: Int) = setValue(ConfigKeys.DASH_TIME, value)
    fun getDashTime(): Int = getValue(ConfigKeys.DASH_TIME, 300)

    fun setLetterIntervalDurationTime(value: Int) = setValue(ConfigKeys.LETTER_INTERVAL_DURATION_TIME, value)
    fun getLetterIntervalDurationTime(): Int = getValue(ConfigKeys.LETTER_INTERVAL_DURATION_TIME, 150)

    fun setWordIntervalDurationTime(value: Int) = setValue(ConfigKeys.WORD_INTERVAL_DURATION_TIME, value)
    fun getWordIntervalDurationTime(): Int = getValue(ConfigKeys.WORD_INTERVAL_DURATION_TIME, 320)

    fun setServerUrl(value: String) = setValue(ConfigKeys.SERVER_URL, value)
    fun getServerUrl(): String = getValue(ConfigKeys.SERVER_URL, "117.72.10.141")

    fun setServerPort(value: Int) = setValue(ConfigKeys.SERVER_PORT, value)
    fun getServerPort(): Int = getValue(ConfigKeys.SERVER_PORT, 1883)

    fun setLanguage(value: String) = setValue(ConfigKeys.LANGUAGE, value)
    fun getLanguage(): String = getValue(ConfigKeys.LANGUAGE, "any")

    fun setBuzzFreq(value: Int) = setValue(ConfigKeys.BUZZ_FREQ, value)
    fun getBuzzFreq(): Int = getValue(ConfigKeys.BUZZ_FREQ, 800)

    fun setAutokeyStatus(value: Boolean) = setValue(ConfigKeys.AUTOKEY_STATUS, value)
    fun getAutokeyStatus(): Boolean = getValue(ConfigKeys.AUTOKEY_STATUS, false)

    fun setKeyboardKey(value: String) = setValue(ConfigKeys.KEYBOARD_KEY, value)
    fun getKeyboardKey(): String = getValue(ConfigKeys.KEYBOARD_KEY, "81,87")

    fun setSendBuzzStatus(value: Boolean) = setValue(ConfigKeys.SEND_BUZZ_STATUS, value)
    fun getSendBuzzStatus(): Boolean = getValue(ConfigKeys.SEND_BUZZ_STATUS, true)

    fun setReceiveBuzzStatus(value: Boolean) = setValue(ConfigKeys.RECEIVE_BUZZ_STATUS, value)
    fun getReceiveBuzzStatus(): Boolean = getValue(ConfigKeys.RECEIVE_BUZZ_STATUS, true)

    fun setTranslationVisibility(value: Boolean) = setValue(ConfigKeys.TRANSLATION_VISIBILITY, value)
    fun getTranslationVisibility(): Boolean = getValue(ConfigKeys.TRANSLATION_VISIBILITY, true)

    fun setVisualizerVisibility(value: Boolean) = setValue(ConfigKeys.VISUALIZER_VISIBILITY, value)
    fun getVisualizerVisibility(): Boolean = getValue(ConfigKeys.VISUALIZER_VISIBILITY, true)

    fun setSenderFontSize(value: Int) = setValue(ConfigKeys.SENDER_FONT_SIZE, value)
    fun getSenderFontSize(): Int = getValue(ConfigKeys.SENDER_FONT_SIZE, 15)

    fun setMyChannel(value: Int) = setValue(ConfigKeys.MY_CHANNEL, value)
    fun getMyChannel(): Int = getValue(ConfigKeys.MY_CHANNEL, 7000)

    fun setMinWordLength(value: Int) = setValue(ConfigKeys.MIN_WORD_LENGTH, value)
    fun getMinWordLength(): Int = getValue(ConfigKeys.MIN_WORD_LENGTH, 4)

    fun setMaxWordLength(value: Int) = setValue(ConfigKeys.MAX_WORD_LENGTH, value)
    fun getMaxWordLength(): Int = getValue(ConfigKeys.MAX_WORD_LENGTH, 4)

    fun setMinGroups(value: Int) = setValue(ConfigKeys.MIN_GROUPS, value)
    fun getMinGroups(): Int = getValue(ConfigKeys.MIN_GROUPS, 4)

    fun setMaxGroups(value: Int) = setValue(ConfigKeys.MAX_GROUPS, value)
    fun getMaxGroups(): Int = getValue(ConfigKeys.MAX_GROUPS, 4)

    fun setListenWeight(value: Float) = setValue(ConfigKeys.LISTEN_WEIGHT, value)
    fun getListenWeight(): Float = getValue(ConfigKeys.LISTEN_WEIGHT, 0.2f)

    fun setTopic(value: String) = setValue(ConfigKeys.TOPIC, value)
    fun getTopic(): String = getValue(ConfigKeys.TOPIC, "123")
}

// 键名常量
object ConfigKeys {
    const val CURRENT_VERSION = "Version/current_version"
    const val FIRST_RUN_STATUS = "Version/first_run_status"
    const val MY_CALL = "SelfInfo/my_call"
    const val DOT_TIME = "Time/dot_time"
    const val DASH_TIME = "Time/dash_time"
    const val LETTER_INTERVAL_DURATION_TIME = "Time/letter_interval_duration_time"
    const val WORD_INTERVAL_DURATION_TIME = "Time/word_interval_duration_time"
    const val SERVER_URL = "server/url"
    const val SERVER_PORT = "server/port"
    const val LANGUAGE = "Setting/language"
    const val BUZZ_FREQ = "Setting/buzz_freq"
    const val AUTOKEY_STATUS = "Setting/autokey_status"
    const val KEYBOARD_KEY = "Setting/keyborad_key"
    const val SEND_BUZZ_STATUS = "Setting/send_buzz_status"
    const val RECEIVE_BUZZ_STATUS = "Setting/receive_buzz_status"
    const val TRANSLATION_VISIBILITY = "Setting/translation_visibility"
    const val VISUALIZER_VISIBILITY = "Setting/visualizer_visibility"
    const val SENDER_FONT_SIZE = "Setting/sender_font_size"
    const val MY_CHANNEL = "Setting/my_channel"
    const val TOPIC = "Setting/topic"
    const val MIN_WORD_LENGTH = "Listen/min_word_length"
    const val MAX_WORD_LENGTH = "Listen/max_word_length"
    const val MIN_GROUPS = "Listen/min_groups"
    const val MAX_GROUPS = "Listen/max_groups"
    const val LISTEN_WEIGHT = "Listen/weight"
    const val WPM = "Decoder/wpm"
}