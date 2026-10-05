package com.earnwage.app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.coroutines.CancellationException
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

/** Public GET requests only. Cached responses always carry their original timestamp. */
internal object ApiClient {
    private val client = OkHttpClient.Builder().connectTimeout(12, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS).callTimeout(40, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true).build()
    private lateinit var directory: File
    fun initialize(context: Context) {
        directory = File(context.filesDir, "public-api-cache").apply { mkdirs() }
    }
    suspend fun get(path: String): JSONObject = withContext(Dispatchers.IO) {
        val url = BuildConfig.API_BASE_URL + path
        val hash = MessageDigest.getInstance("SHA-256").digest(url.toByteArray())
            .joinToString("") { "%02x".format(it) }
        val file = File(directory, hash + ".json")
        var failure: Exception = IOException("Request failed")
        for (attempt in 0..2) {
            try {
                client.newCall(Request.Builder().url(url).header("Accept", "application/json").build())
                    .execute().use { response ->
                        if (!response.isSuccessful) {
                            if (response.code !in listOf(429, 502, 503, 504))
                                throw IllegalStateException("HTTP ${response.code}")
                            throw IOException("HTTP ${response.code}")
                        }
                        val json = JSONObject(response.body?.string() ?: "")
                        val timestamp = System.currentTimeMillis()
                        try {
                            // Small bounded local cache. User-entered salary is stored privately on this device.
                            if ((directory.listFiles()?.size ?: 0) > 150)
                                directory.listFiles()?.minByOrNull { it.lastModified() }?.delete()
                            val temp = File(directory, hash + ".tmp")
                            temp.writeText(JSONObject().put("saved_at", timestamp).put("data", json).toString())
                            temp.renameTo(file)
                        } catch (_: IOException) { /* Cache failure must not hide a valid response. */ }
                        return@withContext json.put("_offline", false).put("_saved_at", timestamp)
                    }
            } catch (e: CancellationException) { throw e
            } catch (e: IllegalStateException) { throw e
            } catch (e: Exception) {
                failure = e
                if (attempt < 2) delay(500L * (attempt + 1))
            }
        }
        try {
            val cached = JSONObject(file.readText())
            cached.getJSONObject("data").put("_offline", true).put("_saved_at", cached.getLong("saved_at"))
        } catch (_: Exception) { throw failure }
    }
}
