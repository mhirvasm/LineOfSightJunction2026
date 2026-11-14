package fi.lineofsight.bridge

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.DelicateCoroutinesApi
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.newSingleThreadContext
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.util.UUID
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

@OptIn(ExperimentalCoroutinesApi::class, DelicateCoroutinesApi::class)
class HubClientTest {
    private class FakeHub : AutoCloseable {
        val server = MockWebServer()
        val uploads = LinkedBlockingQueue<RecordedRequest>()
        val captureUploads = LinkedBlockingQueue<RecordedRequest>()
        val actions = LinkedBlockingQueue<JSONObject>()
        var coffeeReady = false
        var socket: WebSocket? = null
        var run = UUID.randomUUID().toString()
        var stream: String? = null
        var state = "STOPPED"
        var delayFrames = false
        var reject = false
        init {
            server.dispatcher = object : Dispatcher() {
                override fun dispatch(request: RecordedRequest): MockResponse = when (request.requestUrl?.encodedPath) {
                    "/v1/events" -> MockResponse().withWebSocketUpgrade(object : WebSocketListener() {
                        override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
                            socket = webSocket
                            if (reject) webSocket.send(JSONObject().put("v", 1).put("type", "ERROR").put("run_id", run)
                                .put("error", "connection_rejected").put("message", "Other phone already connected").toString())
                            else snapshot()
                        }
                        override fun onMessage(webSocket: WebSocket, text: String) {
                            val json = JSONObject(text)
                            if (json.optString("type") == "ACTION") actions.add(json)
                            if (json.optString("type") == "STREAM_STARTED") stream = json.getString("stream_id")
                            if (json.optString("action") == "START") state = "READY"
                            if (json.optString("action") == "STOP") { state = "STOPPED"; stream = null }
                            snapshot()
                        }
                    })
                    "/openapi.json" -> MockResponse().setBody("""{"paths":{}}""")
                    "/v1/frames" -> {
                        uploads.add(request)
                        MockResponse().setResponseCode(202).setBody("{\"accepted\":true}")
                            .apply { if (delayFrames) setBodyDelay(500, TimeUnit.MILLISECONDS) }
                    }
                    "/v1/captures" -> { captureUploads.add(request); MockResponse().setResponseCode(202) }
                    else -> MockResponse().setResponseCode(404)
                }
            }
            server.start()
        }
        fun snapshot() {
            socket?.send(JSONObject().put("v", 1).put("type", "SNAPSHOT").put("run_id", run).put("state", state)
                .put("source_mode", "fixture").put("can_confirm", false)
                .put("target_id", if (coffeeReady) "coffee" else JSONObject.NULL).put("can_select_coffee", coffeeReady)
                .put("vision", JSONObject().put("stream_id", stream ?: JSONObject.NULL)).toString())
        }
        override fun close() { socket?.close(1000, "test complete"); server.shutdown() }
    }

    @Test fun `real sockets announce a stream and upload only first and newest pending frames`() {
        newSingleThreadContext("bridge-test").use { thread -> runBlocking(thread) {
            FakeHub().use { server ->
                val scope = CoroutineScope(SupervisorJob() + thread)
                try {
                    server.delayFrames = true
                    val client = HubClient(scope, { 1000L })
                    client.connect(server.server.url("/").toString())
                    withTimeout(5000) { client.snapshots.first { it != null } }
                    val lease = client.startStream("camera_stream")
                    client.submit(lease, JpegFrame("FIRST-JPEG".toByteArray(), 1000))
                    withTimeout(5000) { while (server.uploads.isEmpty()) delay(10) }
                    client.submit(lease, JpegFrame("REPLACED-JPEG".toByteArray(), 1000))
                    client.submit(lease, JpegFrame("LATEST-JPEG".toByteArray(), 1000))
                    withTimeout(5000) { while (server.uploads.size < 2) delay(10) }
                    val first = server.uploads.remove().body.readUtf8()
                    val latest = server.uploads.remove().body.readUtf8()
                    assertTrue(first.contains("FIRST-JPEG"))
                    assertTrue(first.contains(lease.runId) && first.contains(lease.streamId))
                    assertTrue(latest.contains("LATEST-JPEG"))
                    assertFalse(latest.contains("REPLACED-JPEG"))
                    assertFalse(client.captureAvailable)
                    client.disconnect()
                } finally { scope.cancel() }
            }
        } }
    }

    @Test fun `reset cancels pending uploads and requires an explicit new start`() {
        newSingleThreadContext("bridge-reset-test").use { thread -> runBlocking(thread) {
            FakeHub().use { server ->
                val scope = CoroutineScope(SupervisorJob() + thread)
                try {
                    server.delayFrames = true
                    val client = HubClient(scope, { 1000L })
                    client.connect(server.server.url("/").toString())
                    withTimeout(5000) { client.snapshots.first { it != null } }
                    val old = client.startStream("camera_stream")
                    client.submit(old, JpegFrame(byteArrayOf(1), 1000))
                    withTimeout(5000) { while (server.uploads.isEmpty()) delay(10) }
                    client.submit(old, JpegFrame("OBSOLETE".toByteArray(), 1000))
                    server.run = UUID.randomUUID().toString()
                    server.state = "STOPPED"
                    server.stream = null
                    server.snapshot()
                    withTimeout(5000) { client.snapshots.first { it?.runId == server.run } }
                    assertNull(client.guard.active)
                    client.submit(old, JpegFrame("REPLAY".toByteArray(), 1000))
                    delay(650)
                    assertEquals(1, server.uploads.size)
                    val fresh = client.startStream("camera_stream")
                    assertNotEquals(old.streamId, fresh.streamId)
                    assertEquals(server.run, fresh.runId)
                    client.disconnect()
                } finally { scope.cancel() }
            }
        } }
    }

    @Test fun `duplicate controller rejection does not reconnect automatically`() {
        newSingleThreadContext("bridge-rejection-test").use { thread -> runBlocking(thread) {
            FakeHub().use { server ->
                val scope = CoroutineScope(SupervisorJob() + thread)
                try {
                    server.reject = true
                    val client = HubClient(scope, { 1000L })
                    client.connect(server.server.url("/").toString())
                    withTimeout(5000) { while (client.status != "Connection rejected") delay(10) }
                    delay(1700)
                    assertEquals(1, server.server.requestCount)
                    assertNull(client.snapshots.value)
                    client.disconnect()
                } finally { scope.cancel() }
            }
        } }
    }

    @Test fun `coffee selection sends its interaction ID without uploading an image`() {
        newSingleThreadContext("coffee-test").use { thread -> runBlocking(thread) {
            FakeHub().use { server ->
                val scope = CoroutineScope(SupervisorJob() + thread)
                try {
                    val client = HubClient(scope, { 1000L })
                    client.connect(server.server.url("/").toString())
                    withTimeout(5000) { client.snapshots.first { it != null } }
                    client.startStream("camera_stream")
                    server.coffeeReady = true; server.snapshot()
                    val current = withTimeout(5000) { client.snapshots.first { it?.canSelectCoffee == true } }
                    val id = UUID.randomUUID().toString()
                    assertTrue(client.perform(requireNotNull(ActionPolicy.current(current, false)), JpegFrame(byteArrayOf(1), 1000), id))
                    withTimeout(5000) { while (server.actions.none { it.optString("action") == "SELECT_COFFEE" }) delay(10) }
                    val action = server.actions.first { it.optString("action") == "SELECT_COFFEE" }
                    assertEquals(id, action.getString("capture_id"))
                    assertTrue(server.captureUploads.isEmpty())
                    client.disconnect()
                } finally { scope.cancel() }
            }
        } }
    }
}
