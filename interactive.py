# app options
from functions import *
import datetime


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

def interactive_main():
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