package com.example.android

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/**
 * 协程应该使用生命周期作用域启动 - 正确的协程作用域管理
 * 
 * 错误示例：launch { } 或 CoroutineScope(Job()).launch { }
 * 正确示例：viewModelScope.launch 或 lifecycleScope.launch
 * 
 * 原因：未绑定生命周期的协程可能导致内存泄漏、难以管理。
 */
class CorrectViewModel : ViewModel() {
    
    // ❌ 错误：未指定作用域的 launch
    // fun wrongMethod() {
    //     launch {  // 缺少作用域
    //         // 执行操作
    //     }
    // }
    
    // ❌ 错误：使用全局作用域
    // fun wrongMethod2() {
    //     CoroutineScope(Job()).launch {
    //         // 执行操作
    //     }
    // }
    
    // ✅ 正确：使用 viewModelScope
    fun correctMethod() {
        viewModelScope.launch {
            // 执行操作 - 协程与 ViewModel 生命周期绑定
            val data = repository.fetchData()
            _uiState.value = data
        }
    }
    
    // ✅ 正确：使用带调度器的 viewModelScope
    fun fetchDataWithDispatcher() {
        viewModelScope.launch(Dispatchers.IO) {
            // 在 IO 线程执行
            val data = repository.getData()
            
            // 切换回主线程更新 UI
            withContext(Dispatchers.Main) {
                _uiState.value = data
            }
        }
    }
}

/**
 * Fragment/Activity 中的正确用法
 */
class MyFragment : Fragment() {
    
    private lateinit var viewModel: MyViewModel
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // ✅ 正确：使用 lifecycleScope
        lifecycleScope.launch {
            // 与 Fragment 生命周期绑定
            viewModel.data.collect { data ->
                updateUI(data)
            }
        }
        
        // ✅ 正确：使用 repeatOnLifecycle（推荐用于 UI 层）
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.data.collect { data ->
                    updateUI(data)
                }
            }
        }
        
        // ✅ 正确：使用 viewLifecycleOwner（Fragment 中）
        viewLifecycleOwner.lifecycleScope.launch {
            // 与 Fragment 的 View 生命周期绑定
        }
    }
}

/**
 * 自定义组件的正确作用域管理
 */
class MyCustomComponent {
    
    // ✅ 正确：使用 SupervisorJob 避免一个协程失败影响其他
    private val customScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    
    fun performOperation() {
        customScope.launch {
            // 执行操作
            try {
                val result = api.call()
                onSuccess(result)
            } catch (e: Exception) {
                onError(e)
            }
        }
    }
    
    fun cleanup() {
        // 在组件销毁时取消作用域
        customScope.cancel()
    }
    
    // ✅ 正确：使用 MainScope（适用于非 Android 组件）
    class MyNonAndroidComponent {
        private val mainScope = MainScope()
        
        fun doWork() {
            mainScope.launch {
                // 执行操作
            }
        }
        
        fun destroy() {
            mainScope.cancel()
        }
    }
}

/**
 * 使用结构化并发的正确模式
 */
class StructuredConcurrencyExample {
    
    fun performSequentialOperations() {
        viewModelScope.launch {
            // 顺序执行 - 结构化并发
            val user = async { repository.getUser() }
            val posts = async { repository.getUserPosts() }
            
            val result = combineResults(user.await(), posts.await())
            _uiState.value = result
        }
    }
    
    fun performParallelOperations() {
        viewModelScope.launch {
            // 并行执行，但有超时控制
            val result = withTimeoutOrNull(5000) {
                val userDeferred = async { repository.getUser() }
                val postsDeferred = async { repository.getUserPosts() }
                
                Pair(userDeferred.await(), postsDeferred.await())
            }
            
            result?.let { (user, posts) ->
                _uiState.value = CombinedData(user, posts)
            } ?: run {
                _uiState.value = ErrorState("Timeout")
            }
        }
    }
}

/**
 * 测试中的正确作用域使用
 */
@ExperimentalCoroutinesApi
class ViewModelTest {
    
    @Test
    fun testViewModelCoroutine() = runTest {
        val viewModel = MyViewModel()
        
        // 使用 TestScope 测试协程
        val testScope = TestScope()
        
        testScope.launch {
            viewModel.fetchData()
        }
        
        // 验证协程执行
        testScope.advanceUntilIdle()
        
        assertEquals(expectedData, viewModel.uiState.value)
    }
}

/**
 * 使用 CoroutineScope 接口进行依赖注入
 */
interface CoroutineScopeProvider {
    val ioScope: CoroutineScope
    val mainScope: CoroutineScope
    val defaultScope: CoroutineScope
}

class AndroidCoroutineScopeProvider : CoroutineScopeProvider {
    override val ioScope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    override val mainScope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    override val defaultScope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    
    fun cleanup() {
        ioScope.cancel()
        mainScope.cancel()
        defaultScope.cancel()
    }
}

/**
 * 在非 Android 组件中使用
 */
class DataProcessor(private val scopeProvider: CoroutineScopeProvider) {
    
    fun processData(input: Data): Flow<Result> = flow {
        // 在 IO 作用域中处理
        scopeProvider.ioScope.launch {
            val processed = heavyProcessing(input)
            emit(processed)
        }
    }
    
    private suspend fun heavyProcessing(input: Data): Result {
        return withContext(Dispatchers.Default) {
            // CPU 密集型操作
            process(input)
        }
    }
}