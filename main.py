"""Phase 1 — Minimal Agent: Run a single hand of 3-player Texas Hold'em."""

from openai import OpenAI
from dotenv import load_dotenv

from game import GameState, Player, Action, Street
from agents import PokerAgent, PERSONALITIES

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
    print(f"  公共牌 : {card_str(gs.board) if gs.board else '（无）'}")
    print(f"  底池   : {gs.pot}")
    for p in gs.players:
        status = "已弃牌" if p.folded else "在场"
        label = player_label(gs, p)
        print(f"  {label:18s} | 筹码: {p.chips:>5} | {status}")


def print_hands(gs: GameState):
    """Show all hands (audience-only view)."""
    print("  【观众视角 — 底牌展示】")
    for p in gs.players:
        print(f"    {player_label(gs, p)}: {card_str(p.hand)}")


# ── Betting round ────────────────────────────────────────────────────

def run_betting_round(gs: GameState, agents: dict[str, PokerAgent]):
    """Run a betting round. Loops until all active players have matched the current bet."""
    order = gs.get_betting_order()
    # Queue of players who still need to act
    action_queue = [p for p in order if not p.folded]

    while action_queue:
        player = action_queue.pop(0)

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

        # If someone raises, everyone else still active needs to respond
        if action == Action.RAISE:
            for p in gs.get_betting_order():
                if not p.folded and p.name != player.name and p not in action_queue:
                    action_queue.append(p)

        # Display
        action_names = {
            Action.FOLD: "弃牌",
            Action.CHECK: "过牌",
            Action.CALL: f"跟注 ({cost_to_call}筹码)",
            Action.RAISE: f"加注 (+{gs.big_blind})",
        }
        action_display = action_names[action]

        label = player_label(gs, player)
        print(f"  {label:18s} -> {action_display:20s} [底池: {gs.pot}]")
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

    temperatures = {"Charlie": 1.2, "Alice": 0.4, "Bob": 1.4}
    agents = {
        p.name: PokerAgent(p.name, PERSONALITIES[p.name], client, temperature=temperatures[p.name])
        for p in players
    }

    gs = GameState(players)

    print_divider("新一手")
    print("  玩家: Charlie (BTN), Alice (SB), Bob (BB)")
    print(f"  盲注: {gs.small_blind}/{gs.big_blind}\n")

    # Post blinds and deal
    gs.post_blinds()
    gs.deal_hole_cards()
    print_hands(gs)

    # Play through streets
    street_names = {
        Street.PREFLOP: "翻牌前",
        Street.FLOP: "翻牌",
        Street.TURN: "转牌",
        Street.RIVER: "河牌",
    }

    print_divider(street_names[Street.PREFLOP])
    print_game_state(gs)
    print()
    run_betting_round(gs, agents)

    for next_street in [Street.FLOP, Street.TURN, Street.RIVER]:
        if gs.is_hand_over():
            break

        gs.advance_street()
        print_divider(street_names[next_street])
        new_cards = gs.board[-3:] if next_street == Street.FLOP else gs.board[-1:]
        print(f"  发牌 : {card_str(new_cards)}")
        print_game_state(gs)
        print()
        run_betting_round(gs, agents)

    # Resolve winner
    print_divider("结果")
    if gs.is_hand_over() and gs.street != Street.SHOWDOWN:
        winner = gs.get_winner()
        print(f"  {player_label(gs, winner)} 赢得 {gs.pot} 筹码（其他玩家全部弃牌）")
    else:
        winner = gs.get_winner()
        print("  最终公共牌: " + card_str(gs.board))
        print()
        for p in gs.get_active_players():
            print(f"  {player_label(gs, p)}: {card_str(p.hand)}")
        print(f"\n  {player_label(gs, winner)} 赢得 {gs.pot} 筹码！")

    winner.chips += gs.pot
    print_divider()


if __name__ == "__main__":
    play_hand()
