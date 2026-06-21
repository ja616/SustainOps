import asyncio
import sys
import traceback
import threading
from fastapi import FastAPI
import uvicorn
from strands._async import run_async

app = FastAPI()

async def dummy_agent():
    print("Worker thread started")
    await asyncio.sleep(1)
    print("Worker thread finished")
    return "OK"

@app.get("/test")
async def test_hang():
    print("Main thread running test_hang")
    
    # Start a background thread to dump frames after 2 seconds
    def dump_frames():
        import time
        time.sleep(2)
        print("Dumping frames...")
        for th_id, frame in sys._current_frames().items():
            print(f"Thread {th_id}:")
            traceback.print_stack(frame)
            print("-" * 40)
            
    threading.Thread(target=dump_frames, daemon=True).start()
    
    try:
        # This simulates run_agent_with_trace
        result = run_async(lambda: dummy_agent())
        return {"status": result}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
