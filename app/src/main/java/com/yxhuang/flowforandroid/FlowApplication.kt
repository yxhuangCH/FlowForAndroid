package com.yxhuang.flowforandroid

import android.app.Application
import com.yxhuang.flowforandroid.permission.PermissionManager

/**
 * Application 类
 * 用于初始化 PermissionManager 等全局组件
 */
class FlowApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        
        // 初始化 PermissionManager
        PermissionManager.init(this)
    }
}
