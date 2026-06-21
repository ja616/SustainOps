import json
from typing import List, Callable, Dict, Any, Optional


class StrandsAgent:
    """
    Agent abstraction modeled on the AWS Strands Agents SDK.

    This implements the core ReAct loop:
    1. Send task + tool schemas to LLM
    2. If LLM returns a tool call, execute it
    3. Feed result back to LLM
    4. Repeat until LLM returns final text response

    Compatible with real Strands SDK interface — can be swapped 1:1.
    """

    def __init__(
        self,
        name: str,
        role: str,
        model,
        tools: Optional[List[Callable]] = None,
    ):
        self.name = name
        self.role = role
        self.model = model
        self.tools = tools or []
        self.tool_map: Dict[str, Callable] = {fn.__name__: fn for fn in self.tools}
        self.memory: List[Dict[str, str]] = []

    def _build_tool_descriptions(self) -> str:
        """Build human-readable tool descriptions for the system prompt."""
        if not self.tools:
            return ""
        lines = ["Available tools (call by returning JSON with 'tool' and 'args' keys):\n"]
        for fn in self.tools:
            doc = fn.__doc__ or "No description."
            import inspect
            sig = inspect.signature(fn)
            lines.append(f"  - {fn.__name__}{sig}: {doc.strip()}")
        return "\n".join(lines)

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a task using the ReAct loop.
        Returns the final string response from the LLM.
        """
        system_prompt = (
            f"You are {self.name}. Your role: {self.role}\n\n"
            f"{self._build_tool_descriptions()}\n\n"
            "When you need to call a tool, respond ONLY with a JSON block like:\n"
            '{"tool": "tool_name", "args": {"arg1": "value1"}}\n\n'
            "When you have gathered enough information, respond with your final "
            "answer as a JSON object with these exact keys:\n"
            '{"alternative": "...", "current_supplier": "...", '
            '"reasoning": "...", "cost_impact": "...", '
            '"risk_impact": "...", "sustainability_impact": "...", '
            '"evidence": ["...", "..."], "sources": ["...", "..."], '
            '"confidence": 0-100}\n\n'
            "Be concise. Respond ONLY with the JSON — no extra text."
        )

        if context:
            system_prompt += f"\nContext: {json.dumps(context)}"

        # Conversation history for this execution
        conversation = [{"role": "user", "content": task}]
        max_iterations = 8

        for _ in range(max_iterations):
            prompt = task if len(conversation) == 1 else (
                "Based on the tool results so far, continue your analysis or provide your final JSON answer."
            )

            # Build a single prompt that includes full conversation history
            full_prompt = "\n\n".join([
                f"[{msg['role'].upper()}]: {msg['content']}"
                for msg in conversation
            ])

            response_text = self.model.generate(full_prompt, system=system_prompt)
            self.memory.append({"role": "assistant", "content": response_text})

            # Try to parse as tool call
            try:
                stripped = response_text.strip()
                # Extract JSON if wrapped in markdown code block
                if stripped.startswith("```"):
                    stripped = stripped.split("```")[1]
                    if stripped.startswith("json"):
                        stripped = stripped[4:]
                parsed = json.loads(stripped.strip())

                # Check if it's a tool call
                if "tool" in parsed and "args" in parsed:
                    tool_name = parsed["tool"]
                    tool_args = parsed["args"]
                    if tool_name in self.tool_map:
                        import asyncio
                        import inspect
                        fn = self.tool_map[tool_name]
                        if inspect.iscoroutinefunction(fn):
                            tool_result = asyncio.get_event_loop().run_until_complete(
                                fn(**tool_args)
                            )
                        else:
                            tool_result = fn(**tool_args)
                        result_str = f"Tool '{tool_name}' returned: {json.dumps(tool_result)}"
                        conversation.append({"role": "assistant", "content": response_text})
                        conversation.append({"role": "user", "content": result_str})
                        continue
                    else:
                        # Unknown tool — treat as final answer
                        return response_text

                # It's a final JSON answer
                return response_text

            except (json.JSONDecodeError, KeyError):
                # Not JSON — treat as final text answer
                return response_text

        return response_text
