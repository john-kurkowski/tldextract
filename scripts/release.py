import subprocess
import sys
from github import Github
from getpass import getpass

def add_git_tag_for_version(version: str) -> None:
    """Add a git tag for the given version."""
    try:
        subprocess.run(["git", "tag", "-a", version, "-m", version], check=True)
        # TODO: Remove this print statement after testing
        print(f"Version {version} tag added successfully.")
    except subprocess.CalledProcessError as error:
        print(f"Failed to add version tag: {error}")
        sys.exit(1)


def clean_repo() -> None:
    """Clean the repo."""
    try:
        subprocess.run(["git", "clean", "-fdx"], check=True)
        # TODO: Remove this print statement after testing
        print("Repo cleaned successfully.")
    except subprocess.CalledProcessError as error:
        print(f"Failed to clean repo: {error}")
        sys.exit(1)


def create_build() -> None:
    """Create a build."""
    try:
        subprocess.run(["python", "-m", "build"], check=True)
        # TODO: Remove this print statement after testing
        print("Build created successfully.")
    except subprocess.CalledProcessError as error:
        print(f"Failed to create build: {error}")
        sys.exit(1)

def verify_build() -> None:
    """Verify the build."""
    try:
        subprocess.run(["ls", "-l", "dist/"], check=True)
        confirmation = input("Does the build look correct? (y/n): ")
        if confirmation == "y":
            # TODO: Remove this print statement after testing
            print("Build verified successfully.")
            upload_build_to_pypi()
            push_git_tags()
        else:
            print("Build not uploaded.")
            sys.exit(1)
    except subprocess.CalledProcessError as error:
        print(f"Failed to verify build: {error}")
        sys.exit(1)
    try:
        subprocess.run(["parallel", "-j", "1", "-t", "tar", "-tvf", ":::", "/dist*"], check=True)
        confirmation = input("Does the build look correct? (y/n): ")
        if confirmation == "y":
            # TODO: Remove this print statement after testing
            print("Build verified successfully.")
            upload_build_to_pypi()
            push_git_tags()
        else:
            print("Build not uploaded.")
            sys.exit(1)
    except subprocess.CalledProcessError as error:
        print(f"Failed to verify build: {error}")
        sys.exit(1)


def get_github_client() -> Github:
    """Get a Github client."""
    


def upload_build_to_pypi() -> None:
    """Upload the build to PyPI."""
    # TODO: This needs to be updated to use the token and password from env variables.
    try:
        subprocess.run(["twine", "upload", "dist/*"], check=True)
        # TODO: Remove this print statement after testing
        print("Build uploaded successfully.")
    except subprocess.CalledProcessError as error:
        print(f"Failed to upload build: {error}")
        sys.exit(1)

def push_git_tags() -> None:
    """Push all git tags to the remote."""
    try:
        subprocess.run(["git", "push", "--tags", "origin", "master"], check=True)
        # TODO: Remove this print statement after testing
        print("Tags pushed successfully.")
    except subprocess.CalledProcessError as error:
        print(f"Failed to push tags: {error}")
        sys.exit(1)

"""
pyPyToken = input("Enter the PyPI token: ")
pyPyPassword = getpass("Enter the PyPI password: ")
githubToken = getpass("Enter the github token: ")
githubPassword = getpass("Enter the github password: ")
"""
version_number = input("Enter the version number: ")

def main() -> None:
    """Run the main program."""
    add_git_tag_for_version(version_number)
    clean_repo()
    create_build()
    verify_build()
