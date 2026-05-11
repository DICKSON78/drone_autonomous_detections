from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_pipeline import DroneSystem

app = FastAPI(title="Integrated Drone Pipeline", version="1.0.0")

# Global drone system instance
drone_system = None

@app.on_event("startup")
async def startup_event():
    global drone_system
    try:
        drone_system = DroneSystem()
        print("Integrated Drone Pipeline started successfully!")
    except Exception as e:
        print(f"Failed to initialize drone system: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "integrated-pipeline"}

@app.post("/process_frame")
async def process_frame(frame_data: dict):
    if drone_system is None:
        raise HTTPException(status_code=500, detail="Drone system not initialized")
    
    try:
        # Process frame with complete system
        result = drone_system.process_frame(frame_data.get("frame"))
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/stats")
async def get_stats():
    if drone_system is None:
        raise HTTPException(status_code=500, detail="Drone system not initialized")
    
    return {
        "system_stats": drone_system.system_stats,
        "flight_history_length": len(drone_system.flight_history)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
