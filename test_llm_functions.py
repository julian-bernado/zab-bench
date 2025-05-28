#!/usr/bin/env python3

from zab import Zab

def test_llm_functions():
    """Test the LLM-dependent functions to make sure they work"""
    zab = Zab(turns=10)
    
    print("Testing LLM-dependent functions:")
    print(f"Initial state: {zab.state()}")
    
    # Test stin (Spanish translation)
    try:
        zab = zab.call_function("stin", "cat")
        print(f"After stin('cat'): {zab.state()}")
        print(f"History: {zab.history[-1]}")
    except Exception as e:
        print(f"Error with stin: {e}")
    
    # Test vox (animal color)
    try:
        zab = zab.call_function("vox", "elephant")
        print(f"After vox('elephant'): {zab.state()}")
        print(f"History: {zab.history[-1]}")
    except Exception as e:
        print(f"Error with vox: {e}")
    
    # Test rox (shape sides)
    try:
        zab = zab.call_function("rox", "hexagon")
        print(f"After rox('hexagon'): {zab.state()}")
        print(f"History: {zab.history[-1]}")
    except Exception as e:
        print(f"Error with rox: {e}")
    
    # Test box (animal properties)
    try:
        zab = zab.call_function("box", "spider")
        print(f"After box('spider'): {zab.state()}")
        print(f"History: {zab.history[-1]}")
    except Exception as e:
        print(f"Error with box: {e}")

if __name__ == "__main__":
    test_llm_functions()
