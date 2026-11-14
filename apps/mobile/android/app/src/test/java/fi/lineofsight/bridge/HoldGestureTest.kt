package fi.lineofsight.bridge

import org.junit.Assert.*
import org.junit.Test

class HoldGestureTest {
    private val actions = mutableListOf<String>()
    private val gesture = HoldGesture({ actions.add("capture"); "c" }, { actions.add("cancel:$it") },
        { _, intent -> actions.add("confirm:${intent.previewId}"); true })
    private fun snapshot(state: String, preview: String? = null, run: String = "r") = HubSnapshot(
        run, state, "s", null, if (preview != null) "expenses" else null, preview, preview != null,
        "fixture", "", "", "EUR 24.80", if (state == "READY") null else "c")
    private fun down() { gesture.update(snapshot("READY")); gesture.down(0f, 0f) }

    @Test fun releaseCancelsOnce() {
        down(); gesture.down(0f, 0f); gesture.up(); gesture.up()
        assertEquals(listOf("capture", "cancel:c"), actions)
    }
    @Test fun noTargetPasteCancels() {
        down(); gesture.update(snapshot("HOLDING")); gesture.move(100f, 0f); gesture.up()
        assertEquals(listOf("capture", "cancel:c"), actions)
    }
    @Test fun textPasteToIncompatibleExpensesCancels() {
        down()
        gesture.update(snapshot("HOLDING").copy(target = "expenses", amount = "", text = "A note"))
        gesture.move(100f, 0f); gesture.up()
        assertEquals(listOf("capture", "cancel:c"), actions)
    }

    @Test fun textWithoutReceiptSendsOnce() {
        down()
        gesture.update(snapshot("PREVIEW", "text-preview").copy(target = "text", amount = "", text = "A note"))
        gesture.move(100f, 0f); gesture.move(200f, 0f); gesture.up()
        assertEquals(listOf("capture", "confirm:text-preview"), actions)
    }

    @Test fun coffeeHoldNeedsSwipeAndReleaseAfterConfirmDoesNotToggleAgain() {
        down()
        gesture.update(snapshot("PREVIEW", "coffee-on").copy(target = "coffee", amount = "", interactionKind = "coffee", coffeeDesired = true))
        assertEquals(listOf("capture"), actions)
        gesture.move(100f, 0f)
        gesture.update(snapshot("APPLIED").copy(interactionKind = "coffee", coffeeOn = true))
        gesture.move(200f, 0f); gesture.up()
        assertEquals(listOf("capture", "confirm:coffee-on"), actions)
    }
    @Test fun readyMovementMustBeFreshAndSendOnce() {
        down(); gesture.move(200f, 0f); gesture.update(snapshot("PREVIEW", "p"))
        gesture.move(210f, 0f)
        assertEquals(listOf("capture"), actions)
        gesture.move(300f, 0f); gesture.move(500f, 0f); gesture.up()
        assertEquals(listOf("capture", "confirm:p"), actions)
    }
    @Test fun changingTargetRebasesAndVerticalMotionDoesNotSend() {
        down(); gesture.update(snapshot("PREVIEW", "a")); gesture.move(70f, 0f)
        gesture.update(snapshot("PREVIEW", "b")); gesture.move(100f, 0f)
        gesture.move(160f, 150f)
        assertEquals(listOf("capture"), actions)
        gesture.up()
        assertEquals("cancel:c", actions.last())
    }
    @Test fun resetCannotSendOldHold() {
        down(); gesture.update(snapshot("PREVIEW", "p")); gesture.update(snapshot("READY", run="new"))
        gesture.move(300f, 0f); gesture.up()
        assertEquals(listOf("capture", "cancel:c"), actions)
    }

    @Test fun oldAppliedSnapshotDuringCaptureDoesNotConsumeNewHold() {
        val old = snapshot("APPLIED").copy(captureId = "previous")
        lateinit var nextGesture: HoldGesture
        nextGesture = HoldGesture(
            { nextGesture.update(old); "new-capture" },
            { actions.add("cancel:$it") },
            { _, intent -> actions.add("confirm:${intent.previewId}"); true },
        )
        nextGesture.update(old)
        nextGesture.down(0f, 0f)
        nextGesture.update(snapshot("PREVIEW", "new-preview").copy(captureId = "new-capture"))
        nextGesture.move(100f, 0f)
        nextGesture.up()
        assertEquals(listOf("confirm:new-preview"), actions)
    }

    @Test fun releaseOfNewHoldStillCancelsWhileOldApplyIsVisible() {
        val old = snapshot("APPLIED").copy(captureId = "previous")
        lateinit var nextGesture: HoldGesture
        nextGesture = HoldGesture({ nextGesture.update(old); "new" }, { actions.add(it) }, { _, _ -> true })
        nextGesture.update(old)
        nextGesture.down(0f, 0f)
        nextGesture.update(old)
        nextGesture.up()
        assertEquals(listOf("new"), actions)
    }
}
