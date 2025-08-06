// Simple Kotlin analyzer without external dependencies
// Uses basic Kotlin file parsing

import java.io.File

data class SimpleAnalysis(
    val fileName: String,
    val packageName: String,
    val imports: Int,
    val functions: List<String>,
    val classes: List<String>,
    val commentLines: Int,
    val codeLines: Int,
    val totalLines: Int
)

fun analyzeKotlinFile(filePath: String): SimpleAnalysis {
    val file = File(filePath)
    val lines = file.readLines()
    
    var packageName = ""
    var importCount = 0
    val functions = mutableListOf<String>()
    val classes = mutableListOf<String>()
    var commentLines = 0
    var inBlockComment = false
    
    for (line in lines) {
        val trimmed = line.trim()
        
        // Count comments (the regex killer!)
        when {
            inBlockComment -> {
                commentLines++
                if (trimmed.contains("*/")) inBlockComment = false
            }
            trimmed.startsWith("/*") -> {
                commentLines++
                inBlockComment = !trimmed.contains("*/")
            }
            trimmed.startsWith("//") -> commentLines++
        }
        
        // Extract info (simple parsing, no regex!)
        when {
            trimmed.startsWith("package ") -> {
                packageName = trimmed.substring(8).trim()
            }
            trimmed.startsWith("import ") -> {
                importCount++
            }
            trimmed.matches(Regex("^(public |private |internal |protected )?(suspend )?fun \\w+.*")) -> {
                val funcName = trimmed
                    .replace(Regex("^(public |private |internal |protected )?"), "")
                    .replace(Regex("^(suspend )?fun "), "")
                    .substringBefore("(")
                    .trim()
                functions.add(funcName)
            }
            trimmed.matches(Regex("^(public |private |internal |protected )?(data |sealed |enum |open |abstract )?(class|interface|object) \\w+.*")) -> {
                val className = trimmed
                    .replace(Regex("^(public |private |internal |protected )?"), "")
                    .replace(Regex("^(data |sealed |enum |open |abstract )?"), "")
                    .replace(Regex("^(class|interface|object) "), "")
                    .substringBefore(" ")
                    .substringBefore("(")
                    .substringBefore(":")
                    .substringBefore("<")
                    .trim()
                classes.add(className)
            }
        }
    }
    
    return SimpleAnalysis(
        fileName = file.name,
        packageName = packageName,
        imports = importCount,
        functions = functions,
        classes = classes,
        commentLines = commentLines,
        codeLines = lines.size - commentLines,
        totalLines = lines.size
    )
}

fun main(args: Array<String>) {
    if (args.isEmpty()) {
        println("Usage: kotlin simple_kotlin_analyzer.kt <file_path>")
        return
    }
    
    try {
        val result = analyzeKotlinFile(args[0])
        
        println("=== Kotlin File Analysis ===")
        println("File: ${result.fileName}")
        println("Package: ${result.packageName}")
        println("Total lines: ${result.totalLines}")
        println("Code lines: ${result.codeLines}")
        println("Comment lines: ${result.commentLines} (${result.commentLines * 100 / result.totalLines}%)")
        println("Imports: ${result.imports}")
        println("\nClasses (${result.classes.size}):")
        result.classes.forEach { println("  - $it") }
        println("\nFunctions (${result.functions.size}):")
        result.functions.forEach { println("  - $it") }
        
    } catch (e: Exception) {
        println("Error: ${e.message}")
    }
}