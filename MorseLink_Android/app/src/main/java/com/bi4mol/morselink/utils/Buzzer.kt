package com.bi4mol.morselink.utils

import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import kotlin.math.PI
import kotlin.math.sin

class Buzzer(
    private val sampleRate: Int = 44100, // 采样率
    private var frequency: Double = 440.0 // 默认频率
) {
    private var audioTrack: AudioTrack? = null
    private var buffer: ShortArray? = null
    @Volatile
    private var isBuzzing = false // 播放状态标志

    init {
        // 缓存音频数据
        buffer = generateSineWave(frequency, 50) // 生成 50ms 的音频数据
    }

    /**
     * 开始播放音频
     */
    fun startBuzz() {
        if (isBuzzing) return // 防止重复调用
        isBuzzing = true

        // 初始化 AudioTrack
        initAudioTrack(buffer!!.size)

        // 播放音频
        audioTrack?.apply {
            play()
            Thread {
                while (isBuzzing) {
                    write(buffer!!, 0, buffer!!.size)
                }
            }.start()
        }
    }

    /**
     * 停止音频播放
     */
    fun stopBuzz() {
        isBuzzing = false
        audioTrack?.apply {
            stop()
            release()
        }
        audioTrack = null
    }

    /**
     * 动态调整频率
     */
    fun setFrequency(newFrequency: Double) {
        if (newFrequency <= 0) return
        frequency = newFrequency
        buffer = generateSineWave(frequency, 50) // 重新生成音频数据
    }

    /**
     * 生成正弦波音频数据
     * @param frequency 音频频率
     * @param durationMs 数据持续时长（毫秒）
     */
    private fun generateSineWave(frequency: Double, durationMs: Int): ShortArray {
        val numSamples = (sampleRate * durationMs / 1000.0).toInt()
        val wave = ShortArray(numSamples)
        val increment = 2 * PI * frequency / sampleRate
        var angle = 0.0
        for (i in wave.indices) {
            wave[i] = (Short.MAX_VALUE * sin(angle)).toInt().toShort()
            angle += increment
        }
        return wave
    }

    /**
     * 初始化 AudioTrack
     */
    private fun initAudioTrack(bufferSize: Int) {
        val minBufferSize = AudioTrack.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )
        audioTrack = AudioTrack(
            AudioManager.STREAM_MUSIC,
            sampleRate,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            minBufferSize.coerceAtLeast(bufferSize),
            AudioTrack.MODE_STREAM
        )
    }
}
