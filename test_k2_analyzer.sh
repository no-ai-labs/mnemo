#!/bin/bash

echo "🚀 K2 Kotlin Analyzer Test Script"
echo "================================"

# Check if Kotlin is installed
if ! command -v kotlin &> /dev/null; then
    echo "❌ Kotlin not found! Please install Kotlin 2.0+"
    echo "   brew install kotlin  # on macOS"
    echo "   sdk install kotlin   # using SDKMAN"
    exit 1
fi

echo "✅ Kotlin found:"
kotlin -version

# Create a test Kotlin file with lots of comments (the regex killer!)
cat > test_comments_heavy.kt << 'EOF'
package com.example.test

/*
 * This is a very long comment
 * that spans multiple lines
 * and would cause regex catastrophic backtracking
 * with patterns like /\*.*?\*/
 * 
 * Let's add more lines...
 * Line 1
 * Line 2
 * Line 3
 * Line 4
 * Line 5
 * Line 6
 * Line 7
 * Line 8
 * Line 9
 * Line 10
 * And even more...
 * This is the kind of comment that kills regex parsers
 * But K2 compiler handles it just fine!
 */

// Single line comment
// Another one
// And another

/**
 * KDoc comment
 * @param name The name parameter
 * @return Some string
 */
fun greet(name: String): String {
    // Function implementation
    return "Hello, $name!" // inline comment
}

/*
 * Another block comment
 * With multiple lines
 * To test the analyzer
 */
class TestClass {
    /*
     * Property with comment
     */
    val property = "value"
    
    /**
     * Method with KDoc
     */
    fun method() {
        println("Method called")
    }
}

// Extension function
fun String.extension(): Int = this.length

// Top-level property
val topLevel = 42

/*
 * One more huge comment block
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
 * This would definitely cause regex issues!
 */
object TestObject {
    fun test() = "test"
}
EOF

echo ""
echo "📝 Created test file: test_comments_heavy.kt"
echo ""
echo "🔍 Running K2 analyzer..."
echo ""

# Run the analyzer
kotlin k2_analyzer.kts test_comments_heavy.kt

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Analysis completed successfully!"
    echo "   The K2 compiler handled the comment-heavy file without issues."
else
    echo ""
    echo "❌ Analysis failed. Check the error messages above."
fi

# Cleanup
rm -f test_comments_heavy.kt

echo ""
echo "💡 To analyze your own file:"
echo "   kotlin k2_analyzer.kts /path/to/your/file.kt"
echo ""
echo "📊 To analyze a whole project, use the Python wrapper:"
echo "   python mnemo/graph/k2_kotlin_analyzer.py /path/to/project"