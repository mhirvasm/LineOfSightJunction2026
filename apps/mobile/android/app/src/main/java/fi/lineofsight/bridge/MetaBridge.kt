package fi.lineofsight.bridge

import android.app.Activity
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.Rect
import android.graphics.YuvImage
import android.os.SystemClock
import android.view.View
import com.meta.wearable.dat.camera.Camera
import com.meta.wearable.dat.camera.addCamera
import com.meta.wearable.dat.camera.types.StreamConfiguration
import com.meta.wearable.dat.camera.types.StreamState
import com.meta.wearable.dat.camera.types.VideoQuality
import com.meta.wearable.dat.inputs.addInputs
import com.meta.wearable.dat.inputs.removeInputs
import com.meta.wearable.dat.inputs.types.InputEvent
import com.meta.wearable.dat.inputs.types.InputSource
import com.meta.wearable.dat.inputs.types.InputsConfiguration
import com.meta.wearable.dat.inputs.types.InputsState
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.selectors.AutoDeviceSelector
import com.meta.wearable.dat.core.selectors.SpecificDeviceSelector
import com.meta.wearable.dat.core.session.DeviceSession
import com.meta.wearable.dat.core.session.DeviceSessionState
import com.meta.wearable.dat.core.types.Permission
import com.meta.wearable.dat.core.types.PermissionStatus
import com.meta.wearable.dat.core.types.RegistrationState
import com.meta.wearable.dat.display.Display
import com.meta.wearable.dat.display.addDisplay
import com.meta.wearable.dat.display.types.DisplayState
import com.meta.wearable.dat.display.views.ActionRole
import com.meta.wearable.dat.display.views.ButtonStyle
import com.meta.wearable.dat.display.views.TextStyle
import com.meta.wearable.dat.mockdevice.MockDeviceKit
import com.meta.wearable.dat.mockdevice.api.GlassesModel
import com.meta.wearable.dat.mockdevice.api.MockGlasses
import com.meta.wearable.dat.mockdevice.api.camera.CameraFacing
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import java.io.ByteArrayOutputStream

class MetaBridge(private val context: Context, private val parent: CoroutineScope) {
    private companion object { var sdkInitialized = false }
    var onDrag: (InputEvent.Drag) -> Unit = {}
    private var inputsAttached = false
    var onFrame: (JpegFrame, Bitmap) -> Unit = { _, _ -> }
    var onPreview: (View?) -> Unit = {}
    var onFailure: (String) -> Unit = {}
    var onStatus: (String) -> Unit = {}
    private val mocks by lazy { MockDeviceKit.getInstance(context.applicationContext) }
    private var mock: MockGlasses? = null
    private var session: DeviceSession? = null
    private var camera: Camera? = null
    private var display: Display? = null
    private var work: CoroutineScope? = null
    private var renderKey: Any? = null
    private var generation = 0L

    fun initialize(): Boolean {
        if (sdkInitialized) return true
        Wearables.initialize(context.applicationContext).fold(
            onSuccess = { sdkInitialized = true },
            onFailure = { error, _ -> onFailure("SDK initialization: ${error.description}") },
        )
        return sdkInitialized
    }

    fun register(activity: Activity) {
        if (!initialize()) return
        mocks.disable()
        Wearables.startRegistration(activity)
    }

    suspend fun start(phone: Boolean, rotation: Int, rawInputs: Boolean = false) {
        stop()
        check(initialize()) { "Meta SDK could not initialize." }
        val epoch = generation
        val errors = CoroutineExceptionHandler { _, throwable ->
            if (epoch == generation) onFailure("SDK session: ${throwable.message}")
        }
        val owner = CoroutineScope(parent.coroutineContext + SupervisorJob(parent.coroutineContext[Job]) + errors)
        work = owner
        val selector = if (phone) {
            mocks.enable()
            val glasses = mocks.pairGlasses(GlassesModel.META_RAYBAN_DISPLAY).fold(
                onSuccess = { it }, onFailure = { error, _ -> error(error.description) })
            mock = glasses
            glasses.services.camera.setCameraFeed(CameraFacing.BACK)
            glasses.powerOn()
            glasses.unfold()
            glasses.don()
            onPreview(glasses.services.display.createPreviewView(context))
            SpecificDeviceSelector(glasses.deviceIdentifier)
        } else {
            mocks.disable()
            check(Wearables.registrationState.value == RegistrationState.REGISTERED) {
                "Register with Meta AI and pair the real Display glasses before Start."
            }
            val permitted = Wearables.checkPermissionStatus(Permission.CAMERA).fold(
                onSuccess = { it == PermissionStatus.Granted }, onFailure = { _, _ -> false })
            check(permitted) { "Grant glasses camera permission using the permission button before Start." }
            AutoDeviceSelector(filter = { it.isDisplayCapable() })
        }
        val created = Wearables.createSession(selector).fold(
            onSuccess = { it }, onFailure = { error, _ -> error(error.description) })
        session = created
        owner.launch { created.errors.collect { onFailure("SDK session: ${it.description}") } }
        created.start()
        withTimeout(12_000) { created.state.first { it == DeviceSessionState.STARTED } }
        check(epoch == generation) { "Camera start was canceled." }
        if (rawInputs) {
            val inputs = created.addInputs(InputsConfiguration(sources = setOf(InputSource.NEURAL_BAND_DRAG)))
                .fold(onSuccess = { it }, onFailure = { error, _ -> error("Inputs approval/configuration: ${error.description}") })
            inputsAttached = true
            owner.launch { inputs.events.collect { event ->
                if (epoch == generation && event is InputEvent.Drag && event.source == InputSource.NEURAL_BAND_DRAG) onDrag(event)
            } }
            owner.launch { inputs.errors.collect { failure ->
                if (failure != null) onFailure("Inputs: ${failure.description}")
            } }
            owner.launch {
                var active = false
                inputs.state.collect { state ->
                    if (state == InputsState.ACTIVE) active = true
                    if (active && state != InputsState.ACTIVE) onFailure("Band input interrupted. Start again.")
                }
            }
            withTimeout(8000) { inputs.state.first { it == InputsState.ACTIVE } }
            onStatus("Raw band inputs active; verify hold and right-drag direction on hardware.")
        }
        val attached = created.addCamera(StreamConfiguration(videoQuality = VideoQuality.MEDIUM, frameRate = 15, compressVideo = false))
            .fold(onSuccess = { it }, onFailure = { error, _ -> error(error.description) })
        camera = attached
        val rawFrames = Channel<RawFrame>(Channel.CONFLATED)
        owner.launch {
            var lastCopied = -1000L
            attached.stream.videoStream.collect { frame ->
                val now = SystemClock.elapsedRealtime()
                if (now - lastCopied < 200) return@collect
                require(!frame.isCompressed) { "Expected uncompressed SDK video." }
                val pixels = frame.width.toLong() * frame.height
                require(pixels in 1..4_000_000 && frame.buffer.remaining().toLong() == pixels * 3 / 2) {
                    "Unexpected SDK pixel layout. Expected packed I420; verify this device's feed."
                }
                lastCopied = now
                // copy before leaving the SDK callback; its buffer may be reused.
                val copy = ByteArray(frame.buffer.remaining())
                frame.buffer.duplicate().get(copy)
                rawFrames.trySend(RawFrame(copy, frame.width, frame.height, now))
            }
        }
        owner.launch {
            for (raw in rawFrames) {
                if (SystemClock.elapsedRealtime() - raw.deliveredAt > 300) continue
                val converted = withContext(Dispatchers.Default) { encode(raw, rotation) }
                if (epoch == generation && SystemClock.elapsedRealtime() - raw.deliveredAt <= 300) {
                    onFrame(JpegFrame(converted.first, raw.deliveredAt), converted.second)
                } else converted.second.recycle()
            }
        }
        owner.launch { attached.stream.errorStream.collect { onFailure("SDK camera: ${it.description}") } }
        owner.launch {
            var hasStarted = false
            attached.stream.state.collect {
                if (it == StreamState.STARTED || it == StreamState.STREAMING) hasStarted = true
                if (hasStarted && it != StreamState.STARTED && it != StreamState.STREAMING && it != StreamState.STARTING) {
                    onFailure("SDK camera paused/stopped. Press Start to resume.")
                }
            }
        }
        owner.launch {
            created.state.collect {
                if (it == DeviceSessionState.PAUSED || it == DeviceSessionState.STOPPED) {
                    onFailure("Glasses session interrupted. Press Start to resume.")
                }
            }
        }
        attached.stream.start().onFailure { error, _ -> error(error.description) }
        created.addDisplay().fold(
            onSuccess = { attachedDisplay ->
                display = attachedDisplay
                owner.launch {
                    attachedDisplay.state.collect {
                        if (it == DisplayState.STARTED) {
                            renderKey = null
                            onStatus("SDK display ready. Check the camera preview for fresh frames.")
                        }
                    }
                }
            },
            onFailure = { error, _ -> error("Camera/display concurrency: ${error.description}") },
        )
        owner.launch {
            try { kotlinx.coroutines.awaitCancellation() } finally { rawFrames.close() }
        }
    }

    fun showCard(title: String, detail: String, action: ActionIntent?, activate: (ActionIntent) -> Unit) {
        val screen = display ?: return
        if (screen.state.value != DisplayState.STARTED) return
        val key = Triple(title, detail, action)
        if (renderKey == key) return
        renderKey = key
        val epoch = generation
        work?.launch {
            screen.sendContent {
                flexBox(padding = 20, gap = 12) {
                    text(title.take(80), style = TextStyle.HEADING)
                    text(detail.take(180))
                    if (action != null) button(
                        label = if (action.action == "CAPTURE") "Capture" else "Confirm",
                        style = ButtonStyle.PRIMARY, actionRole = ActionRole.PRIMARY,
                        onClick = { if (epoch == generation) parent.launch { activate(action) } },
                    )
                }
            }.onFailure { error, _ -> onFailure("SDK display: ${error.description}") }
        }
    }

    fun stop() {
        generation++
        work?.cancel()
        work = null
        camera?.close()
        camera = null
        display?.close()
        display = null
        if (inputsAttached) session?.removeInputs()
        inputsAttached = false
        session?.stop()
        session = null
        renderKey = null
        mock?.doff()
        mock?.powerOff()
        mock = null
        if (sdkInitialized && mocks.isEnabled) mocks.disable()
        onPreview(null)
    }

    private data class RawFrame(val bytes: ByteArray, val width: Int, val height: Int, val deliveredAt: Long)

    private fun encode(raw: RawFrame, rotation: Int): Pair<ByteArray, Bitmap> {
        val jpeg = ByteArrayOutputStream()
        val yuv = YuvImage(YuvLayout.nv21(raw.bytes, raw.width, raw.height), ImageFormat.NV21, raw.width, raw.height, null)
        check(yuv.compressToJpeg(Rect(0, 0, raw.width, raw.height), 85, jpeg)) { "Could not encode SDK frame." }
        val original = requireNotNull(BitmapFactory.decodeByteArray(jpeg.toByteArray(), 0, jpeg.size()))
        var bitmap = original
        if (rotation != 0) {
            bitmap = Bitmap.createBitmap(original, 0, 0, original.width, original.height,
                Matrix().apply { postRotate(rotation.toFloat()) }, true)
            if (bitmap !== original) original.recycle()
        }
        val scale = minOf(1f, 1280f / maxOf(bitmap.width, bitmap.height))
        if (scale < 1) {
            val resized = Bitmap.createScaledBitmap(bitmap, (bitmap.width * scale).toInt(), (bitmap.height * scale).toInt(), true)
            if (resized !== bitmap) bitmap.recycle()
            bitmap = resized
        }
        jpeg.reset()
        check(bitmap.compress(Bitmap.CompressFormat.JPEG, 82, jpeg))
        val bytes = jpeg.toByteArray()
        check(bytes.size <= 2_000_000) { "JPEG exceeds the hub limit." }
        return bytes to bitmap
    }
}
