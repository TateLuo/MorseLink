package com.bi4mol.morselink.model

// JsonData.kt
data class JsonData(
    val morseCode: String,
    val myCall: String,
    val pressedTime: Long,
    val pressedIntervalTime: Long,
    val myChannel: Int
)
