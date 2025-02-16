package com.bi4mol.morselink.utils
// MQTTClientQueryTool.kt
import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import androidx.annotation.RequiresApi
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import java.util.*

@RequiresApi(Build.VERSION_CODES.O)
class ClientQueryTool private constructor(builder: Builder) {
    private val apiService: ApiService
    private val interval: Long
    private val handler = Handler(Looper.getMainLooper())
    private var timerRunnable: Runnable? = null
    private var listener: ClientCountListener? = builder.listener

    init {
        apiService = createApiService(builder)
        interval = builder.interval
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private fun createApiService(builder: Builder): ApiService {
        val auth = "Basic " + Base64.getEncoder()
            .encodeToString("${builder.username}:${builder.password}".toByteArray())

        val client = OkHttpClient.Builder()
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                    .addHeader("Authorization", auth)
                    .build()
                chain.proceed(request)
            }
            .build()

        return Retrofit.Builder()
            .baseUrl("${builder.baseUrl}:${builder.port}")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }

    fun startPolling() {
        stopPolling()
        timerRunnable = object : Runnable {
            override fun run() {
                fetchClientCount()
                handler.postDelayed(this, interval)
            }
        }
        handler.post(timerRunnable!!)
    }

    fun stopPolling() {
        timerRunnable?.let {
            handler.removeCallbacks(it)
            timerRunnable = null
        }
    }

    private fun fetchClientCount() {
        Thread {
            try {
                val response = apiService.getClients().execute()
                if (response.isSuccessful) {
                    val count = response.body()?.meta?.count ?: -1
                    notifySuccess(count)
                } else {
                    notifyError("HTTP Error: ${response.code()}")
                }
            } catch (e: Exception) {
                notifyError("Request failed: ${e.localizedMessage}")
            }
        }.start()
    }

    private fun notifySuccess(count: Int) {
        handler.post { listener?.onClientCountReceived(count) }
    }

    private fun notifyError(message: String) {
        handler.post { listener?.onError(message) }
    }

    interface ClientCountListener {
        fun onClientCountReceived(count: Int)
        fun onError(message: String)
    }

    class Builder(context: Context) {
        var baseUrl: String = "http://117.72.10.141"
        var port: Int = 18083
        var username: String = ""
        var password: String = ""
        var interval: Long = 60000
        var listener: ClientCountListener? = null

        fun setBaseUrl(url: String) = apply { this.baseUrl = url }
        fun setPort(port: Int) = apply { this.port = port }
        fun setCredentials(username: String, password: String) = apply {
            this.username = username
            this.password = password
        }
        fun setInterval(interval: Long) = apply { this.interval = interval }
        fun setListener(listener: ClientCountListener) = apply { this.listener = listener }
        fun build() = ClientQueryTool(this)
    }

    private interface ApiService {
        @GET("/api/v5/clients")
        fun getClients(): retrofit2.Call<ClientResponse>
    }

    private data class ClientResponse(
        val meta: MetaData?
    )

    private data class MetaData(
        val count: Int
    )
}
