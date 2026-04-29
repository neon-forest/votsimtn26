"""
test_run.py  Quick connection test
"""
import asyncio, time, os, sys
sys.path.append(os.getcwd())
from core.ollama_async_client import get_llm_client

async def main():
    print(f"\n{'='*55}")
    print(f"  VoterSim TN '26 - LLM Connectivity Test")
    print(f"{'='*55}\n")

    # Force OLLAMA for test if GEMINI key is missing
    mode = "OLLAMA" if not os.environ.get("GEMINI_API_KEY") else "GEMINI"
    client = get_llm_client(mode)
    
    # ── Test 1: Basic ping ────────────────────────────────
    print("[1/2] Ping test...")
    ok = client.ping()
    print(f"      {'[OK] Client initialized (' + client.mode + ')' if ok else '[FAIL] NOT initialized'}\n")

    # -- Test 2: Single call -----------------------------------------
    print("[2/2] Single call test...")
    prompt = (
        'You simulate a Tamil Nadu voter. '
        'Return ONLY valid JSON: '
        '{"SPA": 40, "AIADMK": 30, "TVK": 20, "Others": 10, "Reason": "Test."}'
    )
    t0 = time.perf_counter()
    res = await client.call_async(prompt)
    elapsed = time.perf_counter() - t0
    if res:
        print(f"      [OK] Response in {elapsed:.2f}s -> {res}\n")
    else:
        print(f"      [FAIL] No response after {elapsed:.2f}s\n")

    print(f"{'='*55}")
    print("  To run full simulation: python core/voter_agent_engine.py")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    asyncio.run(main())
