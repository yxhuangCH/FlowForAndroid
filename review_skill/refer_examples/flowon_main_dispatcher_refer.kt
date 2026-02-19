package com.example.android

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn

/**
 * flowOn 不应该使用 Dispatchers.Main - 正确的 Flow 线程调度
 * 
 * 错误示例：flow { ... }.flowOn(Dispatchers.Main)
 * 正确示例：flow { ... }.flowOn(Dispatchers.IO) 或使用适当的调度器
 * 
 * 原因：flowOn(Dispatchers.Main) 会使上游操作在主线程执行，可能导致界面卡顿。
 */
class CorrectFlowRepository {
    
    // ❌ 错误：使用 Dispatchers.Main 作为 flowOn 的调度器
    // fun getDataWrong(): Flow<Data> = flow {
    //     // 上游操作（可能是 IO）会在主线程执行
    //     val data = database.queryData() // IO 操作
    //     emit(data)
    // }.flowOn(Dispatchers.Main)
    
    // ✅ 正确：使用 Dispatchers.IO 执行 IO 操作
    fun getDataCorrect(): Flow<Data> = flow {
        // 上游操作在 IO 线程执行
        val data = database.queryData()
        emit(data)
    }.flowOn(Dispatchers.IO) // 在 IO 线程执行上游
    
    // ✅ 正确：复杂的多步骤处理
    fun getProcessedData(): Flow<Result> = flow {
        // 第一步：获取原始数据（在 IO 线程）
        val rawData = api.fetchData()
        
        // 第二步：处理数据（在 Default 线程）
        val processedData = processData(rawData)
        
        // 第三步：发射结果
        emit(processedData)
    }.flowOn(Dispatchers.IO) // 上游在 IO 线程
     .map { result ->
        // 中间操作可以使用不同的调度器
        transformResult(result)
    }.flowOn(Dispatchers.Default) // 中间操作在 Default 线程
    
    // ✅ 正确：使用 buffer 提高性能
    fun getBufferedData(): Flow<Data> = flow {
        for (i in 1..100) {
            emit(loadData(i))
        }
    }.flowOn(Dispatchers.IO)
     .buffer() // 添加缓冲区提高吞吐量
}

/**
 * ViewModel 中的正确用法
 */
class DataViewModel : ViewModel() {
    
    private val repository = DataRepository()
    
    val data: Flow<Data> = repository.getData()
        .flowOn(Dispatchers.IO) // Repository 可能已经设置了，这里再加一层保障
        .catch { e ->
            // 错误处理
            emit(Data.Error(e))
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = Data.Loading
        )
    
    // ✅ 正确：在 UI 层收集 Flow
    fun observeData() {
        viewModelScope.launch {
            repository.getData()
                .flowOn(Dispatchers.IO)
                .collect { data ->
                    // 在主线程更新 UI
                    _uiState.value = data
                }
        }
    }
}

/**
 * 使用 channelFlow 的正确方式
 */
class ChannelFlowExample {
    
    // ❌ 错误：channelFlow 中使用错误的调度器
    // fun getDataWrong(): Flow<Data> = channelFlow {
    //     // 可能执行 IO 操作
    //     val data = api.fetchData()
    //     send(data)
    // }.flowOn(Dispatchers.Main)
    
    // ✅ 正确：channelFlow 中使用适当的调度器
    fun getDataCorrect(): Flow<Data> = channelFlow {
        // 在 channelFlow 内部处理调度
        withContext(Dispatchers.IO) {
            val data = api.fetchData()
            send(data)
        }
    }.flowOn(Dispatchers.IO) // 额外的保障
    
    // ✅ 正确：使用 produceIn 和 receiveAsFlow
    fun getProducedData(): Flow<Data> = flow {
        // 使用 produceIn 在指定作用域生产数据
        val channel = produce<Data>(Dispatchers.IO) {
            for (i in 1..10) {
                send(loadData(i))
            }
        }
        
        // 将 channel 转换为 flow
        channel.receiveAsFlow().collect { data ->
            emit(data)
        }
    }
}

/**
 * 测试中的 Flow 线程调度
 */
@ExperimentalCoroutinesApi
class FlowTest {
    
    @Test
    fun testFlowOnDispatcher() = runTest {
        val testDispatcher = StandardTestDispatcher()
        
        val flow = flow {
            emit(1)
            emit(2)
            emit(3)
        }.flowOn(testDispatcher)
        
        // 验证在测试调度器上执行
        val values = mutableListOf<Int>()
        flow.collect { values.add(it) }
        
        assertEquals(listOf(1, 2, 3), values)
    }
    
    @Test
    fun testFlowOnMainDetection() = runTest {
        val repository = TestRepository()
        
        // 应该使用 Dispatchers.IO 而不是 Dispatchers.Main
        val flow = repository.getData()
            .flowOn(Dispatchers.IO) // ✅ 正确
        
        // 验证流程正常工作
        val result = flow.first()
        assertNotNull(result)
    }
}

/**
 * 使用自定义调度器
 */
class CustomDispatcherExample {
    
    // 自定义调度器用于特定类型的操作
    private val databaseDispatcher = Dispatchers.IO.limitedParallelism(4)
    private val networkDispatcher = Dispatchers.IO.limitedParallelism(2)
    
    fun getCombinedData(): Flow<CombinedResult> = flow {
        // 并行获取数据，使用不同的调度器
        val userDeferred = async(networkDispatcher) { api.getUser() }
        val settingsDeferred = async(databaseDispatcher) { database.getSettings() }
        
        val user = userDeferred.await()
        val settings = settingsDeferred.await()
        
        emit(CombinedResult(user, settings))
    }.flowOn(Dispatchers.Default) // 合并操作在 Default 线程
}

/**
 * 避免常见的 Flow 线程错误
 */
class FlowBestPractices {
    
    // ❌ 错误：在 flow 构建器中切换线程
    // fun getDataWrong(): Flow<Data> = flow {
    //     withContext(Dispatchers.IO) {  // 不要在 flow 构建器内部切换
    //         val data = loadData()
    //         emit(data)  // 错误：在 withContext 中 emit
    //     }
    // }
    
    // ✅ 正确：使用 flowOn 而不是 withContext
    fun getDataCorrect(): Flow<Data> = flow {
        val data = loadData() // 这个调用会被 flowOn 调度
        emit(data)
    }.flowOn(Dispatchers.IO)
    
    // ✅ 正确：使用 callbackFlow 处理回调 API
    fun getCallbackData(): Flow<Data> = callbackFlow {
        val callback = object : DataCallback {
            override fun onData(data: Data) {
                trySend(data)
            }
            
            override fun onComplete() {
                close()
            }
            
            override fun onError(error: Throwable) {
                close(error)
            }
        }
        
        api.registerCallback(callback)
        
        awaitClose {
            api.unregisterCallback(callback)
        }
    }.flowOn(Dispatchers.IO)
}

/**
 * 使用 StateFlow/SharedFlow 的线程安全
 */
class StateFlowExample {
    
    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()
    
    fun updateData() {
        viewModelScope.launch(Dispatchers.IO) {
            val data = repository.getData()
            
            // 切换到主线程更新 StateFlow
            withContext(Dispatchers.Main) {
                _uiState.value = UiState.Success(data)
            }
        }
    }
    
    // ✅ 正确：使用 update 函数原子更新
    fun updateStateSafely() {
        viewModelScope.launch(Dispatchers.IO) {
            val newData = repository.fetchData()
            
            _uiState.update { currentState ->
                currentState.copy(data = newData)
            }
        }
    }
}