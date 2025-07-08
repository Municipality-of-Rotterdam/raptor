"""Example scoring script for online deployments.

MS Docs:
https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-online-endpoints?view=azureml-api-2&tabs=cli#understand-the-scoring-script

Returns:
    List of predictions
"""
# ruff: noqa: T201, ANN401, INP001, PLW0603, EM101

import json
import logging
import os
from typing import Any, Union

import joblib
import numpy as np

model: Any = "global_variable_placeholder"


def init() -> None:
    """Initialize ML model.

    This function is called when the container is initialized/started, typically after create/update of the
    deployment. You can write the logic here to perform init operations like caching the model in memory.
    """
    global model
    # AZUREML_MODEL_DIR is an environment variable created during deployment.
    # It is the path to the model folder (./azureml-models/$MODEL_NAME/$VERSION)
    # Please provide your model's folder name if there is one
    model_dir = os.getenv("AZUREML_MODEL_DIR")
    if model_dir is None:
        error_msg = "AZUREML_MODEL_DIR environment variable is not set."
        raise EnvironmentError(error_msg)

    model_path = os.path.join(model_dir, "model.pkl")
    # deserialize the model file back into a sklearn model
    model = joblib.load(model_path)
    logging.info("Init complete")


def run(raw_data: Union[str, bytes]) -> Any:
    """Invoke ML model.

    This function is called for every invocation of the endpoint to perform the actual scoring/prediction.
    In the example we extract the data from the json input and call the scikit-learn model's predict()
    method and return the result back.
    """
    logging.info("Request received")
    data = json.loads(raw_data)["data"]
    data = np.array(data)
    result = model.predict(data)
    logging.info("Request processed")
    return result.tolist()
