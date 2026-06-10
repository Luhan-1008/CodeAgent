import asyncio

from code_agent import LLMAgent


async def main() -> None:
    """A minimal quickstart script to chat with CodeAgent's default LLMAgent.

    Usage:
        1. Set your API key environment variable (for example, ``MODELSCOPE_API_KEY``
           or an OpenAI-compatible key as required by your local configuration).
        2. Run:

           ``PYTHONPATH=. python quickstart_simple_chat.py``

        3. Type your message after the ``>>>`` prompt.
    """
    agent = LLMAgent()
    # Let the agent handle interactive input when query is None
    result = await agent.run(None)
    # Print the final assistant message (if any)
    if result and isinstance(result, list):
        last = result[-1]
        if getattr(last, "content", None):
            print("\n[assistant]:")
            print(last.content)


if __name__ == "__main__":
    asyncio.run(main())


