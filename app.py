from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
import chess
from chess_bot import get_best_move
import sys
import os
from models import db, User, Game, Move

app = Flask(__name__, static_url_path='', static_folder='static')
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chess.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Store active games
active_games = {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/make_move', methods=['POST'])
@login_required
def make_move():
    data = request.get_json()
    game_id = data.get('game_id')
    move = data.get('move')
    
    if not game_id or not move:
        return jsonify({'error': 'Missing game_id or move'}), 400
    
    game = Game.query.get(game_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    if game.status != 'active':
        return jsonify({'error': 'Game is not active'}), 400
    
    # Convert the move to a chess.Move object
    chess_move = chess.Move.from_uci(move)
    board = chess.Board(game.fen)
    
    # Check if the move is legal
    if chess_move not in board.legal_moves:
        return jsonify({'error': 'Illegal move'}), 400
    
    # Make the move
    board.push(chess_move)
    
    # Save the move to the database
    new_move = Move(
        game_id=game_id,
        move_number=len(game.moves) + 1,
        move_uci=move
    )
    db.session.add(new_move)
    
    # Update game state
    game.fen = board.fen()
    if board.is_game_over():
        game.status = 'completed'
        game.result = str(board.outcome().result())
    
    db.session.commit()
    
    # Emit the move to all players in the game room
    socketio.emit('move_made', {
        'game_id': game_id,
        'move': move,
        'fen': game.fen,
        'is_game_over': board.is_game_over(),
        'result': game.result if board.is_game_over() else None
    }, room=f'game_{game_id}')
    
    return jsonify({
        'fen': game.fen,
        'is_game_over': board.is_game_over(),
        'result': game.result if board.is_game_over() else None
    })

@app.route('/create_game', methods=['POST'])
@login_required
def create_game():
    opponent_id = request.json.get('opponent_id')
    if not opponent_id:
        return jsonify({'error': 'Opponent ID is required'}), 400
    
    opponent = User.query.get(opponent_id)
    if not opponent:
        return jsonify({'error': 'Opponent not found'}), 404
    
    game = Game(
        white_player_id=current_user.id,
        black_player_id=opponent_id
    )
    db.session.add(game)
    db.session.commit()
    
    return jsonify({
        'game_id': game.id,
        'fen': game.fen
    })

@socketio.on('join_game')
def on_join_game(data):
    game_id = data.get('game_id')
    if not game_id:
        return
    
    game = Game.query.get(game_id)
    if not game:
        return
    
    if current_user.id not in [game.white_player_id, game.black_player_id]:
        return
    
    join_room(f'game_{game_id}')
    emit('game_joined', {
        'game_id': game_id,
        'fen': game.fen,
        'white_player': game.white_player.username,
        'black_player': game.black_player.username
    }, room=f'game_{game_id}')

@socketio.on('leave_game')
def on_leave_game(data):
    game_id = data.get('game_id')
    if game_id:
        leave_room(f'game_{game_id}')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    try:
        port = int(os.environ.get('PORT', 3000))
        print(f"Starting Flask server on port {port}...", file=sys.stderr)
        print(f"Current working directory: {os.getcwd()}", file=sys.stderr)
        print(f"Template folder: {app.template_folder}", file=sys.stderr)
        print(f"Static folder: {app.static_folder}", file=sys.stderr)
        socketio.run(app, debug=True, port=port)
    except Exception as e:
        print(f"Error starting server: {str(e)}", file=sys.stderr) 