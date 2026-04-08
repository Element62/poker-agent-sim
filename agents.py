"""Poker agents that use OpenAI API to make decisions."""

import json
from openai import OpenAI

from game import Action


SYSTEM_PROMPT = """You are a poker player in a 3-player Texas Hold'em game.
You will receive the current game state and must decide your action.

You can ONLY see:
- Your own hole cards
- The community board cards
- The pot size and current bet
- The action history
- Other players' chip counts and whether they folded

You CANNOT see other players' cards.

Respond with ONLY valid JSON in this exact format:
{"action": "fold" | "check" | "call" | "raise"}

Rules:
- "fold": give up this hand
- "check": pass when there is no bet to match (cost to call is 0)
- "call": match an existing bet (cost to call is greater than 0)
- "raise": increase the bet by the big blind amount

IMPORTANT: Use "check" when cost to call is 0. Use "call" when cost to call is greater than 0.

Think about pot odds, hand strength, and position. Be strategic but decisive.
Do NOT include any explanation — just the JSON."""


def build_user_prompt(player_view: dict) -> str:
    """Format the player's visible game state into a prompt."""
    hand = ", ".join(player_view["your_hand"])
    board = ", ".join(player_view["board"]) if player_view["board"] else "none yet"

    history_lines = []
    for a in player_view["action_history"]:
        line = f"  {a['player']} {a['action']}"
        if a["amount"]:
            line += f" ({a['amount']} chips)"
        history_lines.append(line)
    history_str = "\n".join(history_lines) if history_lines else "  (no actions yet)"

    opponent_lines = []
    for p in player_view["players"]:
        if not p["is_you"]:
            status = "folded" if p["folded"] else "active"
            opponent_lines.append(f"  {p['name']}: {p['chips']} chips ({status})")

    return f"""Current game state:
- Street: {player_view['street']}
- Your hand: {hand}
- Board: {board}
- Pot: {player_view['pot']}
- Current bet: {player_view['current_bet']}
- Your current bet: {player_view['your_current_bet']}
- Cost to call: {player_view['cost_to_call']}
- Your chips: {player_view['your_chips']}

Opponents:
{chr(10).join(opponent_lines)}

Action history:
{history_str}

What is your action?"""


class PokerAgent:
    """A poker-playing agent powered by OpenAI API."""

    def __init__(self, name: str, client: OpenAI, model: str = "gpt-4o-mini"):
        self.name = name
        self.client = client
        self.model = model

    def decide(self, player_view: dict) -> Action:
        """Call OpenAI API to decide an action given the visible game state."""
        user_prompt = build_user_prompt(player_view)

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=50,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()
        return self._parse_action(raw)

    def _parse_action(self, raw: str) -> Action:
        """Parse the JSON response into an Action, with fallback."""
        try:
            data = json.loads(raw)
            action_str = data.get("action", "call").lower()
        except (json.JSONDecodeError, AttributeError):
            # Try to extract action from raw text
            raw_lower = raw.lower()
            if "fold" in raw_lower:
                action_str = "fold"
            elif "raise" in raw_lower:
                action_str = "raise"
            elif "check" in raw_lower:
                action_str = "check"
            else:
                action_str = "call"

        action_map = {
            "fold": Action.FOLD,
            "check": Action.CHECK,
            "call": Action.CALL,
            "raise": Action.RAISE,
        }
        return action_map.get(action_str, Action.CALL)
