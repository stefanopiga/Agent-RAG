#!/usr/bin/env python3
"""
Validates project structure against Epic 6 requirements.
Returns exit code 0 if valid, 1 if violations found.
"""

import sys
from pathlib import Path

# Authorized files in root directory
ROOT_ALLOWED_FILES = [
    "README.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "uv.lock",
    "docker-compose.yml",
    "Dockerfile.streamlit",  # Streamlit container (renamed from Dockerfile)
    "Dockerfile.api",
    "Dockerfile.mcp",
    ".env.example",
    ".gitignore",
    "coderabbit.yaml",
    "mkdocs.yml",
    "package.json",
    "package-lock.json",
    "app.py",
    "mcp_server.py",  # MCP server entry point (Story 6-1)
    "prometheus.yml",  # Prometheus configuration
]

# Forbidden patterns in root (except allowed)
ROOT_FORBIDDEN_PATTERNS = {
    "*.md": ["README.md", "CHANGELOG.md"],  # Only these .md allowed
    "temp_*.py": [],
    "debug_*.py": [],
    "*_copy_*": [],  # directories, but check files too
    "test_*.py": [],
}

# Required directories
REQUIRED_DIRECTORIES = [
    "docling_mcp",
    "core",
    "ingestion",
    "utils",
    "api",
    "tests",
    "scripts",
    "docs",
    "sql",
]

# Required script subdirectories
REQUIRED_SCRIPT_SUBDIRS = [
    "scripts/verification",
    "scripts/debug",
    "scripts/testing",
    "scripts/validation",
]

# Required .gitignore entries
REQUIRED_GITIGNORE_ENTRIES = [
    "site",
    "node_modules",
    "documents_copy_cooleman",
    "documents_copy_mia",
    "metrics",
]


def load_gitignore_patterns(root_dir: Path) -> set[str]:
    """Load patterns from .gitignore."""
    patterns = set()
    gitignore_path = root_dir / ".gitignore"
    
    if gitignore_path.exists():
        for line in gitignore_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove leading / if present
                patterns.add(line.lstrip("/"))
    
    return patterns


def validate_root_files(root_dir: Path) -> list[str]:
    """Validate root directory contains only authorized files."""
    violations = []
    gitignore_patterns = load_gitignore_patterns(root_dir)
    
    for item in root_dir.iterdir():
        if item.is_file():
            name = item.name
            # Skip hidden files
            if name.startswith("."):
                continue
            # Skip files in .gitignore (generated/runtime files)
            if name in gitignore_patterns:
                continue
            # Check if authorized
            if name not in ROOT_ALLOWED_FILES:
                violations.append(f"Unauthorized file in root: {name}")
    
    return violations


def validate_no_forbidden_patterns(root_dir: Path) -> list[str]:
    """Validate no forbidden patterns in root."""
    violations = []
    
    for item in root_dir.iterdir():
        if item.is_file():
            name = item.name
            # Check temp_*.py
            if name.startswith("temp_") and name.endswith(".py"):
                violations.append(f"Forbidden temp file in root: {name}")
            # Check debug_*.py
            if name.startswith("debug_") and name.endswith(".py"):
                violations.append(f"Forbidden debug file in root: {name}")
            # Check test_*.py
            if name.startswith("test_") and name.endswith(".py"):
                violations.append(f"Forbidden test file in root: {name}")
            # Check .md files (only README.md and CHANGELOG.md allowed)
            if name.endswith(".md") and name not in ["README.md", "CHANGELOG.md"]:
                violations.append(f"Unauthorized markdown file in root: {name}")
    
    return violations


def validate_required_directories(root_dir: Path) -> list[str]:
    """Validate required directories exist."""
    violations = []
    
    for dir_name in REQUIRED_DIRECTORIES:
        dir_path = root_dir / dir_name
        if not dir_path.is_dir():
            violations.append(f"Required directory missing: {dir_name}/")
    
    return violations


def validate_script_subdirectories(root_dir: Path) -> list[str]:
    """Validate scripts subdirectories exist."""
    violations = []
    
    for subdir in REQUIRED_SCRIPT_SUBDIRS:
        subdir_path = root_dir / subdir
        if not subdir_path.is_dir():
            violations.append(f"Required scripts subdirectory missing: {subdir}/")
    
    return violations


def validate_scripts_organized(root_dir: Path) -> list[str]:
    """Validate no loose scripts in scripts/ root."""
    violations = []
    scripts_dir = root_dir / "scripts"
    
    if scripts_dir.is_dir():
        for item in scripts_dir.iterdir():
            if item.is_file() and item.suffix == ".py":
                violations.append(
                    f"Script not in subdirectory: scripts/{item.name} "
                    "(should be in verification/, debug/, testing/, or validation/)"
                )
    
    return violations


def validate_gitignore(root_dir: Path) -> list[str]:
    """Validate .gitignore contains required entries."""
    violations = []
    gitignore_path = root_dir / ".gitignore"
    
    if not gitignore_path.exists():
        violations.append(".gitignore file missing")
        return violations
    
    content = gitignore_path.read_text()
    
    for entry in REQUIRED_GITIGNORE_ENTRIES:
        # Check if entry exists (with or without leading /)
        if entry not in content and f"/{entry}" not in content:
            violations.append(f".gitignore missing required entry: {entry}")
    
    return violations


def validate_mcp_server_location(root_dir: Path) -> list[str]:
    """Validate MCP server is in docling_mcp/ module."""
    violations = []
    
    # Check server.py is in docling_mcp/
    server_path = root_dir / "docling_mcp" / "server.py"
    if not server_path.exists():
        violations.append("MCP server not found in docling_mcp/server.py")
    
    # Check no server.py in root
    root_server = root_dir / "server.py"
    if root_server.exists():
        violations.append("server.py should not be in root (move to docling_mcp/)")
    
    return violations


def validate_code_organization(root_dir: Path) -> list[str]:
    """Validate code organization by responsibility."""
    violations = []
    
    expected_modules = {
        "docling_mcp": ["server.py", "__init__.py"],
        "core": ["__init__.py"],
        "ingestion": ["__init__.py"],
        "utils": ["db_utils.py"],
        "api": ["main.py"],
    }
    
    for module, required_files in expected_modules.items():
        module_path = root_dir / module
        if module_path.is_dir():
            for req_file in required_files:
                if not (module_path / req_file).exists():
                    violations.append(f"Required file missing: {module}/{req_file}")
    
    return violations


def main() -> int:
    """Main validation function."""
    root_dir = Path(__file__).parent.parent.parent
    
    all_violations = []
    
    print("Validating project structure...")
    print(f"Root directory: {root_dir.absolute()}")
    print()
    
    # Run all validations
    validations = [
        ("Root files", validate_root_files),
        ("Forbidden patterns", validate_no_forbidden_patterns),
        ("Required directories", validate_required_directories),
        ("Script subdirectories", validate_script_subdirectories),
        ("Scripts organization", validate_scripts_organized),
        ("Gitignore entries", validate_gitignore),
        ("MCP server location", validate_mcp_server_location),
        ("Code organization", validate_code_organization),
    ]
    
    for name, validator in validations:
        violations = validator(root_dir)
        if violations:
            print(f"❌ {name}:")
            for v in violations:
                print(f"   - {v}")
            all_violations.extend(violations)
        else:
            print(f"✓ {name}")
    
    print()
    
    if all_violations:
        print(f"Found {len(all_violations)} violation(s)")
        return 1
    else:
        print("All validations passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

