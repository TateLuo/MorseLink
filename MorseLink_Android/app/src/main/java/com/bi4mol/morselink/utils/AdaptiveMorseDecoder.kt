package com.bi4mol.morselink.utils

import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.pow
import kotlin.math.sqrt

class AdaptiveMorseDecoder(
    private var initialWpm: Int = 20,
    private var learningWindow: Int = 100,
    private var sensitivity: Double = 0.3
    )
{
    // 基于PARIS标准的WPM计算（1个时间单位=1200/WPM毫秒）
    private var baseUnit: Double = 1200.0 / initialWpm
    private var dotDuration: Double = baseUnit
    private var dashThreshold: Double = 3 * baseUnit

    // 使用双缓冲历史记录（点/划分离）
    private val pointHistory: MutableList<Double> = mutableListOf()
    private val dashHistory: MutableList<Double> = mutableListOf()
    private val rawHistory: MutableList<Double> = mutableListOf()

    init {
        sensitivity = sensitivity.coerceIn(0.1, 0.9)
    }

    // 改进的异常值过滤（基于动态四分位距）
    private fun filterOutliers(duration: Double): Double {
        if (rawHistory.size < 10) return duration

        val sorted = rawHistory.sorted()
        val q1 = sorted[sorted.size / 4]
        val q3 = sorted[sorted.size * 3 / 4]
        val iqr = (q3 - q1) * 1.5

        return duration.coerceIn(q1 - iqr, q3 + iqr)
    }

    // 混合聚合策略（中位数+加权平均）
    private fun aggregateDurations(data: List<Double>): Double {
        if (data.isEmpty()) return 0.0

        return when {
            data.size < 10 -> data.average()
            else -> {
                val median = data.sorted()[data.size / 2]
                val weights = List(data.size) { exp(-abs(data[it] - median) / median) }
                data.zip(weights).sumOf { it.first * it.second } / weights.sum()
            }
        }
    }

    // 基于历史分布的动态适应
    private fun adaptThresholds() {
        // 只有当两个历史都有足够数据时才调整
        if (pointHistory.size + dashHistory.size < learningWindow) return

        // 分别聚合点划持续时间
        val newDot = aggregateDurations(pointHistory)
        val newDash = aggregateDurations(dashHistory)

        // 动态学习率（根据历史稳定性调整）
        val pointVariation = pointHistory.stdDev() / newDot
        val dashVariation = dashHistory.stdDev() / newDash
        val dynamicRate = sensitivity * (1 - (pointVariation + dashVariation)/2)

        // 指数平滑更新
        dotDuration = dotDuration * (1 - dynamicRate) + newDot * dynamicRate
        dashThreshold = dashThreshold * (1 - dynamicRate) + newDash * dynamicRate
    }

    fun processDuration(duration: Double): Pair<Char, Double> {
        // 预处理流水线
        val filtered = filterOutliers(duration)
        rawHistory.add(filtered)

        // 实时分类
        val (symbol, confidence) = classifyWithConfidence(filtered)

        // 根据分类结果更新对应历史
        when(symbol) {
            '.' -> pointHistory.add(filtered)
            '-' -> dashHistory.add(filtered)
        }

        // 动态适应（控制学习频率）
        if (rawHistory.size % (learningWindow/5) == 0) {
            adaptThresholds()
            maintainHistory()
        }

        return Pair(symbol, confidence)
    }

    // 基于概率分布的分类（考虑当前阈值）
    private fun classifyWithConfidence(duration: Double): Pair<Char, Double> {
        val dotProb = gaussianProbability(duration, dotDuration, dotDuration/3)
        val dashProb = gaussianProbability(duration, dashThreshold, dashThreshold/3)

        return if (dotProb > dashProb) {
            val confidence = dotProb / (dotProb + dashProb)
            Pair('.', confidence)
        } else {
            val confidence = dashProb / (dotProb + dashProb)
            Pair('-', confidence)
        }
    }

    // 历史维护策略（保留最近数据）
    private fun maintainHistory() {
        fun MutableList<Double>.trim(max: Int) {
            if (size > max) subList(0, size - max).clear()
        }

        pointHistory.trim(learningWindow)
        dashHistory.trim(learningWindow)
        rawHistory.trim(learningWindow * 2)
    }

    // 辅助函数：计算标准差
    private fun List<Double>.stdDev(): Double {
        val mean = average()
        return sqrt(map { (it - mean).pow(2) }.average())
    }

    // 高斯概率计算
    private fun gaussianProbability(x: Double, mean: Double, stdDev: Double): Double {
        val exponent = -0.5 * ((x - mean) / stdDev).pow(2)
        return exp(exponent) / (stdDev * sqrt(2 * Math.PI))
    }
}