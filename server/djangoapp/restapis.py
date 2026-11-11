import requests
import os
from dotenv import load_dotenv

load_dotenv()

backend_url = os.getenv(
    'backend_url', default="http://localhost:3030")
sentiment_analyzer_url = os.getenv(
    'sentiment_analyzer_url',
    default="http://localhost:5050/")

def get_request(endpoint, **kwargs):
    params = ""
    if(kwargs):
        for key,value in kwargs.items():
            params=params+key+"="+value+"&"

    request_url = backend_url+endpoint+"?"+params

    print("GET from {} ".format(request_url))
    try:
        # Call get method of requests library with URL and parameters
        response = requests.get(request_url)
        return response.json()
    except:
        # If any error occurs
        print("Network exception occurred")

def analyze_review_sentiments(text):
    request_url = sentiment_analyzer_url+"analyze/"+text
    try:
        # Call get method of requests library with URL and parameters
        response = requests.get(request_url)
        return response.json()
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        print("Network exception occurred")

# Add post_review function here if requested in future steps
def post_review(data_dict):
    request_url = backend_url.rstrip("/") + "/insert_review"

    print(f"POST to {request_url}")
    print(f"Review fields: {list(data_dict.keys())}")

    try:
        response = requests.post(
            request_url,
            json=data_dict,
            timeout=15
        )

        print(f"Backend HTTP status: {response.status_code}")
        print(f"Backend response: {response.text}")

        # Raise an exception for HTTP 4xx or 5xx errors
        response.raise_for_status()

        result = response.json()

        if result is None:
            raise ValueError("Backend returned null")

        return result

    except (requests.RequestException, ValueError) as err:
        print(f"Review submission failed: {err}")
        raise
