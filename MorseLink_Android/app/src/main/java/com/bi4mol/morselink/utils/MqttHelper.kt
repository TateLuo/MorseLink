package com.bi4mol.morselink.utils

import android.util.Log
import org.eclipse.paho.mqttv5.client.*
import org.eclipse.paho.mqttv5.client.persist.MemoryPersistence
import org.eclipse.paho.mqttv5.common.MqttException
import org.eclipse.paho.mqttv5.common.MqttMessage

class MqttHelper(
    private val host: String,
    private val username: String,
    private val password: String,
    private val clientId: String = "client-${System.currentTimeMillis()}" // 默认生成唯一 clientId
) {
    private var mqttClient: MqttAsyncClient? = null
    private val TAG = "MqttHelper"

    init {
        require(host.isNotEmpty()) { "MQTT host cannot be empty." }
        require(username.isNotEmpty()) { "MQTT username cannot be empty." }
        require(password.isNotEmpty()) { "MQTT password cannot be empty." }
    }

    /**
     * 连接到 MQTT 服务器
     */
    fun connect(
        isCleanStart: Boolean = true,
        automaticReconnect: Boolean = true,
        onConnected: (() -> Unit)? = null,
        onError: ((Throwable) -> Unit)? = null
    ) {
        try {
            if (mqttClient?.isConnected == true) {
                Log.i(TAG, "Already connected to MQTT broker.")
                onConnected?.invoke()
                return
            }

            mqttClient = MqttAsyncClient(host, clientId, MemoryPersistence())
            val options = MqttConnectionOptions().apply {
                this.isCleanStart = isCleanStart
                this.isAutomaticReconnect = automaticReconnect
                this.keepAliveInterval = 30 // 心跳包间隔，单位为秒
                userName = username
                password = this@MqttHelper.password.toByteArray()
            }
            mqttClient?.connect(options, null, object : MqttActionListener {
                override fun onSuccess(asyncActionToken: IMqttToken?) {
                    Log.i(TAG, "Connected to MQTT broker at $host")
                    onConnected?.invoke()
                }

                override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                    Log.e(TAG, "Failed to connect to MQTT broker: ${exception?.message}", exception)
                    onError?.invoke(exception ?: Exception("Unknown connection error"))
                }
            })
        } catch (e: MqttException) {
            Log.e(TAG, "Error initiating MQTT connection: ${e.message}", e)
            onError?.invoke(e)
        }
    }

    /**
     * 断开与 MQTT 服务器的连接
     */
    fun disconnect(onDisconnected: (() -> Unit)? = null) {
        try {
            mqttClient?.let { client ->
                if (client.isConnected) {
                    client.disconnect()?.waitForCompletion()
                    Log.i(TAG, "Disconnected from MQTT broker")
                    onDisconnected?.invoke()
                } else {
                    Log.w(TAG, "Client is not connected. No need to disconnect.")
                }
            }
        } catch (e: MqttException) {
            Log.e(TAG, "Error during MQTT disconnect: ${e.message}", e)
        }
    }

    /**
     * 发布消息
     */
    fun publish(
        topic: String,
        message: String,
        qos: Int = 2,
        retained: Boolean = false,
        onError: ((Throwable) -> Unit)? = null
    ) {
        try {
            require(topic.isNotEmpty()) { "Topic cannot be empty." }
            require(message.isNotEmpty()) { "Message cannot be empty." }

            mqttClient?.let { client ->
                if (client.isConnected) {
                    val mqttMessage = MqttMessage(message.toByteArray(Charsets.UTF_8)).apply {
                        this.qos = qos
                        this.isRetained = retained
                    }
                    client.publish(topic, mqttMessage)
                    Log.i(TAG, "Message published to $topic")
                } else {
                    Log.e(TAG, "Client is not connected. Cannot publish to $topic.")
                    onError?.invoke(Exception("Client is not connected."))
                }
            } ?: run {
                Log.e(TAG, "MQTT client is null. Cannot publish to $topic.")
                onError?.invoke(Exception("MQTT client is null."))
            }
        } catch (e: IllegalArgumentException) {
            Log.e(TAG, "Invalid arguments for publishing: ${e.message}", e)
            onError?.invoke(e)
        } catch (e: MqttException) {
            Log.e(TAG, "Error publishing message to $topic: ${e.message}", e)
            onError?.invoke(e)
        }
    }

    /**
     * 订阅主题
     */
    fun subscribe(
        topic: String,
        qos: Int = 2,
        onSubscribed: (() -> Unit)? = null,
        onError: ((Throwable) -> Unit)? = null
    ) {
        try {
            require(topic.isNotEmpty()) { "Topic cannot be empty." }

            mqttClient?.let { client ->
                if (client.isConnected) {
                    client.subscribe(topic, qos, null, object : MqttActionListener {
                        override fun onSuccess(asyncActionToken: IMqttToken?) {
                            Log.i(TAG, "Subscribed to topic: $topic")
                            onSubscribed?.invoke()
                        }

                        override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                            Log.e(TAG, "Failed to subscribe to topic: $topic - ${exception?.message}", exception)
                            onError?.invoke(exception ?: Exception("Unknown subscription error"))
                        }
                    })
                } else {
                    Log.e(TAG, "Client is not connected. Cannot subscribe to $topic.")
                    onError?.invoke(Exception("Client is not connected."))
                }
            } ?: run {
                Log.e(TAG, "MQTT client is null. Cannot subscribe to $topic.")
                onError?.invoke(Exception("MQTT client is null."))
            }
        } catch (e: IllegalArgumentException) {
            Log.e(TAG, "Invalid arguments for subscribing: ${e.message}", e)
            onError?.invoke(e)
        } catch (e: MqttException) {
            Log.e(TAG, "Error subscribing to $topic: ${e.message}", e)
            onError?.invoke(e)
        }
    }

    /**
     * 设置 MQTT 回调
     */
    fun setCallback(callback: MqttCallback) {
        mqttClient?.setCallback(callback) ?: Log.e(TAG, "MQTT client is null. Cannot set callback.")
    }

    /**
     * 检查是否已连接
     */
    fun isConnected(): Boolean {
        return mqttClient?.isConnected == true
    }
}
