
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.flows import flow_manager

router = APIRouter()

@router.get("/flows", response_model=List[Dict[str, Any]])
def read_flows():
    return flow_manager.get_flows()

@router.get("/flows/{flow_id}", response_model=Dict[str, Any])
def read_flow(flow_id: int):
    flow = flow_manager.get_flow(flow_id)
    if flow is None:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow

@router.post("/flows", response_model=Dict[str, Any], status_code=201)
def create_new_flow(flow_data: Dict[str, Any]):
    return flow_manager.create_flow(flow_data)

@router.put("/flows/{flow_id}", response_model=Dict[str, Any])
def update_existing_flow(flow_id: int, flow_data: Dict[str, Any]):
    flow = flow_manager.update_flow(flow_id, flow_data)
    if flow is None:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow

@router.delete("/flows/{flow_id}", status_code=204)
def delete_existing_flow(flow_id: int):
    if not flow_manager.delete_flow(flow_id):
        raise HTTPException(status_code=404, detail="Flow not found")

@router.put("/flows/{flow_id}/active", response_model=Dict[str, Any])
def set_active_flow(flow_id: int):
    flow = flow_manager.set_active_flow(flow_id)
    if flow is None:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow
