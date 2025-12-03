#!/usr/bin/env python3
"""
Validates all Python imports work correctly after reorganization.
Verifies both syntax and actual import resolution.
Returns exit code 0 if all imports valid, 1 if errors found.
"""

import ast
import sys
from pathlib import Path

# Project modules to validate
PROJECT_MODULES = [
    "core",
    "ingestion",
    "docling_mcp",
    "utils",
    "api",
    "client",
]

# Directories to exclude from scanning
EXCLUDE_DIRS = [
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    "node_modules",
    "site",
    ".pytest_cache",
    "documents",
    "documents_copy_cooleman",
    "documents_copy_mia",
]


def get_python_files(root_dir: Path) -> list[Path]:
    """Get all Python files in project, excluding certain directories."""
    py_files = []
    
    for path in root_dir.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in EXCLUDE_DIRS):
            continue
        py_files.append(path)
    
    return py_files


def extract_imports(file_path: Path) -> tuple[list[str], list[str]]:
    """Extract import statements from a Python file.
    
    Returns:
        Tuple of (imports, errors)
    """
    imports = []
    errors = []
    
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")
    except Exception as e:
        errors.append(f"Parse error: {e}")
    
    return imports, errors


def validate_syntax(file_path: Path) -> list[str]:
    """Validate Python file syntax."""
    errors = []
    
    try:
        content = file_path.read_text(encoding="utf-8")
        compile(content, str(file_path), "exec")
    except SyntaxError as e:
        errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
    except Exception as e:
        errors.append(f"Compilation error: {e}")
    
    return errors


def validate_project_imports(imports: list[str], file_path: Path, root_dir: Path) -> list[str]:
    """Validate that project module imports are resolvable."""
    errors = []
    
    for imp in imports:
        # Get the top-level module
        top_module = imp.split(".")[0]
        
        # Check if it's a project module
        if top_module in PROJECT_MODULES:
            module_path = root_dir / top_module
            if not module_path.is_dir():
                errors.append(f"Import '{imp}' references missing module: {top_module}/")
            elif not (module_path / "__init__.py").exists():
                # Allow api/ without __init__.py (FastAPI convention)
                if top_module != "api":
                    errors.append(f"Module '{top_module}' missing __init__.py")
    
    return errors


def main() -> int:
    """Main validation function."""
    root_dir = Path(__file__).parent.parent.parent
    
    # Add project root to sys.path for import resolution
    sys.path.insert(0, str(root_dir))
    
    print("Validating Python imports...")
    print(f"Root directory: {root_dir.absolute()}")
    print()
    
    py_files = get_python_files(root_dir)
    print(f"Found {len(py_files)} Python files to validate")
    print()
    
    all_errors: list[tuple[str, str]] = []
    
    for py_file in py_files:
        rel_path = py_file.relative_to(root_dir)
        file_errors = []
        
        # Validate syntax
        syntax_errors = validate_syntax(py_file)
        file_errors.extend(syntax_errors)
        
        # Extract and validate imports
        imports, parse_errors = extract_imports(py_file)
        file_errors.extend(parse_errors)
        
        # Validate project imports are resolvable
        import_errors = validate_project_imports(imports, py_file, root_dir)
        file_errors.extend(import_errors)
        
        if file_errors:
            for error in file_errors:
                all_errors.append((str(rel_path), error))
    
    # Print results
    if all_errors:
        print("Errors found:")
        current_file = None
        for file_path, error in all_errors:
            if file_path != current_file:
                print(f"\n❌ {file_path}:")
                current_file = file_path
            print(f"   - {error}")
        
        print(f"\nTotal: {len(all_errors)} error(s) in {len(set(f for f, _ in all_errors))} file(s)")
        return 1
    else:
        print("✓ All imports validated successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

