import chess
import chess.pgn
import random
from typing import List, Tuple

# Piece values
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Piece-square tables for positional evaluation
PAWN_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5,  5, 10, 25, 25, 10,  5,  5,
    0,  0,  0, 20, 20,  0,  0,  0,
    5, -5,-10,  0,  0,-10, -5,  5,
    5, 10, 10,-20,-20, 10, 10,  5,
    0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

def evaluate_position(board: chess.Board) -> float:
    """Evaluate the current position."""
    if board.is_checkmate():
        return -10000 if board.turn else 10000
    
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    
    score = 0
    
    # Material and position evaluation
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue
            
        value = PIECE_VALUES[piece.piece_type]
        
        # Add positional bonus
        if piece.piece_type == chess.PAWN:
            value += PAWN_TABLE[square]
        elif piece.piece_type == chess.KNIGHT:
            value += KNIGHT_TABLE[square]
            
        score += value if piece.color == chess.WHITE else -value
    
    return score

def minimax(board: chess.Board, depth: int, alpha: float, beta: float, maximizing: bool) -> Tuple[float, chess.Move]:
    """Minimax algorithm with alpha-beta pruning."""
    if depth == 0 or board.is_game_over():
        return evaluate_position(board), None
    
    best_move = None
    if maximizing:
        max_eval = float('-inf')
        for move in board.legal_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            if eval > max_eval:
                max_eval = eval
                best_move = move
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            if eval < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval, best_move

def get_best_move(board: chess.Board, depth: int = 3) -> chess.Move:
    """Get the best move for the current position."""
    _, best_move = minimax(board, depth, float('-inf'), float('inf'), board.turn == chess.WHITE)
    return best_move

def load_games_from_pgn(pgn_file: str) -> List[chess.pgn.Game]:
    """Load games from a PGN file."""
    games = []
    with open(pgn_file) as pgn:
        while True:
            game = chess.pgn.read_game(pgn)
            if game is None:
                break
            games.append(game)
    return games

def main():
    # Load games from PGN file
    games = load_games_from_pgn('games.pgn')
    print(f"Loaded {len(games)} games from PGN file")
    
    # Create a new board
    board = chess.Board()
    
    # Play a game against the bot
    while not board.is_game_over():
        print("\nCurrent position:")
        print(board)
        
        if board.turn == chess.WHITE:
            # Human's turn
            while True:
                try:
                    move = input("Enter your move (e.g., 'e2e4'): ")
                    move = chess.Move.from_uci(move)
                    if move in board.legal_moves:
                        break
                    print("Illegal move, try again.")
                except ValueError:
                    print("Invalid move format, try again.")
        else:
            # Bot's turn
            print("Bot is thinking...")
            move = get_best_move(board)
            print(f"Bot plays: {move}")
        
        board.push(move)
    
    print("\nGame Over!")
    print(f"Result: {board.outcome().result()}")

if __name__ == "__main__":
    main()