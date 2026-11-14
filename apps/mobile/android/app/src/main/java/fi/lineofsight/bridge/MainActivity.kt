package fi.lineofsight.bridge

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.os.Bundle
import android.os.SystemClock
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.lifecycleScope
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.types.Permission
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private lateinit var hub: HubClient
    private lateinit var sdk: MetaBridge
    private lateinit var address: EditText
    private lateinit var physical: CheckBox
    private lateinit var connection: TextView
    private lateinit var recognition: TextView
    private lateinit var feedback: TextView
    private lateinit var source: TextView
    private lateinit var sdkState: TextView
    private lateinit var start: Button
    private lateinit var primary: Button
    private lateinit var rotate: Button
    private lateinit var preview: FramePreview
    private lateinit var displayPreview: FrameLayout
    private var frame: JpegFrame? = null
    private var rotation = 0
    private var startJob: Job? = null
    private var ticks: Job? = null
    private var errorMessage = ""
    private var sdkMessage = "SDK not started."
    private var diagnostic = false
    private var selections = 0
    private var actionTime = -1000L
    private val permissions = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        if (result.values.all { it }) connect() else {
            errorMessage = "Camera/Bluetooth permission denied. Grant permissions before connecting."
            render()
        }
    }
    private val glassesPermission = registerForActivityResult(Wearables.RequestPermissionContract()) { result ->
        result.onFailure { error, _ -> errorMessage = "Glasses camera permission: ${error.description}" }
        render()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        hub = HubClient(lifecycleScope, SystemClock::elapsedRealtime)
        sdk = MetaBridge(this, lifecycleScope)
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(30), dp(20), dp(24))
            setBackgroundColor(Color.rgb(245, 247, 250))
        }
        setContentView(ScrollView(this).apply { addView(content) })
        fun label(text: String, size: Float = 16f): TextView = TextView(this).apply {
            this.text = text; textSize = size; setTextColor(Color.rgb(20, 34, 53))
            setPadding(0, dp(8), 0, dp(8)); content.addView(this)
        }
        fun button(text: String, run: () -> Unit): Button = Button(this).apply {
            this.text = text; isAllCaps = false; setOnClickListener { run() }; content.addView(this)
        }
        label("LineOfSight", 28f)
        source = label("PHONE CAMERA VIA META MOCK / BAND SIMULATED", 14f)
        label("Face a screen to choose Expenses or JSON. No destination menu.")
        address = EditText(this).apply {
            hint = "http://YOUR-HUB-IP:8000"
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI
            setSingleLine(true)
            setText(getPreferences(MODE_PRIVATE).getString("hub", ""))
            content.addView(this)
        }
        physical = CheckBox(this).apply {
            text = "Use physical Display glasses (hardware check pending)"
            content.addView(this)
            setOnCheckedChangeListener { _, _ ->
                stop()
                if (sdk.initialize()) sdk.stop()
                render()
            }
        }
        button("Connect to hub") { requestPermissionsAndConnect() }
        connection = label("Disconnected")
        start = button("Start camera test") { startCamera() }
        rotate = button("Camera rotation: 0° (tap +90°)") {
            if (hub.guard.active == null && startJob?.isActive != true) {
                rotation = (rotation + 90) % 360
                rotate.text = "Camera rotation: $rotation° (tap +90°)"
            }
        }
        preview = FramePreview(this).also { content.addView(it, LinearLayout.LayoutParams(-1, dp(250))) }
        label("Central outline = marker selection area. Check upright text before testing.", 13f)
        recognition = label("Recognized: None / Stable target: None", 19f)
        feedback = label("")
        primary = button("Receipt workflow unavailable") { }
        button("Stop camera test") { stop() }
        button("Cancel receipt") { hub.sendAction("CANCEL") }
        label("SDK display preview / simulated selection", 19f)
        sdkState = label(sdkMessage)
        displayPreview = FrameLayout(this).also { content.addView(it, LinearLayout.LayoutParams(-1, dp(300))) }
        button("Show SDK selection test (no transfer)") {
            diagnostic = !diagnostic
            render()
        }
        label("Tap the action inside the SDK preview to test its callback. This is not a real band event.", 13f)
        button("Register physical glasses with Meta AI") {
            stop()
            if (physical.isChecked) sdk.register(this)
            else { errorMessage = "Enable physical-glasses setup first."; render() }
        }
        button("Grant physical glasses camera permission") {
            if (physical.isChecked && sdk.initialize()) glassesPermission.launch(Permission.CAMERA)
        }
        button("Open firmware update") {
            if (physical.isChecked && sdk.initialize()) Wearables.openFirmwareUpdate(this)
                .onFailure { error, _ -> errorMessage = error.description; render() }
        }
        button("Open Meta glasses app update") {
            if (physical.isChecked && sdk.initialize()) Wearables.openDATGlassesAppUpdate(this)
                .onFailure { error, _ -> errorMessage = error.description; render() }
        }
        label("Only one phone/controller may connect. Close /fixture-mobile first.\nReceipt extraction, transfers and Undo require the later hub workflow.\nThis app stops camera work when backgrounded; press Connect and Start after returning.", 13f)

        hub.onChanged = { render() }
        hub.onInvalidated = {
            frame = null
            preview.replace(null)
            diagnostic = false
            sdk.stop()
        }
        sdk.onFrame = { jpeg, bitmap ->
            val lease = hub.guard.active
            if (lease != null && hub.guard.usable(lease, jpeg, SystemClock.elapsedRealtime())) {
                frame = jpeg
                preview.replace(bitmap)
                hub.submit(lease, jpeg)
                render()
            } else bitmap.recycle()
        }
        sdk.onPreview = {
            displayPreview.removeAllViews()
            if (it != null) displayPreview.addView(it, FrameLayout.LayoutParams(-1, -1))
        }
        sdk.onFailure = { reason ->
            errorMessage = reason
            hub.stop()
            render()
        }
        sdk.onStatus = { sdkMessage = it; render() }
        render()
    }

    private fun requestPermissionsAndConnect() {
        val needed = arrayOf(Manifest.permission.CAMERA, Manifest.permission.BLUETOOTH_CONNECT)
            .filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (needed.isEmpty()) connect() else permissions.launch(needed.toTypedArray())
    }

    private fun connect() {
        stop()
        errorMessage = ""
        try {
            HubAddress.parse(address.text.toString())
            if (!sdk.initialize()) return
            getPreferences(MODE_PRIVATE).edit().putString("hub", address.text.toString().trim()).apply()
            hub.connect(address.text.toString())
        } catch (error: Exception) {
            errorMessage = error.message.orEmpty()
            render()
        }
    }

    private fun startCamera() {
        if (startJob?.isActive == true || hub.guard.active != null) return
        errorMessage = ""
        val usePhone = !physical.isChecked
        startJob = lifecycleScope.launch {
            try {
                val lease = hub.startStream(if (usePhone) "camera_stream" else "native_camera")
                sdk.start(usePhone, rotation)
                if (!hub.guard.owns(lease)) sdk.stop()
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                errorMessage = "Camera start failed: ${error.message}"
                hub.stop()
            } finally {
                startJob = null
                render()
            }
        }
        render()
    }

    private fun activate(intent: ActionIntent) {
        if (intent.action == "SDK_TEST") {
            if (diagnostic && hub.guard.active != null) { selections++; render() }
            return
        }
        val now = SystemClock.elapsedRealtime()
        if (now - actionTime < 600) return
        if (hub.perform(intent, frame)) actionTime = now
    }

    private fun stop() {
        startJob?.cancel()
        startJob = null
        hub.stop()
    }

    private fun render() {
        if (!::primary.isInitialized) return
        val snapshot = hub.snapshots.value
        val active = hub.guard.active != null
        source.text = if (physical.isChecked) "PHYSICAL GLASSES PATH / HARDWARE VALIDATION PENDING" else "PHONE CAMERA VIA META MOCK / BAND SIMULATED"
        connection.text = "${hub.status}\nHub run: ${snapshot?.runId ?: "None"}"
        start.isEnabled = hub.status == "Connected" && !active && startJob?.isActive != true
        rotate.isEnabled = !active && startJob?.isActive != true
        physical.isEnabled = !active && startJob?.isActive != true
        val name: (String?) -> String = { if (it == "expenses") "Expenses" else if (it == "json") "JSON" else "None" }
        recognition.text = "Recognized: ${name(snapshot?.recognized)}\nStable target: ${name(snapshot?.target)}"
        feedback.text = listOf(errorMessage, hub.message, snapshot?.visionMessage, snapshot?.feedback,
            "Receipt source: ${snapshot?.receiptMode ?: "unknown"} (independent of camera source)")
            .filterNotNull().filter { it.isNotBlank() }.joinToString("\n")
        val intent = ActionPolicy.current(snapshot, hub.captureAvailable)
        val fresh = frame?.let { SystemClock.elapsedRealtime() - it.deliveredAtMs in 0..300 } == true
        val actionable = active && fresh && !hub.busy && hub.status == "Connected"
        primary.text = when (intent?.action) {
            "CAPTURE" -> "Capture receipt (phone input)"
            "CONFIRM" -> "Confirm ${name(snapshot?.target)} ${snapshot?.amount.orEmpty()}"
            else -> if (!hub.captureAvailable) "Receipt workflow unavailable on this hub" else "Waiting for receipt / target"
        }
        primary.isEnabled = actionable && intent != null
        primary.setOnClickListener { if (intent != null) activate(intent) }
        sdkState.text = "$sdkMessage\nSDK selections received: $selections"
        val displayAction = if (diagnostic && active) ActionIntent(snapshot?.runId.orEmpty(), "SDK_TEST") else intent.takeIf { actionable }
        val title = if (diagnostic) "SDK selection test" else "${name(snapshot?.target)} ${snapshot?.amount.orEmpty()}"
        val detail = if (diagnostic) "Selections: $selections / no transfer" else snapshot?.visionMessage ?: "Waiting for hub"
        sdk.showCard(title, detail, displayAction, ::activate)
    }

    override fun onStart() {
        super.onStart()
        ticks = lifecycleScope.launch { while (isActive) { render(); delay(150) } }
    }

    override fun onStop() {
        ticks?.cancel()
        startJob?.cancel()
        startJob = null
        if (::hub.isInitialized) hub.pause()
        super.onStop()
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
}

private class FramePreview(context: android.content.Context) : View(context) {
    private var image: Bitmap? = null
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val destination = RectF()
    fun replace(next: Bitmap?) {
        val previous = image
        image = next
        invalidate()
        if (previous !== next) previous?.recycle()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.rgb(20, 27, 38))
        val bitmap = image ?: return
        val scale = minOf(width.toFloat() / bitmap.width, height.toFloat() / bitmap.height)
        val w = bitmap.width * scale
        val h = bitmap.height * scale
        val left = (width - w) / 2
        val top = (height - h) / 2
        destination.set(left, top, left + w, top + h)
        canvas.drawBitmap(bitmap, null, destination, paint)
        paint.color = Color.rgb(80, 230, 185)
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 3f
        canvas.drawRect(left + w / 4, top + h / 4, left + 3 * w / 4, top + 3 * h / 4, paint)
        paint.style = Paint.Style.FILL
    }
}
