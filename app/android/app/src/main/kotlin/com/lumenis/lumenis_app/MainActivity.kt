package com.lumenis.lumenis_app

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.speech.tts.Voice
import java.util.Locale
import java.util.UUID

class MainActivity : FlutterActivity() {
    private val channelName = "lumenis/read_aloud"
    private var textToSpeech: TextToSpeech? = null
    private var ttsReady = false
    private var initializing = false
    private var playbackState = "STOPPED"
    private var failed = false
    private var destroyed = false
    private val pendingUtterances = mutableSetOf<String>()
    private data class PendingTtsCall(val call: MethodCall, val result: MethodChannel.Result)
    private val pendingCalls = mutableListOf<PendingTtsCall>()

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "availableLocales", "speak" -> withEngine(call, result)
                    "stop" -> {
                        pendingUtterances.clear()
                        if (ttsReady) textToSpeech?.stop()
                        failed = false
                        playbackState = "STOPPED"
                        val canceledSpeaks = pendingCalls.filter { it.call.method == "speak" }
                        pendingCalls.removeAll(canceledSpeaks.toSet())
                        canceledSpeaks.forEach { it.result.success(mapOf("status" to "STOPPED")) }
                        result.success(null)
                    }
                    "observe" -> result.success(mapOf("status" to observedState()))
                    else -> result.notImplemented()
                }
            }
    }

    private fun withEngine(call: MethodCall, result: MethodChannel.Result) {
        val current = textToSpeech
        if (ttsReady && current != null) {
            dispatchReady(call, result, current)
            return
        }
        pendingCalls.add(PendingTtsCall(call, result))
        if (initializing) return
        initializing = true
        textToSpeech = TextToSpeech(applicationContext) { status ->
            initializing = false
            if (destroyed) {
                textToSpeech?.shutdown()
                textToSpeech = null
                return@TextToSpeech
            }
            ttsReady = status == TextToSpeech.SUCCESS
            val engine = textToSpeech
            if (!ttsReady || engine == null) {
                textToSpeech?.shutdown()
                textToSpeech = null
                val waiting = pendingCalls.toList()
                pendingCalls.clear()
                waiting.forEach { pending ->
                    if (pending.call.method == "availableLocales") {
                        pending.result.success(mapOf("supported" to false, "localLocales" to emptyList<String>()))
                    } else {
                        pending.result.success(mapOf("status" to "UNAVAILABLE"))
                    }
                }
                return@TextToSpeech
            }
            engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String) {
                    if (pendingUtterances.contains(utteranceId)) {
                        playbackState = "PLAYING"
                    }
                }

                override fun onDone(utteranceId: String) {
                    if (!pendingUtterances.remove(utteranceId)) return
                    if (pendingUtterances.isEmpty() && !failed) playbackState = "COMPLETED"
                }

                @Deprecated("Deprecated by Android")
                override fun onError(utteranceId: String) {
                    if (!pendingUtterances.remove(utteranceId)) return
                    failed = true
                    playbackState = "FAILED"
                }

                override fun onError(utteranceId: String, errorCode: Int) {
                    onError(utteranceId)
                }
            })
            val waiting = pendingCalls.toList()
            pendingCalls.clear()
            waiting.forEach { pending -> dispatchReady(pending.call, pending.result, engine) }
        }
    }

    private fun dispatchReady(call: MethodCall, result: MethodChannel.Result, engine: TextToSpeech) {
        if (call.method == "availableLocales") {
            result.success(mapOf("supported" to true, "localLocales" to localLocales(engine).toList()))
        } else {
            speak(call.arguments as? Map<*, *>, engine, result)
        }
    }

    private fun localLocales(engine: TextToSpeech): Set<String> =
        engine.voices.orEmpty()
            .asSequence()
            .filter(::isLocalVoice)
            .mapNotNull { canonicalTag(it.locale) }
            .toSet()

    private fun isLocalVoice(voice: Voice): Boolean =
        !voice.isNetworkConnectionRequired &&
            !voice.features.contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED)

    private fun findLocalVoice(engine: TextToSpeech, tag: String): Voice? =
        engine.voices.orEmpty().firstOrNull {
            isLocalVoice(it) && canonicalTag(it.locale) == tag
        }

    private fun canonicalTag(locale: Locale): String? = when {
        locale.language.equals("zh", ignoreCase = true) && locale.country.equals("CN", ignoreCase = true) -> "zh-CN"
        locale.language.equals("en", ignoreCase = true) && locale.country.equals("US", ignoreCase = true) -> "en-US"
        locale.language.equals("ko", ignoreCase = true) && locale.country.equals("KR", ignoreCase = true) -> "ko-KR"
        else -> null
    }

    private fun speak(arguments: Map<*, *>?, engine: TextToSpeech, result: MethodChannel.Result) {
        val text = arguments?.get("text") as? String
        val localeTag = arguments?.get("locale") as? String
        val rate = (arguments?.get("rate") as? Number)?.toFloat()
        if (text.isNullOrBlank() || rate == null || localeTag == null || rate !in setOf(0.75f, 1.0f, 1.25f)) {
            result.error("INVALID_REQUEST", "Text, exact locale, and rate are required.", null)
            return
        }
        val voice = findLocalVoice(engine, localeTag)
        if (voice == null) {
            result.success(mapOf("status" to "UNAVAILABLE"))
            return
        }
        pendingUtterances.clear()
        failed = false
        playbackState = "STOPPED"
        engine.stop()
        if (engine.setVoice(voice) != TextToSpeech.SUCCESS || engine.setSpeechRate(rate) != TextToSpeech.SUCCESS) {
            playbackState = "FAILED"
            result.success(mapOf("status" to "FAILED"))
            return
        }
        val chunks = splitText(text, TextToSpeech.getMaxSpeechInputLength())
        playbackState = "STARTING"
        chunks.forEachIndexed { index, chunk ->
            val id = UUID.randomUUID().toString()
            pendingUtterances.add(id)
            val queueMode = if (index == 0) TextToSpeech.QUEUE_FLUSH else TextToSpeech.QUEUE_ADD
            val status = engine.speak(chunk, queueMode, Bundle(), id)
            if (status != TextToSpeech.SUCCESS) {
                pendingUtterances.remove(id)
                failed = true
                playbackState = "FAILED"
            }
        }
        if (failed) {
            engine.stop()
            pendingUtterances.clear()
            result.success(mapOf("status" to "FAILED"))
        } else {
            result.success(mapOf("status" to "STARTING"))
        }
    }

    private fun splitText(text: String, maxLength: Int): List<String> {
        val chunks = mutableListOf<String>()
        var remaining = text.trim()
        while (remaining.length > maxLength) {
            var end = remaining.lastIndexOf(' ', maxLength)
            if (end < maxLength / 2) end = maxLength
            if (end > 0 && Character.isHighSurrogate(remaining[end - 1]) && Character.isLowSurrogate(remaining[end])) end--
            chunks.add(remaining.substring(0, end))
            remaining = remaining.substring(end).trimStart()
        }
        if (remaining.isNotEmpty()) chunks.add(remaining)
        return chunks
    }

    private fun observedState(): String {
        if (playbackState == "STARTING" && textToSpeech?.isSpeaking == true) return "PLAYING"
        return playbackState
    }

    override fun onDestroy() {
        destroyed = true
        val waiting = pendingCalls.toList()
        pendingCalls.clear()
        waiting.forEach { pending ->
            if (pending.call.method == "availableLocales") {
                pending.result.success(mapOf("supported" to false, "localLocales" to emptyList<String>()))
            } else {
                pending.result.success(mapOf("status" to "UNAVAILABLE"))
            }
        }
        textToSpeech?.stop()
        textToSpeech?.shutdown()
        textToSpeech = null
        ttsReady = false
        super.onDestroy()
    }
}
