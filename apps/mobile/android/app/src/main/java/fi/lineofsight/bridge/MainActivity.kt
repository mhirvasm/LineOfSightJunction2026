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
import android.view.MotionEvent
import android.content.Intent
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.types.Permission
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private lateinit var runtime: BridgeRuntime
    private lateinit var rawBand: CheckBox
    private lateinit var threshold: EditText
    private lateinit var touchPad: TextView
    private lateinit var receiptPreview: TextView
    private lateinit var summaryPreview: TextView
    private lateinit var interactionFeedback: TextView
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
    private val frame: JpegFrame? get() = runtime.frame
    private var rotation = 0
    private var startJob: Job? = null
    private var errorMessage = ""
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
        runtime = BridgeRuntime.get(this)
        hub = runtime.hub
        sdk = runtime.sdk
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(32), dp(16), dp(24))
            setBackgroundColor(Color.rgb(245, 247, 250))
        }
        val interaction = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(interaction, LinearLayout.LayoutParams(-1, -2))
        root.addView(ScrollView(this).apply { addView(content) }, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
        fun label(text: String, size: Float = 16f): TextView = TextView(this).apply {
            this.text = text; textSize = size; setTextColor(Color.rgb(20, 34, 53))
            setPadding(0, dp(8), 0, dp(8)); content.addView(this)
        }
        fun button(text: String, run: () -> Unit): Button = Button(this).apply {
            this.text = text; isAllCaps = false; setOnClickListener { run() }; content.addView(this)
        }
        label("Setup and diagnostics", 19f)
        source = label("LineOfSight 0.4.0 / phone simulation", 13f)
        label("Face a screen to choose Text, Expenses, JSON or Coffee. No destination menu.")
        address = EditText(this).apply {
            hint = "http://YOUR-HUB-IP:8000"
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI
            setSingleLine(true)
            setText(getPreferences(MODE_PRIVATE).getString("hub", ""))
            content.addView(this)
        }
        physical = CheckBox(this).apply {
            text = "Use physical Display glasses (hardware check pending)"
            isChecked = runtime.physical
            content.addView(this)
            setOnCheckedChangeListener { _, _ ->
                stop()
                if (sdk.initialize()) sdk.stop()
                render()
            }
        }
        rawBand = CheckBox(this).apply {
            text = "Raw band hold/drag (requires Inputs approval); off = tap fallback"
            isChecked = runtime.rawInputs
            content.addView(this)
        }
        threshold = EditText(this).apply {
            hint = "Band right-drag threshold in SDK units"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL
            setText("80")
            content.addView(this)
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
        touchPad = label("PHONE SIMULATION: hold here, move right to send, release to cancel", 18f).apply {
            setBackgroundColor(Color.rgb(200, 235, 224))
            minHeight = dp(88)
            gravity = android.view.Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(8), dp(12), dp(8))
            setOnTouchListener { view, event ->
                if (runtime.physical || hub.guard.active == null) return@setOnTouchListener false
                view.parent.requestDisallowInterceptTouchEvent(true)
                runtime.gesture.threshold = dp(80).toFloat()
                runtime.gesture.update(hub.snapshots.value)
                when (event.actionMasked) {
                    MotionEvent.ACTION_DOWN -> runtime.gesture.down(event.x, event.y)
                    MotionEvent.ACTION_MOVE -> runtime.gesture.move(event.x, event.y)
                    MotionEvent.ACTION_UP -> { runtime.gesture.up(); view.performClick() }
                    MotionEvent.ACTION_CANCEL -> runtime.gesture.abort()
                }
                true
            }
        }
        preview = FramePreview(this).also { content.addView(it, LinearLayout.LayoutParams(-1, dp(150))) }
        label("Central outline = marker selection area. Check upright text before testing.", 13f)
        receiptPreview = label("No text held. Aim at text or a receipt, then hold below.", 18f).apply {
            minLines = 3
            maxLines = 4
            ellipsize = android.text.TextUtils.TruncateAt.END
            setBackgroundColor(Color.WHITE)
            setPadding(dp(12), dp(8), dp(12), dp(8))
        }
        recognition = label("Destination: None", 16f)
        summaryPreview = label("", 14f).apply {
            maxLines = 3
            ellipsize = android.text.TextUtils.TruncateAt.END
        }
        interactionFeedback = label("Connect and start the camera below.", 14f).apply {
            minLines = 2
            maxLines = 3
            ellipsize = android.text.TextUtils.TruncateAt.END
        }
        feedback = label("")
        primary = button("Capture workflow unavailable") { }
        button("Stop camera test") { stop() }
        button("Cancel capture") { runtime.gesture.abort(); (hub.snapshots.value?.captureId ?: hub.lastCaptureId)?.let { hub.cancelCapture(it) } }
        button("Undo last action") { hub.sendAction("UNDO") }
        button("Send again (tap confirmation)") { if (!runtime.rawInputs) hub.sendAction("SEND_AGAIN") }
        label("SDK display preview / simulated selection", 19f)
        sdkState = label(runtime.sdkMessage)
        displayPreview = FrameLayout(this).also { content.addView(it, LinearLayout.LayoutParams(-1, dp(300))) }
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
        label("One controller only. Phone simulation stays foreground. Physical glasses use a foreground service with notification Stop. Live mode sends the captured image to the provider shown above.", 13f)
        listOf(source, preview, receiptPreview, summaryPreview, recognition, touchPad, interactionFeedback).forEach { view ->
            content.removeView(view)
            interaction.addView(view)
        }
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
        startJob = runtime.scope.launch {
            try {
                val lease = hub.startStream(if (usePhone) "camera_stream" else "native_camera")
                runtime.physical = !usePhone
                runtime.rawInputs = !usePhone && rawBand.isChecked
                runtime.gesture.threshold = if (usePhone) dp(80).toFloat() else (threshold.text.toString().toFloatOrNull()?.takeIf { it > 0 && it.isFinite() } ?: 80f)
                if (!usePhone) startForegroundService(Intent(this@MainActivity, GlassesService::class.java))
                sdk.start(usePhone, rotation, runtime.rawInputs)
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
        val now = SystemClock.elapsedRealtime()
        if (now - actionTime < 600) return
        if (hub.perform(intent, frame)) actionTime = now
    }

    private fun stop() {
        startJob?.cancel()
        startJob = null
        runtime.stop()
    }

    private fun render() {
        if (!::primary.isInitialized) return
        val snapshot = hub.snapshots.value
        val active = hub.guard.active != null
        source.text = "LineOfSight 0.4.0 / ${if (physical.isChecked) "glasses" else "phone simulation"} / ${snapshot?.receiptMode ?: "disconnected"}"
        connection.text = "${hub.status}\nHub run: ${snapshot?.runId ?: "None"}"
        start.isEnabled = hub.status == "Connected" && !active && startJob?.isActive != true
        rotate.isEnabled = !active && startJob?.isActive != true
        physical.isEnabled = !active && startJob?.isActive != true
        rawBand.isEnabled = !active && startJob?.isActive != true
        threshold.isEnabled = !active && startJob?.isActive != true
        val name: (String?) -> String = { if (it == "expenses") "Expenses" else if (it == "json") "JSON" else if (it == "text") "Text" else if (it == "coffee") "Coffee" else "None" }
        recognition.text = "Destination: ${name(snapshot?.target)}"
        receiptPreview.text = when {
            snapshot?.interactionKind == "coffee" && snapshot.state == "APPLIED" -> "Coffee is ${if (snapshot.coffeeOn) "ON / brewing" else "OFF"}.\nHold and swipe again to toggle."
            snapshot?.interactionKind == "coffee" -> "Turn coffee ${if (snapshot.coffeeDesired) "ON" else "OFF"}?\nKeep aiming at Coffee and swipe right."
            snapshot?.canSelectCoffee == true -> "Coffee is ${if (snapshot.coffeeOn) "ON" else "OFF"}.\nHold below, then swipe right to toggle."
            hub.busy && snapshot?.state in setOf("READY", "APPLIED") -> "Capturing text...\nKeep holding."
            snapshot?.state == "READING" && snapshot.textStatus == "processing" -> "Text read.\nCorrecting grammar and summarizing...\nKeep holding."
            snapshot?.state == "READING" -> "Reading text...\nKeep holding until the preview appears."
            snapshot?.state in setOf("HOLDING", "PREVIEW", "APPLIED") && !snapshot?.text.isNullOrBlank() && (snapshot?.target == "text" || snapshot?.amount.isNullOrBlank()) ->
                "${if (snapshot?.state == "APPLIED") "Sent" else if (snapshot?.textStatus == "ready") "AI-corrected text" else "Original text"}: ${snapshot?.text}"
            snapshot?.state in setOf("HOLDING", "PREVIEW", "APPLIED") && !snapshot?.amount.isNullOrBlank() ->
                "${if (snapshot?.state == "APPLIED") "Sent" else "Receipt held"}: ${snapshot?.amount}\n${snapshot?.merchant.orEmpty()}\n${snapshot?.receiptDate.orEmpty()}"
            else -> "No text held.\nAim at text or a receipt, then hold below."
        }
        summaryPreview.text = snapshot?.summary?.let { "Summary: $it" }.orEmpty()
        summaryPreview.visibility = if (snapshot?.summary.isNullOrBlank()) View.GONE else View.VISIBLE
        touchPad.text = when {
            runtime.gesture.held && snapshot?.interactionKind == "coffee" && snapshot.state == "PREVIEW" -> "SLIDE RIGHT TO TURN ${if (snapshot.coffeeDesired) "ON" else "OFF"}\nRelease cancels."
            !active -> "Start the camera below to enable hold / drag"
            runtime.gesture.held && !runtime.gesture.hasCapture -> "CAPTURE NOT STARTED\nRelease, keep the camera steady, then hold again."
            runtime.gesture.held && hub.busy && snapshot?.state in setOf("READY", "APPLIED") -> "KEEP HOLDING\nCapturing text..."
            runtime.gesture.held && snapshot?.state == "APPLIED" -> "Sent. Lift your finger before the next capture."
            runtime.gesture.held && snapshot?.state == "PREVIEW" -> "SLIDE RIGHT TO SEND\nKeep touching; release cancels."
            runtime.gesture.held && snapshot?.state == "HOLDING" -> "KEEP HOLDING / AIM AT A SCREEN\nRelease cancels."
            runtime.gesture.held -> "KEEP HOLDING\nText preview appears above."
            else -> "HOLD HERE TO CAPTURE\nSlide right to send; release cancels."
        }
        interactionFeedback.text = when {
            errorMessage.isNotBlank() -> errorMessage
            hub.status != "Connected" -> hub.status
            !active -> "Press Start camera test in setup below."
            hub.message.contains("failed", true) || hub.message.contains("rejected", true) -> hub.message
            else -> snapshot?.feedback ?: "Waiting for the hub."
        }
        feedback.text = listOf(errorMessage, hub.message, snapshot?.visionMessage, snapshot?.feedback,
            "Extraction source: ${snapshot?.receiptMode ?: "unknown"} (independent of camera source)")
            .filterNotNull().filter { it.isNotBlank() }.joinToString("\n")
        val intent = ActionPolicy.current(snapshot, hub.captureAvailable)
        val fresh = frame?.let { SystemClock.elapsedRealtime() - it.deliveredAtMs in 0..300 } == true
        val actionable = active && fresh && !hub.busy && hub.status == "Connected"
        primary.text = when (intent?.action) {
            "SELECT_COFFEE" -> "Select Coffee (phone input)"
            "CAPTURE" -> "Capture text / receipt (phone input)"
            "CONFIRM" -> if (snapshot?.interactionKind == "coffee") "Turn coffee ${if (snapshot.coffeeDesired) "on" else "off"}" else "Confirm ${name(snapshot?.target)} ${snapshot?.amount.orEmpty()}"
            else -> if (!hub.captureAvailable) "Capture workflow unavailable on this hub" else "Waiting for text / target"
        }
        primary.isEnabled = actionable && intent != null && !runtime.rawInputs && !runtime.gesture.held
        primary.setOnClickListener { if (intent != null) activate(intent) }
        sdkState.text = "${runtime.sdkMessage}\n${runtime.inputMessage}"
    }

    override fun onStart() {
        super.onStart()
        runtime.changed = { render() }
        runtime.bitmap = { preview.replace(it) }
        runtime.preview = {
            displayPreview.removeAllViews()
            if (it != null) displayPreview.addView(it, FrameLayout.LayoutParams(-1, -1))
        }
        render()
    }

    override fun onStop() {
        runtime.changed = {}
        runtime.bitmap = null
        runtime.preview = null
        preview.replace(null)
        if (!runtime.physical) {
            startJob?.cancel()
            startJob = null
            runtime.gesture.abort()
            hub.pause()
        }
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
