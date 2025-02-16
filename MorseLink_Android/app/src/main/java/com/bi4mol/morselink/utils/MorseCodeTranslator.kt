package com.bi4mol.morselink.utils

class MorseCodeTranslator {

    // 摩尔斯电码字典
    private val morseCodeDict: Map<String, Any> = mapOf(
        // 字母
        ".-" to 'A', "-..." to 'B', "-.-." to 'C', "-.." to 'D', "." to 'E',
        "..-." to 'F', "--." to 'G', "...." to 'H', ".." to 'I', ".---" to 'J',
        "-.-" to 'K', ".-.." to 'L', "--" to 'M', "-." to 'N', "---" to 'O',
        ".--." to 'P', "--.-" to 'Q', ".-." to 'R', "..." to 'S', "-" to 'T',
        "..-" to 'U', "...-" to 'V', ".--" to 'W', "-..-" to 'X', "-.--" to 'Y',
        "--.." to 'Z',

        // 数字
        "-----" to '0', ".----" to '1', "..---" to '2', "...--" to '3',
        "....-" to '4', "....." to '5', "-...." to '6', "--..." to '7',
        "---.." to '8', "----." to '9',

        // 标点符号
        ".-.-.-" to '.', "---..." to ':', "--..--" to ',', "-.-.-." to ';',
        "..--.." to '?', "-...-" to '=', ".----." to "'",
        "-.-.--" to '!', "-..-." to '/', "-.--." to '(', "-.--.-" to ')',
        ".-..." to '&', ".-..-." to '"', "...-..-" to '$', ".--.-." to '@',
        "///" to ' '  // 用于分隔单词
    )

    // 将摩尔斯电码翻译为对应字母
    fun morseToLetter(morseCode: String): Any {
        return morseCodeDict[morseCode] ?: '*'
    }

    // 翻译整个句子
    fun morseToText(morseCode: String): String {
        val code = morseCode.removeSuffix("///") // 去掉末尾的 '///'（如果存在）
        val words = code.split("///")
        val decodedMessage = words.joinToString(" ") { word ->
            word.split("/").joinToString("") { letter ->
                morseCodeDict[letter]?.toString() ?: "?"
            }
        }
        return decodedMessage
    }

    // 加密字符串为摩尔斯代码
    fun textToMorse(text: String): String {
        return text.uppercase().split(" ").joinToString("///") { word ->
            word.map { char ->
                morseCodeDict.entries.find { it.value == char }?.key ?: ""
            }.filter { it.isNotEmpty() }.joinToString("/")
        }
    }

    // 将字母翻译回摩尔斯码
    fun letterToMorseCode(letter: Char): String {
        return morseCodeDict.entries.find { it.value == letter.uppercaseChar() }?.key ?: "未知"
    }
}
