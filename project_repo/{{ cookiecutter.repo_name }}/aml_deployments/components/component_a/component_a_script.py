"""Example component.

Note that package a and b do not exist so this code does not work,
but conceptually should work if you publish the raptor package repo twice, as package a and b.
"""
# ruff: noqa: T201, INP001

import argparse

from example_package.examples import divide, multiply

# # example how to use environment variables
# import os
# kv_name = os.environ["KEY_VAULT_NAME"]
# # extended example for loading secrets from keyvault
# from azure.identity import DefaultAzureCredential
# from azure.keyvault.secrets import SecretClient
# kv_uri = f"https://{kv_name}.vault.azure.net"
# # loading credentials, should load from session.
# # Works both for developing locally in compute instance (uses user credentials via DefaultAzureCredential) and
# # in azureml jobs (uses AML compute cluster managed identity via ManagedIdentityCredential)
# credential = DefaultAzureCredential()
# client = SecretClient(vault_url=kv_uri, credential=credential)
# secret_value = client.get_secret("SECRET_NAME").value


def parse_args() -> argparse.Namespace:
    """Function to parse the arguments.

    Returns:
        argparse.Namespace: object with parsed arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--operator", type=str, default="multiply", help="Multiply or divide"
    )
    parser.add_argument("--a", type=float)
    parser.add_argument("--b", type=float)
    return parser.parse_args()


def main() -> None:
    """Main function for this component."""
    args = parse_args()
    if args.operator == "multiply":
        result = multiply(args.a, args.b)
        print(f"{args.a} * {args.b} = {result}")
    else:
        result = divide(args.a, args.b)
        print(f"{args.a} / {args.b} = {result}")


if __name__ == "__main__":
    main()
