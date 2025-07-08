"""Invoke batch endpoint in Azure Machine Learning using test input data.

Invokes batch endpoint and writes results to the output location based on Azure DevOps pipeline build number.
MS Docs:
https://learn.microsoft.com/en-us/azure/machine-learning/how-to-use-batch-scoring-pipeline?view=azureml-api-2&tabs=python
https://learn.microsoft.com/en-us/azure/machine-learning/how-to-access-data-batch-endpoints-jobs?view=azureml-api-2&tabs=sdk

Args:
    endpoint_name: name of batch endpoint
    deployment_name: name of batch deployment
    input_data: input data path
    output_data: output data path

Returns:
    batch job details

"""
# ruff: noqa: INP001, TD002, N816, T201

import logging
import os
from argparse import ArgumentParser

from azure.ai.ml import Input, MLClient, Output
from azure.identity import DefaultAzureCredential

# TODO: Place in separate file.
# Define format new logger
logger = logging.getLogger()
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)
logger.setLevel(logging.INFO)


def main() -> None:
    """Invokes batch endpoint in AzureML with custom input and output."""
    parser = ArgumentParser()
    endpoint_name = "Name of batch endpoint"
    parser.add_argument("--endpoint_name", required=True, type=str, help=endpoint_name)
    deployment_name = "Name of batch deployment. If not passed, uses default deployment"
    parser.add_argument(
        "--deployment_name", required=False, type=str, help=deployment_name
    )
    input_data = "Input data path"
    parser.add_argument(
        "--input_data",
        required=True,
        type=str,
        help=input_data,
        default="azureml://datastores/rdameuwdvlmdloxgn01_datascience/paths/azureml",
    )
    output_data = "Output data path. If not passed, uses default output path"
    parser.add_argument(
        "--output_data",
        required=False,
        type=str,
        help=output_data,
        default="azureml://datastores/[datastore_name]/paths/[folder_on_datastore]/output.csv",
    )
    args = parser.parse_args()

    ENDPOINT_NAME = args.endpoint_name
    DEPLOYMENT_NAME = args.deployment_name
    INPUT_DATA = args.input_data
    OUTPUT_DATA = args.output_data

    logger.info("Endpoint name: %s", ENDPOINT_NAME)
    logger.info("Deployment name: %s", DEPLOYMENT_NAME)
    logger.info("Input data path: %s", INPUT_DATA)
    logger.info("Output data path: %s", OUTPUT_DATA)

    # Retrieve Azure ML workspace credentials
    aml_subscription_id = os.environ["AML_SUBSCRIPTION_ID"]
    aml_resource_group = os.environ["AML_RESOURCE_GROUP"]
    aml_workspace_name = os.environ["AML_WORKSPACE_NAME"]

    credential = DefaultAzureCredential()

    # Check if given credential can get token successfully.
    credential.get_token("https://management.azure.com/.default")

    # The DefaultAzureCredential class looks for the following environment variables
    # and uses the values when authenticating as the service principal:
    # AZURE_CLIENT_ID - The client ID returned when you created the service principal.
    # AZURE_TENANT_ID - The tenant ID returned when you created the service principal.
    # AZURE_CLIENT_SECRET - The password/credential generated for the service principal.

    try:
        ml_client = MLClient(
            credential, aml_subscription_id, aml_resource_group, aml_workspace_name
        )
    except Exception:
        logger.exception(
            "Connection with AML workspace unsuccessful, please check your credentials."
        )
        raise

    # Define custom inputs and outputs
    input_data = Input(type="uri_folder", path=INPUT_DATA, mode="ro_mount")
    output_data = Output(type="uri_file", path=OUTPUT_DATA, mode="upload")

    # Invoke batch endpoint
    job = ml_client.batch_endpoints.invoke(
        endpoint_name=ENDPOINT_NAME,
        deployment_name=DEPLOYMENT_NAME,
        inputs={"input_data": input_data},
        outputs={"output_data": output_data},
    )

    # Get job details
    print(ml_client.jobs.get(name=job.name))


if __name__ == "__main__":
    main()
