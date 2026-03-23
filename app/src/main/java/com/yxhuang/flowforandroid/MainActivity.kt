package com.yxhuang.flowforandroid

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.yxhuang.flowforandroid.permission.PermissionManager
import com.yxhuang.flowforandroid.permission.PermissionResult
import com.yxhuang.flowforandroid.permission.requestNotificationPermission
import com.yxhuang.flowforandroid.ui.theme.FlowForAndroidTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // 注册 PermissionManager（必须在 super.onCreate 之后，setContent 之前）
        PermissionManager.registerActivity(this)
        
        enableEdgeToEdge()

        setContent {
            FlowForAndroidTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    PermissionDemoScreen(
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        PermissionManager.unregisterActivity(this)
    }
}

@Composable
fun PermissionDemoScreen(modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    val permissionManager = PermissionManager.getInstance()

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text(text = "PermissionManager 示例")

        Spacer(modifier = Modifier.height(16.dp))

        // 示例 1：使用协程申请权限
        Button(
            onClick = {
                scope.launch {
                    val result = permissionManager.requestNotificationPermission()
                    val message = when (result) {
                        is PermissionResult.Granted -> "通知权限已授权"
                        is PermissionResult.Denied -> "通知权限被拒绝"
                        is PermissionResult.NeverAskAgain -> "用户选择了不再询问"
                        is PermissionResult.NoActivityAvailable -> "无可用 Activity"
                        is PermissionResult.NotRequired -> "不需要申请（Android 13 以下）"
                        is PermissionResult.Error -> "错误: ${result.exception.message}"
                    }
                    // 注意：实际应用中应该使用 Snackbar 或 Toast
                    println(message)
                }
            }
        ) {
            Text("申请通知权限（协程方式）")
        }

        Spacer(modifier = Modifier.height(8.dp))

        // 示例 2：使用回调申请权限
        Button(
            onClick = {
                permissionManager.requestPermission(
                    permission = android.Manifest.permission.POST_NOTIFICATIONS,
                    minApiLevel = android.os.Build.VERSION_CODES.TIRAMISU
                ) { result ->
                    val message = when (result) {
                        is PermissionResult.Granted -> "通知权限已授权"
                        is PermissionResult.Denied -> "通知权限被拒绝"
                        is PermissionResult.NeverAskAgain -> "用户选择了不再询问"
                        is PermissionResult.NoActivityAvailable -> "无可用 Activity"
                        is PermissionResult.NotRequired -> "不需要申请"
                        is PermissionResult.Error -> "错误: ${result.exception.message}"
                    }
                    println(message)
                }
            }
        ) {
            Text("申请通知权限（回调方式）")
        }

        Spacer(modifier = Modifier.height(8.dp))

        // 示例 3：检查权限状态
        Button(
            onClick = {
                val hasPermission = permissionManager.checkPermission(
                    android.Manifest.permission.POST_NOTIFICATIONS
                )
                println("通知权限状态: $hasPermission")
            }
        ) {
            Text("检查权限状态")
        }
    }
}

@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
    Text(
        text = "Hello $name!",
        modifier = modifier
    )
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    FlowForAndroidTheme {
        Greeting("Android")
    }
}
