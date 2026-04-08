"""Poker agents that use OpenAI API to make decisions."""

import json
from openai import OpenAI

from game import Action


SYSTEM_PROMPT = """你是一名三人德州扑克游戏中的玩家。
你会收到当前的游戏状态，然后必须做出行动决策。

你只能看到：
- 你自己的底牌
- 公共牌
- 底池大小和当前下注
- 行动历史
- 其他玩家的筹码数和是否弃牌

你看不到其他玩家的底牌。

请仅以如下JSON格式回复：
{{"action": "fold" | "check" | "call" | "raise", "private_thought": "你的内心想法"}}

规则：
- "fold"：弃牌
- "check"：过牌（当不需要跟注时，即跟注费用为0）
- "call"：跟注（当需要匹配已有下注时，即跟注费用大于0）
- "raise"：加注一个大盲注的金额

重要：跟注费用为0时用"check"，跟注费用大于0时用"call"。

"private_thought"要求：用1-2句话解释你为什么做出这个决定。
只能基于你能看到的信息（你的底牌、公共牌、底池、行动历史）。
不要猜测或假设其他玩家的底牌。
用中文表达你的内心独白，风格要符合你的性格。

你的性格：
{personality}

保持角色。让你的性格驱动你的决策和内心想法。"""


PERSONALITIES = {
    "Charlie": (
        "你是一个疯狂的赌徒。你几乎每次都加注——翻牌前、翻牌后都无所谓。"
        "过牌是懦夫的行为。你只在极少数情况下过牌或跟注来设陷阱。"
        "你至少70%的时候都要加注。即使拿到烂牌，你也加注来吓跑对手。"
        "你的内心独白要嚣张自大，觉得自己是牌桌上最强的，其他人都是菜鸡。"
    ),
    "Alice": (
        "你是一个极其保守的玩家。不是顶级牌（大对子、强听牌或更好）你就弃牌。"
        "你至少50%的时候会弃牌。当你决定玩的时候，你会加注来保护你的好牌——"
        "你绝不会拿着好牌只是跟注。你的内心独白冷静、理性、精于计算——"
        "你用概率和期望值来思考，对烂牌毫不留情地嫌弃。"
    ),
    "Bob": (
        "你是一个不按常理出牌的疯子。你有时候拿着垃圾牌也加注，就为了看看会发生什么。"
        "有时候你追不可能的听牌，跟注大额下注。你大约40%的时候凭直觉加注。"
        "你的内心独白搞笑轻松——你把扑克当派对游戏，经常说'管他呢'、"
        "'让牌神决定吧'之类的话。"
    ),
}


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

    def __init__(self, name: str, personality: str, client: OpenAI, model: str = "gpt-4o-mini", temperature: float = 1.0):
        self.name = name
        self.personality = personality
        self.client = client
        self.model = model
        self.temperature = temperature

    def decide(self, player_view: dict) -> tuple[Action, str]:
        """Call OpenAI API to decide an action given the visible game state.
        Returns (action, private_thought)."""
        user_prompt = build_user_prompt(player_view)
        system = SYSTEM_PROMPT.format(personality=self.personality)

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=150,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> tuple[Action, str]:
        """Parse the JSON response into (Action, private_thought), with fallback."""
        thought = ""
        try:
            data = json.loads(raw)
            action_str = data.get("action", "call").lower()
            thought = data.get("private_thought", "")
        except (json.JSONDecodeError, AttributeError):
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
        return action_map.get(action_str, Action.CALL), thought
