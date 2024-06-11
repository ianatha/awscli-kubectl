#!/usr/bin/env python3
from jwt import JWT, jwk_from_pem
import base64
import json
import time
import sys
import subprocess
import requests

def jwt_from_pem(pem, client_id):
    with open(pem, 'rb') as pem_file:
        signing_key = jwk_from_pem(pem_file.read())
        payload = {
            # Issued-At time
            'iat': int(time.time()),
            # Expiration Time (10 minutes maximum)
            'exp': int(time.time()) + 600,
            'iss': client_id
        }
        jwt_instance = JWT()
        encoded_jwt = jwt_instance.encode(payload, signing_key, alg='RS256')
        return encoded_jwt

def apply_kubectl(yaml_string):
    """Apply a Kubernetes YAML file using kubectl."""
    try:
        cmd = ['/usr/local/bin/kubectl', 'apply', '-f', '-']
        result = subprocess.run(cmd, input=yaml_string, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(e.stdout)
        print(e.stderr)

def generate_docker_auth_base64(username, password):
    user_pass_str = f"{username}:{password}"
    encoded_user_pass = base64.b64encode(user_pass_str.encode()).decode()
    data = {
        "auths": {
            "ghcr.io": {
                "username": username,
                "password": password,
                "auth": encoded_user_pass
            }
        }
    }
    json_str = json.dumps(data)
    result_base64 = base64.b64encode(json_str.encode()).decode()
    return result_base64

def generate_k8s_secret(input_value, name, namespace):
    # Formatting the string with the placeholders replaced by the function arguments.
    template = f"""apiVersion: v1
data:
    .dockerconfigjson: {input_value}
kind: Secret
metadata:
    name: {name}
    namespace: {namespace}
type: kubernetes.io/dockerconfigjson"""
    return template

def generate_k8s_httpsecret(username, password, name, namespace):
    # Formatting the string with the placeholders replaced by the function arguments.
    template = f"""apiVersion: v1
kind: Secret
metadata:
    name: {name}
    namespace: {namespace}
data:
    username: {base64.b64encode(username.encode()).decode()}
    password: {base64.b64encode(password.encode()).decode()}
type: Opaque"""
    return template

def get_installation_id(jwt, username):
    url = "https://api.github.com/app/installations"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {jwt}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        installations = response.json()
        for installation in installations:
            if installation['account']['login'].lower() == username.lower():
                return installation['id']
    return None

def generate_access_token(jwt, installation_id):
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {jwt}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    response = requests.post(url, headers=headers)
    res = response.json()
    return res['token']

def tenant_name(name):
    return f"tenant-{name[0].lower()}{len(name)-1}"

pemfile = sys.argv[1]
client_id = sys.argv[2]
username = sys.argv[3]
orgname = sys.argv[4]

jwt = jwt_from_pem(pemfile, client_id)
password = generate_access_token(jwt, get_installation_id(jwt, orgname))
yamlsecret = generate_k8s_secret(generate_docker_auth_base64(username, password), "ghcr-credentials", tenant_name(orgname))
apply_kubectl(yamlsecret)
httpsecret = generate_k8s_httpsecret(username + "[bot]", password, tenant_name(orgname) + "-apeirobot", "flux-system")
apply_kubectl(httpsecret)
