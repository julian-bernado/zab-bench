#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify, session
import os
import uuid
import threading
import time
from io import StringIO
import sys
from contextlib import redirect_stdout, redirect_stderr
from zab_game_oai import ZabGameOAI

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Store game sessions
game_sessions = {}

class GameOutputCapture:
    """Capture game output for web display"""
    def __init__(self):
        self.turns = []  # List of turn objects
        self.current_turn_index = 0
        self.game_state = {}
        self.is_complete = False
        self.is_paused = False
        self.final_analysis = None
        
    def start_new_turn(self, turn_number, total_turns):
        """Start a new turn"""
        turn_data = {
            'turn_number': turn_number,
            'total_turns': total_turns,
            'steps': [],
            'initial_state': None,
            'final_state': None,
            'action_taken': None,
            'llm_response': None,
            'is_complete': False
        }
        self.turns.append(turn_data)
        self.current_turn_index = len(self.turns) - 1
        
    def add_step(self, text, step_type="info", data=None):
        """Add a step to the current turn"""
        if not self.turns:
            return
            
        current_turn = self.turns[-1]
        step = {
            'text': text,
            'type': step_type,
            'timestamp': time.time(),
            'data': data or {}
        }
        current_turn['steps'].append(step)
        
        # Update specific turn data based on step type
        if step_type == "initial_state":
            current_turn['initial_state'] = data
        elif step_type == "final_state":
            current_turn['final_state'] = data
        elif step_type == "llm_response":
            current_turn['llm_response'] = text
        elif step_type == "action_result":
            current_turn['action_taken'] = text
            
    def complete_current_turn(self):
        """Mark the current turn as complete"""
        if self.turns:
            self.turns[-1]['is_complete'] = True
            
    def set_final_analysis(self, analysis):
        """Set the final analysis"""
        self.final_analysis = analysis

class WebZabGame(ZabGameOAI):
    """Modified ZabGame for web interface"""
    
    def __init__(self, total_turns=10, model_name="gpt-4.1-mini", api_key=None, output_capture=None):
        self.output_capture = output_capture or GameOutputCapture()
        super().__init__(total_turns, model_name, api_key)
        
    def log_output(self, text, output_type="info", data=None):
        """Log output to capture"""
        if self.output_capture:
            self.output_capture.add_step(text, output_type, data)
            
    def play_turn(self):
        """Play a single turn with web-friendly output"""
        self.output_capture.start_new_turn(self.current_turn + 1, self.total_turns)
        
        # Log initial state
        initial_state = {
            'name': self.current_zab.name,
            'bim': self.current_zab.bim,
            'pim': self.current_zab.pim
        }
        self.log_output(f"TURN {self.current_turn + 1}/{self.total_turns}", "turn_header")
        self.log_output(f"Current state: {self.current_zab.state()}", "initial_state", initial_state)
        
        prompt = self.create_prompt()
        self.log_output("Sending prompt to LLM...", "info")
        
        response = self.get_llm_response(prompt)
        self.log_output(response, "llm_response")
        
        func_name, args = self.parse_action(response)
        
        if func_name:
            success, message = self.execute_action(func_name, args)
            self.log_output(message, "action_result" if success else "error")
            if success:
                final_state = {
                    'name': self.current_zab.name,
                    'bim': self.current_zab.bim,
                    'pim': self.current_zab.pim
                }
                self.log_output(f"New state: {self.current_zab.state()}", "final_state", final_state)
        else:
            self.log_output("No valid action found in response. Skipping turn.", "warning")
        
        self.current_turn += 1
        
        # Update game state for web display
        self.output_capture.game_state = {
            'name': self.current_zab.name,
            'bim': self.current_zab.bim,
            'pim': self.current_zab.pim,
            'turn': self.current_turn,
            'total_turns': self.total_turns,
            'selected_functions': self.selected_functions,
            'scratchpad': self.scratchpad,
            'history': self.current_zab.history
        }
        
        self.output_capture.complete_current_turn()
        
        # Pause for readability if not in fast mode
        if not getattr(self.output_capture, 'fast_mode', False):
            time.sleep(2)  # 2 second pause between turns
        
    def play_game(self):
        """Play the complete game with web-friendly output"""
        self.log_output("Starting Zab Game with OpenAI!", "game_start")
        self.log_output(f"Model: {self.model_name}", "info")
        self.log_output(f"Initial state: {self.current_zab.state()}", "info")
        self.log_output(f"Available functions: {self.selected_functions}", "info")
        
        # Play all turns
        while self.current_turn < self.total_turns:
            self.play_turn()
        
        # Final analysis
        self.log_output("GAME COMPLETE - FINAL ANALYSIS", "game_complete")
        
        final_prompt = f"""The game is now complete! Based on your {self.total_turns} turns of experimentation, please provide your final analysis.

Your final state: {self.current_zab.state()}

Your complete history:
{chr(10).join(self.current_zab.history) if self.current_zab.history else "No actions were successfully executed."}

Your final scratchpad:
{self.scratchpad}

Now, please provide your best guess for what each of the three functions does:
{chr(10).join([f"- {func}:" for func in self.selected_functions])}

Be specific about how each function affects your name, bim, and pim values."""
        
        self.log_output("Requesting final analysis from LLM...", "info")
        final_response = self.get_llm_response(final_prompt)
        
        # Show actual function effects
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
        
        actual_effects_text = "\n".join([f"- {func}: {actual_effects[func]}" for func in self.selected_functions])
        
        # Set final analysis data
        self.output_capture.set_final_analysis({
            'llm_analysis': final_response,
            'actual_effects': actual_effects_text,
            'selected_functions': self.selected_functions,
            'final_state': {
                'name': self.current_zab.name,
                'bim': self.current_zab.bim,
                'pim': self.current_zab.pim
            }
        })
        
        self.output_capture.is_complete = True

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    """Start a new game"""
    data = request.json
    model_name = data.get('model_name', 'gpt-4.1-mini')
    total_turns = data.get('total_turns', 10)
    api_key = data.get('api_key', None)
    
    # Create new game session
    session_id = str(uuid.uuid4())
    session['game_id'] = session_id
    
    try:
        output_capture = GameOutputCapture()
        game = WebZabGame(total_turns=total_turns, model_name=model_name, api_key=api_key, output_capture=output_capture)
        
        game_sessions[session_id] = {
            'game': game,
            'output_capture': output_capture,
            'thread': None
        }
        
        # Start game in background thread
        def run_game():
            try:
                game.play_game()
            except Exception as e:
                game.log_output(f"Error: {str(e)}", "error")
        
        thread = threading.Thread(target=run_game)
        game_sessions[session_id]['thread'] = thread
        thread.start()
        
        return jsonify({'success': True, 'session_id': session_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/game_status')
def game_status():
    """Get current game status"""
    session_id = session.get('game_id')
    if not session_id or session_id not in game_sessions:
        return jsonify({'error': 'No active game session'})
    
    game_session = game_sessions[session_id]
    output_capture = game_session['output_capture']
    
    return jsonify({
        'turns': output_capture.turns,
        'game_state': output_capture.game_state,
        'is_complete': output_capture.is_complete,
        'final_analysis': output_capture.final_analysis,
        'total_turns': len(output_capture.turns)
    })

@app.route('/set_pause', methods=['POST'])
def set_pause():
    """Pause or unpause the game"""
    session_id = session.get('game_id')
    if not session_id or session_id not in game_sessions:
        return jsonify({'error': 'No active game session'})
    
    data = request.json
    is_paused = data.get('paused', False)
    
    game_session = game_sessions[session_id]
    output_capture = game_session['output_capture']
    output_capture.is_paused = is_paused
    
    return jsonify({'success': True, 'paused': is_paused})

@app.route('/templates/index.html')
def serve_template():
    """Serve the HTML template directly for debugging"""
    return render_template('index.html')

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create the HTML template
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zab Game Interface</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: #667eea;
            color: white;
            padding: 20px;
            text-align: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2em;
        }
        
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        
        .content {
            padding: 20px;
        }
        
        .game-setup {
            max-width: 600px;
            margin: 0 auto;
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }
        
        input, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-right: 10px;
        }
        
        .btn:hover {
            background: #5a6fd8;
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .game-display {
            display: none;
        }
        
        .game-controls {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .turn-navigation {
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .turn-selector {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .game-content {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
        }
        
        @media (max-width: 900px) {
            .game-content {
                grid-template-columns: 1fr;
            }
        }
        
        .sidebar {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }
        
        .main-content {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            min-height: 500px;
        }
        
        .game-state {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .state-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }
        
        .state-item:last-child {
            border-bottom: none;
        }
        
        .state-label {
            font-weight: 600;
            color: #555;
        }
        
        .state-value {
            color: #667eea;
            font-weight: bold;
        }
        
        .functions-list {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .function-item {
            background: #f8f9fa;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 5px;
            font-family: monospace;
            border-left: 3px solid #667eea;
            font-size: 14px;
        }
        
        .turn-list {
            background: white;
            padding: 15px;
            border-radius: 8px;
        }
        
        .turn-item {
            background: #f8f9fa;
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 4px solid #ddd;
        }
        
        .turn-item:hover {
            background: #e9ecef;
        }
        
        .turn-item.active {
            background: #e8f4fd;
            border-left-color: #667eea;
        }
        
        .turn-item.completed {
            border-left-color: #28a745;
        }
        
        .turn-content {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .turn-header {
            background: #667eea;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .step-section {
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ddd;
        }
        
        .step-section h4 {
            margin-top: 0;
            margin-bottom: 10px;
            color: #333;
        }
        
        .initial_state {
            background: #e8f4fd;
            border-left-color: #667eea;
        }
        
        .llm_response {
            background: #fff3cd;
            border-left-color: #ffc107;
        }
        
        .action_result {
            background: #d4edda;
            border-left-color: #28a745;
        }
        
        .error {
            background: #f8d7da;
            border-left-color: #dc3545;
        }
        
        .warning {
            background: #fff3cd;
            border-left-color: #ffc107;
        }
        
        .final_state {
            background: #d1ecf1;
            border-left-color: #17a2b8;
        }
        
        .response-text {
            white-space: pre-wrap;
            font-family: inherit;
            line-height: 1.6;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .analysis-section {
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ddd;
        }
        
        .llm-analysis {
            background: #e8f4fd;
            border-left-color: #667eea;
        }
        
        .actual-effects {
            background: #f8d7da;
            border-left-color: #dc3545;
        }
        
        .progress-indicator {
            width: 100%;
            height: 8px;
            background: #e1e5e9;
            border-radius: 4px;
            margin: 10px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: #667eea;
            transition: width 0.3s ease;
        }
        
        .empty-state {
            text-align: center;
            color: #666;
            padding: 40px;
        }
        
        .keyboard-help {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Zab Game Interface</h1>
            <p>Watch an AI solve the Zab puzzle step by step</p>
        </div>
        
        <div class="content">
            <div id="game-setup" class="game-setup">
                <h2>Game Configuration</h2>
                <div class="form-group">
                    <label for="model-select">OpenAI Model:</label>
                    <select id="model-select">
                        <option value="gpt-4.1">GPT-4.1</option>
                        <option value="gpt-4.1-mini">GPT-4.1 Mini</option>
                        <option value="gpt-4.1-nano">GPT-4.1 Nano</option>
                        <option value="gpt-4.5-preview">GPT-4.5 Preview</option>
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="o1">o1</option>
                        <option value="o3">o3</option>
                        <option value="o4-mini">o4-mini</option>
                        <option value="o3-mini">o3-mini</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="turns-input">Number of Turns:</label>
                    <input type="number" id="turns-input" value="10" min="1" max="20">
                </div>
                <div class="form-group">
                    <label for="api-key-input">OpenAI API Key (optional, uses environment variable if not provided):</label>
                    <input type="password" id="api-key-input" placeholder="sk-...">
                </div>
                <button id="start-btn" class="btn">Start Game</button>
            </div>
            
            <div id="game-display" class="game-display">
                <div class="game-controls">
                    <div class="turn-navigation">
                        <button id="prev-turn" class="btn btn-secondary">← Previous</button>
                        <div class="turn-selector">
                            <span>Turn:</span>
                            <select id="turn-select">
                                <option value="-1">Game Start</option>
                            </select>
                        </div>
                        <button id="next-turn" class="btn btn-secondary">Next →</button>
                        <button id="auto-play" class="btn btn-secondary">Auto Play</button>
                    </div>
                    <div>
                        <span id="game-status">Ready</span>
                        <div class="keyboard-help">💡 Use ← → arrow keys or Space for auto-play</div>
                    </div>
                </div>
                
                <div class="game-content">
                    <div class="sidebar">
                        <div class="game-state">
                            <h3>Current State</h3>
                            <div class="progress-indicator">
                                <div id="progress-fill" class="progress-fill" style="width: 0%"></div>
                            </div>
                            <div class="state-item">
                                <span class="state-label">Name:</span>
                                <span id="current-name" class="state-value">-</span>
                            </div>
                            <div class="state-item">
                                <span class="state-label">Bim:</span>
                                <span id="current-bim" class="state-value">-</span>
                            </div>
                            <div class="state-item">
                                <span class="state-label">Pim:</span>
                                <span id="current-pim" class="state-value">-</span>
                            </div>
                            <div class="state-item">
                                <span class="state-label">Turn:</span>
                                <span id="current-turn" class="state-value">0/0</span>
                            </div>
                        </div>
                        
                        <div id="functions-display" class="functions-list">
                            <h4>Available Functions:</h4>
                            <div id="functions-list">
                                <div style="color: #666; font-style: italic;">Game starting...</div>
                            </div>
                        </div>
                        
                        <div class="turn-list">
                            <h4>Game Progress</h4>
                            <div id="turn-list-items"></div>
                        </div>
                    </div>
                    
                    <div class="main-content">
                        <div id="turn-content">
                            <div class="empty-state">
                                <h3>Welcome to the Zab Game!</h3>
                                <p>The game will start automatically once you begin.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let gameData = null;
        let currentTurnIndex = -1;
        let gameInterval = null;
        let autoPlayMode = false;
        
        document.getElementById('start-btn').addEventListener('click', startGame);
        document.getElementById('prev-turn').addEventListener('click', () => {
            if (currentTurnIndex === 'final') {
                navigateToTurn(gameData.turns.length - 1);
            } else {
                navigateToTurn(currentTurnIndex - 1);
            }
        });
        
        document.getElementById('next-turn').addEventListener('click', () => {
            if (gameData.is_complete && currentTurnIndex === gameData.turns.length - 1) {
                navigateToTurn('final');
            } else {
                navigateToTurn(currentTurnIndex + 1);
            }
        });
        document.getElementById('turn-select').addEventListener('change', (e) => {
            const value = e.target.value;
            if (value === 'final') {
                navigateToTurn('final');
            } else {
                navigateToTurn(parseInt(value));
            }
        });
        document.getElementById('auto-play').addEventListener('click', toggleAutoPlay);
        
        // Add keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!gameData) return;
            
            // Only handle keys when not typing in input fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
            
            switch(e.key) {
                case 'ArrowLeft':
                case 'ArrowUp':
                    e.preventDefault();
                    if (currentTurnIndex === 'final') {
                        navigateToTurn(gameData.turns.length - 1);
                    } else if (currentTurnIndex > -1) {
                        navigateToTurn(currentTurnIndex - 1);
                    }
                    break;
                case 'ArrowRight':
                case 'ArrowDown':
                    e.preventDefault();
                    if (gameData.is_complete && currentTurnIndex === gameData.turns.length - 1) {
                        navigateToTurn('final');
                    } else if (currentTurnIndex < gameData.turns.length - 1) {
                        navigateToTurn(currentTurnIndex + 1);
                    }
                    break;
                case 'Home':
                    e.preventDefault();
                    navigateToTurn(-1);
                    break;
                case 'End':
                    e.preventDefault();
                    if (gameData.is_complete && gameData.final_analysis) {
                        navigateToTurn('final');
                    } else if (gameData.turns.length > 0) {
                        navigateToTurn(gameData.turns.length - 1);
                    }
                    break;
                case ' ':
                    e.preventDefault();
                    toggleAutoPlay();
                    break;
            }
        });
        
        async function startGame() {
            const model = document.getElementById('model-select').value;
            const turns = parseInt(document.getElementById('turns-input').value);
            const apiKey = document.getElementById('api-key-input').value;
            
            const startBtn = document.getElementById('start-btn');
            startBtn.disabled = true;
            startBtn.textContent = 'Starting Game...';
            
            try {
                const response = await fetch('/start_game', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        model_name: model,
                        total_turns: turns,
                        api_key: apiKey || null
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('game-setup').style.display = 'none';
                    document.getElementById('game-display').style.display = 'block';
                    
                    // Start polling for game updates
                    gameInterval = setInterval(updateGameStatus, 1000);
                } else {
                    alert('Error starting game: ' + result.error);
                    startBtn.disabled = false;
                    startBtn.textContent = 'Start Game';
                }
            } catch (error) {
                alert('Error: ' + error.message);
                startBtn.disabled = false;
                startBtn.textContent = 'Start Game';
            }
        }
        
        async function updateGameStatus() {
            try {
                const response = await fetch('/game_status');
                const data = await response.json();
                
                if (data.error) {
                    console.error('Game status error:', data.error);
                    return;
                }
                
                gameData = data;
                updateGameDisplay();
                
                // Auto-advance to latest turn if in auto-play mode (but not if user is manually navigating)
                if (autoPlayMode && data.turns && data.turns.length > currentTurnIndex + 1 && 
                    (currentTurnIndex === -1 || currentTurnIndex === data.turns.length - 2)) {
                    navigateToTurn(data.turns.length - 1);
                }
                
                // Stop polling if game is complete
                if (data.is_complete) {
                    clearInterval(gameInterval);
                    gameInterval = null;
                    document.getElementById('game-status').textContent = 'Complete';
                    
                    // Disable auto-play when complete
                    if (autoPlayMode) {
                        toggleAutoPlay();
                    }
                    
                    // Add final analysis option to turn selector
                    const turnSelect = document.getElementById('turn-select');
                    if (!document.querySelector('option[value="final"]')) {
                        const finalOption = document.createElement('option');
                        finalOption.value = 'final';
                        finalOption.textContent = 'Final Analysis';
                        turnSelect.appendChild(finalOption);
                    }
                    
                    // Show final analysis if available and not already viewing a specific turn
                    if (data.final_analysis && (currentTurnIndex === -1 || currentTurnIndex >= data.turns.length - 1)) {
                        // Show a notification that final analysis is ready
                        const statusElement = document.getElementById('game-status');
                        statusElement.innerHTML = 'Complete - <span style="color: #28a745; font-weight: bold;">Final Analysis Ready!</span>';
                        
                        // Only auto-navigate if in auto-play mode
                        if (autoPlayMode) {
                            navigateToTurn('final');
                        }
                    }
                }
                
            } catch (error) {
                console.error('Error updating game status:', error);
            }
        }
        
        function updateGameDisplay() {
            if (!gameData) return;
            
            // Update turn selector
            const turnSelect = document.getElementById('turn-select');
            const currentOptions = turnSelect.children.length - 1; // -1 for "Game Start"
            const newTurns = gameData.turns.length;
            
            if (newTurns > currentOptions) {
                for (let i = currentOptions; i < newTurns; i++) {
                    const option = document.createElement('option');
                    option.value = i;
                    option.textContent = `Turn ${i + 1}`;
                    turnSelect.appendChild(option);
                }
            }
            
            // Update turn list
            updateTurnList();
            
            // Update game state if available
            if (gameData.game_state) {
                updateGameState(gameData.game_state);
            }
        }
        
        function updateTurnList() {
            const turnListItems = document.getElementById('turn-list-items');
            turnListItems.innerHTML = '';
            
            // Add game start item
            const startItem = document.createElement('div');
            startItem.className = 'turn-item' + (currentTurnIndex === -1 ? ' active' : '');
            startItem.innerHTML = '<strong>Game Start</strong>';
            startItem.onclick = () => navigateToTurn(-1);
            turnListItems.appendChild(startItem);
            
            // Add turn items
            if (gameData.turns) {
                gameData.turns.forEach((turn, index) => {
                    const turnItem = document.createElement('div');
                    turnItem.className = 'turn-item' + 
                        (index === currentTurnIndex ? ' active' : '') +
                        (turn.is_complete ? ' completed' : '');
                    turnItem.innerHTML = `<strong>Turn ${turn.turn_number}</strong><br><small>${turn.is_complete ? 'Complete' : 'In Progress'}</small>`;
                    turnItem.onclick = () => navigateToTurn(index);
                    turnListItems.appendChild(turnItem);
                });
            }
            
            // Add final analysis item if game is complete
            if (gameData.is_complete && gameData.final_analysis) {
                const finalItem = document.createElement('div');
                finalItem.className = 'turn-item' + (currentTurnIndex === 'final' ? ' active' : '') + ' completed';
                finalItem.innerHTML = '<strong>🎯 Final Analysis</strong><br><small>Complete</small>';
                finalItem.onclick = () => navigateToTurn('final');
                finalItem.style.borderLeftColor = '#28a745';
                finalItem.style.background = currentTurnIndex === 'final' ? '#e8f4fd' : '#f0fff0';
                turnListItems.appendChild(finalItem);
            }
        }
        
        function updateGameState(state) {
            document.getElementById('current-name').textContent = state.name || '-';
            document.getElementById('current-bim').textContent = state.bim || '-';
            document.getElementById('current-pim').textContent = state.pim || '-';
            document.getElementById('current-turn').textContent = `${state.turn || 0}/${state.total_turns || 0}`;
            
            // Update progress bar
            const progress = ((state.turn || 0) / (state.total_turns || 1)) * 100;
            document.getElementById('progress-fill').style.width = progress + '%';
            
            // Update functions if available
            const functionsList = document.getElementById('functions-list');
            if (state.selected_functions && state.selected_functions.length > 0) {
                functionsList.innerHTML = state.selected_functions.map(func => 
                    `<div class="function-item">${func}</div>`
                ).join('');
            }
        }
        
        function navigateToTurn(turnIndex) {
            if (!gameData) return;
            
            currentTurnIndex = turnIndex;
            
            // Handle special case for final analysis
            if (turnIndex === 'final') {
                document.getElementById('prev-turn').disabled = false;
                document.getElementById('next-turn').disabled = true;
                document.getElementById('turn-select').value = 'final';
                updateTurnList();
                if (gameData.final_analysis) {
                    showFinalAnalysis(gameData.final_analysis);
                }
                return;
            }
            
            // Convert back to number if it's a string
            turnIndex = parseInt(turnIndex);
            currentTurnIndex = turnIndex;
            
            // Update navigation buttons
            document.getElementById('prev-turn').disabled = turnIndex <= -1;
            document.getElementById('next-turn').disabled = !gameData.turns || 
                (turnIndex >= gameData.turns.length - 1 && !gameData.is_complete);
            
            // If game is complete and we're at the last turn, enable next to go to final analysis
            if (gameData.is_complete && turnIndex === gameData.turns.length - 1) {
                document.getElementById('next-turn').disabled = false;
            }
            
            // Update turn selector
            document.getElementById('turn-select').value = turnIndex;
            
            // Update turn list highlighting
            updateTurnList();
            
            // Show turn content
            showTurnContent(turnIndex);
        }
        
        function showTurnContent(turnIndex) {
            const contentDiv = document.getElementById('turn-content');
            
            if (turnIndex === -1) {
                // Show game start
                contentDiv.innerHTML = `
                    <div class="turn-content">
                        <div class="turn-header">🎮 Game Starting</div>
                        <div class="step-section">
                            <h4>Welcome to the Zab Game!</h4>
                            <p>The AI will now attempt to figure out what the three randomly selected functions do by experimenting with them over multiple turns.</p>
                            <p><strong>Goal:</strong> Understand the effects of each function on the Zab's name, bim, and pim values.</p>
                            ${gameData.game_state ? `
                                <div class="response-text">
                                    Initial State: ${gameData.game_state.name || 'Unknown'} (${gameData.game_state.bim || 'Unknown'}, ${gameData.game_state.pim || 'Unknown'})
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
                return;
            }
            
            if (!gameData.turns || turnIndex >= gameData.turns.length) {
                contentDiv.innerHTML = '<div class="empty-state"><h3>Turn not available yet</h3></div>';
                return;
            }
            
            const turn = gameData.turns[turnIndex];
            let html = `
                <div class="turn-content">
                    <div class="turn-header">Turn ${turn.turn_number} of ${turn.total_turns}</div>
            `;
            
            // Show steps
            turn.steps.forEach(step => {
                if (step.type === 'turn_header') return; // Skip turn header
                
                let title = '';
                switch (step.type) {
                    case 'initial_state':
                        title = '📊 Initial State';
                        break;
                    case 'llm_response':
                        title = '🤖 AI Response';
                        break;
                    case 'action_result':
                        title = '⚡ Action Result';
                        break;
                    case 'final_state':
                        title = '📈 Final State';
                        break;
                    case 'error':
                        title = '❌ Error';
                        break;
                    case 'warning':
                        title = '⚠️ Warning';
                        break;
                    default:
                        title = '💡 ' + step.type.replace('_', ' ').toUpperCase();
                }
                
                html += `
                    <div class="step-section ${step.type}">
                        <h4>${title}</h4>
                        <div class="response-text">${step.text}</div>
                    </div>
                `;
            });
            
            html += '</div>';
            contentDiv.innerHTML = html;
        }
        
        function showFinalAnalysis(analysis) {
            const contentDiv = document.getElementById('turn-content');
            
            let html = `
                <div class="turn-content">
                    <div class="turn-header">🎯 Final Analysis - Game Complete!</div>
                    
                    <div class="analysis-section llm-analysis">
                        <h4>🤖 AI's Final Analysis</h4>
                        <p><em>What the AI thinks each function does after ${gameData.turns ? gameData.turns.length : 0} turns of experimentation:</em></p>
                        <div class="response-text">${analysis.llm_analysis}</div>
                    </div>
                    
                    <div class="analysis-section actual-effects">
                        <h4>✅ Actual Function Effects (The Truth Revealed)</h4>
                        <p><em>Here's what each function actually does:</em></p>
                        <div class="response-text">${analysis.actual_effects}</div>
                    </div>
                    
                    <div class="analysis-section">
                        <h4>📊 Final Game State</h4>
                        <div class="response-text">Name: ${analysis.final_state.name}
Bim: ${analysis.final_state.bim}
Pim: ${analysis.final_state.pim}</div>
                    </div>
                    
                    <div class="analysis-section" style="background: #f8f9fa; border-left-color: #6c757d;">
                        <h4>🎮 Game Summary</h4>
                        <p>The AI had ${gameData.turns ? gameData.turns.length : 0} turns to figure out what the functions <strong>${analysis.selected_functions.join(', ')}</strong> do.</p>
                        <p>Compare the AI's guesses above with the actual effects to see how well it did!</p>
                        <p><em>Use the navigation buttons to review any turn in detail.</em></p>
                    </div>
                </div>
            `;
            
            contentDiv.innerHTML = html;
        }
        
        function toggleAutoPlay() {
            autoPlayMode = !autoPlayMode;
            const btn = document.getElementById('auto-play');
            btn.textContent = autoPlayMode ? 'Pause Auto' : 'Auto Play';
            btn.style.background = autoPlayMode ? '#dc3545' : '#6c757d';
        }
    </script>
</body>
</html>'''
    
    with open('templates/index.html', 'w') as f:
        f.write(html_template)
    
    print("Starting Flask web server...")
    print("Open your browser to http://localhost:5000")
    app.run(debug=True, port=5000)
