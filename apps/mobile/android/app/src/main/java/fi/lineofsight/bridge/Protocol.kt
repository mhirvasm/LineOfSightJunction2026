package fi.lineofsight.bridge

import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import org.json.JSONObject
import java.util.UUID

data class HubAddress(val base: HttpUrl) {
    fun endpoint(path: String): HttpUrl = base.newBuilder().encodedPath(path).build()
    fun socket(): HttpUrl = endpoint("/v1/events").newBuilder().addQueryParameter("role", "mobile").build()

    companion object {
        fun parse(value: String): HubAddress {
            val url = value.trim().toHttpUrl()
            require(url.username.isEmpty() && url.password.isEmpty()) { "Use a hub address without credentials." }
            require(url.encodedPath == "/" && url.query == null && url.fragment == null) {
                "Enter only the hub origin, for example http://192.168.1.100:8000"
            }
            return HubAddress(url)
        }
    }
}

data class HubSnapshot(
    val runId: String,
    val state: String,
    val streamId: String?,
    val recognized: String?,
    val target: String?,
    val previewId: String?,
    val canConfirm: Boolean,
    val receiptMode: String,
    val feedback: String,
    val visionMessage: String,
    val amount: String,
    val captureId: String? = null,
) {
    companion object {
        fun parse(json: JSONObject): HubSnapshot {
            require(json.getInt("v") == 1 && json.getString("type") == "SNAPSHOT")
            val run = json.getString("run_id")
            UUID.fromString(run)
            val vision = json.optJSONObject("vision")
            val receipt = json.optJSONObject("receipt")
            val minor = receipt?.optLong("total_minor", -1) ?: -1
            val amount = if (minor >= 0) "${receipt?.optString("currency")} ${minor / 100}.${(minor % 100).toString().padStart(2, '0')}" else ""
            return HubSnapshot(run, json.getString("state"), vision?.nullable("stream_id"),
                vision?.nullable("detected_target_id"), json.nullable("target_id"),
                json.nullable("preview_id"), json.optBoolean("can_confirm"),
                json.optString("source_mode", "unknown") + " / " + json.optString("extraction_provider", "unknown"), json.optString("feedback"),
                vision?.optString("message").orEmpty(), amount, json.nullable("capture_id"))
        }
    }
}

internal fun JSONObject.nullable(name: String): String? =
    if (isNull(name)) null else optString(name).takeIf { it.isNotBlank() }

data class ActionIntent(val runId: String, val action: String, val previewId: String? = null)

object ActionPolicy {
    fun current(snapshot: HubSnapshot?, captureAvailable: Boolean): ActionIntent? = when {
        snapshot == null -> null
        snapshot.state == "PREVIEW" && snapshot.canConfirm && snapshot.previewId != null ->
            ActionIntent(snapshot.runId, "CONFIRM", snapshot.previewId)
        snapshot.state in setOf("READY", "APPLIED") && captureAvailable -> ActionIntent(snapshot.runId, "CAPTURE")
        else -> null
    }

    fun accepts(intent: ActionIntent, snapshot: HubSnapshot?, captureAvailable: Boolean): Boolean =
        intent == current(snapshot, captureAvailable)
}

data class StreamLease(val generation: Long, val runId: String, val streamId: String)
data class JpegFrame(val bytes: ByteArray, val deliveredAtMs: Long)

class StreamGuard {
    var generation = 0L
        private set
    var active: StreamLease? = null
        private set

    fun invalidate() { generation++; active = null }
    fun activate(runId: String, streamId: String): StreamLease =
        StreamLease(generation, runId, streamId).also { active = it }
    fun owns(lease: StreamLease): Boolean = active == lease && generation == lease.generation
    fun usable(lease: StreamLease, frame: JpegFrame, nowMs: Long): Boolean =
        owns(lease) && nowMs - frame.deliveredAtMs in 0..300 && frame.bytes.size in 1..2_000_000
}

object YuvLayout {
    fun nv21(i420: ByteArray, width: Int, height: Int): ByteArray {
        require(width > 0 && height > 0 && width % 2 == 0 && height % 2 == 0)
        val pixels = width.toLong() * height
        require(pixels <= 4_000_000 && i420.size.toLong() == pixels * 3 / 2) { "Expected packed I420 video frame." }
        val ySize = pixels.toInt()
        val chroma = ySize / 4
        val result = ByteArray(i420.size)
        i420.copyInto(result, endIndex = ySize)
        repeat(chroma) { index ->
            result[ySize + index * 2] = i420[ySize + chroma + index]
            result[ySize + index * 2 + 1] = i420[ySize + index]
        }
        return result
    }
}
