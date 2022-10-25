import atexit
import base64
import datetime
import json
import os
from platform import platform
import requests
import msal
import sys
import logging

from msal_extensions import *

# you can get more information about MSAL for python here:
# https://github.com/AzureAD/microsoft-authentication-library-for-python
# for more information abouth the PAT api check here:
# https://learn.microsoft.com/en-us/rest/api/azure/devops/tokens/?view=azure-devops-rest-7.1&tabs=powershell
# https://learn.microsoft.com/en-us/rest/api/azure/devops/tokens/pats?view=azure-devops-rest-7.1


def get_access_token_cache():
    # do not use in production, you should use a more secure storage
    # depending on the platform
    persistence = FilePersistence("token.bin")
    return PersistedTokenCache(persistence)


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


def get_access_token(cache: msal.SerializableTokenCache):
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

    # if there is no cache or the cache is empty
    app = msal.PublicClientApplication(
        config["client_id"], authority=config["authority"]
    )

    # here you can use other authentication methods
    # keep in mind that some methods require a user interaction
    # and may not support caching
    result = app.acquire_token_interactive(scopes=config["scope"])

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

# app options


def opt_create_tokens(access_token: str):
    allOrgs = input("All Organizations? (True/False): ").lower() == "true"
    displayName = input("Display Name: ")
    scope = input("Scope: ")
    time_valid = int(input("days valid: "))
    # valid to is in ISO 8601 format
    # example: 2020-12-01T23:46:23.319Z
    # is from 10 days from now
    time_now = datetime.datetime.now()
    time_10_days = time_now + datetime.timedelta(days=time_valid)
    validTo = time_10_days.isoformat()
    print(create_pat(access_token, allOrgs, displayName, scope, validTo))


def opt_list_tokens(access_token: str):
    print(list_pats(access_token))


def opt_get_token(access_token: str):
    authorization_id = input("Authorization ID: ")
    print(get_pat(access_token, authorization_id))


def opt_revoke_token(access_token: str):
    authorization_id = input("Authorization ID: ")
    print(revoke_pat(access_token, authorization_id))


def opt_update_token(access_token: str):
    authorization_id = input("Authorization ID: ")
    allOrgs = input(
        "All Organizations? (True/False) [empty for same]: ").lower()
    displayName = input("Display Name [empty for same]: ")
    scope = input("Scope [empty for same]: ")
    time_valid = input("days valid [empty for same]: ")
    # check if the values are empty
    if allOrgs != "":
        allOrgs = allOrgs == "true"
    else:
        allOrgs = None
    if displayName == "":
        displayName = None
    if scope == "":
        scope = None
    if time_valid != "":
        time_valid = int(time_valid)
        # valid to is in ISO 8601 format
        # example: 2020-12-01T23:46:23.319Z
        # is from 10 days from now
        time_now = datetime.datetime.now()
        time_10_days = time_now + datetime.timedelta(days=time_valid)
        validTo = time_10_days.isoformat()
    else:
        validTo = None

    print(update_pat(access_token, authorization_id,
          allOrgs, displayName, scope, validTo))


options = [
    ["Create a new PAT", opt_create_tokens],
    ["List all PATs", opt_list_tokens],
    ["Get a PAT", opt_get_token],
    ["Revoke a PAT", opt_revoke_token],
    ["Update a PAT", opt_update_token],
    ["Exit", exit],
]

if __name__ == '__main__':
    cache = get_access_token_cache()
    access_token = get_access_token(cache)
    option = 0
    while option != len(options):
        print("Select an option:")
        for i, option in enumerate(options):
            print(f"{i + 1}. {option[0]}")
        option = input("Option: ")
        if option.isnumeric():
            option = int(option)
            if option > 0 and option <= len(options):
                options[option - 1][1](access_token)
