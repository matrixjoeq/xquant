#!/usr/bin/env python3
import os
import stat
from pathlib import Path

def make_python3_compatible():
    """Make all Python files in the project compatible with Python 3."""
    project_root = Path(__file__).parent.parent
    python_files = list(project_root.rglob("*.py"))
    
    for py_file in python_files:
        # Read the file content
        with open(py_file, 'r') as f:
            content = f.read()
        
        # Add shebang if not present
        if not content.startswith('#!/usr/bin/env python3'):
            with open(py_file, 'w') as f:
                f.write('#!/usr/bin/env python3\n' + content)
        
        # Make file executable
        current_permissions = os.stat(py_file).st_mode
        os.chmod(py_file, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        
        print(f"Processed: {py_file}")

if __name__ == '__main__':
    make_python3_compatible() 