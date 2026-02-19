package com.example.android

import androidx.lifecycle.ViewModel
import android.content.Context

/**
 * ViewModel 不应该持有 Android Context - 正确的依赖注入方式
 * 
 * 错误示例：class MyViewModel(private val context: Context)
 * 正确示例：使用依赖注入提供所需资源
 * 
 * 原因：ViewModel 的生命周期可能比 Activity/Fragment 长，
 *      持有 Context 可能导致内存泄漏或访问无效的 Context。
 */
class CorrectViewModel : ViewModel() {
    
    // ❌ 错误：ViewModel 持有 Context
    // class WrongViewModel(private val context: Context) : ViewModel()
    
    // ✅ 正确：通过接口或包装类获取所需资源
    private val stringProvider: StringProvider
    
    constructor(stringProvider: StringProvider) {
        this.stringProvider = stringProvider
    }
    
    fun getAppName(): String {
        return stringProvider.getAppName()
    }
    
    // ✅ 正确：使用 Application Context（如果需要）
    // 通过 Application 类或依赖注入获取
    class AppDependentViewModel(
        private val application: Application
    ) : ViewModel() {
        
        fun getAppInfo(): String {
            // 使用 Application Context 是安全的
            return application.packageName
        }
    }
}

/**
 * 正确的方式：通过接口抽象资源访问
 */
interface StringProvider {
    fun getAppName(): String
    fun getString(resId: Int): String
}

class AndroidStringProvider(
    private val context: Context
) : StringProvider {
    
    override fun getAppName(): String {
        return context.getString(R.string.app_name)
    }
    
    override fun getString(resId: Int): String {
        return context.getString(resId)
    }
}

/**
 * 在 Activity/Fragment 中注入依赖
 */
class MyActivity : AppCompatActivity() {
    
    private lateinit var viewModel: CorrectViewModel
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // ✅ 正确：注入 StringProvider 而不是 Context
        val stringProvider = AndroidStringProvider(applicationContext)
        viewModel = CorrectViewModel(stringProvider)
        
        // 或者使用 ViewModelProvider.Factory
        val factory = object : ViewModelProvider.Factory {
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                val stringProvider = AndroidStringProvider(applicationContext)
                return CorrectViewModel(stringProvider) as T
            }
        }
        
        viewModel = ViewModelProvider(this, factory).get(CorrectViewModel::class.java)
    }
}

/**
 * 如果需要 Resource ID，传递资源 ID 而不是 Context
 */
class ResourceViewModel : ViewModel() {
    
    fun getLocalizedString(@StringRes resId: Int, vararg args: Any): String {
        // 通过其他方式获取字符串，例如从 Repository
        return repository.getLocalizedString(resId, *args)
    }
}

/**
 * 使用 Hilt/Dagger 进行依赖注入的示例
 */
@HiltViewModel
class HiltViewModel @Inject constructor(
    private val resourceManager: ResourceManager
) : ViewModel() {
    
    fun getAppInfo(): String {
        return resourceManager.getAppName()
    }
}

/**
 * ResourceManager 接口和实现
 */
interface ResourceManager {
    fun getAppName(): String
    fun getString(@StringRes resId: Int): String
}

@Singleton
class AndroidResourceManager @Inject constructor(
    @ApplicationContext private val appContext: Context
) : ResourceManager {
    
    override fun getAppName(): String {
        return appContext.getString(R.string.app_name)
    }
    
    override fun getString(@StringRes resId: Int): String {
        return appContext.getString(resId)
    }
}