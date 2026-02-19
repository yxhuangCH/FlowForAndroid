package com.example.android

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import android.content.Context

/**
 * remember 不应该持有 Context - 正确的 Compose 状态管理
 * 
 * 错误示例：remember { context } 或 remember { SomeClass(context) }
 * 正确示例：使用 lambda 参数、ViewModel 或状态提升
 * 
 * 原因：remember 缓存的值在重组时不会重新计算，持有 Context 可能导致内存泄漏或访问无效 Context。
 */
@Composable
fun CorrectScreen(context: Context) {
    
    // ❌ 错误：remember 持有 Context
    // val rememberedContext = remember { context }
    // val someObject = remember { SomeClass(context) }
    
    // ✅ 正确：使用 lambda 参数，在需要时获取最新值
    val stringResource = remember(context) {
        // 当 context 变化时重新计算
        context.getString(R.string.app_name)
    }
    
    // ✅ 正确：使用 derivedStateOf 派生状态
    val formattedText = remember(context) {
        derivedStateOf {
            // 基于 context 计算派生状态
            context.getString(R.string.app_name).uppercase()
        }
    }
    
    // ✅ 正确：使用 ViewModel 管理状态
    val viewModel: MyViewModel = viewModel()
    
    // UI 使用 ViewModel 提供的状态
    val uiState by viewModel.uiState.collectAsState()
    
    Text(text = uiState.appName)
}

/**
 * 状态提升 - 将 Context 依赖移到 Composable 外部
 */
@Composable
fun StateHoistingExample() {
    
    var text by remember { mutableStateOf("") }
    
    // ❌ 错误：在内部处理 Context
    // fun InnerComposable(context: Context) {
    //     val appName = remember { context.getString(R.string.app_name) }
    //     Text(text = appName)
    // }
    
    // ✅ 正确：状态提升，将数据作为参数传递
    InnerComposable(
        appName = stringResource(R.string.app_name),
        onTextChange = { text = it }
    )
}

@Composable
fun InnerComposable(
    appName: String,  // 数据作为参数
    onTextChange: (String) -> Unit
) {
    Column {
        Text(text = appName)
        TextField(
            value = "",
            onValueChange = onTextChange
        )
    }
}

/**
 * 使用 ViewModel 管理 Context 相关逻辑
 */
class MyViewModel @Inject constructor(
    private val resourceProvider: ResourceProvider
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(MyUiState())
    val uiState: StateFlow<MyUiState> = _uiState.asStateFlow()
    
    fun loadAppInfo() {
        viewModelScope.launch {
            val appName = resourceProvider.getAppName()
            _uiState.update { it.copy(appName = appName) }
        }
    }
}

/**
 * ResourceProvider 接口抽象资源访问
 */
interface ResourceProvider {
    fun getAppName(): String
    fun getString(@StringRes resId: Int): String
    fun getColor(@ColorRes resId: Int): Int
}

class AndroidResourceProvider @Inject constructor(
    @ApplicationContext private val context: Context
) : ResourceProvider {
    
    override fun getAppName(): String {
        return context.getString(R.string.app_name)
    }
    
    override fun getString(@StringRes resId: Int): String {
        return context.getString(resId)
    }
    
    override fun getColor(@ColorRes resId: Int): Int {
        return ContextCompat.getColor(context, resId)
    }
}

/**
 * 使用 LocalContext 的正确方式
 */
@Composable
fun LocalContextExample() {
    
    val context = LocalContext.current
    
    // ❌ 错误：remember 持有 LocalContext.current
    // val rememberedContext = remember { LocalContext.current }
    
    // ✅ 正确：在需要时直接使用，或使用 remember(key) 模式
    val stringResource = remember(context) {
        context.getString(R.string.app_name)
    }
    
    // ✅ 正确：使用 LaunchedEffect 执行 Context 相关操作
    LaunchedEffect(Unit) {
        // 如果需要执行一次性的 Context 操作
        val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
        analytics.trackAppVersion(packageInfo.versionName)
    }
    
    Text(text = stringResource)
}

/**
 * 处理 Configuration 变化
 */
@Composable
fun ConfigurationAwareExample() {
    
    val configuration = LocalConfiguration.current
    val context = LocalContext.current
    
    // ✅ 正确：根据 configuration 变化重新计算
    val orientationText = remember(configuration.orientation) {
        when (configuration.orientation) {
            Configuration.ORIENTATION_LANDSCAPE -> "横屏"
            Configuration.ORIENTATION_PORTRAIT -> "竖屏"
            else -> "未知方向"
        }
    }
    
    // ✅ 正确：使用 Resources 获取本地化字符串
    val resources = LocalContext.current.resources
    val localizedText = remember(resources.configuration.locale) {
        resources.getString(R.string.localized_text)
    }
    
    Column {
        Text(text = "方向: $orientationText")
        Text(text = localizedText)
    }
}

/**
 * 使用 CompositionLocal 提供依赖
 */
@Composable
fun CompositionLocalExample() {
    
    // 定义 CompositionLocal
    val LocalResourceProvider = staticCompositionLocalOf<ResourceProvider> {
        error("ResourceProvider not provided")
    }
    
    // 在根 Composable 提供依赖
    CompositionLocalProvider(
        LocalResourceProvider provides AndroidResourceProvider(LocalContext.current)
    ) {
        AppContent()
    }
}

@Composable
fun AppContent() {
    // 在任意层级获取依赖
    val resourceProvider = LocalResourceProvider.current
    
    val appName = remember(resourceProvider) {
        resourceProvider.getAppName()
    }
    
    Text(text = appName)
}

/**
 * 测试 Compose 中 Context 的使用
 */
@Composable
@TestOnly
fun TestableComposable(
    resourceProvider: ResourceProvider = FakeResourceProvider()
) {
    
    val appName = remember(resourceProvider) {
        resourceProvider.getAppName()
    }
    
    Text(text = appName)
}

class FakeResourceProvider : ResourceProvider {
    override fun getAppName(): String = "Test App"
    override fun getString(resId: Int): String = "Test String"
    override fun getColor(resId: Int): Int = Color.RED
}

/**
 * 使用 rememberSaveable 保存状态
 */
@Composable
fun RememberSaveableExample() {
    
    // ❌ 错误：尝试保存 Context
    // var contextState by rememberSaveable { mutableStateOf<Context?>(null) }
    
    // ✅ 正确：保存需要的数据，而不是 Context
    var username by rememberSaveable { mutableStateOf("") }
    var preferences by rememberSaveable(saver = mapSaver(
        save = { mapOf("theme" to it.theme, "language" to it.language) },
        restore = { UserPreferences(it["theme"] as String, it["language"] as String) }
    )) { mutableStateOf(UserPreferences()) }
    
    // 使用 ViewModel 管理持久化数据
    val viewModel: UserViewModel = viewModel()
    val userState by viewModel.userState.collectAsState()
}