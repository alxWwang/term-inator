import sys, os
print("executable:", sys.executable)
print("version:", sys.version)
print("prefix:", sys.prefix)
print("cwd:", os.getcwd())
print("VIRTUAL_ENV:", os.environ.get("VIRTUAL_ENV"))
print("sys.path (first items):", sys.path[:8])