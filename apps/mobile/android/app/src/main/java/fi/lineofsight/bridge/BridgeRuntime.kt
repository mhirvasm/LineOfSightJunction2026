package fi.lineofsight.bridge

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.os.SystemClock
import android.view.View
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.util.UUID

class BridgeRuntime private constructor(private val context: Context) {
    companion object {
        private var instance: BridgeRuntime? = null
        fun get(context: Context): BridgeRuntime = instance ?: BridgeRuntime(context.applicationContext).also { instance = it }
    }
    val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    val hub = HubClient(scope, SystemClock::elapsedRealtime)
    val sdk = MetaBridge(context, scope)
    var frame: JpegFrame? = null
        private set
    var physical = false
    var rawInputs = false
    var sdkMessage = "SDK not started"
    var inputMessage = "No band events"
    var changed: () -> Unit = {}
    var bitmap: ((Bitmap) -> Unit)? = null
    var preview: ((View?) -> Unit)? = null
    val gesture = HoldGesture(
        capture = {
            val id = UUID.randomUUID().toString()
            val intent = ActionPolicy.current(hub.snapshots.value, hub.captureAvailable)
            if (intent?.action == "CAPTURE" && hub.perform(intent, frame, id)) id else null
        },
        cancel = { hub.cancelCapture(it) },
        confirm = { id, intent ->
            hub.snapshots.value?.captureId == id && hub.perform(intent, frame)
        },
    )
    private val band = BandDragAdapter(gesture)

    init {
        hub.onChanged = { refresh() }
        hub.onInvalidated = {
            band.reset()
            frame = null
            sdk.stop()
            context.stopService(Intent(context, GlassesService::class.java))
        }
        sdk.onFrame = { jpeg, image ->
            val lease = hub.guard.active
            if (lease != null && hub.guard.usable(lease, jpeg, SystemClock.elapsedRealtime())) {
                frame = jpeg
                hub.submit(lease, jpeg)
                bitmap?.invoke(image) ?: image.recycle()
                refresh()
            } else image.recycle()
        }
        sdk.onPreview = { preview?.invoke(it) }
        sdk.onFailure = { reason -> sdkMessage = reason; hub.stop(); refresh() }
        sdk.onStatus = { sdkMessage = it; refresh() }
        sdk.onDrag = { event ->
            inputMessage = "${event.action}: x=${event.x}, y=${event.y} (device units)"
            if (physical && rawInputs && hub.guard.active != null) {
                gesture.update(hub.snapshots.value)
                band.accept(event)
            }
            refresh()
        }
        scope.launch { while (isActive) { refresh(); delay(150) } }
    }

    fun refresh() {
        val s = hub.snapshots.value
        gesture.update(s)
        val fresh = frame?.let { SystemClock.elapsedRealtime() - it.deliveredAtMs in 0..300 } == true
        val intent = ActionPolicy.current(s, hub.captureAvailable).takeIf {
            !rawInputs && !gesture.held && fresh && !hub.busy && hub.guard.active != null && hub.status == "Connected"
        }
        val title = when (s?.state) {
            "READING" -> "Reading receipt"
            "PREVIEW" -> "${s.target?.replaceFirstChar { it.uppercase() }} ${s.amount}"
            "HOLDING" -> "Receipt held"
            "APPLIED" -> "Receipt sent"
            else -> "Hold to capture"
        }
        sdk.showCard(title, "${s?.receiptMode ?: "unknown"}: ${s?.feedback ?: "Connect and start"}", intent) {
            if (!rawInputs) hub.perform(it, frame)
        }
        changed()
    }

    fun stop() { gesture.abort(); hub.stop() }
}
