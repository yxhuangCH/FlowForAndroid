package com.example.android

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch

/**
 * 正确的协程启动方式 - 使用 ViewModel 的生命周期作用域
 * 
 * 错误示例：GlobalScope.launch
 * 正确示例：viewModelScope.launch
 * 
 * 原因：GlobalScope 与组件的生命周期无关，可能导致内存泄漏。
 *      viewModelScope 与 ViewModel 绑定，ViewModel 销毁时自动取消协程。
 */
class CorrectViewModel : ViewModel() {
    
    fun fetchData() {
        // ✅ 正确：使用 viewModelScope 启动协程
        viewModelScope.launch {
            // 执行耗时操作
            val data = repository.fetchData()
            // 更新 UI
            _uiState.value = data
        }
    }
    
    // 对于非 ViewModel 类，可以使用 lifecycleScope
    class MyFragment : Fragment() {
        override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
            super.onViewCreated(view, savedInstanceState)
            
            // ✅ 正确：使用 lifecycleScope 启动协程
            lifecycleScope.launch {
                // 执行与 Fragment 生命周期绑定的操作
            }
        }
    }
    
    // 对于自定义作用域，可以使用 CoroutineScope 并配合 SupervisorJob
    class MyCustomComponent {
        private val customScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
        
        fun doWork() {
            // ✅ 正确：使用自定义作用域
            customScope.launch {
                // 执行操作
            }
        }
        
        fun cleanup() {
            // 手动取消作用域以释放资源
            customScope.cancel()
        }
    }
}

/**
 * 避免使用 GlobalScope 的原因：
 * 1. 内存泄漏：GlobalScope 启动的协程永远不会自动取消
 * 2. 生命周期不匹配：与 Android 组件的生命周期无关
 * 3. 难以测试：无法控制协程的执行和取消
 * 4. 结构化并发：破坏了结构化并发原则
 */