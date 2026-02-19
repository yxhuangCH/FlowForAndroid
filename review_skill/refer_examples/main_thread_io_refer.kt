package com.example.android

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * 避免在主线程执行 IO 操作 - 正确的线程调度方式
 * 
 * 错误示例：Dispatchers.Main 中执行 repository 操作
 * 正确示例：使用 Dispatchers.IO 或 withContext 切换线程
 * 
 * 原因：主线程用于 UI 渲染，执行 IO 操作会导致界面卡顿、ANR。
 */
class CorrectRepository {
    
    // ❌ 错误：在主线程执行 IO 操作
    // suspend fun fetchDataWrong(): Data {
    //     return withContext(Dispatchers.Main) {
    //         // IO 操作不应该在主线程执行
    //         database.queryData()
    //     }
    // }
    
    // ✅ 正确：在 IO 线程执行 IO 操作
    suspend fun fetchDataCorrect(): Data {
        return withContext(Dispatchers.IO) {
            // IO 操作在 IO 线程执行
            database.queryData()
        }
    }
    
    // ✅ 正确：使用适当的调度器
    suspend fun fetchUserData(): User {
        return withContext(Dispatchers.IO) {
            val user = api.getUser()
            database.saveUser(user)
            user
        }
    }
    
    // ✅ 正确：复杂操作可以分解
    suspend fun fetchAndProcessData(): Result {
        // 第一步：在 IO 线程获取数据
        val rawData = withContext(Dispatchers.IO) {
            api.fetchData()
        }
        
        // 第二步：在主线程更新 UI（如果需要）
        withContext(Dispatchers.Main) {
            updateProgress()
        }
        
        // 第三步：在 Default 线程处理数据
        val processedData = withContext(Dispatchers.Default) {
            processData(rawData)
        }
        
        // 第四步：在 IO 线程保存结果
        return withContext(Dispatchers.IO) {
            database.saveResult(processedData)
            Result.Success(processedData)
        }
    }
}

/**
 * ViewModel 中的正确用法
 */
class UserViewModel : ViewModel() {
    
    private val repository = UserRepository()
    
    fun loadUser() {
        viewModelScope.launch {
            // ✅ 正确：在 ViewModel 中启动协程，repository 负责线程调度
            val user = repository.getUser()
            
            // 在主线程更新 UI
            _userState.value = user
        }
    }
}

/**
 * Repository 层的线程调度
 */
class UserRepository {
    
    private val apiService = ApiService()
    private val userDao = UserDao()
    
    suspend fun getUser(): User {
        // ✅ 正确：Repository 负责线程调度
        return withContext(Dispatchers.IO) {
            // 检查缓存
            val cachedUser = userDao.getUser()
            if (cachedUser != null) {
                return@withContext cachedUser
            }
            
            // 从网络获取
            val remoteUser = apiService.fetchUser()
            
            // 保存到数据库
            userDao.insertUser(remoteUser)
            
            remoteUser
        }
    }
    
    // ✅ 正确：使用 flow 和 flowOn
    fun getUserStream(): Flow<User> = flow {
        // 从数据库观察变化
        userDao.observeUser().collect { user ->
            emit(user)
        }
    }.flowOn(Dispatchers.IO) // 在 IO 线程执行上游操作
     .catch { e ->
        // 错误处理
        emit(User.Error(e.message ?: "Unknown error"))
    }
}

/**
 * 使用协程调度器的最佳实践：
 * 1. Dispatchers.Main - 更新 UI、轻量级操作
 * 2. Dispatchers.IO - 文件操作、数据库访问、网络请求
 * 3. Dispatchers.Default - CPU 密集型计算、数据转换
 * 4. Dispatchers.Unconfined - 一般不使用，除非有特定需求
 */

/**
 * 测试中的线程调度
 */
@ExperimentalCoroutinesApi
class UserRepositoryTest {
    
    private val testDispatcher = StandardTestDispatcher()
    
    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
    }
    
    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }
    
    @Test
    fun testGetUser() = runTest {
        val repository = UserRepository()
        
        // 测试会在 TestDispatcher 上运行
        val user = repository.getUser()
        
        assertNotNull(user)
    }
}

/**
 * 使用自定义调度器进行测试
 */
class NetworkTest {
    
    @Test
    fun testNetworkCall() = runTest {
        val testDispatcher = UnconfinedTestDispatcher()
        
        val repository = UserRepository()
        
        // 使用测试调度器
        val result = withContext(testDispatcher) {
            repository.getUser()
        }
        
        assertEquals(expectedUser, result)
    }
}