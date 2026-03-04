package com.yxhuang.flowforandroid

import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

class TestClass {
    fun test() {
        GlobalScope.launch { println("test") }
    }

    fun test2() {
        GlobalScope.launch { println("test") }
    }
}
