"""K2 Kotlin compiler-based analyzer - no more regex hell!"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from py2neo import Graph, Node, Relationship
import time


class K2KotlinAnalyzer:
    """
    Kotlin analyzer using K2 compiler for accurate AST parsing.
    No more regex catastrophic backtracking on comments!
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        self.k2_script_path = self._setup_k2_analyzer()
        
    def _setup_k2_analyzer(self) -> Path:
        """Create K2 analyzer script with better comment handling."""
        script_content = '''@file:Repository("https://repo1.maven.org/maven2/")
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
'''
        
        # Save script
        script_dir = Path.home() / ".mnemo" / "k2"
        script_dir.mkdir(parents=True, exist_ok=True)
        script_path = script_dir / "k2_analyzer.kts"
        script_path.write_text(script_content)
        
        return script_path
    
    def analyze_file(self, file_path: str) -> Optional[Dict]:
        """Analyze single file with K2 compiler."""
        try:
            # Check if file is too large
            file_size = os.path.getsize(file_path) / 1024  # KB
            if file_size > 500:  # 500KB limit
                print(f"⚠️  Skipping large file: {Path(file_path).name} ({file_size:.1f}KB)")
                return None
            
            # Run K2 analyzer
            result = subprocess.run(
                ["kotlin", str(self.k2_script_path), file_path],
                capture_output=True,
                text=True,
                timeout=10  # 10 second timeout per file
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"K2 error on {Path(file_path).name}: {result.stderr[:200]}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  Timeout analyzing: {Path(file_path).name}")
            return None
        except Exception as e:
            print(f"❌ Error analyzing {Path(file_path).name}: {e}")
            return None
    
    def analyze_project(self, project_path: str, project_name: str, 
                       save_to_neo4j: bool = True, max_files: Optional[int] = None) -> Dict:
        """Analyze project with K2 compiler."""
        print(f"\n🚀 K2 Kotlin Analysis (No More Regex Hell!)")
        print(f"   Project: {project_name}")
        print(f"   Path: {project_path}")
        
        start_time = time.time()
        project_path = Path(project_path)
        
        # Find Kotlin files
        kotlin_files = []
        for root, dirs, files in os.walk(project_path):
            # Skip build directories
            dirs[:] = [d for d in dirs if d not in {'.gradle', 'build', 'out', '.git'}]
            
            for file in files:
                if file.endswith('.kt'):
                    kotlin_files.append(Path(root) / file)
        
        if max_files:
            kotlin_files = kotlin_files[:max_files]
        
        total_files = len(kotlin_files)
        print(f"   Found {total_files} Kotlin files")
        
        if total_files == 0:
            return {'error': 'No Kotlin files found'}
        
        # Check if kotlin is available
        try:
            subprocess.run(["kotlin", "--version"], capture_output=True, check=True)
        except:
            print("\n❌ Kotlin not found! Please install Kotlin 2.0+")
            print("   brew install kotlin  # on macOS")
            print("   sdk install kotlin   # using SDKMAN")
            return {'error': 'Kotlin compiler not found'}
        
        stats = {
            'files': 0,
            'classes': 0,
            'functions': 0,
            'comments': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Process files
        for idx, kt_file in enumerate(kotlin_files):
            if idx % 10 == 0:
                print(f"\n📄 Processing {idx}/{total_files} files...")
            
            result = self.analyze_file(str(kt_file))
            
            if result:
                stats['files'] += 1
                stats['classes'] += len(result.get('classes', []))
                stats['functions'] += len(result.get('functions', []))
                stats['comments'] += result.get('commentLines', 0)
                
                # Save to Neo4j if enabled
                if save_to_neo4j:
                    self._save_to_neo4j(result, project_name)
            else:
                stats['errors'] += 1
        
        duration = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ K2 Analysis Complete!")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Files analyzed: {stats['files']}/{total_files}")
        print(f"   Classes: {stats['classes']}")
        print(f"   Functions: {stats['functions']}")
        print(f"   Comment lines: {stats['comments']}")
        print(f"   Errors: {stats['errors']}")
        print(f"   Speed: {stats['files']/duration:.1f} files/second")
        
        return stats
    
    def _save_to_neo4j(self, analysis: Dict, project_name: str):
        """Save analysis results to Neo4j."""
        try:
            # Create file node
            file_node = Node(
                "KotlinFile",
                path=analysis['path'],
                package=analysis['packageName'],
                project=project_name,
                totalLines=analysis['totalLines'],
                codeLines=analysis['codeLines'],
                commentLines=analysis['commentLines']
            )
            self.graph.merge(file_node, "KotlinFile", "path")
            
            # Create class nodes
            for cls in analysis.get('classes', []):
                class_node = Node(
                    "KotlinClass",
                    name=cls['name'],
                    type=cls['type'],
                    package=analysis['packageName'],
                    project=project_name
                )
                self.graph.merge(class_node, "KotlinClass", "name")
                self.graph.merge(Relationship(file_node, "CONTAINS", class_node))
            
            # Create function nodes
            for func in analysis.get('functions', []):
                func_node = Node(
                    "KotlinFunction",
                    name=func['name'],
                    package=analysis['packageName'],
                    project=project_name,
                    isExtension=func.get('isExtension', False)
                )
                self.graph.merge(func_node, "KotlinFunction", "name")
                self.graph.merge(Relationship(file_node, "CONTAINS", func_node))
                
        except Exception as e:
            print(f"   Neo4j save error: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        analyzer = K2KotlinAnalyzer()
        analyzer.analyze_project(sys.argv[1], "test_project", save_to_neo4j=False)
    else:
        print("Usage: python k2_kotlin_analyzer.py <project_path>")