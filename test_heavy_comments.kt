package com.example.test

/*
 * This is a MASSIVE comment block
 * that would kill regex parsers
 * with catastrophic backtracking
 * 
 * Let's make it really long...
 * Line 1 of many
 * Line 2 of many
 * Line 3 of many
 * Line 4 of many
 * Line 5 of many
 * Line 6 of many
 * Line 7 of many
 * Line 8 of many
 * Line 9 of many
 * Line 10 of many
 * Line 11 of many
 * Line 12 of many
 * Line 13 of many
 * Line 14 of many
 * Line 15 of many
 * Line 16 of many
 * Line 17 of many
 * Line 18 of many
 * Line 19 of many
 * Line 20 of many
 * 
 * This is the kind of comment that makes regex go:
 * /\*.*?\*/ -> BOOM! 💥
 * 
 * But our simple analyzer handles it just fine!
 */

import kotlin.math.*
import java.util.*
import java.io.File

// Single line comment
// Another one
// And another

/**
 * KDoc comment for the main class
 * @property name The name property
 * @constructor Creates a test class
 */
data class TestClass(
    val name: String,
    val age: Int
) {
    /*
     * Another block comment inside class
     * With multiple lines
     * Just to test
     */
    fun greet(): String {
        // Method implementation
        return "Hello, $name!" // inline comment
    }
    
    /**
     * Suspend function with KDoc
     */
    suspend fun doAsync(): Int {
        return 42
    }
}

// Extension function
fun String.extension(): Int = this.length

// Top-level function
fun topLevelFunction(param: String): String {
    /*
     * Comment inside function
     * Multiple lines
     */
    return param.uppercase()
}

/*
 * One more HUGE comment block
 * Line 1 of the final boss
 * Line 2 of the final boss
 * Line 3 of the final boss
 * Line 4 of the final boss
 * Line 5 of the final boss
 * Line 6 of the final boss
 * Line 7 of the final boss
 * Line 8 of the final boss
 * Line 9 of the final boss
 * Line 10 of the final boss
 * Line 11 of the final boss
 * Line 12 of the final boss
 * Line 13 of the final boss
 * Line 14 of the final boss
 * Line 15 of the final boss
 * Line 16 of the final boss
 * Line 17 of the final boss
 * Line 18 of the final boss
 * Line 19 of the final boss
 * Line 20 of the final boss
 * Line 21 of the final boss
 * Line 22 of the final boss
 * Line 23 of the final boss
 * Line 24 of the final boss
 * Line 25 of the final boss
 * 
 * This would definitely cause regex catastrophic backtracking!
 * But we're not using regex for comment parsing anymore 😎
 */
sealed interface TestInterface {
    fun interfaceMethod(): Boolean
}

object TestObject : TestInterface {
    override fun interfaceMethod() = true
    
    private fun privateMethod() {
        println("Private method")
    }
}