# ## References:
#
# - [Bulk User Imports](https://auth0.com/docs/manage-users/user-migration/bulk-user-imports)
# - [Create User Import Job](https://auth0.com/docs/api/management/v2/jobs/post-users-imports)
# - [Bulk User Import JSON Schema](https://auth0.com/docs/manage-users/user-migration/bulk-user-import-database-schema-and-examples)

import os
import json
import bcrypt  # auth0 default encryption
import requests
import time
from dotenv import load_dotenv
from pathlib import Path
from io import StringIO

# auth0 username max length
MAX_USERNAME_LENGTH = 5  # Auth0 username max length


# to os and load .env from project root
def get_env_var(var_name, default=None):
    value = os.getenv(var_name)
    # if not in evn, try loading from .env
    if value is None:
        dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path)
            value = os.getenv(var_name)
    if value is None:
        return default
    return value


DOMAIN = get_env_var("AUTH0_SECRET_DOMAIN")
CLIENT_ID = get_env_var("AUTH0_SECRET_CLIENT_ID")
CLIENT_SECRET = get_env_var("AUTH0_SECRET_CLIENT_SECRET")
CONNECTION_NAME = get_env_var("AUTH0_SECRET_CONNECTION_NAME", "Username-Password-Authentication")
if DOMAIN is None or CLIENT_ID is None or CLIENT_SECRET is None:
    raise ValueError(
        f"Make sure to set \nAUTH0_SECRET_DOMAIN \nAUTH0_SECRET_CLIENT_ID \nAUTH0_SECRET_CLIENT_SECRET \n in your environment variables or in a .env file at the project root."
    )
BEAERER_TOKEN = None  # to be set after getting token

def get_bearer_token(domain, client_id, client_secret):
    headers = {"content-type": "application/json"}
    payload = {"client_id": client_id, "client_secret": client_secret, "audience": f"https://{domain}/api/v2/", "grant_type": "client_credentials"}
    response = requests.post(f"https://{domain}/oauth/token", json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print("❌ Error obtaining bearer token:")
        print(response.status_code, response.text)
        return None



# Retrieve the connection ID for a specific Auth0 connection.
# API Reference: https://auth0.com/docs/api/management/v2/connections/get-connections
def get_connection_id(domain, access_token, connection_name="Username-Password-Authentication"):
    url = f"https://{domain}/api/v2/connections"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"strategy": "auth0"}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        for key, value in response.json().items():
            print(f"{key}: {value}")
        return None, None
    connections = response.json()
    return (
        next(conn["id"] for conn in connections if conn["name"] == connection_name),
        response.json(),
    )


# Retrieve the options by connection id
# https://auth0.com/docs/api/management/v2/connections/get-connections-by-id
# https://auth0.com/docs/authenticate/identity-providers/retrieve-connection-options
def get_connection(domain, access_token, connection_id):
    url = url = f"https://{domain}/api/v2/connections/{connection_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"fields": "options"}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(f"Error: {response.text()}")
        
        return None
    return response.json()

# Auth0 prefers bcryp for hashing
# Hash a password using bcrypt with 10 salt rounds.
def hash_password(password):
    # Generate a salt
    salt = bcrypt.gensalt(rounds=10)
    # Hash the password with the salt
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_password.decode("utf-8")


# Create a user dictionary with hashed password and other details.
# email_verified should be set to True to avoid accidental attempts to verify the email.
def create_user(prefix="user", domain="example.com", password=None, i=1):
    username = f"{prefix}{i:02d}"
    if password is None:
        password = username
    return {
        "email": f"{username}@{domain}",
        "email_verified": True,
        "password_hash": hash_password(password),
        "name": f"{username}@{domain}",
        "nickname": username,  # optional
        "username": username,
    }


def create_user_from_username_and_password(username, domain="example.com", password=None):
    if password is None:
        password = username
    return {
        "email": f"{username}@{domain}",
        "email_verified": True,
        "password_hash": hash_password(password),
        "name": f"{username}@{domain}",
        "nickname": username,  # optional
        "username": username,
    }


# Create a list of users with the same prefix and domain.
def create_users(prefix, domain="example.com", N=5, password=None):
    return [create_user(prefix, domain, password, i) for i in range(1, N + 1)]


# Create a JSON file with user data for bulk import.
def create_users(prefix, domain="example.com", N=5, password=None):
    return [create_user(prefix, domain, password, i) for i in range(1, N + 1)]


def create_users_with_passwords(usernames, passwords=None, domain="example.com"):
    if passwords is None:
        return [create_user_from_username_and_password(u, domain=domain, password=None) for u in usernames]
    if len(usernames) != len(passwords):
        raise ValueError(f"usernames and passwords must have the same length: len(users) {len(usernames)}, len(pass) {len(passwords)}")
    return [create_user_from_username_and_password(u, domain=domain, password=p) for u, p in zip(usernames, passwords)]


# Create a JSON file with user data for bulk import.
def create_user_file(prefix, domain="example.com", N=5, password=None, id=None, create_file=True):
    """
    Generate a JSON file containing user data.
    Pass a value to `id` to create a single user. Useful for testing.
    Set the password, otherwise it will default to the username (i.e., prefix_01, ...).
    ️If create_file is False, the function will return the JSON string instead of creating a file.
    """
    if id is None:
        users = create_users(prefix, domain, N, password)
    else:
        users = [create_user(prefix, domain, password, id)]

    if not create_file:
        return users

    filename = f"{prefix}_users.json"
    with open(filename, "w") as f:
        json.dump(users, f, indent=4)
    print(f"Created {filename} with {len(users)} users.")
    return filename


# Create a JSON import payload using explicit username/password lists.
def create_user_file_from_list(usernames, passwords=None, domain="example.com", create_file=True):
    """
    Create users from parallel username/password lists.
    Pass `passwords=None` to use each username as the password.
    """
    users = create_users_with_passwords(usernames, passwords, domain)

    if not create_file:
        return users

    filename = f"{usernames[0]}_users.json"
    with open(filename, "w") as f:
        json.dump(users, f, indent=4)
    print(f"Created {filename} with {len(users)} users.")
    return filename



# Start a bulk user import job in Auth0.
# API Reference: https://auth0.com/docs/api/management/v2/jobs/post-users-imports
def start_import_job(filename, connection_id, domain, access_token, external_id=None):
    url = f"https://{domain}/api/v2/jobs/users-imports"
    headers = {"Authorization": f"Bearer {access_token}"}

    def _make_request(filename, fobj):
        files = {
            "users": (filename, f.read(), "application/json"),
            "connection_id": (None, connection_id),
            "send_completion_email": (None, "false"),
            "upsert": (None, "false"),
        }

        if external_id:
            files["external_id"] = (None, external_id)

        return requests.post(url, headers=headers, files=files)
        
    
    if isinstance(filename, StringIO):
        with filename as f:
            filename = "users.json"
            response = _make_request(filename, f)
    else:
        with open(filename, "rb") as f:
            response = _make_request(filename, f)

    if response.status_code == 200 or response.status_code == 202:
        job = response.json()
        print("Import job started successfully.")
        return job
    else:
        print("❌ Error during users-imports:")
        print(response.status_code, response.text)
    return response




# Check the status of a bulk user import job in Auth0.
# API Reference: https://auth0.com/docs/api/management/v2/jobs/get-jobs-by-id
def check_job_status(job, connection_id, domain, access_token, sleep=5):
    if job is None:
        return None
    url = f"https://{domain}/api/v2/jobs/{job['id']}"
    headers = {"Authorization": f"Bearer {access_token}"}

    pending = True
    while pending:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            job_status = response.json()
            pending = job_status["status"] == "pending"
            if pending:
                print("Waiting for job to complete... (5 seconds)")
                time.sleep(5)
        else:
            print("❌ Error during job status check:")
            print(response.status_code, response.text)
            return response

    print(f"Job id: {job_status['id']}")
    print(f"Job status: {job_status['status']}")
    print(f"Job summary: {job_status['summary']}")
    return job_status

def get_job_errors(job, domain, access_token):
    if job is None:
        return None
    url = f"https://{domain}/api/v2/jobs/{job['id']}/errors"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("Retrieved job errors successfully.")
        errors = response.json()
        return errors
    elif response.status_code == 204:
        print("No job errors found.")
        return []
    else:
        print("❌ Error retrieving job errors:")
        print(response.status_code, response.text)
        return None
# PREFIX = "john_quick_test" # username will look like imfake_01, imfake_02, etc.
# EMAIL_DOMAIN = "test.edu" # email will look like imfake_01@email_domain
# FILENAME = create_user_file(prefix=PREFIX, domain=EMAIL_DOMAIN, N=1)


# job = start_import_job(
#     filename=FILENAME,
#     connection_id=CONNECTION_ID,
#     domain=DOMAIN,
#     access_token=MGMT_API_ACCESS_TOKEN,
# )

# job_status = check_job_status(job, CONNECTION_ID, DOMAIN, MGMT_API_ACCESS_TOKEN)


def search_users(domain, access_token, query: str):
    """
    query fiven in Lucene syntax
    # o = search_users(DOMAIN, MGMT_API_ACCESS_TOKEN, "email:*nodeclass*")
    """
    url = f"https://{domain}/api/v2/users"
    headers = {"Authorization": f"Bearer {access_token}"}
    # query parameters
    params = {
        "fields": "username,email,user_id",
        "include_fields": "true",
        "q": query,
    }
    response = requests.get(url, headers=headers, params=params)
    print(response.url)
    if response.status_code == 200:
        users = response.json()
        print(f"Found {len(users)} users.")
        return users
    else:
        print("❌ Error during user search:")
        print(response.status_code, response.text)
    return None


def delete_user(domain, access_token, user_id):
    raise NotImplementedError("CAUTION: NOT GOING TO DO THIS. THIS JUST SHOWS THE IMPLEMENTATION")
    url = f"https://{domain}/api/v2/users/{user_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.request("DELETE", url, headers=headers)
    return response
