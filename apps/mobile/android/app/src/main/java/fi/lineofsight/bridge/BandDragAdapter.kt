package fi.lineofsight.bridge

import com.meta.wearable.dat.inputs.types.DragAction
import com.meta.wearable.dat.inputs.types.InputEvent
import com.meta.wearable.dat.inputs.types.InputSource

class BandDragAdapter(private val gesture: HoldGesture) {
    private var lastTimestamp = Long.MIN_VALUE
    fun reset() { lastTimestamp = Long.MIN_VALUE; gesture.abort() }
    fun accept(event: InputEvent.Drag) {
        if (event.source != InputSource.NEURAL_BAND_DRAG || event.timestampMs < lastTimestamp) return
        if (!event.x.isFinite() || !event.y.isFinite()) return
        lastTimestamp = event.timestampMs
        when (event.action) {
            DragAction.DOWN -> gesture.down(event.x, event.y)
            DragAction.MOVE -> gesture.move(event.x, event.y)
            DragAction.UP -> gesture.up()
        }
    }
}
