package com.yxhuang.flowforandroid

import android.util.Log
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

class TestClass {
    fun test() {
        GlobalScope.launch {
            Log.e("TestClass", "test: ")
        }
    }
}
