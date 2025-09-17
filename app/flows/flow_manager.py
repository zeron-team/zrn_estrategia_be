import json
import os
from typing import List, Dict, Any

# Get the directory of the current script to build a reliable path
script_dir = os.path.dirname(__file__)
FLOWS_FILE = os.path.join(script_dir, "flows.json")

def load_flows() -> List[Dict[str, Any]]:
    """Loads conversation flows from the JSON file."""
    try:
        with open(FLOWS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_flows(flows: List[Dict[str, Any]]) -> None:
    """Saves conversation flows to the JSON file."""
    with open(FLOWS_FILE, "w") as f:
        json.dump(flows, f, indent=2)

def get_flows() -> List[Dict[str, Any]]:
    """Returns all conversation flows."""
    return load_flows()

def get_flow(flow_id: int) -> Dict[str, Any] | None:
    """Returns a single conversation flow by its ID."""
    flows = load_flows()
    for flow in flows:
        if flow["id"] == flow_id:
            return flow
    return None

def create_flow(flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new conversation flow."""
    flows = load_flows()
    new_id = max([flow["id"] for flow in flows]) + 1 if flows else 1
    flow_data["id"] = new_id
    flow_data["is_active"] = False
    flows.append(flow_data)
    save_flows(flows)
    return flow_data

def update_flow(flow_id: int, flow_data: Dict[str, Any]) -> Dict[str, Any] | None:
    """Updates an existing conversation flow."""
    flows = load_flows()
    for i, flow in enumerate(flows):
        if flow["id"] == flow_id:
            flows[i] = flow_data
            flow_data["id"] = flow_id
            save_flows(flows)
            return flow_data
    return None

def delete_flow(flow_id: int) -> bool:
    """Deletes a conversation flow."""
    flows = load_flows()
    initial_len = len(flows)
    flows = [flow for flow in flows if flow["id"] != flow_id]
    if len(flows) < initial_len:
        save_flows(flows)
        return True
    return False

def set_active_flow(flow_id: int) -> Dict[str, Any] | None:
    """Sets a flow as active and deactivates all others."""
    flows = load_flows()
    updated_flow = None
    for flow in flows:
        if flow["id"] == flow_id:
            flow["is_active"] = True
            updated_flow = flow
        else:
            flow["is_active"] = False
    save_flows(flows)
    return updated_flow