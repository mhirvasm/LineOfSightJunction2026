package fi.lineofsight.bridge

import com.meta.wearable.dat.inputs.types.DragAction
import com.meta.wearable.dat.inputs.types.InputEvent
import com.meta.wearable.dat.inputs.types.InputSource
import org.junit.Assert.*
import org.junit.Test

class BandDragAdapterTest {
    @Test fun sdkDragEventsUseSameControllerAndRejectOldOrOtherSources() {
        val actions = mutableListOf<String>()
        val gesture = HoldGesture({ actions.add("capture"); "c" }, { actions.add("cancel") }, { _, _ -> actions.add("confirm"); true })
        val adapter = BandDragAdapter(gesture)
        val snapshot = HubSnapshot("r", "READY", "s", null, null, null, false, "fixture", "", "", "")
        gesture.update(snapshot)
        fun input(action: DragAction, x: Float, time: Long, source: InputSource = InputSource.NEURAL_BAND_DRAG) =
            InputEvent.Drag(action, x, 0f, 0f, 0f, source, time)
        adapter.accept(input(DragAction.DOWN, 0f, 1, InputSource.CAPTOUCH))
        assertTrue(actions.isEmpty())
        adapter.accept(input(DragAction.DOWN, 0f, 10))
        gesture.update(snapshot.copy(state="PREVIEW", captureId="c", target="expenses", previewId="p", canConfirm=true))
        adapter.accept(input(DragAction.UP, 0f, 9))
        adapter.accept(input(DragAction.MOVE, 100f, 11))
        adapter.accept(input(DragAction.UP, 100f, 12))
        assertEquals(listOf("capture", "confirm"), actions)
        adapter.reset()
        adapter.accept(input(DragAction.DOWN, 0f, 1))
        adapter.reset()
        assertEquals("cancel", actions.last())
    }
}
