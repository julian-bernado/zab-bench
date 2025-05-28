#!/usr/bin/env python3

import openai
import random
import re
from zab import Zab, ZabFunctions
import os

class ZabGameOAI:
    def __init__(self, total_turns=10, model_name="gpt-4o-mini", api_key=None):
        self.total_turns = total_turns
        self.model_name = model_name
        
        # Set up OpenAI client
        if api_key:
            openai.api_key = api_key
        elif os.getenv("OPENAI_API_KEY"):
            openai.api_key = os.getenv("OPENAI_API_KEY")
        else:
            raise ValueError("OpenAI API key must be provided or set in OPENAI_API_KEY environment variable")
        
        self.client = openai.OpenAI()
        
        # Available functions for the game (subset of all functions)
        available_functions = ["fin", "rox", "lox"]
        
        # Randomly select 3 functions for this game
        self.selected_functions = random.sample(available_functions, 3)
        print(f"Selected functions for this game: {self.selected_functions}")
        
        # Create function descriptions (intentionally vague to make it a puzzle)
        self.function_descriptions = {
            "fin": "Fin - Takes no parameters\n      - Example: Fin()",
            "bin": "Bin - Takes no parameters\n      - Example: Bin()",
            "stin": "Stin - Takes a single noun\n      - Example: Stin(\"cat\")",
            "hin": "Hin - Takes a positive integer\n      - Example: Hin(3)",
            "min": "Min - Takes a single word\n      - Example: Min(\"hello\")",
            "tox": "Tox - Takes no parameters\n      - Example: Tox()",
            "plox": "Plox - Takes a number from 1-10\n      - Example: Plox(4)",
            "rox": "Rox - Takes the name of a 2D shape\n      - Example: Rox(\"triangle\")",
            "sox": "Sox - Takes no parameters\n      - Example: Sox()",
            "vox": "Vox - Takes the name of an animal\n      - Example: Vox(\"elephant\")",
            "lox": "Lox - Takes the name of a color\n      - Example: Lox(\"blue\")",
            "mox": "Mox - Takes a number from 1-7\n      - Example: Mox(3)",
            "hox": "Hox - Takes no parameters\n      - Example: Hox()",
            "box": "Box - Takes the name of an animal\n      - Example: Box(\"spider\")"
        }
        
        # Initialize zab and game state
        self.current_zab = Zab(turns=total_turns)
        self.current_turn = 0
        self.scratchpad = ""
        
    def get_function_descriptions(self):
        """Get descriptions for the selected functions"""
        descriptions = []
        for func in self.selected_functions:
            descriptions.append(f"    - {self.function_descriptions[func]}")
        return "\n".join(descriptions)
    
    def create_prompt(self):
        """Create the prompt for the current turn"""
        history_text = ""
        if self.current_zab.history:
            history_text = "\n".join(self.current_zab.history)
        else:
            history_text = "No actions taken yet."
            
        additional_context = ""
        if self.current_turn > 0:
            additional_context = f"\n    \nYour history (the actions you've taken already):\n{history_text}"
        
        prompt = f"""You are a Zab.
As a Zab, you have three qualities: your name is "{self.current_zab.name}", your bim is "{self.current_zab.bim}", and your pim is "{self.current_zab.pim}".
You have access to the following actions:
{self.get_function_descriptions()}

This is turn {self.current_turn + 1}/{self.total_turns}.

You can include private notes in a scratchpad by wrapping them with <scratch></scratch> tags. This information will be preserved across turns.

Your scratchpad:
{self.scratchpad}

Your goal is to figure out what all the functions do over the course of your turns. At the end, you'll be prompted to make a guess as to what each function does. It is helpful to use your <scratch></scratch> functionality to include working theories so they can be tested later.
Submit an action after describing your current working theory for what the functions do as well as what your goal is. Include notes you'd like to pass into the future with the <scratch></scratch> tags{additional_context}"""
        
        return prompt
    
    def get_llm_response(self, prompt):
        """Get response from OpenAI API"""
        try:
            # Prepare API call parameters
            api_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "You are playing a puzzle game called Zab. Follow the instructions carefully and make one function call per turn."},
                    {"role": "user", "content": prompt}
                ]
            }
            
            # Handle model-specific parameters
            if self.model_name.startswith('o'):
                # o-series models (o1, o3, o3-mini, etc.) don't support temperature
                api_params["max_completion_tokens"] = 1000
            else:
                # Other models support temperature and use max_tokens
                api_params["temperature"] = 0.7
                api_params["max_tokens"] = 1000
            
            response = self.client.chat.completions.create(**api_params)
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return "Error: Could not get response from OpenAI API"
    
    def parse_action(self, response):
        """Parse the LLM's response to extract the action and update scratchpad"""
        # Extract scratchpad content
        scratch_match = re.search(r'<scratch>(.*?)</scratch>', response, re.DOTALL)
        if scratch_match:
            self.scratchpad = scratch_match.group(1).strip()
        
        # Remove scratchpad content from response before parsing for actions
        response_without_scratch = re.sub(r'<scratch>.*?</scratch>', '', response, flags=re.DOTALL)
        
        # Extract action - look for function calls (find last occurrence)
        action_patterns = [
            r'(\w+)\s*\(\s*([^)]*)\s*\)',  # Function(arg) format
            r'(\w+)\s*\(\s*\)',            # Function() format
        ]
        
        last_valid_action = None, None
        
        for pattern in action_patterns:
            matches = re.findall(pattern, response_without_scratch, re.IGNORECASE)
            for match in matches:
                func_name = match[0].lower()
                if func_name in [f.lower() for f in self.selected_functions]:
                    # Found a valid function call - store it (last one will be kept)
                    if len(match) == 2 and match[1]:
                        # Has arguments
                        arg_str = match[1].strip().strip('"\'')
                        # Try to parse as int, otherwise treat as string
                        try:
                            arg = int(arg_str)
                        except ValueError:
                            arg = arg_str
                        last_valid_action = func_name, [arg]
                    else:
                        # No arguments
                        last_valid_action = func_name, []
        
        return last_valid_action
    
    def execute_action(self, func_name, args):
        """Execute the parsed action"""
        try:
            # Map to correct case
            correct_func_name = None
            for f in self.selected_functions:
                if f.lower() == func_name.lower():
                    correct_func_name = f
                    break
            
            if correct_func_name:
                self.current_zab = self.current_zab.call_function(correct_func_name, *args)
                return True, f"Action executed: {correct_func_name}({', '.join(map(str, args)) if args else ''})"
            else:
                return False, f"Function '{func_name}' is not available in this game."
        except Exception as e:
            return False, f"Error executing action: {str(e)}"
    
    def play_turn(self):
        """Play a single turn"""
        print(f"\n{'='*50}")
        print(f"TURN {self.current_turn + 1}/{self.total_turns}")
        print(f"Current state: {self.current_zab.state()}")
        print(f"{'='*50}")
        
        prompt = self.create_prompt()
        print(f"\nPrompt sent to LLM:\n{prompt}\n")
        
        response = self.get_llm_response(prompt)
        print(f"LLM Response:\n{response}\n")
        
        func_name, args = self.parse_action(response)
        
        if func_name:
            success, message = self.execute_action(func_name, args)
            print(f"Action result: {message}")
            if success:
                print(f"New state: {self.current_zab.state()}")
        else:
            print("No valid action found in response. Skipping turn.")
        
        self.current_turn += 1
        
    def play_game(self):
        """Play the complete game"""
        print("Starting Zab Game with OpenAI!")
        print(f"Model: {self.model_name}")
        print(f"Initial state: {self.current_zab.state()}")
        print(f"Available functions: {self.selected_functions}")
        
        # Play all turns
        while self.current_turn < self.total_turns:
            self.play_turn()
        
        # Final analysis prompt
        print(f"\n{'='*50}")
        print("GAME COMPLETE - FINAL ANALYSIS")
        print(f"{'='*50}")
        
        final_prompt = f"""The game is now complete! Based on your {self.total_turns} turns of experimentation, please provide your final analysis.

Your final state: {self.current_zab.state()}

Your complete history:
{chr(10).join(self.current_zab.history) if self.current_zab.history else "No actions were successfully executed."}

Your final scratchpad:
{self.scratchpad}

Now, please provide your best guess for what each of the three functions does:
{chr(10).join([f"- {func}:" for func in self.selected_functions])}

Be specific about how each function affects your name, bim, and pim values."""
        
        print(f"Final analysis prompt:\n{final_prompt}\n")
        
        final_response = self.get_llm_response(final_prompt)
        print(f"LLM's final analysis:\n{final_response}")
        
        # Show actual function effects
        print(f"\n{'='*50}")
        print("ACTUAL FUNCTION EFFECTS (for comparison)")
        print(f"{'='*50}")
        
        actual_effects = {
            "fin": "Reverses the name",
            "bin": "Changes name to 'bad name, please change me immediately!'",
            "stin": "Changes name to Spanish translation of the input noun",
            "hin": "Keeps first N characters of the name",
            "min": "Changes name to input string without its first character",
            "tox": "Doubles the pim value",
            "plox": "Adds the input number (1-10) to pim",
            "rox": "Adds the number of sides of the shape to pim",
            "sox": "Changes bim to 'Red'",
            "vox": "Changes bim to color associated with the input animal",
            "lox": "Changes bim to intermediate color between current bim and input color",
            "mox": "Changes bim to ROYGBIV color at position N (1-7)",
            "hox": "Resets to name='Cama', bim='Red', pim=1",
            "box": "Changes bim to animal's color, pim to animal's leg count"
        }
        
        for func in self.selected_functions:
            print(f"- {func}: {actual_effects[func]}")

def main():
    """Run a single game"""
    # You can specify model and API key here
    game = ZabGameOAI(total_turns=10, model_name="gpt-4.1")
    game.play_game()

if __name__ == "__main__":
    main()