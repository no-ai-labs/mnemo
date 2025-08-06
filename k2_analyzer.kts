@file:Repository("https://repo1.maven.org/maven2/")
@file:DependsOn("com.google.code.gson:gson:2.10.1")
@file:DependsOn("org.jetbrains.kotlin:kotlin-compiler:2.0.0")

import com.google.gson.Gson
import com.google.gson.GsonBuilder
import org.jetbrains.kotlin.cli.common.CLIConfigurationKeys
import org.jetbrains.kotlin.cli.common.config.addKotlinSourceRoot
import org.jetbrains.kotlin.cli.common.messages.MessageRenderer
import org.jetbrains.kotlin.cli.common.messages.PrintingMessageCollector
import org.jetbrains.kotlin.cli.jvm.compiler.EnvironmentConfigFiles
import org.jetbrains.kotlin.cli.jvm.compiler.KotlinCoreEnvironment
import org.jetbrains.kotlin.com.intellij.openapi.util.Disposer
import org.jetbrains.kotlin.com.intellij.psi.PsiElement
import org.jetbrains.kotlin.com.intellij.psi.PsiRecursiveElementVisitor
import org.jetbrains.kotlin.config.CompilerConfiguration
import org.jetbrains.kotlin.config.LanguageFeature
import org.jetbrains.kotlin.config.LanguageVersion
import org.jetbrains.kotlin.config.languageVersionSettings
import org.jetbrains.kotlin.psi.*
import java.io.File

data class FunctionInfo(
    val name: String,
    val packageName: String,
    val className: String?,
    val returnType: String?,
    val parameters: List<String>,
    val modifiers: List<String>,
    val lineNumber: Int?,
    val isExtension: Boolean,
    val calls: List<String> = emptyList()
)

data class ClassInfo(
    val name: String,
    val packageName: String,
    val type: String, // class, interface, object, enum
    val modifiers: List<String>,
    val superTypes: List<String>,
    val functions: List<String>,
    val properties: List<String>,
    val lineNumber: Int?
)

data class ImportInfo(
    val import: String,
    val isWildcard: Boolean,
    val alias: String?
)

data class CommentInfo(
    val type: String, // line, block, kdoc
    val lineStart: Int,
    val lineEnd: Int,
    val length: Int
)

data class FileAnalysis(
    val path: String,
    val packageName: String,
    val imports: List<ImportInfo>,
    val classes: List<ClassInfo>,
    val functions: List<FunctionInfo>,
    val topLevelProperties: List<String>,
    val comments: List<CommentInfo>,
    val totalLines: Int,
    val codeLines: Int,
    val commentLines: Int
)

class K2Analyzer {
    private val gson = GsonBuilder()
        .setPrettyPrinting()
        .disableHtmlEscaping()
        .create()
    
    fun analyzeFile(filePath: String): FileAnalysis {
        val file = File(filePath)
        val content = file.readText()
        val lines = content.lines()
        
        // Setup K2 compiler configuration
        val configuration = CompilerConfiguration().apply {
            put(CLIConfigurationKeys.MESSAGE_COLLECTOR_KEY,
                PrintingMessageCollector(System.err, MessageRenderer.PLAIN_RELATIVE_PATHS, false))
            
            // Enable K2 features
            languageVersionSettings = LanguageVersion.KOTLIN_2_0.toSettings()
            
            addKotlinSourceRoot(file.path)
        }
        
        val disposable = Disposer.newDisposable()
        
        try {
            val environment = KotlinCoreEnvironment.createForLocalClasspathAnalysis(
                disposable, configuration, EnvironmentConfigFiles.JVM_CONFIG_FILES
            )
            
            val psiFile = environment.getSourceFiles().firstOrNull()
                ?: throw IllegalStateException("Failed to parse file: $filePath")
            
            val packageName = psiFile.packageFqName.asString()
            val imports = mutableListOf<ImportInfo>()
            val classes = mutableListOf<ClassInfo>()
            val functions = mutableListOf<FunctionInfo>()
            val topLevelProperties = mutableListOf<String>()
            val comments = mutableListOf<CommentInfo>()
            
            // Visit all elements
            psiFile.accept(object : PsiRecursiveElementVisitor() {
                override fun visitElement(element: PsiElement) {
                    when (element) {
                        is KtImportDirective -> {
                            imports.add(ImportInfo(
                                import = element.importPath?.pathStr ?: "",
                                isWildcard = element.isAllUnder,
                                alias = element.alias?.name
                            ))
                        }
                        
                        is KtClass -> {
                            if (element.parent == psiFile) {  // Top-level only
                                val modifiers = mutableListOf<String>()
                                if (element.isData()) modifiers.add("data")
                                if (element.isSealed()) modifiers.add("sealed")
                                if (element.isInner()) modifiers.add("inner")
                                if (element.isEnum()) modifiers.add("enum")
                                
                                val type = when {
                                    element.isInterface() -> "interface"
                                    element.isEnum() -> "enum"
                                    else -> "class"
                                }
                                
                                classes.add(ClassInfo(
                                    name = element.name ?: "Anonymous",
                                    packageName = packageName,
                                    type = type,
                                    modifiers = modifiers,
                                    superTypes = element.superTypeListEntries.map { it.text },
                                    functions = element.declarations
                                        .filterIsInstance<KtNamedFunction>()
                                        .mapNotNull { it.name },
                                    properties = element.declarations
                                        .filterIsInstance<KtProperty>()
                                        .mapNotNull { it.name },
                                    lineNumber = getLineNumber(element, lines)
                                ))
                            }
                        }
                        
                        is KtObjectDeclaration -> {
                            if (element.parent == psiFile) {  // Top-level only
                                classes.add(ClassInfo(
                                    name = element.name ?: "Anonymous",
                                    packageName = packageName,
                                    type = "object",
                                    modifiers = if (element.isCompanion()) listOf("companion") else emptyList(),
                                    superTypes = element.superTypeListEntries.map { it.text },
                                    functions = element.declarations
                                        .filterIsInstance<KtNamedFunction>()
                                        .mapNotNull { it.name },
                                    properties = element.declarations
                                        .filterIsInstance<KtProperty>()
                                        .mapNotNull { it.name },
                                    lineNumber = getLineNumber(element, lines)
                                ))
                            }
                        }
                        
                        is KtNamedFunction -> {
                            if (element.parent == psiFile) {  // Top-level only
                                val modifiers = mutableListOf<String>()
                                element.modifierList?.let { ml ->
                                    if (ml.hasModifier(KtTokens.PRIVATE_KEYWORD)) modifiers.add("private")
                                    if (ml.hasModifier(KtTokens.PUBLIC_KEYWORD)) modifiers.add("public")
                                    if (ml.hasModifier(KtTokens.INTERNAL_KEYWORD)) modifiers.add("internal")
                                    if (ml.hasModifier(KtTokens.SUSPEND_KEYWORD)) modifiers.add("suspend")
                                    if (ml.hasModifier(KtTokens.INLINE_KEYWORD)) modifiers.add("inline")
                                }
                                
                                // Find function calls
                                val calls = mutableListOf<String>()
                                element.accept(object : PsiRecursiveElementVisitor() {
                                    override fun visitElement(element: PsiElement) {
                                        if (element is KtCallExpression) {
                                            val callee = element.calleeExpression?.text
                                            if (callee != null && !isKeyword(callee)) {
                                                calls.add(callee)
                                            }
                                        }
                                        super.visitElement(element)
                                    }
                                })
                                
                                functions.add(FunctionInfo(
                                    name = element.name ?: "anonymous",
                                    packageName = packageName,
                                    className = null,
                                    returnType = element.typeReference?.text,
                                    parameters = element.valueParameters.map { it.text },
                                    modifiers = modifiers,
                                    lineNumber = getLineNumber(element, lines),
                                    isExtension = element.receiverTypeReference != null,
                                    calls = calls
                                ))
                            }
                        }
                        
                        is KtProperty -> {
                            if (element.parent == psiFile && element.isTopLevel) {
                                topLevelProperties.add(element.name ?: "anonymous")
                            }
                        }
                    }
                    super.visitElement(element)
                }
            })
            
            // Analyze comments separately (avoiding regex issues!)
            val commentLines = countCommentLines(content)
            val codeLines = lines.size - commentLines
            
            return FileAnalysis(
                path = filePath,
                packageName = packageName,
                imports = imports,
                classes = classes,
                functions = functions,
                topLevelProperties = topLevelProperties,
                comments = comments,
                totalLines = lines.size,
                codeLines = codeLines,
                commentLines = commentLines
            )
            
        } finally {
            Disposer.dispose(disposable)
        }
    }
    
    private fun getLineNumber(element: PsiElement, lines: List<String>): Int? {
        // Simple line number approximation
        val text = element.text
        return lines.indexOfFirst { it.contains(text.take(20)) } + 1
    }
    
    private fun countCommentLines(content: String): Int {
        var count = 0
        var inBlockComment = false
        
        content.lines().forEach { line ->
            val trimmed = line.trim()
            when {
                inBlockComment -> {
                    count++
                    if (trimmed.contains("*/")) inBlockComment = false
                }
                trimmed.startsWith("/*") -> {
                    count++
                    inBlockComment = !trimmed.contains("*/")
                }
                trimmed.startsWith("//") -> count++
                trimmed.startsWith("*") && trimmed.length > 1 -> count++ // KDoc
            }
        }
        
        return count
    }
    
    private fun isKeyword(name: String): Boolean {
        return setOf(
            "if", "when", "for", "while", "do", "return", "break", "continue",
            "try", "catch", "finally", "throw", "assert", "require", "check"
        ).contains(name)
    }
}

// Main
if (args.isEmpty()) {
    System.err.println("Usage: kotlin k2_analyzer.kts <file_path>")
    System.exit(1)
}

try {
    val analyzer = K2Analyzer()
    val result = analyzer.analyzeFile(args[0])
    println(analyzer.gson.toJson(result))
} catch (e: Exception) {
    System.err.println("Error: ${e.message}")
    e.printStackTrace()
    System.exit(1)
}