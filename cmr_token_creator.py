"""AWS Lambda that creates and stores an Authrorization Bearer Token.

Stores token in SSM Parameter Store 'SecureString'. Meant to be run every 59 
days as token expires every 60 days. Logs status and the errors.

Documentation on tokens: https://urs.earthdata.nasa.gov/documentation/for_users/user_token
"""

# Standard imports
import json
import logging
import os
import sys

# Third-party imports
import boto3
import botocore
import requests
from requests.auth import HTTPBasicAuth

# Constants
HEADERS = {"Accept": "application/json"}

def lambda_handler(event, context):
    """Handles the creation of a EDL bearer token."""
    
    logger = get_logger()
    token_url = "https://urs.earthdata.nasa.gov/api/users/token"
    delete_token_url = "https://urs.earthdata.nasa.gov/api/users/revoke_token?token"
    logger.info("Attempting to create token.")
    
    try:
        username, password = get_edl_creds(logger)
        token = generate_token(username, password, token_url, delete_token_url, logger)
        store_token(token, event["prefix"], logger)
        if not token:
            logger.info("Program exiting.")
            sys.exit(1)
    except botocore.exceptions.ClientError:
        logger.info("Program exiting.")
        sys.exit(1)
        
def get_logger():
    """Return a formatted logger object."""
    
    # Remove AWS Lambda logger
    logger = logging.getLogger()
    for handler in logger.handlers:
        logger.removeHandler(handler)
    
    # Create a Logger object and set log level
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create a handler to console and set level
    console_handler = logging.StreamHandler()

    # Create a formatter and add it to the handler
    console_format = logging.Formatter("%(asctime)s - %(module)s - %(levelname)s : %(message)s")
    console_handler.setFormatter(console_format)

    # Add handlers to logger
    logger.addHandler(console_handler)

    # Return logger
    return logger

def get_edl_creds(logger):
    """Return EDL username and password stored in SSM Parameter Store.
    
    Raises botocore.exceptions.ClientError
    """
    
    try:
        ssm_client = boto3.client('ssm', region_name="us-west-2")
        username = ssm_client.get_parameter(Name="edl_username", WithDecryption=True)["Parameter"]["Value"]
        password = ssm_client.get_parameter(Name="edl_password", WithDecryption=True)["Parameter"]["Value"]
        logger.info("Retrieved EDL username and password.")
        return username, password
    except botocore.exceptions.ClientError as error:
        logger.error("Could not retrieve EDL credentials from SSM Parameter Store.")
        logger.error(error)
        raise error
    
def generate_token(username, password, token_url, delete_token_url, logger):
    """Generate and store bearer token using EDL credentials in SSM Parameter Store."""
    
    post_response = requests.post(token_url, headers=HEADERS, auth=HTTPBasicAuth(username, password))
    token_data = post_response.json()
    if "error" in token_data.keys(): 
        if token_data["error"] == "max_token_limit": 
            token = handle_token_error(token_data, username, password, token_url, delete_token_url, logger)
        else:
            logger.error("Error encountered when trying to retrieve bearer token from EDL.")
            return False
    else:
        token = token_data["access_token"]
    logger.info("Successfully generated EDL bearer token.")
    return token
    
def handle_token_error(token_data, username, password, token_url, delete_token_url, logger):
    """Attempts to handle errors encoutered in token generation and return a
    valid bearer token."""
    
    # Get all tokens and attempt to remove any that exist
    post_get = requests.get(f"{token_url}s", headers=HEADERS, auth=HTTPBasicAuth(username, password))
    token_data = post_get.json()
    for token in token_data:
        if "access_token" in token.keys():
            requests.post(f"{delete_token_url}={token['access_token']}", headers=HEADERS, auth=HTTPBasicAuth(username, password))
    
    # Generate a new token
    post_response = requests.post(token_url, headers=HEADERS, auth=HTTPBasicAuth(username, password))
    token_data = post_response.json()
    if "error" in token_data.keys():
        logger.error("Error encountered when trying to retrieve bearer token from EDL.")
        return False
    else:
        return token_data["access_token"]
    
def store_token(token, prefix, logger):
    """Store bearer token in SSM Parameter Store."""
    
    try:
        
        kms_client = boto3.client('kms', region_name="us-west-2")
        kms_response = kms_client.describe_key(KeyId=f"alias/{prefix}-ssm-parameter-store")
        key = kms_response["KeyMetadata"]["KeyId"]
        
        ssm_client = boto3.client('ssm', region_name="us-west-2")
        ssm_response = ssm_client.put_parameter(
            Name=f"bearer--edl--token",
            Description="Temporary EDL bearer token",
            Value=token,
            Type="SecureString",
            KeyId=key,
            Overwrite=True,
            Tier="Standard"
        )
        logger.info("EDL bearer token has been stored as a secure string in SSM Parameter Store.")
    except botocore.exceptions.ClientError as error:
        logger.error("Could not store EDL bearer token in SSM Parameter Store.")
        logger.error(error)
        raise error
