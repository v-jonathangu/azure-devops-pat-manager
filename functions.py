import atexit
import base64
import getpass
import json
import sys
import requests
import msal
import logging
import os

from msal_extensions import *

# you can get more information about MSAL for python here:
# https://github.com/AzureAD/microsoft-authentication-library-for-python
# for more information abouth the PAT api check here:
# https://learn.microsoft.com/en-us/rest/api/azure/devops/tokens/?view=azure-devops-rest-7.1&tabs=powershell
# https://learn.microsoft.com/en-us/rest/api/azure/devops/tokens/pats?view=azure-devops-rest-7.1


def save_token_cache(location, token_cache):
    if token_cache.has_state_changed:
        with open(location, "w") as f:
            f.write(token_cache.serialize())
            logging.info("Token cache saved to %s", location or "in memory")
    else:
        logging.info("Token cache unchanged, skipping save.")

def build_persistence(location, fallback_to_plaintext=False):
    # try to get a secure storage, if it fails, fallback to plaintext
    if sys.platform.startswith('win'):
        return FilePersistenceWithDataProtection(location)
    if sys.platform.startswith('darwin'):
        return KeychainPersistence(location, "AzPAT_Manager", "AzPAT_Manager")
    if sys.platform.startswith('linux'):
        try:
            return LibsecretPersistence(
                location,
                schema_name="AzPAT_Manager",
                attributes={"application": "AzPAT_Manager",
                            "flavor": "python"},
            )
        except:
            if not fallback_to_plaintext:
                raise
            logging.exception(
                "Encryption unavailable. Opting in to plain text.")
    return FilePersistence(location)


def get_access_token_cache():
    persistence = build_persistence("token.bin")
    token_cache = PersistedTokenCache(persistence)
    if os.path.exists("token.bin"):
        token_cache.deserialize(open("token.bin", "r").read())
    atexit.register(save_token_cache, "token.bin", token_cache)
    return token_cache



def get_config():
    """
    Gets the configuration from the config.json file

    your configuration will look like this example:
    {
        "authority": "https://login.microsoftonline.com/common",
        "client_id": "00000000-0000-0000-0000-000000000000",
        "scope": [
            "permission1 permission2 permission3"
        ],
        "organization": "your_organization",
        "api_version": "7.1-preview.1"
    }
    """
    return json.load(open('config.json'))


def device_flow_token(app, config):
    flow = app.initiate_device_flow(scopes=config["scope"])
    # print the message on the screen and wait for the code
    print(flow["message"])
    if "user_code" not in flow:
        raise ValueError(
            "Fail to create device flow. Err: %s" % json.dumps(flow, indent=4))
    return app.acquire_token_by_device_flow(flow)


def interactive_flow_token(app, config):
    return app.acquire_token_interactive(config["scope"])

def username_password_flow_token(app, config):
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ", stream=None)
    return app.acquire_token_by_username_password(username, password, config["scope"])


# key pair of supported names and functions
flows = {
    "device_flow": device_flow_token,
    "interactive": interactive_flow_token,
    "username_password": username_password_flow_token,
}


def get_access_token(cache: msal.SerializableTokenCache, preferred_flow=None):
    config = get_config()
    if cache is not None:
        app = msal.PublicClientApplication(
            config['client_id'], authority=config['authority'], token_cache=cache)
        # get the first account in the cache
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(
                config['scope'], account=accounts[0])
            if "access_token" in result:
                return result["access_token"]
    else:
        # if there is no cache
        app = msal.PublicClientApplication(
            config["client_id"], authority=config["authority"],
        )

    # here you can use other authentication methods
    # keep in mind that some methods require a user interaction
    # and may not support caching
    if preferred_flow is None:
        preferred_flow = "interactive"

    if preferred_flow in flows:
        result = flows[preferred_flow](app, config)
    else:
        raise ValueError(
            "Unsupported preferred_flow. Supported flows are: " +
            ", ".join(flows.keys())
        )

    if "access_token" in result:
        # here we can use the result["access_token"] to use the DevOps API
        return result["access_token"]
    return {
        "error": result.get("error"),
        "error_description": result.get("error_description"),
        "correlation_id": result.get("correlation_id"),
    }


def get_base_url():
    config = get_config()
    organization = config["organization"]
    api_version = config["api_version"]
    return f"https://vssps.dev.azure.com/{organization}/_apis/tokens/pats?api-version={api_version}"


def encode_pat(pat: str):
    """
    Encodes the personal access token (PAT) for use in an HTTP request.
    """
    return base64.b64encode(pat.encode("utf-8")).decode()


# REST api wrappers

def create_pat(access_token: str, allOrgs: bool, displayName: str, scope: str, validTo: str):
    """
    Creates a new personal access token (PAT) for the requesting user.

    parameters:
    access_token: string
        - the Azure AD access token
    allOrgs: boolean
      - True, if this personal access token (PAT) is for all of the
        user's accessible organizations.
        False, if otherwise (e.g. if the token is for a specific
        organization)
    displayName
      - the token name
    scope
      - The token scopes for accessing Azure DevOps resources
    validTo
      - The token expiration date
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    data = {
        "allOrgs": allOrgs,
        "displayName": displayName,
        "scope": scope,
        "validTo": validTo,
    }
    response = requests.post(get_base_url(), headers=headers, json=data)
    # if 203
    #   - The token is valid, but the user is not authorized to create a PAT
    if response.status_code == 201:
        return response.json()
    elif response.status_code == 203:
        return response.content


def list_pats(access_token: str):
    """
    Lists the personal access tokens (PATs) for the requesting user.

    parameters:
    access_token: string
      - the Azure AD access token
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(get_base_url(), headers=headers)
    return response.json()


def get_pat(access_token: str, authorization_id: str):
    """
    Gets a personal access token (PAT) for the requesting user.

    parameters:
    access_token: string
      - the Azure AD access token
    authorization_id: string
      - the authorization id, you can get it using the list_pats function
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(
        f"{get_base_url()}&authorizationId={authorization_id}", headers=headers)
    return response.json()


def revoke_pat(access_token: str, authorization_id: str):
    """
    Revokes a personal access token (PAT) for the requesting user.

    parameters:
    access_token: string
      - the Azure AD access token
    authorization_id: string
      - the authorization id, you can get it using the list_pats function
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.delete(
        f"{get_base_url()}&authorizationId={authorization_id}", headers=headers)
    # this endpoint returns 204 if the token was revoked
    return response.status_code == 204


def update_pat(access_token: str, authorization_id: str, allOrgs: bool, displayName: str, scope: str, validTo: str):
    """
    Updates a personal access token (PAT) for the requesting user.

    parameters:
    access_token: string
      - the Azure AD access token
    authorization_id: string
      - the authorization id, you can get it using the list_pats function
    allOrgs: boolean
      - True, if this personal access token (PAT) is for all of the
        user's accessible organizations.
        False, if otherwise (e.g. if the token is for a specific
        organization)
    displayName
      - the token name
    scope
      - The token scopes for accessing Azure DevOps resources
    validTo
      - The token expiration date
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    data = {
        "authorizationId": authorization_id,
    }
    # put the optional parameters
    if allOrgs is not None:
        data["allOrgs"] = allOrgs
    if displayName is not None:
        data["displayName"] = displayName
    if scope is not None:
        data["scope"] = scope
    if validTo is not None:
        data["validTo"] = validTo

    response = requests.put(f"{get_base_url()}",
                            headers=headers, json=data)
    return response.json()
