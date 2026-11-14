package fi.lineofsight.bridge

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.util.UUID

class ProtocolTest {
    private fun snapshot(state: String = "READY", preview: String? = null, confirm: Boolean = false): HubSnapshot =
        HubSnapshot(UUID.randomUUID().toString(), state, null, null, null, preview, confirm, "fixture", "", "", "")

    @Test fun `hub endpoints preserve the origin and assign only the mobile role`() {
        val address = HubAddress.parse(" http://192.168.1.100:8000 ")
        assertEquals("http://192.168.1.100:8000/v1/frames", address.endpoint("/v1/frames").toString())
        assertEquals("mobile", address.socket().queryParameter("role"))
        listOf("http://user:secret@localhost", "http://localhost/expense", "http://localhost/?token=x", "ftp://localhost").forEach {
            assertThrows(IllegalArgumentException::class.java) { HubAddress.parse(it) }
        }
    }

    @Test fun `recognition stays distinct from a current stable target`() {
        val data = JSONObject("""{"v":1,"type":"SNAPSHOT","run_id":"${UUID.randomUUID()}","state":"READY","target_id":null,"can_confirm":false,"vision":{"detected_target_id":"json","stream_id":null}}""")
        val parsed = HubSnapshot.parse(data)
        assertEquals("json", parsed.recognized)
        assertNull(parsed.target)
        assertNull(ActionPolicy.current(parsed, false))
    }

    @Test fun `held receipt details are available without a destination`() {
        val data = JSONObject("""{"v":1,"type":"SNAPSHOT","run_id":"${UUID.randomUUID()}","state":"HOLDING","target_id":null,"capture_id":"capture","receipt":{"merchant":"Demo Cafe","date":"2026-11-14","total_minor":2480,"currency":"EUR"}}""")
        val parsed = HubSnapshot.parse(data)
        assertNull(parsed.target)
        assertEquals("EUR 24.80", parsed.amount)
        assertEquals("Demo Cafe", parsed.merchant)
        assertEquals("2026-11-14", parsed.receiptDate)
        assertNull(ActionPolicy.current(parsed, true))
    }

    @Test fun `text preview preserves newlines and confirms without receipt fields`() {
        val data = JSONObject("""{"v":1,"type":"SNAPSHOT","run_id":"${UUID.randomUUID()}","state":"PREVIEW","target_id":"text","capture_id":"capture","preview_id":"text-preview","can_confirm":true,"receipt":null,"text":"Hyvää päivää!\n<em>literal</em>"}""")
        val parsed = HubSnapshot.parse(data)
        assertEquals("Hyvää päivää!\n<em>literal</em>", parsed.text)
        assertEquals("", parsed.amount)
        assertEquals("text", parsed.target)
        assertEquals("text-preview", ActionPolicy.current(parsed, true)?.previewId)
        assertNull(ActionPolicy.current(parsed.copy(state = "HOLDING", canConfirm = false, previewId = null), true))
    }

    @Test fun `old confirmation cannot follow a changed target preview or reset run`() {
        val old = snapshot("PREVIEW", "expenses-preview", true)
        val action = requireNotNull(ActionPolicy.current(old, true))
        assertTrue(ActionPolicy.accepts(action, old, true))
        assertFalse(ActionPolicy.accepts(action, old.copy(previewId = "json-preview"), true))
        assertFalse(ActionPolicy.accepts(action, old.copy(runId = UUID.randomUUID().toString()), true))
        assertFalse(ActionPolicy.accepts(action, old.copy(canConfirm = false), true))
        assertFalse(ActionPolicy.accepts(action, old.copy(state = "APPLIED"), true))
        assertFalse(ActionPolicy.accepts(action, null, true))
    }

    @Test fun `capture requires both a ready state and the implemented server endpoint`() {
        val ready = snapshot()
        assertNull(ActionPolicy.current(ready, false))
        assertEquals("CAPTURE", ActionPolicy.current(ready, true)?.action)
        assertNull(ActionPolicy.current(ready.copy(state = "READING"), true))
        assertNull(ActionPolicy.current(ready.copy(state = "STOPPED"), true))
    }

    @Test fun `reset and stream replacement invalidate all queued frame leases`() {
        val guard = StreamGuard()
        val first = guard.activate("run", "stream")
        val frame = JpegFrame(byteArrayOf(1), 1000)
        assertTrue(guard.usable(first, frame, 1300))
        assertFalse(guard.usable(first, frame, 1301))
        assertFalse(guard.usable(first, frame, 999))
        assertFalse(guard.usable(first, frame.copy(bytes = ByteArray(2_000_001)), 1000))
        guard.invalidate()
        val next = guard.activate("run", "replacement")
        assertFalse(guard.usable(first, frame, 1000))
        assertTrue(guard.usable(next, frame, 1000))
    }

    @Test fun `I420 chroma becomes NV21 VU without altering luminance`() {
        val source = byteArrayOf(1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 20, 21)
        assertArrayEquals(byteArrayOf(1, 2, 3, 4, 5, 6, 7, 8, 20, 10, 21, 11), YuvLayout.nv21(source, 4, 2))
        assertThrows(IllegalArgumentException::class.java) { YuvLayout.nv21(source, 3, 2) }
        assertThrows(IllegalArgumentException::class.java) { YuvLayout.nv21(source, 8, 2) }
        assertThrows(IllegalArgumentException::class.java) { YuvLayout.nv21(source, Int.MAX_VALUE - 1, 4) }
    }
}
