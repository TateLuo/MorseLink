package com.bi4mol.morselink.customviews

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View
import kotlin.math.min

class MorseCodeAnimationView @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null
) : View(context, attrs) {

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }

    private val blocks = mutableListOf<Block>()

    private val activeChannels = mutableMapOf<Int, ActiveChannel>()

    private var normalSpeed = 4f
    private var acceleratedSpeed = 8f

    private val channelCount = 11
    private var channelWidth = 0f
    private var channelSpacing = 0f

    private var currentChannel = -1

    private val moveRunnable = object : Runnable {
        override fun run() {
            moveBlocks()
            postDelayed(this, 16L)
        }
    }

    init {
        post(moveRunnable)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        channelWidth = width / (channelCount * 2f)
        channelSpacing = channelWidth

        drawCurrentChannelHighlight(canvas)
        drawChannelMarkers(canvas)

        for (block in blocks) {
            paint.color = block.color
            canvas.drawRect(block.x, block.y, block.x + block.width, block.y + block.height, paint)
        }
    }

    private fun drawCurrentChannelHighlight(canvas: Canvas) {
        if (currentChannel < 0 || currentChannel >= channelCount) return

        val highlightPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#ADD8E6")
        }

        val channelLeftX = currentChannel * (channelWidth + channelSpacing)
        val channelRightX = channelLeftX + channelWidth

        canvas.drawRect(
            channelLeftX,
            0f,
            channelRightX,
            50f,
            highlightPaint
        )
    }

    private fun drawChannelMarkers(canvas: Canvas) {
        val markerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.GRAY
            strokeWidth = 4f
            textSize = 36f
            textAlign = Paint.Align.CENTER
        }

        for (channel in 0 until channelCount) {
            val channelLeftX = channel * (channelWidth + channelSpacing)

            canvas.drawLine(
                channelLeftX,
                0f,
                channelLeftX,
                20f,
                markerPaint
            )
        }
    }

    fun setCurrentChannel(channel: Int) {
        if (channel < 0 || channel >= channelCount) {
            throw IllegalArgumentException("通道索引必须在 0 到 ${channelCount - 1} 之间")
        }
        currentChannel = channel
        invalidate()
    }

    fun startDrawing(channel: Int) {
        if (channel < 0 || channel >= channelCount) {
            throw IllegalArgumentException("通道索引必须在 0 到 ${channelCount - 1} 之间")
        }

        if (activeChannels.containsKey(channel)) {
            return
        }

        val channelCenterX = channel * (channelWidth + channelSpacing) + channelWidth / 2

        val block = Block(
            x = channelCenterX - channelWidth / 2,
            y = 0f,
            width = channelWidth,
            height = 3f,
            color = Color.BLACK,
            speed = 0f,
            isFalling = false
        )
        blocks.add(block)

        activeChannels[channel] = ActiveChannel(block, System.currentTimeMillis())
    }

    fun stopDrawing(channel: Int) {
        val activeChannel = activeChannels[channel] ?: return

        activeChannel.block.isFalling = true
        activeChannel.block.speed = normalSpeed

        activeChannels.remove(channel)
    }

    private fun moveBlocks() {
        val iterator = blocks.iterator()
        while (iterator.hasNext()) {
            val block = iterator.next()

            if (block.isFalling) {
                block.y += block.speed
            }

            if (block.y > height) {
                iterator.remove()
            }
        }

        for ((channel, activeChannel) in activeChannels) {
            val duration = System.currentTimeMillis() - activeChannel.startTime
            val height = duration / 10f
            activeChannel.block.height = height
            activeChannel.block.color = Color.rgb(
                min(255, (duration / 10).toInt()), 0, 0
            )
        }

        invalidate()
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        removeCallbacks(moveRunnable)
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        post(moveRunnable)
    }

    private data class Block(
        var x: Float,
        var y: Float,
        var width: Float,
        var height: Float,
        var color: Int,
        var speed: Float,
        var isFalling: Boolean
    )

    private data class ActiveChannel(
        val block: Block,
        val startTime: Long
    )
}
