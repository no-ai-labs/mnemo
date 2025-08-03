"""Kotlin analyzer using Kotlin compiler API via subprocess."""

import os
import json
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
from py2neo import Graph, Node, Relationship


class KotlinCompilerAnalyzer:
    """
    Kotlin analyzer using Kotlin compiler for accurate AST parsing.
    
    This requires a Kotlin script that uses the Kotlin compiler API
    to parse source files and output structured data.
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        self.kotlin_script_path = self._setup_kotlin_analyzer()
    
    def _setup_kotlin_analyzer(self) -> Path:
        """Create Kotlin analyzer script."""
        script_content = '''
import java.io.File
import kotlin.script.experimental.jvm.util.classpathFromClass
import com.google.gson.Gson
import com.google.gson.GsonBuilder

@file:Repository("https://repo1.maven.org/maven2/")
@file:DependsOn("com.google.code.gson:gson:2.8.9")
@file:DependsOn("org.jetbrains.kotlin:kotlin-compiler-embeddable:1.9.0")

import org.jetbrains.kotlin.cli.common.CLIConfigurationKeys
import org.jetbrains.kotlin.cli.common.messages.MessageRenderer
import org.jetbrains.kotlin.cli.common.messages.PrintingMessageCollector
import org.jetbrains.kotlin.cli.jvm.compiler.EnvironmentConfigFiles
import org.jetbrains.kotlin.cli.jvm.compiler.KotlinCoreEnvironment
import org.jetbrains.kotlin.com.intellij.openapi.util.Disposer
import org.jetbrains.kotlin.com.intellij.psi.PsiElement
import org.jetbrains.kotlin.com.intellij.psi.PsiRecursiveElementVisitor
import org.jetbrains.kotlin.config.CompilerConfiguration
import org.jetbrains.kotlin.psi.*

data class FunctionInfo(
    val name: String,
    val packageName: String,
    val className: String?,
    val returnType: String,
    val parameters: List<String>,
    val calls: List<String>
)

data class ClassInfo(
    val name: String,
    val packageName: String,
    val type: String,
    val superTypes: List<String>,
    val functions: List<String>
)

data class AnalysisResult(
    val file: String,
    val functions: List<FunctionInfo>,
    val classes: List<ClassInfo>
)

class KotlinAnalyzer {
    private val gson = GsonBuilder().setPrettyPrinting().create()
    
    fun analyzeFile(filePath: String): AnalysisResult {
        val configuration = CompilerConfiguration().apply {
            put(CLIConfigurationKeys.MESSAGE_COLLECTOR_KEY,
                PrintingMessageCollector(System.err, MessageRenderer.PLAIN_RELATIVE_PATHS, false))
        }
        
        val disposable = Disposer.newDisposable()
        try {
            val environment = KotlinCoreEnvironment.createForLocalClasspathAnalysis(
                disposable, configuration, EnvironmentConfigFiles.JVM_CONFIG_FILES
            )
            
            val ktFile = environment.getSourceFiles().find { it.virtualFilePath == filePath }
                ?: throw IllegalArgumentException("File not found: $filePath")
            
            val functions = mutableListOf<FunctionInfo>()
            val classes = mutableListOf<ClassInfo>()
            
            ktFile.accept(object : PsiRecursiveElementVisitor() {
                override fun visitElement(element: PsiElement) {
                    when (element) {
                        is KtNamedFunction -> {
                            val functionCalls = mutableListOf<String>()
                            element.accept(object : PsiRecursiveElementVisitor() {
                                override fun visitElement(element: PsiElement) {
                                    if (element is KtCallExpression) {
                                        val callee = element.calleeExpression?.text
                                        if (callee != null) {
                                            functionCalls.add(callee)
                                        }
                                    }
                                    super.visitElement(element)
                                }
                            })
                            
                            functions.add(FunctionInfo(
                                name = element.name ?: "anonymous",
                                packageName = ktFile.packageFqName.asString(),
                                className = (element.parent as? KtClass)?.name,
                                returnType = element.typeReference?.text ?: "Unit",
                                parameters = element.valueParameters.map { it.text },
                                calls = functionCalls
                            ))
                        }
                        is KtClass -> {
                            val classFunctions = element.declarations
                                .filterIsInstance<KtNamedFunction>()
                                .map { it.name ?: "anonymous" }
                            
                            classes.add(ClassInfo(
                                name = element.name ?: "anonymous",
                                packageName = ktFile.packageFqName.asString(),
                                type = when {
                                    element is KtClassOrObject && element.isInterface() -> "interface"
                                    element is KtObjectDeclaration -> "object"
                                    else -> "class"
                                },
                                superTypes = element.superTypeListEntries.map { it.text },
                                functions = classFunctions
                            ))
                        }
                    }
                    super.visitElement(element)
                }
            })
            
            return AnalysisResult(filePath, functions, classes)
        } finally {
            Disposer.dispose(disposable)
        }
    }
}

// Main execution
val analyzer = KotlinAnalyzer()
val filePath = args[0]
val result = analyzer.analyzeFile(filePath)
println(analyzer.gson.toJson(result))
'''
        
        # Save script
        script_path = Path.home() / ".mnemo" / "kotlin_analyzer.kts"
        script_path.parent.mkdir(exist_ok=True)
        script_path.write_text(script_content)
        
        return script_path
    
    def analyze_with_compiler(self, file_path: str) -> Optional[Dict]:
        """
        Analyze Kotlin file using the compiler API.
        
        Note: This requires Kotlin to be installed and kotlinc-jvm in PATH.
        """
        try:
            # Run Kotlin script
            result = subprocess.run(
                ["kotlinc", "-script", str(self.kotlin_script_path), file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"Kotlin compiler error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("Kotlin analysis timed out")
            return None
        except FileNotFoundError:
            print("kotlinc not found. Please install Kotlin compiler.")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse Kotlin output: {e}")
            return None
    
    def build_accurate_call_graph(self, project_path: str, project_name: str) -> Dict:
        """Build call graph using Kotlin compiler for accuracy."""
        print(f"[KOTLIN-COMPILER] Building accurate call graph for: {project_name}")
        
        project_path = Path(project_path)
        kotlin_files = list(project_path.rglob("*.kt"))
        
        stats = {
            'files': 0,
            'functions': 0,
            'classes': 0,
            'calls': 0,
            'errors': 0
        }
        
        for kt_file in kotlin_files:
            if any(skip in str(kt_file) for skip in ['/build/', '/.gradle/']):
                continue
            
            result = self.analyze_with_compiler(str(kt_file))
            
            if result:
                stats['files'] += 1
                stats['functions'] += len(result.get('functions', []))
                stats['classes'] += len(result.get('classes', []))
                
                # Store in Neo4j
                self._store_analysis(result, project_name)
            else:
                stats['errors'] += 1
        
        print(f"[KOTLIN-COMPILER] Analysis complete: {stats}")
        return stats
    
    def _store_analysis(self, analysis: Dict, project_name: str):
        """Store analysis results in Neo4j."""
        # Create function nodes
        for func in analysis.get('functions', []):
            func_node = Node(
                "KotlinFunction",
                name=f"{func['packageName']}.{func['className']}.{func['name']}" 
                      if func['className'] else f"{func['packageName']}.{func['name']}",
                short_name=func['name'],
                package=func['packageName'],
                class_name=func['className'],
                return_type=func['returnType'],
                project=project_name
            )
            self.graph.create(func_node)
            
            # Create call relationships
            for callee in func['calls']:
                # This is simplified - in reality, we'd need to resolve the full name
                call_rel = Relationship(
                    func_node,
                    "CALLS",
                    Node("FunctionCall", name=callee, project=project_name),
                    call_type="direct"
                )
                self.graph.create(call_rel)
        
        # Create class nodes
        for cls in analysis.get('classes', []):
            cls_node = Node(
                "KotlinClass",
                name=f"{cls['packageName']}.{cls['name']}",
                short_name=cls['name'],
                package=cls['packageName'],
                type=cls['type'],
                project=project_name
            )
            self.graph.create(cls_node)
            
            # Create inheritance relationships
            for super_type in cls['superTypes']:
                inherit_rel = Relationship(
                    cls_node,
                    "EXTENDS",
                    Node("SuperType", name=super_type, project=project_name)
                )
                self.graph.create(inherit_rel)


# Fallback: Tree-sitter based analyzer (alternative approach)
class TreeSitterKotlinAnalyzer:
    """
    Alternative: Use tree-sitter for Kotlin parsing.
    This requires tree-sitter and tree-sitter-kotlin to be installed.
    """
    
    def __init__(self):
        try:
            import tree_sitter
            import tree_sitter_kotlin
        except ImportError:
            raise ImportError(
                "tree-sitter libraries not found. Install with:\n"
                "pip install tree-sitter tree-sitter-kotlin"
            )
        
        # Initialize tree-sitter
        self.parser = tree_sitter.Parser()
        self.parser.set_language(tree_sitter_kotlin.language())
    
    def parse_kotlin_file(self, file_path: str) -> Dict:
        """Parse Kotlin file using tree-sitter."""
        with open(file_path, 'rb') as f:
            content = f.read()
        
        tree = self.parser.parse(content)
        
        # Extract information from AST
        functions = []
        classes = []
        
        # This is a simplified example - real implementation would traverse the AST
        # and extract detailed information
        
        return {
            'functions': functions,
            'classes': classes
        }


if __name__ == "__main__":
    # Example usage
    print("Kotlin Compiler Analyzer")
    print("========================")
    print("\nThis analyzer provides three approaches:")
    print("1. Kotlin Compiler API (most accurate, requires Kotlin)")
    print("2. Tree-sitter (good balance, pure Python)")
    print("3. Enhanced Regex (fastest, less accurate)")
    print("\nFor production use, combine multiple approaches.")