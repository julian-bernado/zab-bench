#!/usr/bin/env python3

print("Starting minimal test...")

try:
    import lmstudio as lms
    print("lmstudio imported")
    
    from zab import Zab, ZabFunctions
    print("zab imported")
    
    zab = Zab(turns=10)
    print(f"Zab created: {zab.state()}")
    
    import random
    functions = ["fin", "tox", "sox"]
    selected = random.sample(functions, 2)
    print(f"Selected functions: {selected}")
    
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
