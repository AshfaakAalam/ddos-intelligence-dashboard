"""This file calls the CloudFlare api
gets the top 5 attacks percentage , from source country to target country
and returns a list of dictionary """


import requests
from dotenv import load_dotenv
import os

load_dotenv()


account_id = os.getenv("ACCOUNT_ID")
api_token = os.getenv("API_TOKEN")

url = (
    f"https://api.cloudflare.com/client/v4/radar/attacks/layer7/top/attacks"
)
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json" ,
    }


def get_attack_data():

    params = {
    "dateRange":"1d",
    "normalization":"PERCENTAGE"
}
    response = requests.get(url , headers=headers, params=params) 

    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.json()
