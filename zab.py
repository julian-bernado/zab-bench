import lmstudio as lms
from typing import Dict, Callable

class Zab:
    def __init__(self, turns, name = "Cama", bim = "Red", pim = 1):
        self.turns = turns
        self.name = name
        self.bim = bim  # color string
        self.pim = pim  # nonzero integer
        self.history = []
        
    def state(self):
        return f"You are a zab named {self.name} with bim {self.bim} and pim {self.pim}."

    def call_function(self, func_name: str, *args) -> 'Zab':
        """Call a zab function and return new Zab instance"""
        if func_name in ZabFunctions.registry:
            # Store old state
            old_state = f"(name: {self.name}, bim: {self.bim}, pim: {self.pim})"
            
            # Create new zab
            new_zab = ZabFunctions.registry[func_name](self, *args)
            
            # Format function call
            if args:
                func_call = f"{func_name}({', '.join(str(arg) for arg in args)})"
            else:
                func_call = f"{func_name}()"
            
            # Store new state
            new_state = f"(name: {new_zab.name}, bim: {new_zab.bim}, pim: {new_zab.pim})"
            
            # Create history entry
            history_entry = f"{old_state} -> {func_call} -> {new_state}"
            
            # Copy history and add new entry
            new_zab.history = self.history + [history_entry]
            
            return new_zab
        raise ValueError(f"Unknown function: {func_name}")

class ZabFunctions:
    registry: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, name: str):
        def decorator(func):
            cls.registry[name] = func
            return func
        return decorator

@ZabFunctions.register("fin")
def fin(zab: Zab) -> Zab:
    return Zab(zab.turns, name=zab.name[::-1], bim=zab.bim, pim=zab.pim)

@ZabFunctions.register("tox")
def tox(zab: Zab) -> Zab:
    return Zab(zab.turns, name=zab.name, bim=zab.bim, pim=zab.pim * 2)

@ZabFunctions.register("sox")
def sox(zab: Zab) -> Zab:
    return Zab(zab.turns, name=zab.name, bim="Red", pim=zab.pim)

# Name-affecting functions
@ZabFunctions.register("bin")
def bin(zab: Zab) -> Zab:
    return Zab(zab.turns, name="bad name, please change me immediately!", bim=zab.bim, pim=zab.pim)

@ZabFunctions.register("stin")
def stin(zab: Zab, noun: str) -> Zab:
    # Use LLM for Spanish translation
    model = lms.llm("gemma-3-12b-it-qat")
    prompt = f"Translate the English noun '{noun}' to Spanish. Respond with only the Spanish word, no explanation."
    response = model.respond(prompt)
    spanish_translation = str(response).strip()
    return Zab(zab.turns, name=spanish_translation, bim=zab.bim, pim=zab.pim)

@ZabFunctions.register("hin")
def hin(zab: Zab, n: int) -> Zab:
    if n <= 0:
        raise ValueError("n must be positive")
    new_name = zab.name[:n]
    return Zab(zab.turns, name=new_name, bim=zab.bim, pim=zab.pim)

@ZabFunctions.register("min")
def min(zab: Zab, string: str) -> Zab:
    if not string:
        raise ValueError("string must be non-empty")
    new_name = string[1:] if len(string) > 1 else ""
    if not new_name:  # Ensure name is non-empty
        new_name = "unnamed"
    return Zab(zab.turns, name=new_name, bim=zab.bim, pim=zab.pim)

# Pim-affecting functions
@ZabFunctions.register("plox")
def plox(zab: Zab, n: int) -> Zab:
    if not (1 <= n <= 10):
        raise ValueError("n must be between 1 and 10")
    return Zab(zab.turns, name=zab.name, bim=zab.bim, pim=zab.pim + n)

@ZabFunctions.register("rox")
def rox(zab: Zab, shape: str) -> Zab:
    # Map common 2D shapes to their number of sides
    shape_sides = {
        "triangle": 3, "square": 4, "rectangle": 4, "rhombus": 4, "parallelogram": 4,
        "pentagon": 5, "hexagon": 6, "heptagon": 7, "octagon": 8, "nonagon": 9, "decagon": 10,
        "circle": 0, "ellipse": 0, "oval": 0
    }
    
    shape_lower = shape.lower()
    if shape_lower in shape_sides:
        sides = shape_sides[shape_lower]
    else:
        # Use LLM for unknown shapes
        model = lms.llm("gemma-3-12b-it-qat")
        prompt = f"How many sides does the 2D shape '{shape}' have? Respond with only a number."
        try:
            response = model.respond(prompt)
            sides = int(str(response).strip())
        except:
            sides = 0  # Default for unknown shapes
    
    return Zab(zab.turns, name=zab.name, bim=zab.bim, pim=zab.pim + sides)

# Bim-affecting functions
@ZabFunctions.register("vox")
def vox(zab: Zab, animal: str) -> Zab:
    # Use LLM to determine animal color
    model = lms.llm("gemma-3-12b-it-qat")
    valid_colors = ["Pink", "Crimson", "Brown", "Maroon", "Red", "Salmon", "Coral", "Chocolate", 
                   "Orange", "Gold", "Ivory", "Yellow", "Olive", "Chartreuse", "Lime", "Green", 
                   "Aquamarine", "Turquoise", "Azure", "Cyan", "Teal", "Navy", "Blue", "Lavender", 
                   "Indigo", "Plum", "Violet", "Magenta", "Purple", "Tan", "Beige", "White", 
                   "Silver", "Gray", "Black"]
    
    color_list = ", ".join(valid_colors)
    prompt = f"What color is most associated with a {animal}? Choose from this list: {color_list}. Respond with only the color name."
    
    response = model.respond(prompt)
    color = str(response).strip()
    # Ensure the color is in our valid list
    if color not in valid_colors:
        # Try to find a close match
        color_lower = color.lower()
        for valid_color in valid_colors:
            if valid_color.lower() == color_lower:
                color = valid_color
                break
        else:
            color = "Brown"  # Default fallback
    
    return Zab(zab.turns, name=zab.name, bim=color, pim=zab.pim)

@ZabFunctions.register("lox")
def lox(zab: Zab, color: str) -> Zab:
    # Use LLM to find intermediate color
    model = lms.llm("gemma-3-12b-it-qat")
    valid_colors = ["Pink", "Crimson", "Brown", "Maroon", "Red", "Salmon", "Coral", "Chocolate", 
                   "Orange", "Gold", "Ivory", "Yellow", "Olive", "Chartreuse", "Lime", "Green", 
                   "Aquamarine", "Turquoise", "Azure", "Cyan", "Teal", "Navy", "Blue", "Lavender", 
                   "Indigo", "Plum", "Violet", "Magenta", "Purple", "Tan", "Beige", "White", 
                   "Silver", "Gray", "Black"]
    
    color_list = ", ".join(valid_colors)
    prompt = f"What color would be between {zab.bim} and {color}? Choose from this list: {color_list}. Respond with only the color name."
    
    response = model.respond(prompt)
    intermediate_color = str(response).strip()
    # Ensure the color is in our valid list
    if intermediate_color not in valid_colors:
        intermediate_color = zab.bim  # Default to current color if invalid
    
    return Zab(zab.turns, name=zab.name, bim=intermediate_color, pim=zab.pim)

@ZabFunctions.register("mox")
def mox(zab: Zab, i: int) -> Zab:
    if not (1 <= i <= 7):
        raise ValueError("i must be between 1 and 7")
    
    roygbiv_colors = ["Red", "Orange", "Yellow", "Green", "Blue", "Indigo", "Violet"]
    color = roygbiv_colors[i - 1]
    return Zab(zab.turns, name=zab.name, bim=color, pim=zab.pim)

# Multi-quality functions
@ZabFunctions.register("hox")
def hox(zab: Zab) -> Zab:
    # According to spec: changes name to "Cama," bim to 0, pim to "Red"
    # But this seems inconsistent with the data types (bim should be color, pim should be nonzero int)
    # The spec might have an error, so interpreting as: name="Cama", bim="Red", pim=1
    return Zab(zab.turns, name="Cama", bim="Red", pim=1)

@ZabFunctions.register("box")
def box(zab: Zab, animal: str) -> Zab:
    # According to spec: changes bim to number of legs, pim to predominant color
    # But that's backwards - bim should be color, pim should be integer
    # Following the spec literally would be inconsistent, so interpreting as:
    # bim = predominant color, pim = number of legs
    model = lms.llm("gemma-3-12b-it-qat")
    
    # Get number of legs
    legs_prompt = f"How many legs does a {animal} have? Respond with only a number."
    try:
        response = model.respond(legs_prompt)
        legs = int(str(response).strip())
    except:
        legs = 4  # Default
    
    # Get predominant color
    valid_colors = ["Pink", "Crimson", "Brown", "Maroon", "Red", "Salmon", "Coral", "Chocolate", 
                   "Orange", "Gold", "Ivory", "Yellow", "Olive", "Chartreuse", "Lime", "Green", 
                   "Aquamarine", "Turquoise", "Azure", "Cyan", "Teal", "Navy", "Blue", "Lavender", 
                   "Indigo", "Plum", "Violet", "Magenta", "Purple", "Tan", "Beige", "White", 
                   "Silver", "Gray", "Black"]
    
    color_list = ", ".join(valid_colors)
    color_prompt = f"What is the predominant color of a {animal}? Choose from this list: {color_list}. Respond with only the color name."
    
    response = model.respond(color_prompt)
    color = str(response).strip()
    # Ensure the color is in our valid list
    if color not in valid_colors:
        color = "Brown"  # Default fallback
    
    return Zab(zab.turns, name=zab.name, bim=color, pim=legs)

# Quality-dependent functions would need special initialization logic
# For now, implementing basic versions that would need to be customized per zab instance

@ZabFunctions.register("vin")
def vin(zab: Zab) -> Zab:
    # This would normally depend on other text-based qualities
    # For now, using the name itself as a placeholder since it's the only text quality
    return Zab(zab.turns, name=zab.name, bim=zab.bim, pim=zab.pim)

@ZabFunctions.register("cin")
def cin(zab: Zab) -> Zab:
    # This would normally track previous name values
    # For now, reverting to default name as a placeholder
    return Zab(zab.turns, name="Cama", bim=zab.bim, pim=zab.pim)


if __name__ == "__main__":
    current_zab = Zab(turns=10)
    current_zab = current_zab.call_function("fin")
    current_zab = current_zab.call_function("tox")
    
    print("Testing basic functions:")
    for entry in current_zab.history:
        print(entry)
    
    print(f"\nFinal state: {current_zab.state()}")
    
    # Test a few more functions
    print("\nTesting additional functions:")
    current_zab = current_zab.call_function("bin")
    current_zab = current_zab.call_function("mox", 3)  # Yellow
    current_zab = current_zab.call_function("plox", 5)
    
    for entry in current_zab.history[-3:]:
        print(entry)