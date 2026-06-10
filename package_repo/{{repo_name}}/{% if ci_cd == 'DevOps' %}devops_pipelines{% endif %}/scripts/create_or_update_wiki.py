import logging
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsServiceError
from azure.devops.v7_1.client_factory import ClientFactoryV7_1
from azure.devops.v7_1.core.core_client import CoreClient
from azure.devops.v7_1.git.git_client import GitClient
from azure.devops.v7_1.wiki.models import (
    GitVersionDescriptor,
    WikiCreateParametersV2,
    WikiPageCreateOrUpdateParameters,
    WikiPageResponse,
    WikiV2,
)
from azure.devops.v7_1.wiki.wiki_client import WikiClient
from msal import ConfidentialClientApplication
from msrest.authentication import OAuthTokenAuthentication

# TODO: Place in separate file.
# Define format new logger
logger = logging.getLogger()
streamHandler = logging.StreamHandler()
logger.addHandler(streamHandler)
logger.setLevel(logging.INFO)

parser = ArgumentParser()
parser.add_argument(
    "-f", "--filepath", dest="md_filepath", help="Path to the directory containing all docfiles in md format"
)
parser.add_argument(
    "-p", "--project", dest="dvo_project_name", help="The name of the devops project in which the wiki (will) reside"
)
parser.add_argument("-n", "--name", dest="dvo_wiki_name", help="Name of the wiki")
parser.add_argument(
    "-b", "--branch", dest="dvo_branch_name", help="The name of the branch on which the wiki will be based off of"
)
parser.add_argument("-s", "--clientsecret", dest="client_secret", help="Client Secret")
parser.add_argument("-i", "--clientid", dest="client_id", help="Client Id")
parser.add_argument(
    "-t", "--tenant", dest="tenant_name", help="The tenant name used to access the Azure Devops services"
)
parser.add_argument(
    "-o", "--organisation", dest="organisation", help="The organisation used to access the Azure Devops services"
)

@dataclass
class WikiConfig:
    """Class that holds all needed info for calls towards the wiki"""

    wiki_name: str
    branch_name: str
    project_name: str
    root_page: str = "/Technische documentatie"


def get_clients(client_id: str, token: Dict[str, str], organization_url: str) -> ClientFactoryV7_1:
    """Initialize connection to devops and return the client instantiator which can be used
    to retrieve clients such as: WikiClient, GitClient and so on.
    Currently based on the 7.1 version of the devops rest api

    Args:
        client_id (str): the client id of the service principal which will be used to make the connection
        token (dict): A dict containing an access token to make a connection to devops
        organization_url (str): the url of the Azure Devops environment which will be used for all the
        actions in this script

    Returns:
        ClientFactoryV7_1: 7.1 version azure devops Client Factory
    """
    credentials = OAuthTokenAuthentication(client_id, token)
    connection = Connection(base_url=organization_url, creds=credentials)
    return connection.clients_v7_1


def _get_page(
    wiki_client: WikiClient, wiki_config: WikiConfig, path: str, recursion_level: int = 1, get_content: bool = False
) -> WikiPageResponse:
    """Get a page from an existing wiki in Azure Devops.

    Args:
        wiki_client (WikiClient): Client used to execute calls to the devops service, interfacing with wiki services
        wiki_config (WikiConfig): Data class containing relevant data to access the specified wiki
        path (str): path to the wiki page, respectively from the root_page specific in wiki_config
        recursion_level (int): decides how many recursions need to be made to retrieve underlying pages
        get_content (bool): Decides whether or not the content of the page needs to be retrieved as well

    Returns:
        WikiPageResponse: Response instance for a wiki page
    """

    logger.debug("searching in path %s, at branch: %s", path, wiki_config.branch_name)

    return wiki_client.get_page(
        project=wiki_config.project_name,
        wiki_identifier=wiki_config.wiki_name,
        path=path,
        recursion_level=recursion_level,
        version_descriptor=GitVersionDescriptor(
            version=wiki_config.branch_name, version_options=None, version_type="branch"
        ),
        include_content=get_content,
    )


def _create_or_update_page(
    wiki_client: WikiClient, wiki_config: WikiConfig, content: str, upload_path: str, page_etag: Optional[object] = None
) -> WikiPageResponse:
    """Create or update a page from an existing wiki in Azure Devops.

    Args:
        wiki_client (WikiClient): Client used to execute calls to the devops service
        wiki_config (WikiConfig): Data class containing relevant data to access the specified wiki
        upload_path (str): path to the wiki page, respectively from the root_page specific in wiki_config
        page_etag (str): tag of the page in case this function is used to update an existing page.
        leave as None when creating a new page. Defaults to None

    Returns:
        WikiPageResponse: Response instance for a wiki page
    """
    return wiki_client.create_or_update_page(
        parameters=WikiPageCreateOrUpdateParameters(content),
        project=wiki_config.project_name,
        wiki_identifier=wiki_config.wiki_name,
        path=upload_path,
        version=page_etag,
        comment=None,
        version_descriptor=GitVersionDescriptor(
            version=wiki_config.branch_name, version_options=None, version_type="branch"
        ),
    )


def get_existing_pages(wiki_client: WikiClient, wiki_config: WikiConfig) -> Dict[Any, Dict[str, str]]:
    """Check for existing pages in a given existing wiki at a specified root path.

    Args:
        wiki_client (WikiClient): Client used to execute calls to the devops service, interfacing with wiki services
        wiki_config (WikiConfig): Data class containing relevant data to access the specified wiki

    Returns:
        Dict[any, Dict[str:str]]: Dictionary with the found existing page paths as keys and a dictionary as value.
        The value dictionary contains the content of the page and the eTag which is needed to update the page
    """
    logger.info("checking for existing pages in %s...", wiki_config.root_page)
    existing_pages = {}
    try:
        root_page = _get_page(wiki_client, wiki_config, wiki_config.root_page, 1)

        # Iterate through the subpages of the root page
        for page in root_page.page.sub_pages:
            val = {"content": "", "eTag": "", "path": ""}
            subpage = _get_page(wiki_client=wiki_client, wiki_config=wiki_config, path=page.path, get_content=True)
            val["content"] = subpage.page.content
            val["eTag"] = subpage.eTag
            val["path"] = subpage.page.path
            existing_pages[page.path] = val
            logger.debug("existing page: %s : %s", page.path, val)

        logger.info("found pages: %s", [existing_pages.keys()])
        return existing_pages
    except AzureDevOpsServiceError:
        # In case root page doesn't exist, create it since it will be needed in further actions
        logger.info("root dir: '%s' not found, creating..", wiki_config.root_page)
        _create_or_update_page(wiki_client, wiki_config, "", wiki_config.root_page)
        return existing_pages


def get_md_content(md_dir_location: str) -> Dict[str, str]:
    """Reads all the markdown files in the given location and returns their content in a dictionaryu.

    Args:
        md_dir_location (str): The directory where the md files are stored

    Returns:
        Dict[str,str]: Dictionary with the filenames of the files as keys and their content as values
    """

    locations = Path(md_dir_location).glob("**/*.md")
    md_dict = {}

    for loc in locations:
        with loc.open(mode="r", encoding="utf-8") as read_md:
            md_dict[loc.stem] = read_md.read()

    logger.info("documentation files to create/update: %s", md_dict.keys())
    return md_dict


def create_or_update_pages(
    wiki_client, wiki_config: WikiConfig, pages_to_upload: Dict[str, str], existing_pages: Dict[Any, Dict[str, str]]
) -> bool:
    """Check for existing pages in a given existing wiki at a specified root path.

    Args:
        wiki_client (WikiClient): Client used to execute calls to the devops service, interfacing with wiki services
        wiki_config (WikiConfig): Data class containing relevant data to access the specified wiki
        pages_to_upload (Dict[str,str]): pages that need to be uploaded to the wiki (result from: get_md_content)
        existing_pages (Dict[str, Dict[str.str]]): existing pages with their content, eTags and paths
            (result from get_existing_pages)

    Returns:
        True (bool)
    """
    for page, content in pages_to_upload.items():
        upload_path = f"{wiki_config.root_page}/{page}"
        logger.debug("designated upload path: %s, will search in: %s", upload_path, existing_pages)

        if upload_path in existing_pages:
            ep_val = existing_pages.get(upload_path)
            assert ep_val, f"content and etag for {upload_path} not supplied"
            if ep_val["content"] == content:
                logger.info("page: %s exists and is already up-to-date", upload_path)
                continue
            logger.info("page: %s exists.. updating with new docs", upload_path)
            _create_or_update_page(wiki_client, wiki_config, content, upload_path, ep_val["eTag"])
        else:
            logger.info("creating new page: %s and adding docs", upload_path)
            _create_or_update_page(wiki_client, wiki_config, content, upload_path)
    return True


def delete_unneeded_pages(
    wiki_client: WikiClient,
    wiki_config: WikiConfig,
    autogenerated_pages: Dict[str, str],
    existing_pages: Dict[Any, Dict[str, str]],
) -> List[WikiPageResponse]:
    """Delete existing pages that are not being generated by source code
    Args:
        wiki_client (WikiClient): Client used to execute calls to the devops service, interfacing with wiki services
        wiki_config (WikiConfig): Data class containing relevant data to access the specified wiki
        autogenerated_pages (Dict[str, str]): pages created from autogenerated markdown files
        existing_pages (Dict[str, Dict[str.str]]): existing pages with their content, eTags and path
            (result from get_existing_pages)

    Returns:
        List[WikiPageResponse]: list of deleted pages
    """

    pages_to_delete = {
        k: v["path"]
        for k, v in existing_pages.items()
        if k not in [f"{wiki_config.root_page}/{y}" for y in autogenerated_pages.keys()]
    }

    logger.info("Will delete existing pages: %s", pages_to_delete.keys())
    deleted_pages = []
    for page, page_path in pages_to_delete.items():
        try:
            deleted_pages.append(
                wiki_client.delete_page(
                    project=wiki_config.project_name,
                    wiki_identifier=wiki_config.wiki_name,
                    path=page_path,
                    comment=f"Deleting page {page} from automated CI step",
                    version_descriptor=GitVersionDescriptor(
                        version=wiki_config.branch_name, version_options=None, version_type="branch"
                    ),
                )
            )
        except AzureDevOpsServiceError as e:
            logger.error("Was not able to delete page: %s due to error: %s", page, e)

    return deleted_pages


def get_project_id(core_client: CoreClient, project_name: str) -> str:
    """Get the project id for the given project name in Azure Devops
    Args:
        core_client (CoreClient): Client used to execute calls to the devops service, interfacing with core services
        project_name (str): Name of the azure devops project

    Returns:
        str: returns the id for the given project_name
    """
    projects = {x.name: x.id for x in core_client.get_projects()}
    return projects[project_name]


def get_repository_id(git_client: GitClient, project_name: str, repo_name: str) -> str:
    """Get the repository id for the given project name in Azure Devops
    Args:
        git_client (GitClient): Client used to execute calls to the devops service, interfacing with Git
        project_name (str): Name of the azure devops project
        repo_name (str): Name of the repository for which the get the id of

    Returns:
        str: returns the id for the given  repository
    """
    repos = {x.name: x.id for x in git_client.get_repositories(project=project_name)}
    return repos[repo_name]


def create_or_verify_wiki(wiki_client, core_client, git_client, wiki_config) -> WikiV2:
    """Get a page from an existing wiki in Azure Devops.
    Args:
        wiki_client (WikiClient): Client used to execute calls to the devops service, interfacing with wiki services
        git_client (GitClient): Client used to execute calls to the devops service, interfacing with Git
        core_client (CoreClient): Client used to execute calls to the devops service, interfacing with core services
        wiki_config (WikiConfig): Data class containing relevant data to access the specified wiki

    Returns:
        WikiV2: Response instance for a wiki
    """
    try:
        found_wiki = wiki_client.get_wiki(wiki_config.wiki_name, project=wiki_config.project_name)
        logger.info("wiki found: %s", wiki_config.wiki_name)
        return found_wiki
    except AzureDevOpsServiceError:
        logger.info("Was not able to find wiki: %s, creating...", wiki_config.wiki_name)
        return wiki_client.create_wiki(
            wiki_create_params=WikiCreateParametersV2(
                mapped_path="/docs",
                name=wiki_config.wiki_name,
                project_id=get_project_id(core_client, wiki_config.project_name),
                repository_id=get_repository_id(git_client, wiki_config.project_name, wiki_config.wiki_name),
                type="codewiki",
                version=GitVersionDescriptor(
                    version=wiki_config.branch_name, version_options=None, version_type="branch"
                ),
            ),
            project=wiki_config.project_name,
        )


def retrieve_auth_app(config: Dict[str, str]) -> ConfidentialClientApplication:
    """
    Create ConfidentialClientApplication to be able to interact wit devops through SP.

    Args:
        config: (Dict): Dicitionary containing the client_id, client_secret
            of the service pricipal and other values needed to interact with devops
    Returns:
        ConfidentialClientApplication
    """
    return ConfidentialClientApplication(
        client_id=config["client_id"],
        authority=config["authority"],
        client_credential=config["client_credential"],
    )


if __name__ == "__main__":

    args = parser.parse_args()

    wiki_config = WikiConfig(
        wiki_name=args.dvo_wiki_name,
        branch_name="/".join(args.dvo_branch_name.split("/")[2:]),
        project_name=args.dvo_project_name,
    )

    logger.info(
        """wiki details:\n
        Wiki Name:%s\n
        Branch:%s\n
        Project:%s""",
        wiki_config.wiki_name,
        wiki_config.branch_name,
        wiki_config.project_name,
    )

    ORGANIZATION_URL = f"https://dev.azure.com/{args.organisation}"
    AZURE_DEVOPS_SCOPE = "499b84ac-1321-427f-aa17-267ca6975798/.default"

    # current scope is static in microsoft (not just our tenant) is used to provide access to azure devops services
    config = {
        "client_id": args.client_id,
        "authority": f"https://login.microsoftonline.com/{args.tenant_name}",
        "client_credential": args.client_secret,
        "scope": [AZURE_DEVOPS_SCOPE],
    }

    authenticated_app = retrieve_auth_app(config)

    result_token = authenticated_app.acquire_token_for_client(scopes=config["scope"])
    if "access_token" not in result_token:
        logger.error("was not able to retrieve access token for service principal with Id: %s", {config["client_id"]})
        sys.exit(1)



    clients = get_clients(client_id=args.client_id, token=result_token, organization_url=ORGANIZATION_URL)

    wiki_client = clients.get_wiki_client()
    core_client = clients.get_core_client()
    git_client = clients.get_git_client()

    create_or_verify_wiki(wiki_client, core_client, git_client, wiki_config)

    pages_to_upload = get_md_content(md_dir_location=args.md_filepath)

    existing_pages = get_existing_pages(wiki_client=wiki_client, wiki_config=wiki_config)

    create_or_update_pages(wiki_client, wiki_config, pages_to_upload, existing_pages)

    delete_unneeded_pages(wiki_client, wiki_config, pages_to_upload, existing_pages)

    logger.info("docs up-to-date")
