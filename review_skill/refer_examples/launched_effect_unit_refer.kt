package com.example.android

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.SideEffect

/**
 * LaunchedEffect 应该使用合适的 key - 避免使用 Unit 作为 key
 * 
 * 错误示例：LaunchedEffect(Unit) { ... }
 * 正确示例：LaunchedEffect(key1, key2) { ... } 或使用合适的依赖
 * 
 * 原因：LaunchedEffect(Unit) 只在初始组合时运行一次，可能不会在依赖变化时重新执行。
 */
@Composable
fun CorrectScreen(viewModel: MyViewModel) {
    
    val uiState by viewModel.uiState.collectAsState()
    
    // ❌ 错误：使用 Unit 作为 key
    // LaunchedEffect(Unit) {
    //     viewModel.loadData() // 只在初始组合时执行一次
    // }
    
    // ✅ 正确：使用合适的 key（例如 viewModel）
    LaunchedEffect(viewModel) {
        // 当 viewModel 变化时重新执行
        viewModel.loadData()
    }
    
    // ✅ 正确：使用状态作为 key
    val shouldLoadData by remember { derivedStateOf { uiState.shouldRefresh } }
    
    LaunchedEffect(shouldLoadData) {
        if (shouldLoadData) {
            viewModel.refreshData()
        }
    }
    
    // ✅ 正确：使用多个 key
    val userId = uiState.userId
    val forceRefresh = uiState.forceRefresh
    
    LaunchedEffect(userId, forceRefresh) {
        viewModel.loadUserData(userId, forceRefresh)
    }
    
    // ✅ 正确：使用 rememberUpdatedState 处理长时间运行的操作
    val currentOnSuccess by rememberUpdatedState(viewModel::onSuccess)
    
    LaunchedEffect(Unit) {
        // 如果确实只需要执行一次，但需要访问最新值
        val result = longRunningOperation()
        currentOnSuccess(result)
    }
}

/**
 * 使用 SideEffect 替代 LaunchedEffect(Unit)
 */
@Composable
fun SideEffectExample(viewModel: MyViewModel) {
    
    // ❌ 错误：使用 LaunchedEffect(Unit) 执行副作用
    // LaunchedEffect(Unit) {
    //     viewModel.trackScreenView()
    // }
    
    // ✅ 正确：使用 SideEffect 执行不依赖于状态的副作用
    SideEffect {
        viewModel.trackScreenView()
    }
    
    // ✅ 正确：使用 DisposableEffect 处理资源清理
    DisposableEffect(Unit) {
        val listener = EventListener()
        viewModel.addListener(listener)
        
        onDispose {
            viewModel.removeListener(listener)
        }
    }
}

/**
 * 使用 derivedStateOf 创建派生状态
 */
@Composable
fun DerivedStateExample(items: List<Item>, filter: String) {
    
    // ✅ 正确：使用派生状态避免不必要的重组
    val filteredItems by remember(items, filter) {
        derivedStateOf {
            items.filter { it.matches(filter) }
        }
    }
    
    LaunchedEffect(filteredItems) {
        // 当过滤结果变化时执行
        analytics.trackFilteredCount(filteredItems.size)
    }
}

/**
 * 使用 produceState 管理异步状态
 */
@Composable
fun ProduceStateExample(userId: String) {
    
    // ✅ 正确：使用 produceState 管理异步状态
    val userState by produceState<UserState>(initialValue = UserState.Loading, userId) {
        // 当 userId 变化时重新执行
        value = UserState.Loading
        
        try {
            val user = userRepository.getUser(userId)
            value = UserState.Success(user)
        } catch (e: Exception) {
            value = UserState.Error(e)
        }
    }
    
    // 基于 userState 显示 UI
    when (userState) {
        is UserState.Loading -> LoadingScreen()
        is UserState.Success -> UserScreen((userState as UserState.Success).user)
        is UserState.Error -> ErrorScreen()
    }
}

/**
 * 使用 snapshotFlow 将 Compose 状态转换为 Flow
 */
@Composable
fun SnapshotFlowExample(viewModel: MyViewModel) {
    
    var searchQuery by remember { mutableStateOf("") }
    
    // ✅ 正确：使用 snapshotFlow 观察 Compose 状态变化
    LaunchedEffect(searchQuery) {
        snapshotFlow { searchQuery }
            .debounce(300)
            .distinctUntilChanged()
            .collect { query ->
                viewModel.search(query)
            }
    }
    
    // UI 代码
    TextField(
        value = searchQuery,
        onValueChange = { searchQuery = it }
    )
}

/**
 * 避免在 LaunchedEffect 中直接修改状态
 */
@Composable
fun AvoidStateModificationInEffect() {
    
    var counter by remember { mutableStateOf(0) }
    
    // ❌ 错误：在 LaunchedEffect 中直接修改状态可能导致无限循环
    // LaunchedEffect(Unit) {
    //     while (true) {
    //         delay(1000)
    //         counter++  // 修改状态会触发重组，重组会重启 LaunchedEffect
    //     }
    // }
    
    // ✅ 正确：使用其他方式管理状态
    val elapsedTime by produceState(initialValue = 0) {
        while (true) {
            delay(1000)
            value++
        }
    }
}

/**
 * 测试 Compose 效果
 */
@Composable
@TestOnly
fun TestableComposable(viewModel: MyViewModel = fakeViewModel()) {
    
    var data by remember { mutableStateOf<String?>(null) }
    
    LaunchedEffect(viewModel) {
        viewModel.data.collect { newData ->
            data = newData
        }
    }
    
    // 可测试的 UI
    if (data != null) {
        Text(text = "Data: $data")
    }
}

/**
 * 使用 rememberCoroutineScope 管理协程
 */
@Composable
fun RememberCoroutineScopeExample() {
    
    // ✅ 正确：使用 rememberCoroutineScope 获取与组合生命周期绑定的作用域
    val scope = rememberCoroutineScope()
    
    var isLoading by remember { mutableStateOf(false) }
    
    Button(
        onClick = {
            isLoading = true
            scope.launch {
                try {
                    val result = api.call()
                    // 处理结果
                } finally {
                    isLoading = false
                }
            }
        }
    ) {
        if (isLoading) CircularProgressIndicator() else Text("Load Data")
    }
}