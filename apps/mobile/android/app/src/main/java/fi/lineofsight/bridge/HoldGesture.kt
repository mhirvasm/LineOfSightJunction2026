package fi.lineofsight.bridge

import kotlin.math.abs

/** One hold owns one capture; displacement before readiness is never queued. */
class HoldGesture(
    private val capture: () -> String?,
    private val cancel: (String) -> Unit,
    private val confirm: (String, ActionIntent) -> Boolean,
) {
    var threshold = 80f
    var held = false
        private set
    private var consumed = false
    private var captureId: String? = null
    private var snapshot: HubSnapshot? = null
    private var key: String? = null
    private var x = 0f
    private var y = 0f
    private var originX = 0f
    private var originY = 0f

    fun update(next: HubSnapshot?) {
        if (held && snapshot?.runId != next?.runId) abort()
        snapshot = next
        val ready = next?.captureId == captureId && next?.state in setOf("HOLDING", "PREVIEW")
        val nextKey = if (ready) "${next?.runId}:${next?.previewId}:${next?.target}" else null
        if (key != nextKey) { originX = x; originY = y; key = nextKey }
        if (held && next?.state == "APPLIED") consumed = true
    }

    fun down(px: Float, py: Float) {
        if (held) return
        x = px; y = py; originX = px; originY = py
        held = true; consumed = false; key = null
        captureId = capture()
        if (captureId == null) consumed = true
    }

    fun move(px: Float, py: Float) {
        x = px; y = py
        if (!held || consumed || key == null || !px.isFinite() || !py.isFinite()) return
        val dx = x - originX
        if (dx < threshold || dx < abs(y - originY) * 1.5f) return
        consumed = true
        val id = captureId ?: return
        val current = snapshot
        val intent = ActionPolicy.current(current, true)
        if (intent?.action != "CONFIRM" || !confirm(id, intent)) cancel(id)
    }

    fun up() {
        val id = captureId.takeIf { held && !consumed }
        reset()
        id?.let(cancel)
    }

    fun abort() {
        val id = captureId.takeIf { held && !consumed }
        reset()
        id?.let(cancel)
    }

    private fun reset() {
        held = false; consumed = false; captureId = null; key = null
    }
}
