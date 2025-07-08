{% raw %}"""Creating a logger object to use in all other files."""

import logging
import os
import re

from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
from dotenv import load_dotenv
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

# Load dotenv in case you want to send logs to applicationinsights while developing in compute instances
# Think twice before you do this, you probably only want to set this up in dvlm/prod runs on clusters
load_dotenv()

logger = logging.getLogger("{% endraw %}{{cookiecutter.package_name}}{% raw %}")
# set level to lowest possible, we filter at handles
logger.setLevel(logging.DEBUG)  # do not change here
# very important, don't send to higher level logger, then all messages will be printed anyway
logger.propagate = False

# create stream (console) handler, set level in init
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # set filter what to print to console
console_formatter = logging.Formatter(
    "%(asctime)s - %(name)-8.8s - %(levelname)-5.5s - %(message)s [%(filename)s:%(lineno)d]"
)
console_handler.setFormatter(console_formatter)

# Add handlers to the logger
logger.addHandler(console_handler)


def add_appinsights_handler(connection_string: str) -> None:
    """Construct an App Insights handler based on the provided connection string.

    This function sets up a logger to send logs to Azure Application Insights using the given connection string.

    Args:
        connection_string (str): The connection string for the Azure Application Insights resource.

    Returns:
        None

    Notes:
        - If the provided connection string is empty, no handler will be added and the logger will remain inactive.
        - Logs will be sent with a severity level of INFO or higher.
    """
    if connection_string != "":
        # https://learn.microsoft.com/nl-nl/python/api/overview/azure/monitor-opentelemetry-exporter-readme
        # ?view=azure-python-preview#export-hello-world-log
        logger_provider = LoggerProvider()
        set_logger_provider(logger_provider)
        exporter = AzureMonitorLogExporter(connection_string=connection_string)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

        # Attach LoggingHandler to logger
        azure_handler = LoggingHandler()
        azure_handler.setLevel(logging.WARNING)  # filter what is sent to appInsights
        logger.addHandler(azure_handler)
        logger.info("AzureML logger activated")
    else:
        logger.info(
            "`add_appinsights_handler` function was called with empty `connection_string`"
        )


# try reading connection string from environment variable (from .env or set in azureml job/pipeline)
connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", default="")
if connection_string != "":
    add_appinsights_handler(connection_string=connection_string)
# you can also read appinsights key from keyvault (APPLICATIONINSIGHTS-CONNECTION-STRING) and call function manually


# project name to use in appinsights, possibly get from environment variable
# this way you can use a single alert rule for logs from different packages used for a project
project_name = os.getenv("APPLICATIONINSIGHTS_PROJECT_NAME", default=logger.name)


# Using LogRecordFactory to extract labels from log messages and set them as separate label
# This makes it easier to separate different logs in azureml
class CustomLogRecord(logging.LogRecord):
    """A custom log record that adds additional information such as project name and label(s).

    The labels are extracted from the log message (within square brackets), such as "[label] message".
    """

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Update log record.

        Args:
            args: args
            kwargs: kwargs
        """
        super().__init__(*args, **kwargs)
        # add project name
        self.project = project_name
        # add label(s) if found in log message (within square brackets)
        message = self.getMessage()
        match = re.findall(r"\[(.*?)\]", message)
        if match:
            # use join to concat if multiple labels are found (but difficult to use in azure!)
            label = ",".join(match)
            self.label = label


# Set this custom log record factory
logging.setLogRecordFactory(CustomLogRecord)
{% endraw %}