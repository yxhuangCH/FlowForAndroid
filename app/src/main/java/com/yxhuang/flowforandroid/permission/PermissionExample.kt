package com.yxhuang.flowforandroid.permission

import android.Manifest
import android.util.Log
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

/**
 * 权限申请流程示例
 * 展示如何在业务流程中使用 PermissionManager
 */
object PermissionExample {

    private const val TAG = "PermissionExample"

    /**
     * 示例 1：在 ViewModel 或 Repository 中申请权限（协程方式）
     * 适用于需要等待权限结果的流程
     */
    suspend fun executeFlowWithPermission(): Flow<FlowStep> = flow {
        emit(FlowStep.Started)
        
        // 步骤 1：初始化
        emit(FlowStep.Initializing)
        // 执行初始化操作...
        
        // 步骤 2：申请通知权限
        emit(FlowStep.RequestingPermission)
        val permissionManager = PermissionManager.getInstance()
        val result = permissionManager.requestNotificationPermission()
        
        when (result) {
            is PermissionResult.Granted -> {
                Log.d(TAG, "通知权限已授权，继续流程")
                emit(FlowStep.PermissionGranted)
                
                // 步骤 3：执行需要通知权限的操作
                emit(FlowStep.ExecutingTask)
                // 发送通知、执行后台任务等...
                
                emit(FlowStep.Completed)
            }
            is PermissionResult.Denied -> {
                Log.d(TAG, "通知权限被拒绝，但用户可能再次申请")
                emit(FlowStep.PermissionDenied(result.shouldShowRationale))
                // 可以选择重试或跳过
                emit(FlowStep.Completed)
            }
            is PermissionResult.NeverAskAgain -> {
                Log.d(TAG, "用户选择了不再询问，需要引导去设置")
                emit(FlowStep.PermissionNeverAskAgain(result.permission))
                // 引导用户去设置页面
                emit(FlowStep.Completed)
            }
            is PermissionResult.NoActivityAvailable -> {
                Log.w(TAG, "无可用 Activity，稍后再试")
                emit(FlowStep.Error("应用不在前台，无法申请权限"))
            }
            is PermissionResult.NotRequired -> {
                // Android 13 以下不需要申请，直接继续
                emit(FlowStep.PermissionGranted)
                emit(FlowStep.ExecutingTask)
                emit(FlowStep.Completed)
            }
            is PermissionResult.Error -> {
                Log.e(TAG, "申请权限时发生错误", result.exception)
                emit(FlowStep.Error(result.exception.message ?: "未知错误"))
            }
        }
    }

    /**
     * 示例 2：在 Service 或 Worker 中申请权限（回调方式）
     * 适用于不依赖协程的场景
     */
    fun requestPermissionWithCallback(
        onGranted: () -> Unit,
        onDenied: (shouldShowRationale: Boolean) -> Unit,
        onNeverAskAgain: () -> Unit,
        onError: (String) -> Unit
    ) {
        val permissionManager = PermissionManager.getInstance()
        
        permissionManager.requestPermission(
            permission = Manifest.permission.POST_NOTIFICATIONS,
            minApiLevel = android.os.Build.VERSION_CODES.TIRAMISU
        ) { result ->
            when (result) {
                is PermissionResult.Granted -> onGranted()
                is PermissionResult.Denied -> onDenied(result.shouldShowRationale)
                is PermissionResult.NeverAskAgain -> onNeverAskAgain()
                is PermissionResult.NoActivityAvailable -> 
                    onError("应用不在前台，无法申请权限")
                is PermissionResult.NotRequired -> onGranted()
                is PermissionResult.Error -> onError(result.exception.message ?: "未知错误")
            }
        }
    }

    /**
     * 示例 3：申请多个权限
     */
    suspend fun requestMultiplePermissions(): Map<String, Boolean> {
        val permissionManager = PermissionManager.getInstance()
        
        val permissions = listOf(
            Manifest.permission.POST_NOTIFICATIONS,
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO
        )
        
        return permissionManager.requestPermissions(permissions)
    }

    /**
     * 示例 4：链式权限申请
     * 按顺序申请多个权限，每个权限可以有不同的处理逻辑
     */
    suspend fun chainPermissionRequest() {
        val permissionManager = PermissionManager.getInstance()
        
        // 申请第一个权限
        val notificationResult = permissionManager.requestNotificationPermission()
        
        if (notificationResult is PermissionResult.Granted || 
            notificationResult is PermissionResult.NotRequired) {
            
            // 通知权限通过，继续申请相机权限
            val cameraResult = permissionManager.requestPermission(
                Manifest.permission.CAMERA
            )
            
            when (cameraResult) {
                is PermissionResult.Granted -> {
                    // 相机权限也通过了，继续流程
                }
                else -> {
                    // 处理相机权限被拒绝的情况
                }
            }
        }
    }

    /**
     * 流程步骤状态
     */
    sealed class FlowStep {
        data object Started : FlowStep()
        data object Initializing : FlowStep()
        data object RequestingPermission : FlowStep()
        data object PermissionGranted : FlowStep()
        data class PermissionDenied(val shouldShowRationale: Boolean) : FlowStep()
        data class PermissionNeverAskAgain(val permission: String) : FlowStep()
        data object ExecutingTask : FlowStep()
        data class Error(val message: String) : FlowStep()
        data object Completed : FlowStep()
    }
}
