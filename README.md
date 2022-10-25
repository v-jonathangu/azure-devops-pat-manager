# Python PAT manager for Azure Devops

this package lets you manage your PATs for Azure Devops. It is a wrapper around the Azure Devops API.

## quick setup

in order to run this package
- install python
- install the package requirements `pip install -r requirements.txt`
- create a config.json like the following:
  - ```json
    {
        "authority": "https://login.microsoftonline.com/common",
        "client_id": "00000000-0000-0000-0000-000000000000",
        "scope": [
            "permission1 permission2 permission3"
        ],
        "organization": "your_organization",
        "api_version": "7.1-preview.1"
    }
    ```
    then change `client_id`, `scope` and `organization`
    > the required scope for user impersonation(Azure DevOps API access) is `499b84ac-1321-427f-aa17-267ca6975798/.default`
- run with python `source.py`
  ```sh
  python source.py
  ```
> keep in mind that the instalation of python may vary depending of your OS, for example some linux distributions have python3 instead of python or pip may be also required to install along it, please check your OS documentation for more information

---

### Azure AD App setup

you will also need to setup a Azure AD app in order to use the app, for more information check [Use the portal to create an Azure AD application and service principal that can access resources](https://learn.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal#register-an-application-with-azure-ad-and-create-a-service-principal)

## useful links 

the following links may help you setting up and similar example or modifying this one

 - [Authorize access to REST APIs with OAuth 2.0](https://learn.microsoft.com/en-us/azure/devops/integrate/get-started/authentication/oauth?view=azure-devops)
 - [MSAL library for python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
 - for more information about the PAT api check here
   - [Tokens (Azure DevOps)](https://learn.microsoft.com/en-us/rest/api/azure/devops/tokens/?view=azure-devops-rest-7.1&tabs=powershell)
   - [PAT Lifecycle Management API(Azure DevOps)](https://learn.microsoft.com/en-us/rest/api/azure/devops/tokens/pats?view=azure-devops-rest-7.1)
