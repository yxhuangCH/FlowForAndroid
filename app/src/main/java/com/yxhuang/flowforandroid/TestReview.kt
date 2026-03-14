package com.yxhuang.flowforandroid

import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

class TestReview {
    
    // 测试问题1: 在主线程执行IO操作
    fun badIOOperation() {
        val data = loadDataFromNetwork() // 问题：在主线程执行网络请求
    }
    
    // 测试问题2: 使用 GlobalScope
    fun useGlobalScope() {
        GlobalScope.launch {
            delay(1000)
        }
    }
    
    // 测试问题3: Flow 没有指定调度器
    fun flowWithoutDispatcher(): Flow<String> = flow {
        emit("data")
    }
    
    // 测试问题4: 没有指定协程上下文
    fun coroutineWithoutContext() {
        CoroutineScope(Dispatchers.Default).launch {
            // 没有使用 withContext
            val result = heavyComputation()
        }
    }
    
    // 辅助方法
    private fun loadDataFromNetwork(): String {
        Thread.sleep(1000)
        return "data"
    }
    
    private suspend fun heavyComputation(): String {
        delay(100)
        return "result"
    }
}