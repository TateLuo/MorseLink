package com.bi4mol.morselink.utils

// JsonParser.kt
import com.bi4mol.morselink.model.JsonData
import com.google.gson.Gson
import com.google.gson.JsonSyntaxException

class JsonParser {
    fun parseJsonData(json: String): JsonData {
        val gson = Gson()
        return gson.fromJson(json, JsonData::class.java)
    }

    fun parseDataToJson(
        morseCode: String,
        myCall: String,
        pressedTime: Long,
        pressedIntervalTime: Long,
        myChannel: Int
    ): String {

        // 创建一个数据映射
        val data = mapOf(
            "morseCode" to morseCode,
            "myCall" to myCall,
            "pressedTime" to pressedTime,
            "pressedIntervalTime" to pressedIntervalTime,
            "myChannel" to myChannel
        )

        return try {
            // 将数据转换为JSON格式
            Gson().toJson(data)
        } catch (e: JsonSyntaxException) {
            // 处理JSON转换异常
            println("JSON解析错误: ${e.message}")
            "{}" // 返回空的JSON对象
        }
    }
}
