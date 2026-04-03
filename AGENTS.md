# AGENTS.md - Developer Guide for FlowForAndroid

## Project Overview

This is an Android application built with Kotlin and Jetpack Compose demonstrating Flow and permission handling patterns.

## Build Commands

```bash
# Build debug APK
./gradlew assembleDebug

# Build release APK
./gradlew assembleRelease

# Run unit tests
./gradlew test

# Run unit tests for specific module
./gradlew :app:testDebugUnitTest

# Run a single test class
./gradlew testDebugUnitTest --tests="com.yxhuang.flowforandroid.ExampleUnitTest"

# Run a single test method
./gradlew testDebugUnitTest --tests="com.yxhuang.flowforandroid.ExampleUnitTest.addition_isCorrect"

# Run instrumentation tests (requires emulator/device)
./gradlew connectedAndroidTest

# Run lint analysis
./gradlew lint

# Check Kotlin code style
./gradlew ktlintCheck

# Format Kotlin code
./gradlew ktlintFormat

# Clean and rebuild
./gradlew clean assembleDebug

# View dependencies
./gradlew app:dependencies
```

## Code Style Guidelines

### General Principles

- Use Kotlin idioms and avoid Java-style code
- Prefer immutability; use `val` by default
- Use data classes for simple data holders
- Avoid nullable types (`?`) unless necessary; prefer empty collections over null

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Packages | lowercase, snake_case allowed | `com.yxhuang.flowforandroid.permission` |
| Classes | PascalCase | `PermissionManager`, `HomeViewModel` |
| Functions | camelCase | `requestNotificationPermission()` |
| Variables | camelCase | `permissionManager`, `hasPermission` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Composable functions | PascalCase (noun) | `PermissionDemoScreen` |

### Import Organization

Order imports as follows (blank line between groups):

1. Kotlin standard library (`kotlinx.*`)
2. Android imports (`android.*`)
3. AndroidX imports (`androidx.*`)
4. Jetpack Compose imports (`androidx.compose.*`)
5. Third-party libraries
6. Project imports

```kotlin
package com.yxhuang.flowforandroid

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.yxhuang.flowforandroid.permission.PermissionManager
```

### Formatting

- Use 4 spaces for indentation (no tabs)
- Maximum line length: 120 characters
- Use semicolons: **never**
- Trailing commas: **always** (for better diffs)

```kotlin
// Good
data class PermissionResult(
    val status: Status,
    val message: String,
)

// When calling
val result = PermissionResult(
    status = Status.GRANTED,
    message = "Permission granted",
)
```

### Type System

- Always specify return types for public functions
- Use explicit types for function parameters
- Prefer `Int`, `Boolean`, etc. over boxed types

```kotlin
// Good
fun requestPermission(
    permission: String,
    minApiLevel: Int,
): PermissionResult { ... }

// Avoid
fun requestPermission(permission, minApiLevel) { ... }
```

### Composable Guidelines

- Composable functions must NOT be called outside of Compose runtime
- Use `remember` to store mutable state across recompositions
- Use `rememberCoroutineScope` for launching coroutines in Composables
- Always provide default values for Modifier parameters

```kotlin
@Composable
fun MyComponent(
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    val state by viewModel.state.collectAsState()

    Button(
        onClick = onClick,
        modifier = modifier,
    ) {
        Text("Click me")
    }
}
```

### Coroutines and Flow

- Use `viewModelScope` instead of `GlobalScope` in ViewModels
- Use `StateFlow` for UI state
- Use `SharedFlow` for one-time events

```kotlin
// Good - HomeViewModel pattern
class HomeViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            // collect flows here
        }
    }
}

// Avoid - GlobalScope
class BadViewModel : ViewModel() {
    init {
        GlobalScope.launch { ... } // Don't do this
    }
}
```

### Error Handling

- Use sealed classes for result types (like `PermissionResult`)
- Provide meaningful error messages
- Never silently swallow exceptions

```kotlin
sealed class PermissionResult {
    data class Granted(val permission: String) : PermissionResult()
    data class Denied(val permission: String) : PermissionResult()
    data class Error(val exception: Throwable) : PermissionResult()
}
```

### Permission Handling

- Always check API level before requesting permissions
- Register Activity in `onCreate` before `setContent`
- Unregister in `onDestroy`

```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    PermissionManager.registerActivity(this)
    setContent { ... }
}

override fun onDestroy() {
    super.onDestroy()
    PermissionManager.unregisterActivity(this)
}
```

### Testing

- Place unit tests in `app/src/test/java/`
- Place instrumentation tests in `app/src/androidTest/java/`
- Use descriptive test names: `test[MethodName]_[ExpectedBehavior]`

```kotlin
class ExampleUnitTest {
    @Test
    fun addition_isCorrect() {
        assertEquals(4, 2 + 2)
    }
}
```

### File Organization

```
app/src/main/java/com/yxhuang/flowforandroid/
├── MainActivity.kt
├── FlowApplication.kt
├── HomeViewModel.kt
├── permission/
│   ├── PermissionManager.kt
│   ├── PermissionResult.kt
│   └── PermissionExample.kt
└── ui/theme/
    ├── Theme.kt
    ├── Color.kt
    └── Type.kt
```

## Common Issues and Solutions

- **"Unresolved reference"**: Run Gradle sync in Android Studio or `./gradlew dependencies`
- **"Activity not registered"**: Ensure `PermissionManager.registerActivity(this)` is called in `onCreate`
- **"Flow not collecting"**: Ensure collector is in correct scope (viewModelScope)
