package com.yxhuang.flowforandroid.permission

/**
 * 权限申请结果
 */
sealed class PermissionResult {
    /**
     * 权限已授予
     */
    data object Granted : PermissionResult()

    /**
     * 权限被拒绝
     * @param shouldShowRationale 是否应该显示权限说明
     */
    data class Denied(
        val shouldShowRationale: Boolean = false
    ) : PermissionResult()

    /**
     * 无可用 Activity（应用在后台或未初始化）
     */
    data object NoActivityAvailable : PermissionResult()

    /**
     * 权限申请过程中发生错误
     */
    data class Error(
        val exception: Throwable
    ) : PermissionResult()

    /**
     * 用户选择了"不再询问"
     */
    data class NeverAskAgain(
        val permission: String
    ) : PermissionResult()

    /**
     * 不需要申请（Android 版本低于要求）
     */
    data object NotRequired : PermissionResult()
}
