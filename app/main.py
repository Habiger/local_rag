import sys
import asyncio

#from app.pipeline.main_pipeline_websocket import main
from app.workers.pipeline_conversion_post_chunking import pipeline


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(pipeline())
    except KeyboardInterrupt:
        print("Shutting down...")