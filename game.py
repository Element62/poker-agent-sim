"""Texas Hold'em game engine for 3-player poker simulation."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


SUITS = ["hearts", "diamonds", "clubs", "spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

RANK_VALUES = {r: i for i, r in enumerate(RANKS, 2)}


class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


class Action(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"


@dataclass
class Card:
    rank: str
    suit: str

    def __str__(self):
        symbols = {"hearts": "♥", "diamonds": "♦", "clubs": "♣", "spades": "♠"}
        return f"{self.rank}{symbols[self.suit]}"


@dataclass
class Player:
    name: str
    chips: int = 1000
    hand: list[Card] = field(default_factory=list)
    folded: bool = False
    current_bet: int = 0

    def reset_for_hand(self):
        self.hand = []
        self.folded = False
        self.current_bet = 0


@dataclass
class ActionRecord:
    player_name: str
    street: Street
    action: Action
    amount: int = 0


class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        random.shuffle(self.cards)

    def deal(self, n: int = 1) -> list[Card]:
        dealt = self.cards[:n]
        self.cards = self.cards[n:]
        return dealt


class GameState:
    """Manages the state of a single hand of Texas Hold'em."""

    def __init__(self, players: list[Player], small_blind: int = 10, big_blind: int = 20):
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.deck = Deck()
        self.board: list[Card] = []
        self.pot = 0
        self.street = Street.PREFLOP
        self.action_history: list[ActionRecord] = []
        self.current_bet = 0  # highest bet on current street

        for p in self.players:
            p.reset_for_hand()

    def post_blinds(self):
        """Post small and big blinds (players[0]=dealer, [1]=SB, [2]=BB)."""
        sb_player = self.players[1]
        bb_player = self.players[2]

        sb_amount = min(self.small_blind, sb_player.chips)
        sb_player.chips -= sb_amount
        sb_player.current_bet = sb_amount

        bb_amount = min(self.big_blind, bb_player.chips)
        bb_player.chips -= bb_amount
        bb_player.current_bet = bb_amount

        self.pot += sb_amount + bb_amount
        self.current_bet = bb_amount

    def deal_hole_cards(self):
        for p in self.players:
            p.hand = self.deck.deal(2)

    def deal_community(self):
        if self.street == Street.FLOP:
            self.board.extend(self.deck.deal(3))
        elif self.street in (Street.TURN, Street.RIVER):
            self.board.extend(self.deck.deal(1))

    def get_active_players(self) -> list[Player]:
        return [p for p in self.players if not p.folded]

    def get_betting_order(self) -> list[Player]:
        """Return players in betting order for the current street."""
        active = self.get_active_players()
        if self.street == Street.PREFLOP:
            # Preflop: action starts left of BB (dealer in 3-player)
            # Order: player[0] (dealer), player[1] (SB), player[2] (BB)
            order = [self.players[0], self.players[1], self.players[2]]
        else:
            # Postflop: SB first, then BB, then dealer
            order = [self.players[1], self.players[2], self.players[0]]
        return [p for p in order if not p.folded]

    def apply_action(self, player: Player, action: Action, raise_amount: int = 0):
        """Apply a player's action to the game state."""
        if action == Action.FOLD:
            player.folded = True
            self.action_history.append(
                ActionRecord(player.name, self.street, action)
            )
        elif action == Action.CHECK:
            self.action_history.append(
                ActionRecord(player.name, self.street, action)
            )
        elif action == Action.CALL:
            call_cost = self.current_bet - player.current_bet
            call_cost = min(call_cost, player.chips)
            player.chips -= call_cost
            player.current_bet += call_cost
            self.pot += call_cost
            self.action_history.append(
                ActionRecord(player.name, self.street, action, call_cost)
            )
        elif action == Action.RAISE:
            # Raise to current_bet + raise_amount
            total_to_put = (self.current_bet + raise_amount) - player.current_bet
            total_to_put = min(total_to_put, player.chips)
            player.chips -= total_to_put
            player.current_bet += total_to_put
            self.current_bet = player.current_bet
            self.pot += total_to_put
            self.action_history.append(
                ActionRecord(player.name, self.street, action, total_to_put)
            )

    def advance_street(self):
        """Move to the next street and deal community cards."""
        streets = [Street.PREFLOP, Street.FLOP, Street.TURN, Street.RIVER, Street.SHOWDOWN]
        idx = streets.index(self.street)
        if idx < len(streets) - 1:
            self.street = streets[idx + 1]
            # Reset per-street bets
            for p in self.players:
                p.current_bet = 0
            self.current_bet = 0
            if self.street != Street.SHOWDOWN:
                self.deal_community()

    def get_player_view(self, player: Player) -> dict:
        """Return the game state visible to a specific player (no info leakage)."""
        return {
            "your_name": player.name,
            "your_hand": [str(c) for c in player.hand],
            "your_chips": player.chips,
            "board": [str(c) for c in self.board],
            "pot": self.pot,
            "current_bet": self.current_bet,
            "your_current_bet": player.current_bet,
            "cost_to_call": self.current_bet - player.current_bet,
            "street": self.street.value,
            "action_history": [
                {
                    "player": a.player_name,
                    "street": a.street.value,
                    "action": a.action.value,
                    "amount": a.amount,
                }
                for a in self.action_history
            ],
            "players": [
                {
                    "name": p.name,
                    "chips": p.chips,
                    "folded": p.folded,
                    "is_you": p.name == player.name,
                }
                for p in self.players
            ],
        }

    def is_hand_over(self) -> bool:
        """Hand ends if only 1 player remains or we've reached showdown."""
        active = self.get_active_players()
        return len(active) <= 1 or self.street == Street.SHOWDOWN

    def get_winner(self) -> Player:
        """Determine the winner. For Phase 1, use simple hand ranking."""
        active = self.get_active_players()
        if len(active) == 1:
            return active[0]
        # Simple ranking: best high card from hand + board
        return max(active, key=lambda p: _score_hand(p.hand, self.board))


def _score_hand(hand: list[Card], board: list[Card]) -> tuple:
    """
    Simplified hand scoring. Evaluates basic poker hands.
    Returns a tuple for comparison (hand_rank, tiebreakers...).

    Hand ranks: 0=high card, 1=pair, 2=two pair, 3=three of a kind,
                4=straight, 5=flush, 6=full house, 7=four of a kind,
                8=straight flush
    """
    all_cards = hand + board
    ranks = sorted([RANK_VALUES[c.rank] for c in all_cards], reverse=True)
    suits = [c.suit for c in all_cards]

    rank_counts: dict[int, int] = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1

    counts_sorted = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    # Check for flush
    suit_counts: dict[str, int] = {}
    for s in suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    flush_suit = None
    for s, count in suit_counts.items():
        if count >= 5:
            flush_suit = s
            break

    # Check for straight
    unique_ranks = sorted(set(ranks), reverse=True)
    straight_high = _find_straight(unique_ranks)

    # Straight flush
    if flush_suit and straight_high:
        flush_cards = sorted(
            [RANK_VALUES[c.rank] for c in all_cards if c.suit == flush_suit],
            reverse=True,
        )
        sf_high = _find_straight(sorted(set(flush_cards), reverse=True))
        if sf_high:
            return (8, sf_high)

    # Four of a kind
    if counts_sorted[0][1] == 4:
        quad_rank = counts_sorted[0][0]
        kicker = max(r for r in ranks if r != quad_rank)
        return (7, quad_rank, kicker)

    # Full house
    if counts_sorted[0][1] == 3 and len(counts_sorted) > 1 and counts_sorted[1][1] >= 2:
        return (6, counts_sorted[0][0], counts_sorted[1][0])

    # Flush
    if flush_suit:
        flush_ranks = sorted(
            [RANK_VALUES[c.rank] for c in all_cards if c.suit == flush_suit],
            reverse=True,
        )[:5]
        return (5, *flush_ranks)

    # Straight
    if straight_high:
        return (4, straight_high)

    # Three of a kind
    if counts_sorted[0][1] == 3:
        trip_rank = counts_sorted[0][0]
        kickers = sorted([r for r in ranks if r != trip_rank], reverse=True)[:2]
        return (3, trip_rank, *kickers)

    # Two pair
    if counts_sorted[0][1] == 2 and len(counts_sorted) > 1 and counts_sorted[1][1] == 2:
        high_pair = counts_sorted[0][0]
        low_pair = counts_sorted[1][0]
        kicker = max(r for r in ranks if r != high_pair and r != low_pair)
        return (2, high_pair, low_pair, kicker)

    # One pair
    if counts_sorted[0][1] == 2:
        pair_rank = counts_sorted[0][0]
        kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)[:3]
        return (1, pair_rank, *kickers)

    # High card
    return (0, *ranks[:5])


def _find_straight(unique_ranks_desc: list[int]) -> Optional[int]:
    """Find the highest straight in a list of unique ranks (descending). Returns high card or None."""
    # Check for ace-low straight (A-2-3-4-5)
    if {14, 2, 3, 4, 5}.issubset(set(unique_ranks_desc)):
        return 5

    for i in range(len(unique_ranks_desc) - 4):
        window = unique_ranks_desc[i : i + 5]
        if window[0] - window[4] == 4:
            return window[0]
    return None
