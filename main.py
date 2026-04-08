"""Phase 1 — Minimal Agent: Run a single hand of 3-player Texas Hold'em."""

from openai import OpenAI
from dotenv import load_dotenv

from game import GameState, Player, Action, Street
from agents import PokerAgent

load_dotenv()

# ── Display helpers ──────────────────────────────────────────────────

def card_str(cards):
    return " ".join(str(c) for c in cards)


def print_divider(label: str = ""):
    if label:
        print(f"\n{'─' * 20} {label} {'─' * 20}")
    else:
        print("─" * 50)


# Position labels: players[0]=Button, players[1]=SB, players[2]=BB
POSITIONS = {0: "BTN", 1: "SB", 2: "BB"}


def player_label(gs: GameState, p: Player) -> str:
    idx = gs.players.index(p)
    return f"{p.name} ({POSITIONS[idx]})"


def print_game_state(gs: GameState):
    print(f"  Board : {card_str(gs.board) if gs.board else '(none)'}")
    print(f"  Pot   : {gs.pot}")
    for p in gs.players:
        status = "FOLDED" if p.folded else "active"
        label = player_label(gs, p)
        print(f"  {label:18s} | chips: {p.chips:>5} | {status}")


def print_hands(gs: GameState):
    """Show all hands (audience-only view)."""
    print("  [Audience view — hole cards]")
    for p in gs.players:
        print(f"    {player_label(gs, p)}: {card_str(p.hand)}")


# ── Betting round ────────────────────────────────────────────────────

def run_betting_round(gs: GameState, agents: dict[str, PokerAgent]):
    """Run a single betting round. Each active player acts once (simplified)."""
    order = gs.get_betting_order()

    for player in order:
        if player.folded:
            continue
        if len(gs.get_active_players()) <= 1:
            break

        view = gs.get_player_view(player)
        agent = agents[player.name]
        action, thought = agent.decide(view)

        # If agent says "call" but there's nothing to call, convert to check
        cost_to_call = view["cost_to_call"]
        if action == Action.CALL and cost_to_call == 0:
            action = Action.CHECK
        # If agent says "check" but there's a bet to match, convert to call
        elif action == Action.CHECK and cost_to_call > 0:
            action = Action.CALL

        # Apply raise amount as one big blind
        raise_amount = gs.big_blind if action == Action.RAISE else 0
        gs.apply_action(player, action, raise_amount)

        # Display
        action_display = action.value.upper()
        if action == Action.CALL:
            action_display += f" ({cost_to_call} chips)"
        elif action == Action.RAISE:
            action_display += f" (+{gs.big_blind})"

        label = player_label(gs, player)
        print(f"  {label:18s} -> {action_display:20s} [pot: {gs.pot}]")
        if thought:
            print(f'    "{thought}"')


# ── Main game loop ───────────────────────────────────────────────────

def play_hand():
    client = OpenAI()  # reads OPENAI_API_KEY from env

    players = [
        Player("Charlie"),  # Button
        Player("Alice"),    # SB
        Player("Bob"),      # BB
    ]

    agents = {
        p.name: PokerAgent(p.name, client) for p in players
    }

    gs = GameState(players)

    print_divider("NEW HAND")
    print("  Players: Charlie (BTN), Alice (SB), Bob (BB)")
    print(f"  Blinds: {gs.small_blind}/{gs.big_blind}\n")

    # Post blinds and deal
    gs.post_blinds()
    gs.deal_hole_cards()
    print_hands(gs)

    # Play through streets: preflop first, then advance + display for each subsequent street
    print_divider("PREFLOP")
    print_game_state(gs)
    print()
    run_betting_round(gs, agents)

    for next_street in [Street.FLOP, Street.TURN, Street.RIVER]:
        if gs.is_hand_over():
            break

        gs.advance_street()  # deals community cards
        print_divider(next_street.value.upper())
        print(f"  Dealt : {card_str(gs.board[-3:] if next_street == Street.FLOP else gs.board[-1:])}")
        print_game_state(gs)
        print()
        run_betting_round(gs, agents)

    # Resolve winner
    print_divider("RESULT")
    if gs.is_hand_over() and gs.street != Street.SHOWDOWN:
        winner = gs.get_winner()
        print(f"  {player_label(gs, winner)} wins {gs.pot} chips (everyone else folded)")
    else:
        winner = gs.get_winner()
        print("  Final board: " + card_str(gs.board))
        print()
        for p in gs.get_active_players():
            print(f"  {player_label(gs, p)}: {card_str(p.hand)}")
        print(f"\n  {player_label(gs, winner)} wins {gs.pot} chips!")

    winner.chips += gs.pot
    print_divider()


if __name__ == "__main__":
    play_hand()
