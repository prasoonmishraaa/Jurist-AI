import os
import ast
from pathlib import Path

tests_dir = Path("ml-service/tests")
test_files = sorted(tests_dir.glob("test_*.py"))

print(f"Total test files in ml-service/tests/: {len(test_files)}")
print("=" * 60)

total_tests = 0
for tf in test_files:
    with open(tf, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    
    count = 0
    test_names = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            count += 1
            test_names.append(node.name)
        elif isinstance(node, ast.ClassDef):
            for subnode in node.body:
                if isinstance(subnode, ast.FunctionDef) and subnode.name.startswith("test_"):
                    count += 1
                    test_names.append(f"{node.name}::{subnode.name}")
                    
    total_tests += count
    print(f"{tf.name:45s}: {count:2d} tests")

print("=" * 60)
print(f"Total collected tests: {total_tests}")
