package com.bi4mol.morselink.utils

import com.bi4mol.morselink.customviews.MorseCodeAnimationView

/**
 * 管理蜂鸣器和动画播放的工具类。
 * 使用 TimerManager 控制计时。
 * @param fallingBlockLayout 控制动画的自定义视图
 */
class ReceivedMessageAudio(
    private val fallingBlockLayout: MorseCodeAnimationView,
) {
    //计时器TimerManager
    private val timerIntervalManager = TimerManager()

    //计时器TimerManager
    private val timePlaylManager = TimerManager()

    //控制蜂鸣器的接口
    private val buzzer= Buzzer()

    //播放的通道
    private var playChannel: Int = 5


    // 任务列表，任务格式为 (间隔时间, 播放时间)
    // 定义四元组数据类（推荐）
    data class Task(
        val interval: Long,
        val duration: Long,
        val myChannel: Int,
        val senderChannel: Int
    )

    // 修改任务列表声明
    private val taskList = mutableListOf<Task>()

    // 标志当前是否正在播放任务
    private var isPlaying = false

    /**
     * 添加任务到列表
     *
     * @param intervalTime 任务开始前的等待时间（毫秒）
     * @param playTime 蜂鸣器播放的持续时间（毫秒）
     */
    fun addMessage(intervalTime: Long, playTime: Long, myChannel: Int, senderChannel: Int) {
        taskList.add(Task(intervalTime, playTime, myChannel, senderChannel))
    }

    /**
     * 开始播放接收音频任务
     * 如果当前已经在播放，则直接返回。
     */
    fun startPlaying() {
        if (isPlaying) return // 如果正在播放，不重复启动
        isPlaying = true

        // 按顺序执行任务
        playNextTask()
    }

    /**
     * 停止播放并清空任务列表
     * 调用此方法将终止当前的播放任务。
     */
    fun stopPlaying() {
        isPlaying = false
        taskList.clear() // 清空任务列表

        // 停止蜂鸣器和动画
        buzzer.stopBuzz()
        fallingBlockLayout.stopDrawing(6)

        // 停止通用计时器
        timerIntervalManager.stopGenericTimer()

        println("播放已停止，任务列表已清空")
    }

    /**
     * 播放下一个任务
     */
    private fun playNextTask() {
        if (!isPlaying || taskList.isEmpty()) {
            isPlaying = false
            println("所有任务已完成")
            return
        }

        // 获取并移除列表中的第一个任务
        val (intervalTime, playTime, myChannel, senderChannel) = taskList.removeAt(0)
        playChannel = getPlayChannel(myChannel, senderChannel)
        // 使用 TimerManager 等待间隔时间
        timerIntervalManager.startGenericTimer(intervalTime) {
            onIntervalTimeout(playTime)
            timerIntervalManager.stopGenericTimer()
        }
    }

    /**
     * 任务间隔超时后的逻辑
     *
     * @param playTime Long - 蜂鸣器播放的持续时间（毫秒）
     */
    private fun onIntervalTimeout(playTime: Long) {
        //5是最中间的通道
        if (playChannel == 5){
            // 开始播放蜂鸣器和动画
            buzzer.startBuzz()
            fallingBlockLayout.startDrawing(playChannel)
            println("开始播放任务：播放 $playTime 毫秒")
        }
        else{
            // 开始播放动画
            fallingBlockLayout.startDrawing(playChannel)
            println("开始播放任务：播放 $playTime 毫秒")
        }


        // 使用 TimerManager 等待间隔时间
        timePlaylManager.startGenericTimer(playTime) {
            onPlayTimeout()
            timePlaylManager.stopGenericTimer()
        }
    }

    /**
     * 任务播放超时后的逻辑
     *
     */
    private fun onPlayTimeout() {
        // 停止蜂鸣器和动画
        buzzer.stopBuzz()
        fallingBlockLayout.stopDrawing(playChannel)
        println("任务播放完成")

        // 播放下一个任务
        playNextTask()
    }

    /**
     * 返回当前任务列表中的任务数量
     */
    fun getCurrentTaskCount(): Int {
        return taskList.size
    }

    /**
     * 计算动画应该播放的通道
     * @param myChannel 我的频率
     * @param senderChannel 收到消息的频率
     */
    private fun getPlayChannel(myChannel: Int, senderChannel: Int): Int {
        if (myChannel==senderChannel){
            return 5
        }
        else{
            return 5 - (myChannel - senderChannel)
        }
    }
}
