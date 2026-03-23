package com.yxhuang.flowforandroid.permission

import android.app.Activity
import android.app.Application
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

/**
 * 权限管理器 - 独立于特定 Activity，支持在流程中使用
 * 
 * 使用方式：
 * 1. 在 Application 中初始化：PermissionManager.init(application)
 * 2. 在每个 Activity 的 onCreate 中注册：PermissionManager.registerActivity(this)
 * 3. 在流程中申请权限：
 *    val result = PermissionManager.getInstance().requestNotificationPermission()
 *    when (result) {
 *        is PermissionResult.Granted -> { /* 继续流程 */ }
 *        is PermissionResult.Denied -> { /* 处理拒绝 */ }
 *        ...
 *    }
 */
class PermissionManager private constructor() {

    companion object {
        @Volatile
        private var instance: PermissionManager? = null

        fun getInstance(): PermissionManager {
            return instance ?: synchronized(this) {
                instance ?: PermissionManager().also { instance = it }
            }
        }

        /**
         * 初始化 PermissionManager
         * 必须在 Application.onCreate() 中调用
         */
        fun init(application: Application) {
            getInstance().initialize(application)
        }

        /**
         * 在 Activity.onCreate() 中注册
         * 必须在 super.onCreate() 之后调用
         */
        fun registerActivity(activity: ComponentActivity) {
            getInstance().registerActivityInternal(activity)
        }

        /**
         * 在 Activity.onDestroy() 中注销
         */
        fun unregisterActivity(activity: ComponentActivity) {
            getInstance().unregisterActivityInternal(activity)
        }
    }

    // 当前 Activity
    private var currentActivity: ComponentActivity? = null
    
    // 权限申请回调
    private var pendingCallback: ((PermissionResult) -> Unit)? = null
    private var permissionLauncher: ActivityResultLauncher<String>? = null

    // 权限状态 Flow（可选，用于观察权限变化）
    private val _permissionState = MutableStateFlow<Map<String, Boolean>>(emptyMap())
    val permissionState: StateFlow<Map<String, Boolean>> = _permissionState.asStateFlow()

    /**
     * 初始化 - 监听 Activity 生命周期
     */
    private fun initialize(application: Application) {
        application.registerActivityLifecycleCallbacks(object : Application.ActivityLifecycleCallbacks {
            override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) {}

            override fun onActivityStarted(activity: Activity) {}

            override fun onActivityResumed(activity: Activity) {
                if (activity is ComponentActivity && activity == currentActivity) {
                    // Activity 已在前台
                }
            }

            override fun onActivityPaused(activity: Activity) {}

            override fun onActivityStopped(activity: Activity) {}

            override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) {}

            override fun onActivityDestroyed(activity: Activity) {
                if (activity == currentActivity) {
                    permissionLauncher = null
                    currentActivity = null
                }
            }
        })
    }

    /**
     * 注册 Activity - 在 Activity.onCreate() 中调用
     */
    private fun registerActivityInternal(activity: ComponentActivity) {
        currentActivity = activity
        registerPermissionLauncher(activity)
    }

    /**
     * 注销 Activity
     */
    private fun unregisterActivityInternal(activity: ComponentActivity) {
        if (currentActivity == activity) {
            permissionLauncher = null
            currentActivity = null
        }
    }

    /**
     * 注册权限申请 Launcher
     * 必须在 Activity onCreate 中调用，在 STARTED 之前
     */
    private fun registerPermissionLauncher(activity: ComponentActivity) {
        // 先注销旧的 launcher
        permissionLauncher = null
        
        permissionLauncher = activity.registerForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { isGranted: Boolean ->
            val callback = pendingCallback
            pendingCallback = null
            
            if (isGranted) {
                callback?.invoke(PermissionResult.Granted)
            } else {
                // 检查是否是"不再询问"
                val shouldShow = if (pendingPermission != null) {
                    activity.shouldShowRequestPermissionRationale(pendingPermission!!)
                } else false
                
                callback?.invoke(
                    if (shouldShow) {
                        PermissionResult.Denied(shouldShowRationale = true)
                    } else {
                        PermissionResult.NeverAskAgain(pendingPermission ?: "")
                    }
                )
            }
        }
    }

    private var pendingPermission: String? = null

    /**
     * 检查权限是否已授予
     */
    fun checkPermission(permission: String): Boolean {
        val activity = currentActivity ?: return false
        return ContextCompat.checkSelfPermission(
            activity, permission
        ) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * 申请单个权限（回调方式）
     * 
     * @param permission 权限字符串，如 Manifest.permission.POST_NOTIFICATIONS
     * @param minApiLevel 最低 API 等级要求（如 Android 13+ 才需要申请通知权限）
     * @param callback 权限申请结果回调
     * 
     * @return Boolean 是否成功发起申请（false 表示无可用 Activity）
     */
    fun requestPermission(
        permission: String,
        minApiLevel: Int = 1,
        callback: (PermissionResult) -> Unit
    ): Boolean {
        // 检查 API 等级
        if (Build.VERSION.SDK_INT < minApiLevel) {
            callback(PermissionResult.NotRequired)
            return true
        }

        val activity = currentActivity
        
        if (activity == null) {
            callback(PermissionResult.NoActivityAvailable)
            return false
        }

        // 检查是否已有权限
        if (ContextCompat.checkSelfPermission(
                activity, permission
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            callback(PermissionResult.Granted)
            return true
        }

        // 申请权限
        pendingPermission = permission
        pendingCallback = callback
        
        try {
            permissionLauncher?.launch(permission)
        } catch (e: Exception) {
            pendingCallback = null
            callback(PermissionResult.Error(e))
            return false
        }
        
        return true
    }

    /**
     * 申请单个权限（挂起函数方式）
     * 适用于协程中的流程
     * 
     * @param permission 权限字符串
     * @param minApiLevel 最低 API 等级要求
     * @return PermissionResult 权限申请结果
     */
    suspend fun requestPermission(
        permission: String,
        minApiLevel: Int = 1
    ): PermissionResult = suspendCancellableCoroutine { continuation ->
        val started = requestPermission(permission, minApiLevel) { result ->
            continuation.resume(result)
        }
        
        if (!started) {
            continuation.resume(PermissionResult.NoActivityAvailable)
        }
    }

    /**
     * 申请多个权限（回调方式）
     * 
     * @param permissions 权限列表
     * @param callback 所有权限申请完成后的回调，返回 Map<权限, 是否已授予>
     */
    fun requestPermissions(
        permissions: List<String>,
        callback: (Map<String, Boolean>) -> Unit
    ) {
        val activity = currentActivity
        
        if (activity == null) {
            callback(permissions.associateWith { false })
            return
        }

        val result = mutableMapOf<String, Boolean>()
        val iterator = permissions.iterator()

        fun requestNext() {
            if (!iterator.hasNext()) {
                callback(result)
                return
            }

            val permission = iterator.next()
            requestPermission(permission) { permissionResult ->
                result[permission] = permissionResult is PermissionResult.Granted
                requestNext()
            }
        }

        requestNext()
    }

    /**
     * 申请多个权限（挂起函数方式）
     */
    suspend fun requestPermissions(
        permissions: List<String>
    ): Map<String, Boolean> = suspendCancellableCoroutine { continuation ->
        requestPermissions(permissions) { result ->
            continuation.resume(result)
        }
    }

    /**
     * 检查是否应该显示权限说明
     */
    fun shouldShowRequestPermissionRationale(permission: String): Boolean {
        val activity = currentActivity ?: return false
        return activity.shouldShowRequestPermissionRationale(permission)
    }

    /**
     * 获取当前 Activity（用于特殊情况下的手动处理）
     */
    fun getCurrentActivity(): ComponentActivity? = currentActivity
}

/**
 * 便捷的扩展函数 - 在流程中使用
 */
suspend fun PermissionManager.requestNotificationPermission(): PermissionResult {
    return requestPermission(
        android.Manifest.permission.POST_NOTIFICATIONS,
        minApiLevel = Build.VERSION_CODES.TIRAMISU // Android 13
    )
}
