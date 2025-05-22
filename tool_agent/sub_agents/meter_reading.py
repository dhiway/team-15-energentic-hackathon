import requests
from google.adk.agents import Agent
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timezone
import json

load_dotenv()

API_METER_ENDPOINT = "http://world-engine-team7.becknprotocol.io/meter-data-simulator/meters"
API_METER_HISTORY_ENDPOINT = "http://world-engine-team7.becknprotocol.io/meter-data-simulator/meter-datasets"

# Global list to store meter IDs from responses
meter_ids_list = []
# Global counter for meter codes, starting from 4
current_meter_id_counter = 328

# New global variables for transformer IDs
TRANSFORMER_IDS = [180,181,182,183,184,185,186,187,188,189,175,176,177,178,179]
current_transformer_index = 0


METER_CREATE_TEMPLATE = """{
    "data": {
        "code": "{{code}}",
        "parent": null,
        "energyResource": null,
        "consumptionLoadFactor": 1.0,
        "productionLoadFactor": 0.0,
        "type": "SMART",
        "city": "San Francisco",
        "state": "California",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "pincode": "94103",
        "transformer": "{{transformer}}"
    }
}"""

def create_meter_data(search_query: str) -> str:
    """
    Creates a meter data based on a given search query.
    The meter code is auto-incremented for each request.
    The ID from the response is stored in a global list.
    The transformer ID is selected cyclically from a predefined list.
    This function will be used as a tool by the agent.

     Returns:
        A string representation of the JSON response from the API, containing all meter data,
        or an error message.
    """
    global current_meter_id_counter
    global meter_ids_list
    global current_transformer_index

    try:
        bap_id = os.getenv("bap_id")
        bap_uri = os.getenv("bap_uri")
        bpp_id = os.getenv("bpp_id")
        bpp_uri = os.getenv("bpp_uri")

        if not all([bap_id, bap_uri, bpp_id, bpp_uri]):
            return "Error: BAP_ID, BAP_URI, BPP_ID, or BPP_URI environment variables are not set."

        transaction_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        # Increment meter ID counter and format the new meter code
        current_meter_id_counter += 1
        code = f"METER{current_meter_id_counter:03}"

        # Prepare payload by parsing the template string into a dictionary
        payload_dict = json.loads(METER_CREATE_TEMPLATE)
        # Update the meter code
        payload_dict["data"]["code"] = code
        
        # Assign transformer ID cyclically
        if TRANSFORMER_IDS: # Check if the list is not empty
            transformer = TRANSFORMER_IDS[current_transformer_index]
            # payload_dict["data"]["transformer"] is now {"id": "{{transformer_id_placeholder}}"}
            # Update the value of the "id" key within this dictionary.
            payload_dict["data"]["transformer"] = transformer
            current_transformer_index = (current_transformer_index + 1) % len(TRANSFORMER_IDS)
        else:
            # Default to null for the entire transformer field if TRANSFORMER_IDS is empty
            # This will replace the {"id": "{{transformer_id_placeholder}}"} object.
            payload_dict["data"]["transformer"] = None
        
        # Convert the dictionary back to a JSON string for the request
        current_payload = json.dumps(payload_dict)
        
        # The original replacements for context variables are not in the template anymore.
        # If they were intended to be part of the payload sent to API_METER_ENDPOINT,
        # they should be added to the `payload_dict` before `json.dumps`.
        # For now, assuming they are not needed directly in this specific payload.
        # Example: If they were needed in a context block (not shown in METER_CREATE_TEMPLATE):
        # payload_dict['context'] = {
        #     "bap_id": bap_id, "bap_uri": bap_uri, "bpp_id": bpp_id, "bpp_uri": bpp_uri,
        #     "transaction_id": transaction_id, "message_id": message_id, "timestamp": timestamp
        # }
        # current_payload = json.dumps(payload_dict)


        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_METER_ENDPOINT, data=current_payload, headers=headers)
        response.raise_for_status()
        
        response_data = response.json()
        
        # Extract and store the ID
        if "data" in response_data and "id" in response_data["data"]:
            meter_ids_list.append(response_data["data"]["id"])
            # You can print or log the list to see it grow:
            print(f"Current meter IDs: {meter_ids_list}")
        
        return response_data
    except requests.exceptions.HTTPError as http_err:
        error_details = ""
        try:
            error_details = response.text
        except Exception:
            pass
        return f"HTTP error occurred: {http_err} - {error_details}"
    except requests.exceptions.RequestException as e:
        return f"Error calling API: {e}"
    except ValueError as json_err: # Catch errors from json.loads or response.json()
        error_details = ""
        try:
            # If response object exists, try to get its text
            if 'response' in locals() and response is not None:
                error_details = response.text
            else: # Otherwise, the error might be from parsing METER_CREATE_TEMPLATE
                error_details = "Could not parse METER_CREATE_TEMPLATE or API response"
        except Exception:
            pass
        return f"Error decoding JSON: {json_err} - Details: {error_details}"
    except Exception as e: # Catch any other unexpected errors
        return f"An unexpected error occurred: {e}"


def get_meter_history() -> str:
    """
    Retrieves the history of meter readings for the latest created meter ID.

    Returns:
        A string representation of the JSON response from the API, containing all meter history data,
        or an error message if no meter IDs are available or an API error occurs.
    """
    global meter_ids_list

    if not meter_ids_list:
        return "Error: No meter IDs available in the list. Please create a meter first."

    try:
        # Get the latest meter ID from the list
        latest_meter_id = meter_ids_list[-1]

        response = requests.get(API_METER_HISTORY_ENDPOINT + f"/{latest_meter_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_details = ""
        # It's good practice to check if 'response' exists before trying to access response.text
        if 'response' in locals() and hasattr(response, 'text'):
            try:
                error_details = response.text
            except Exception:
                pass # Keep error_details empty if response.text is not accessible
        return f"HTTP error occurred while retrieving meter history: {http_err} - {error_details}"
    except requests.exceptions.RequestException as req_err:
        return f"Error calling meter history API: {req_err}"
    except Exception as e:
        error_context = ""
        if 'response' in locals() and hasattr(response, 'text'):
             error_context = f" - Response text: {response.text[:500]}" # Show first 500 chars of response
        return f"An unexpected error occurred while retrieving meter history: {e}{error_context}"