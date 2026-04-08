# Poker Agent Demo

Build a simplified Texas Hold'em simulation for a terminal-style educational video.

## Rules
- 3 AI player personas: Alice (Dealer), Bob (SB), Charlie (BB)
- Each player sees only its own hole cards plus public board/action history
- Private thoughts are audience-only and must not be passed to other agents
- Actions: fold / call / raise
- Thoughts: short, humorous, readable (Phase 2+)
- Start with minimal simulation first; do not add memory, pot odds, or advanced tools until the baseline works
- Output should look like a live terminal log

## Tech Stack
- Python 3.11+
- `anthropic` SDK for Claude API calls
- `python-dotenv` for env management

## Project Structure
- `game.py` — Game engine: deck, cards, betting, hand evaluation
- `agents.py` — PokerAgent class that calls Claude API for decisions
- `main.py` — Runner that plays a single hand and prints results
- `.env` — API key (not committed); copy from `.env.example`

## How to Run
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
python main.py
```

## Phases
- **Phase 1** (current): Minimal agent — input game state → output action via Claude API
- **Phase 2**: Add private_thought reasoning to agent output
- **Phase 3**: Full agentic loop with commentator agent


## Python environment (for agent-service)
- Python 3.13 at:
  C:\Users\zhenga\AppData\Local\Programs\Python\Python313\python.exe
- Not on system PATH — use full path for venv creation
- OS: Windows