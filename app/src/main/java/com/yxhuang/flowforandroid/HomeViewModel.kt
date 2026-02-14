package com.yxhuang.flowforandroid

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.asFlow
import kotlinx.coroutines.launch

class HomeViewModel : ViewModel() {

    init {
        GlobalScope.launch {
            val flow = (1..10).asFlow()
            flow.collect {
                println("collect $it")
                delay(1000)
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
    }
}