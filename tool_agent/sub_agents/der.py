import requests
from google.adk.agents import Agent
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timezone
from .er_house_hold import er_household_ids_list
import json

load_dotenv()

API_CREATE_DER_ENDPOINT = "http://world-engine-team7.becknprotocol.io/meter-data-simulator/der"
API_TOOGLE_DER_ENDPOINT = "http://world-engine-team7.becknprotocol.io/meter-data-simulator/toggle-der/"

# Appliance mapping
APPLIANCE_MAPPING = {
    "Air Conditioner(1.5 Ton)": 8,
    "Ceiling Fan": 2,
    "Electric Geyser": 10,
    "Laptop Charger": 5,
    "LED Bulb(10 W)": 1,
    "Microwave Oven": 6,
    "Refrigerator": 4,
    "Room Heater": 9,
    "Solar Panel(production)": 12,
    "Television(LED)": 3,
    "Washing machine": 7,
    "Water pump": 11,
}

# Global list to store details of created DERs
# Each element will be a dict: {"id": der_id, "appliance_id": appliance_id, "er_id": er_id}
created_ders_details = []

CREATE_DER_TEMPLATE = '''
{
    "energy_resource":1915,
    "appliance":5
}
'''

def create_der(search_query: str) -> str:
    """
    Creates a new DER (Distributed Energy Resource) using the latest energy resource ID
    and an appliance ID mapped from the search query.
    The ID of the created DER is stored globally.

    Args:
        search_query (str): The search query containing the appliance name to create the DER for.
                            Example: "Create a DER for Ceiling Fan"

    Returns:
        str: A string representation of the JSON response from the API, containing the created DER,
        or an error message.
    """
    global er_household_ids_list
    global created_ders_details

    if not er_household_ids_list:
        return "Error: No energy resource IDs available. Cannot create a DER without an energy resource."

    latest_er_id = er_household_ids_list[-1]
    
    selected_appliance_name = None
    appliance_id = None
    
    for key_in_map in APPLIANCE_MAPPING.keys():
        if key_in_map.lower() in search_query.lower():
            selected_appliance_name = key_in_map
            appliance_id = APPLIANCE_MAPPING[selected_appliance_name]
            break
            
    if appliance_id is None:
        return f"Error: Could not find a recognized appliance name in the search query: '{search_query}'. Available appliances: {list(APPLIANCE_MAPPING.keys())}"

    try:
        payload_dict = json.loads(CREATE_DER_TEMPLATE)
        payload_dict["energy_resource"] = latest_er_id
        payload_dict["appliance"] = appliance_id
        current_payload = json.dumps(payload_dict)

        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_CREATE_DER_ENDPOINT, data=current_payload, headers=headers)
        response.raise_for_status()

        response_data = response.json()

        # Extract and store the DER ID and its details
        # Assuming response structure like: {"data": {"id": "der_id", ...}} or {"id": "der_id"}
        der_id = None
        if "data" in response_data and isinstance(response_data["data"], dict) and "id" in response_data["data"]:
            der_id = response_data["data"]["id"]
        elif "id" in response_data:
            der_id = response_data["id"]
        
        if der_id is not None:
            created_ders_details.append({
                "id": der_id,
                "appliance_id": appliance_id,
                "er_id": latest_er_id
            })
            # print(f"Current DERs: {created_ders_details}") # For debugging
            print(f"DER created for {selected_appliance_name} with ID: {der_id}")
        else:
            return f"Successfully called API, but could not extract DER ID from response: {response_data}"
            
        return json.dumps(response_data)

    except requests.exceptions.HTTPError as http_err:
        error_details = ""
        if hasattr(response, 'text'):
            try:
                error_details = response.text
            except Exception:
                pass # Keep error_details empty if response.text is not accessible
        return f"HTTP error occurred: {http_err} - Details: {error_details}"
    except requests.exceptions.RequestException as req_err:
        return f"Error calling API: {req_err}"
    except json.JSONDecodeError as json_err:
        return f"Error decoding JSON: {json_err}"
    except Exception as e:
        return f"An unexpected error occurred in create_der: {e}"


def toggle_der(search_query: str) -> str:
    """
    Toggles the state of the latest DER matching the appliance name found in the search query.
    It sends a POST request to an API endpoint like /der/{der_id}/on or /der/{der_id}/off.

    Args:
        search_query (str): The search query to toggle the DER. 
                            Example: "Turn on the Ceiling Fan" or "Switch Laptop Charger off".

    Returns:
        str: A string representation of the JSON response from the API, or an error message.
    """
    global created_ders_details

    if not created_ders_details:
        return "Error: No DERs have been created yet. Cannot toggle."

    # Parse action (on/off) and appliance name
    switched_on_flag = None
    search_query_lower = search_query.lower()

    # Determine action: on or off
    if "turn on" in search_query_lower or "switch on" in search_query_lower:
        switched_on_flag = True
    elif "turn off" in search_query_lower or "switch off" in search_query_lower:
        switched_on_flag = False
    # General check if specific phrases didn't match
    elif " on" in search_query_lower and not (" off on" in search_query_lower) : # Avoid "off on"
         switched_on_flag = True
    elif " off" in search_query_lower:
         switched_on_flag = False

    if switched_on_flag is None:
        return f"Error: Could not determine action (on/off) from search query: '{search_query}'"

    target_appliance_name = None
    target_appliance_id = None
    for key_in_map in APPLIANCE_MAPPING.keys():
        if key_in_map.lower() in search_query_lower:
            target_appliance_name = key_in_map
            target_appliance_id = APPLIANCE_MAPPING[target_appliance_name]
            break
    
    if not target_appliance_id:
        return f"Error: Could not find a recognized appliance name in search query: '{search_query}'. Available: {list(APPLIANCE_MAPPING.keys())}"

    # Find the latest DER ID and associated ER ID for this appliance type
    der_id_to_toggle = None
    er_id_for_toggle = None
    for der_info in reversed(created_ders_details):
        if der_info["appliance_id"] == target_appliance_id:
            der_id_to_toggle = der_info["id"]
            er_id_for_toggle = der_info["er_id"]
            break
            
    if not der_id_to_toggle or not er_id_for_toggle:
        return f"Error: No DER found for appliance '{target_appliance_name}' with an associated ER ID. Please create one first."

    try:
        # Construct the new API URL: API_TOOGLE_DER_ENDPOINT/{er_id}
        # Ensure no double slashes if API_TOOGLE_DER_ENDPOINT ends with /
        base_toggle_url = API_TOOGLE_DER_ENDPOINT.rstrip('/')
        toggle_api_url = f"{base_toggle_url}/{er_id_for_toggle}"
        
        payload = {
            "der_id": str(der_id_to_toggle), # Ensure der_id is a string if API expects it
            "switched_on": switched_on_flag
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(toggle_api_url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Try to return JSON if possible, otherwise text
        try:
            response_data = response.json()
            return json.dumps(response_data)
        except json.JSONDecodeError:
            return response.text if response.text else "Success (No content in response)"

    except requests.exceptions.HTTPError as http_err:
        error_details = ""
        if hasattr(response, 'text'):
            try:
                error_details = response.text
            except Exception:
                pass
        return f"HTTP error occurred while toggling DER: {http_err} - Details: {error_details}"
    except requests.exceptions.RequestException as req_err:
        return f"Error calling toggle API: {req_err}"
    except Exception as e:
        return f"An unexpected error occurred in toggle_der: {e}"
