package fi.lineofsight.bridge

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeout
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.io.IOException
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class HubClient(
    private val scope: CoroutineScope,
    private val clock: () -> Long,
    private val http: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(java.time.Duration.ofSeconds(4))
        .readTimeout(java.time.Duration.ofSeconds(5))
        .callTimeout(java.time.Duration.ofSeconds(6))
        .pingInterval(java.time.Duration.ofSeconds(10)).build(),
) {
    val snapshots = MutableStateFlow<HubSnapshot?>(null)
    var status = "Disconnected"
        private set
    var message = "Connect to the demo hub."
        private set
    var captureAvailable = false
        private set
    var busy = false
        private set
    var onChanged: () -> Unit = {}
    var onInvalidated: () -> Unit = {}
    val guard = StreamGuard()
    private var address: HubAddress? = null
    private var socket: WebSocket? = null
    private var wanted = false
    private var reconnect: Job? = null
    private var sequence = 0L
    private val calls = ConcurrentHashMap.newKeySet<Call>()
    private val frames = Channel<Pair<StreamLease, JpegFrame>>(Channel.CONFLATED)

    init {
        scope.launch {
            for ((lease, frame) in frames) {
                if (!guard.usable(lease, frame, clock())) continue
                val seq = ++sequence
                try {
                    val form = frameForm(lease, frame, seq)
                    val base = address ?: continue
                    val result = request(Request.Builder().url(base.endpoint("/v1/frames")).post(form).build())
                    if (guard.owns(lease) && !result.success) {
                        message = "Frame rejected: ${result.detail}"
                        onChanged()
                    }
                } catch (error: IOException) {
                    if (guard.owns(lease)) {
                        message = "Frame upload failed; no replay. ${error.message}"
                        onChanged()
                    }
                }
            }
        }
    }

    fun connect(value: String) {
        val parsed = HubAddress.parse(value)
        disconnect()
        address = parsed
        wanted = true
        openSocket()
    }

    private fun openSocket() {
        val base = address ?: return
        status = "Connecting"
        onChanged()
        socket = http.newWebSocket(Request.Builder().url(base.socket()).build(), object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                scope.launch {
                    if (socket !== webSocket) return@launch
                    try {
                        require(text.length <= 131_072) { "Hub message is too large." }
                        val json = JSONObject(text)
                        if (json.optString("type") == "ERROR") {
                            busy = false
                            message = json.optString("message", "Hub rejected this action.")
                            if (json.optString("error") == "connection_rejected") {
                                wanted = false
                                lost(webSocket, "Connection rejected. Close the other phone/controller and reconnect.")
                                webSocket.close(1000, "rejected")
                            } else onChanged()
                            return@launch
                        }
                        val next = HubSnapshot.parse(json)
                        val old = snapshots.value
                        if (old?.state != next.state || old.previewId != next.previewId) busy = false
                        if (old != null && old.runId != next.runId) {
                            invalidate()
                            message = "Hub run reset. Press Start for a new interaction."
                        }
                        val lease = guard.active
                        if (lease != null && (next.state == "STOPPED" || next.streamId != lease.streamId)) {
                            invalidate()
                            message = "Camera interaction stopped. Press Start to resume."
                        }
                        snapshots.value = next
                        status = "Connected"
                        onChanged()
                        if (old == null) probeWorkflow(base, webSocket)
                    } catch (error: Exception) {
                        message = "Invalid hub message: ${error.message}"
                        wanted = false
                        lost(webSocket, message)
                        webSocket.close(1000, "invalid snapshot")
                    }
                }
            }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                scope.launch { lost(webSocket, "Connection lost: ${t.message}") }
            }
            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                scope.launch {
                    if (code == 4409 || code == 4400) wanted = false
                    lost(webSocket, if (code == 4409) "Connection rejected. Close the other controller." else "Hub closed the connection ($code).")
                    webSocket.close(1000, null)
                }
            }
        })
    }

    private fun lost(owner: WebSocket, reason: String) {
        if (socket !== owner) return
        socket = null
        invalidate()
        snapshots.value = null
        captureAvailable = false
        status = if (wanted) "Disconnected; retrying" else "Connection rejected"
        message = reason
        onChanged()
        if (wanted) {
            reconnect?.cancel()
            reconnect = scope.launch { delay(1500); if (wanted) openSocket() }
        }
    }

    private fun probeWorkflow(base: HubAddress, owner: WebSocket) {
        scope.launch {
            try {
                val result = request(Request.Builder().url(base.endpoint("/openapi.json")).build())
                if (socket !== owner) return@launch
                captureAvailable = result.success && JSONObject(result.detail).optJSONObject("paths")
                    ?.optJSONObject("/v1/captures")?.has("post") == true
                if (!captureAvailable) message = "Marker test ready. This hub has no receipt capture/transfer workflow yet."
                onChanged()
            } catch (_: Exception) {
                if (socket === owner) {
                    captureAvailable = false
                    message = "Could not verify receipt endpoint; Capture stays disabled. Marker testing is available."
                    onChanged()
                }
            }
        }
    }

    suspend fun startStream(source: String): StreamLease {
        val before = snapshots.value ?: error("Connect to the hub first.")
        check(status == "Connected") { "Hub is disconnected." }
        invalidate()
        val generation = guard.generation
        val id = UUID.randomUUID().toString()
        if (before.state == "STOPPED") check(sendAction("START")) { "Could not send Start." }
        check(send(JSONObject().put("type", "STREAM_STARTED").put("stream_id", id).put("input_source", source))) {
            "Could not announce the camera stream."
        }
        withTimeout(4000) {
            snapshots.first { it != null && (it.runId != before.runId || (it.streamId == id && it.state != "STOPPED")) }
        }
        check(guard.generation == generation && snapshots.value?.runId == before.runId && status == "Connected") {
            "The run or connection changed. Press Start again."
        }
        sequence = 0
        return guard.activate(before.runId, id)
    }

    fun submit(lease: StreamLease, frame: JpegFrame) {
        if (guard.usable(lease, frame, clock())) frames.trySend(lease to frame)
    }

    fun stop() {
        sendAction("STOP")
        invalidate()
        message = "Stopped. Applied drafts are unchanged."
        onChanged()
    }

    fun pause() {
        send(JSONObject().put("type", "DEVICE_PAUSED").put("reason", "android_backgrounded"))
        disconnect()
    }

    fun disconnect() {
        wanted = false
        reconnect?.cancel()
        reconnect = null
        val previous = socket
        socket = null
        previous?.close(1000, "controller closed")
        invalidate()
        snapshots.value = null
        captureAvailable = false
        status = "Disconnected"
        onChanged()
    }

    private fun invalidate() {
        guard.invalidate()
        busy = false
        calls.toList().forEach { it.cancel() }
        while (frames.tryReceive().isSuccess) { /* discard old stream frames */ }
        onInvalidated()
    }

    fun perform(intent: ActionIntent, frame: JpegFrame?): Boolean {
        if (busy || status != "Connected" || !ActionPolicy.accepts(intent, snapshots.value, captureAvailable)) return false
        val lease = guard.active ?: return false
        if (frame == null || !guard.usable(lease, frame, clock())) return false
        if (intent.action == "CONFIRM") {
            busy = true
            val sent = sendAction("CONFIRM", intent.previewId)
            // keep one rendered confirmation consumed until a new snapshot or explicit stop.
            if (!sent) busy = false
            onChanged()
            return sent
        }
        val frozen = JpegFrame(frame.bytes.copyOf(), frame.deliveredAtMs)
        val captureId = UUID.randomUUID().toString()
        val base = address ?: return false
        busy = true
        onChanged()
        scope.launch {
            try {
                if (!guard.usable(lease, frozen, clock())) throw IOException("Receipt frame expired. Capture again.")
                val body = MultipartBody.Builder().setType(MultipartBody.FORM)
                    .addFormDataPart("run_id", intent.runId).addFormDataPart("capture_id", captureId)
                    .addFormDataPart("age_ms", (clock() - frozen.deliveredAtMs).toString())
                    .addFormDataPart("image", "receipt.jpg", frozen.bytes.toRequestBody("image/jpeg".toMediaType())).build()
                val result = request(Request.Builder().url(base.endpoint("/v1/captures")).post(body).build())
                if (guard.owns(lease)) {
                    message = if (result.success) "Capture accepted; waiting for the hub receipt result." else "Capture failed: ${result.detail}"
                    if (!result.success) busy = false
                    onChanged()
                }
            } catch (error: IOException) {
                if (guard.owns(lease)) {
                    busy = false
                    message = "Capture failed; never replayed: ${error.message}"
                    onChanged()
                }
            }
        }
        return true
    }

    fun sendAction(action: String, previewId: String? = null): Boolean = send(
        JSONObject().put("type", "ACTION").put("action", action).apply { if (previewId != null) put("preview_id", previewId) })

    private fun send(event: JSONObject): Boolean {
        val run = snapshots.value?.runId ?: return false
        return socket?.send(event.put("v", 1).put("run_id", run).toString()) == true
    }

    private fun frameForm(lease: StreamLease, frame: JpegFrame, seq: Long): MultipartBody =
        MultipartBody.Builder().setType(MultipartBody.FORM)
            .addFormDataPart("run_id", lease.runId).addFormDataPart("stream_id", lease.streamId)
            .addFormDataPart("frame_seq", seq.toString()).addFormDataPart("age_ms", (clock() - frame.deliveredAtMs).toString())
            .addFormDataPart("image", "frame.jpg", frame.bytes.toRequestBody("image/jpeg".toMediaType())).build()

    private data class Result(val success: Boolean, val detail: String)

    private suspend fun request(request: Request): Result = suspendCancellableCoroutine { continuation ->
        val call = http.newCall(request)
        calls.add(call)
        continuation.invokeOnCancellation { calls.remove(call); call.cancel() }
        call.enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                calls.remove(call)
                if (continuation.isActive) continuation.resumeWithException(e)
            }
            override fun onResponse(call: Call, response: Response) {
                try {
                    response.use {
                        val source = it.body?.source()
                        source?.request(131_073)
                        val bytes = source?.buffer?.readByteArray(minOf(source.buffer.size, 131_073)) ?: byteArrayOf()
                        if (continuation.isActive) {
                            if (bytes.size > 131_072) continuation.resumeWithException(IOException("Hub response is too large."))
                            else continuation.resume(Result(it.isSuccessful, bytes.toString(Charsets.UTF_8)))
                        }
                    }
                } catch (error: IOException) {
                    if (continuation.isActive) continuation.resumeWithException(error)
                } finally {
                    calls.remove(call)
                }
            }
        })
    }
}
