import requests
from google.adk.agents import Agent
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timezone
import json

# Import meter_ids_list from meter_reading.py
from .meter_reading import meter_ids_list

load_dotenv()

# Global list to store Energy Resource household IDs from responses
er_household_ids_list = []

API_ER_HOUSE_HOLD_ENDPOINT = "http://world-engine-team7.becknprotocol.io/meter-data-simulator/energy-resources"
# Base URL for GETting a specific energy resource. The ID will be appended.
ER_HOUSE_HOLD_BASE_URL = "http://world-engine-team7.becknprotocol.io/meter-data-simulator/energy-resources"
# Query parameters for the GET request
ER_HOUSE_HOLD_GET_QUERY_PARAMS = "?populate[0]=meter.parent&populate[1]=meter.children&populate[2]=meter.appliances"

ER_HOUSE_HOLD_CREATE_TEMPLATE = """
{
    "data": {
        "name": "Mudit's Home",
        "type": "CONSUMER",
        "meter": "{{latest_meter_id}}" 
    }
}
"""

def create_er_house_hold(search_query: str) -> str:
    """
    Creates a new energy resource (ER) for a household using the latest meter ID.
    The ID of the created ER is stored in a global list.

    Args:
        search_query (str): The search query to create the energy resource. (Currently unused but kept for future flexibility)

    Returns:
        str: A string representation of the JSON response from the API, containing the created energy resource,
        or an error message.
    """
    global meter_ids_list
    global er_household_ids_list # Declare global to modify it

    if not meter_ids_list:
        return "Error: No meter IDs available. Cannot create an energy resource without a meter."

    try:
        latest_meter_id = meter_ids_list[-1]

        payload_dict = json.loads(ER_HOUSE_HOLD_CREATE_TEMPLATE)
        payload_dict["data"]["meter"] = latest_meter_id
        current_payload = json.dumps(payload_dict)

        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_ER_HOUSE_HOLD_ENDPOINT, data=current_payload, headers=headers)
        response.raise_for_status()

        response_data = response.json()

        # Extract and store the ER household ID
        if "data" in response_data and "id" in response_data["data"]:
            er_household_ids_list.append(response_data["data"]["id"])
            # You can print or log the list to see it grow:
            print(f"Current ER Household IDs: {er_household_ids_list}")
        
        return response_data # Return the full response data

    except requests.exceptions.HTTPError as http_err:
        error_details = ""
        if hasattr(response, 'text'):
            try:
                error_details = response.text
            except Exception:
                pass
        return f"HTTP error occurred: {http_err} - {error_details}"
    except requests.exceptions.RequestException as req_err:
        return f"Error calling API: {req_err}"
    except json.JSONDecodeError as json_err:
        return f"Error decoding JSON template: {json_err}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"


def get_er_house_hold() -> str:
    """
    Retrieves the energy resource (ER) for a household using the latest meter ID
    associated with that ER. 
    Assumes the ER was created for the latest meter in meter_ids_list.

    Returns:
        str: A string representation of the JSON response from the API, containing the energy resource,
        or an error message. 
    """
    global meter_ids_list # meter_ids_list contains IDs of meters, not ER households directly.
                         # We need the ID of the ER household itself.
                         # For now, assuming the user wants to fetch an ER whose *associated meter* is the latest.
                         # The endpoint structure `energy-resources/{id}` suggests we need the ER ID.
                         # If the intention is to find an ER *by its meter ID*, the API endpoint might be different
                         # or require query parameters.
                         # Given the current API_GET_ER_HOUSE_HOLD_ENDPOINT provided by user:
                         # "http://world-engine-team7.becknprotocol.io/meter-data-simulator/energy-resources/1664?..."
                         # This `1664` should be the *Energy Resource ID*, not the meter ID.
                         # This function needs a way to get the ID of the ER that was just created or is relevant.

    # Clarification: The prompt says "dynamically add the latest_meter_id to this api in the place of 1664".
    # This implies the ID in that path *is* the meter ID, or is somehow derived from it.
    # Or, the user assumes the ER ID is the same as the meter ID. This is unlikely.
    # Let's assume the user *meant* that the ID in the path should be the latest *meter ID*.
    # The API structure `energy-resources/{id}` usually means `id` is the ID of the energy resource.
    # If the API allows fetching an energy resource *using its associated meter's ID directly in the path like this*, then it's fine.
    # Otherwise, this function will need modification or clarification on how to get the ER ID.

    if not meter_ids_list:
        return "Error: No meter IDs available. Cannot determine which energy resource to fetch."

    try:
        # Assuming the ID in the path of API_GET_ER_HOUSE_HOLD_ENDPOINT should be the latest meter_id
        latest_id_for_path = meter_ids_list[-1]
        
        # Construct the URL dynamically
        request_url = f"{ER_HOUSE_HOLD_BASE_URL}/{latest_id_for_path}{ER_HOUSE_HOLD_GET_QUERY_PARAMS}"
        
        headers = {'Content-Type': 'application/json'} # GET requests usually don't need Content-Type for the body
                                                      # but it doesn't harm to send it if API expects/tolerates it.
        response = requests.get(request_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        return response.json()  # Return the JSON response from the API

    except requests.exceptions.HTTPError as http_err:
        error_details = ""
        if hasattr(response, 'text'):
            try:
                error_details = response.text
            except Exception:
                pass
        return f"HTTP error occurred while fetching ER household: {http_err} - {error_details}"
    except requests.exceptions.RequestException as req_err:
        return f"Error calling API to fetch ER household: {req_err}"
    except json.JSONDecodeError as json_err: # If the response isn't valid JSON
        error_text = ""
        if hasattr(response, 'text'):
            error_text = response.text
        return f"Error decoding JSON response from ER household API: {json_err}. Response text: {error_text[:500]}"
    except Exception as e:
        return f"An unexpected error occurred while fetching ER household: {e}"
