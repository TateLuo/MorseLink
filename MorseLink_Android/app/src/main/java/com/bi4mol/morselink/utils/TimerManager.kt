package com.bi4mol.morselink.utils

import kotlinx.coroutines.*

/**
 * TimerManager - 管理两个独立计时器：字母计时器和单词计时器。
 */
class TimerManager {

    // 定义计时器类型
    enum class TimerType { LETTER, WORD, GENERIC }

    // 每个计时器的状态和任务信息
    private data class TimerState(
        var job: Job? = null,        // 协程 Job，用于控制计时器
        var isRunning: Boolean = false // 标记计时器是否正在运行
    )

    // 独立的计时器状态
    private val letterTimer = TimerState()
    private val wordTimer = TimerState()
    private val genericTimer = TimerState() // 新增的通用计时器

    /**
     * 启动字母计时器
     * @param timeoutMillis Long - 超时时间（毫秒）
     * @param onTimeout () -> Unit - 超时后执行的回调
     */
    fun startLetterTimer(timeoutMillis: Long, onTimeout: () -> Unit) {
        startTimer(letterTimer, timeoutMillis, onTimeout)
    }

    /**
     * 停止字母计时器
     */
    fun stopLetterTimer() {
        stopTimer(letterTimer)
    }

    /**
     * 启动单词计时器
     * @param timeoutMillis Long - 超时时间（毫秒）
     * @param onTimeout () -> Unit - 超时后执行的回调
     */
    fun startWordTimer(timeoutMillis: Long, onTimeout: () -> Unit) {
        startTimer(wordTimer, timeoutMillis, onTimeout)
    }

    /**
     * 停止单词计时器
     */
    fun stopWordTimer() {
        stopTimer(wordTimer)
    }

    /**
     * 启动通用计时器
     * @param timeoutMillis Long - 超时时间（毫秒）
     * @param onTimeout () -> Unit - 超时后执行的回调
     */
    fun startGenericTimer(timeoutMillis: Long, onTimeout: () -> Unit) {
        startTimer(genericTimer, timeoutMillis, onTimeout)
    }

    /**
     * 停止通用计时器
     */
    fun stopGenericTimer() {
        stopTimer(genericTimer)
    }

    /**
     * 检查指定计时器是否正在运行
     * @param timerType TimerType - 计时器类型
     * @return Boolean - 返回计时器是否正在运行
     */
    fun isTimerRunning(timerType: TimerType): Boolean {
        return when (timerType) {
            TimerType.LETTER -> letterTimer.isRunning
            TimerType.WORD -> wordTimer.isRunning
            TimerType.GENERIC -> genericTimer.isRunning // 检查通用计时器状态
        }
    }

    /**
     * 启动指定计时器
     * @param timerState TimerState - 计时器状态对象
     * @param timeoutMillis Long - 超时时间（毫秒）
     * @param onTimeout () -> Unit - 超时后执行的回调
     */
    private fun startTimer(timerState: TimerState, timeoutMillis: Long, onTimeout: () -> Unit) {
        // 停止当前计时器（如果已经运行）
        stopTimer(timerState)

        // 设置计时器为运行状态并启动协程
        timerState.isRunning = true
        timerState.job = CoroutineScope(Dispatchers.Main).launch {
            delay(timeoutMillis) // 等待超时时间

            if (timerState.isRunning) {
                onTimeout() // 执行超时回调
            }

            timerState.isRunning = false // 超时后标记为停止状态
        }
    }

    /**
     * 停止指定计时器
     * @param timerState TimerState - 计时器状态对象
     */
    private fun stopTimer(timerState: TimerState) {
        timerState.job?.cancel() // 取消协程任务
        timerState.isRunning = false // 标记计时器为停止状态
    }
}
