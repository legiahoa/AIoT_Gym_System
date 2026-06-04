package com.example.stream_main_applatest

import android.annotation.SuppressLint
import android.os.Bundle
import android.util.Log
import android.view.View
import android.webkit.WebView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import com.google.firebase.firestore.FirebaseFirestore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken
import org.eclipse.paho.client.mqttv3.MqttCallback
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttMessage
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import com.google.firebase.FirebaseApp

class MainActivity : AppCompatActivity() {

    // Firebase & Auth
    private lateinit var auth: FirebaseAuth
    private lateinit var db: FirebaseFirestore
    private lateinit var googleSignInClient: GoogleSignInClient

    // MQTT
    private var mqttClient: MqttClient? = null
    //IP CỦA MÁY TÍNH CHẠY PYTHON (Mạng nội bộ)
    private val PYTHON_STREAM_URL = "http://172.29.192.1:5000/video_feed"
    private val MQTT_BROKER = "tcp://broker.emqx.io:1883"
    private val TOPIC_COMMAND = "fitness/app/command"
    private val TOPIC_RESULT = "fitness/iot/result"

    // UI & State
    private var userId: String? = null
    private var mistakesCount = 0
    private lateinit var webViewStream: WebView
    private lateinit var tvWarning: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Adjust for EdgeToEdge
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        // THÊM DÒNG NÀY ĐỂ KHỞI ĐỘNG FIREBASE
        FirebaseApp.initializeApp(this)

        // Các dòng code cũ giữ nguyên
        auth = FirebaseAuth.getInstance()
        db = FirebaseFirestore.getInstance()

        setupUI()
        setupGoogleSignIn()
        setupMqtt()

        auth = FirebaseAuth.getInstance()
        db = FirebaseFirestore.getInstance()

        setupUI()
        setupGoogleSignIn()
        setupMqtt()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupUI() {
        webViewStream = findViewById(R.id.webViewStream)
        tvWarning = findViewById(R.id.tvWarning)
        val spinnerExercise = findViewById<Spinner>(R.id.spinnerExercise)
        val btnStart = findViewById<Button>(R.id.btnStart)
        val btnStop = findViewById<Button>(R.id.btnStop)
        val btnLoginGoogle = findViewById<Button>(R.id.btnLoginGoogle)

        // Spinner setup
        val exercises = arrayOf("Squat", "Push-up", "Plank")
        spinnerExercise.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, exercises)

        // WebView setup (Tối ưu cho MJPEG stream)
        webViewStream.settings.javaScriptEnabled = true
        webViewStream.settings.loadWithOverviewMode = true
        webViewStream.settings.useWideViewPort = true

        btnLoginGoogle.setOnClickListener { signInWithGoogle() }

        btnStart.setOnClickListener {
            if (userId == null) {
                Toast.makeText(this, "Vui lòng đăng nhập trước!", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            mistakesCount = 0
            // Nạp URL stream (Sẽ tự động lấy khung hình liên tục từ Python)
            webViewStream.loadUrl(PYTHON_STREAM_URL)
            publishMqtt(TOPIC_COMMAND, "START")
            Toast.makeText(this, "Đã gửi lệnh Bắt đầu", Toast.LENGTH_SHORT).show()
        }

        btnStop.setOnClickListener {
            publishMqtt(TOPIC_COMMAND, "STOP")
            webViewStream.loadUrl("about:blank") // Ngắt stream
            tvWarning.visibility = View.GONE
            Toast.makeText(this, "Đang đợi lưu video từ AIoT...", Toast.LENGTH_SHORT).show()
        }
    }

    // ==========================================
    // 1. GOOGLE SIGN-IN
    // ==========================================
    private fun setupGoogleSignIn() {
        val webClientId = "1059848506889-msn15g2rmkg3l0rli66od7j81gp46ea7.apps.googleusercontent.com"
        // ID token client ID (Mặc định trong google-services.json)
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(webClientId)
            .requestEmail()
            .build()
        googleSignInClient = GoogleSignIn.getClient(this, gso)
    }

    private val launcher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == RESULT_OK) {
            val task = GoogleSignIn.getSignedInAccountFromIntent(result.data)
            try {
                val account = task.getResult(ApiException::class.java)
                firebaseAuthWithGoogle(account.idToken!!)
            } catch (e: ApiException) {
                Toast.makeText(this, "Google Sign in failed", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun signInWithGoogle() {
        val signInIntent = googleSignInClient.signInIntent
        launcher.launch(signInIntent)
    }

    private fun firebaseAuthWithGoogle(idToken: String) {
        val credential = GoogleAuthProvider.getCredential(idToken, null)
        auth.signInWithCredential(credential)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    userId = user?.uid
                    findViewById<TextView>(R.id.tvUserInfo).text = "Xin chào: ${user?.displayName}"
                    Toast.makeText(this, "Đăng nhập thành công", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this, "Lỗi xác thực Firebase", Toast.LENGTH_SHORT).show()
                }
            }
    }

    // ==========================================
    // 2. MQTT CLIENT
    // ==========================================
    private fun setupMqtt() {
        try {
            val clientId = MqttClient.generateClientId()
            mqttClient = MqttClient(MQTT_BROKER, clientId, MemoryPersistence())
            val options = MqttConnectOptions()
            options.isCleanSession = true

            mqttClient?.setCallback(object : MqttCallback {
                override fun connectionLost(cause: Throwable?) {}
                override fun messageArrived(topic: String?, message: MqttMessage?) {
                    val payload = message?.payload?.let { String(it) } ?: return
                    runOnUiThread { handleMqttMessage(payload) }
                }
                override fun deliveryComplete(token: IMqttDeliveryToken?) {}
            })

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    mqttClient?.connect(options)
                    mqttClient?.subscribe(TOPIC_RESULT)
                } catch (e: Exception) {
                    Log.e("MQTT", "Connection error", e)
                }
            }
        } catch (e: Exception) { e.printStackTrace() }
    }

    private fun publishMqtt(topic: String, msg: String) {
        CoroutineScope(Dispatchers.IO).launch {
            if (mqttClient?.isConnected == true) {
                mqttClient?.publish(topic, MqttMessage(msg.toByteArray()))
            }
        }
    }

    private fun handleMqttMessage(payload: String) {
        if (payload.startsWith("WARNING")) {
            val warningMsg = payload.split("|").getOrNull(1) ?: "Sai tư thế!"
            mistakesCount++
            tvWarning.text = warningMsg
            tvWarning.visibility = View.VISIBLE
            // Tự tắt chữ sau 2 giây
            tvWarning.postDelayed({ tvWarning.visibility = View.GONE }, 2000)

        } else if (payload.startsWith("UPLOAD_SUCCESS")) {
            val videoUrl = payload.split("|").getOrNull(1) ?: return
            saveSessionToFirestore(videoUrl)
        }
    }

    // ==========================================
    // 3. FIRESTORE
    // ==========================================
    private fun saveSessionToFirestore(videoUrl: String) {
        if (userId == null) return
        val spinner = findViewById<Spinner>(R.id.spinnerExercise)

        val sessionData = hashMapOf(
            "userId" to userId,
            "exercise" to spinner.selectedItem.toString(),
            "timestamp" to System.currentTimeMillis(),
            "mistakes" to mistakesCount,
            "videoUrl" to videoUrl
        )

        db.collection("workout_sessions").add(sessionData)
            .addOnSuccessListener {
                Toast.makeText(this, "Đã lưu lịch sử tập vào Database!", Toast.LENGTH_LONG).show()
            }
            .addOnFailureListener {
                Toast.makeText(this, "Lỗi lưu DB", Toast.LENGTH_SHORT).show()
            }
    }
}