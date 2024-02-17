import subprocess
import sys
import json
import re
from getpass import getpass


def add_git_tag_for_version(version: str) -> None:
    """Add a git tag for the given version."""
    try:
        subprocess.run(["git", "tag", "-a", version, "-m", version], check=True)
        print(f"Version {version} tag added successfully.")
    except subprocess.CalledProcessError as error:
        print(f"Failed to add version tag: {error}")
        sys.exit(1)


def remove_previous_dist() -> None:
    """Check for dist folder, and if it exists, remove it."""
    try:
        subprocess.run(["rm", "-rf", "dist/"], check=True)
    except subprocess.CalledProcessError as error:
        print(f"Failed to clean repo: {error}")
        sys.exit(1)


def create_build() -> None:
    """Create a build."""
    try:
        subprocess.run(["python", "-m", "build"], check=True)
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
        subprocess.run(["parallel", "-j", "1", "-t", "tar", "-tvf", ":::", "dist*"], check=True)
        confirmation = input("Does the build look correct? (y/n): ")
        if confirmation == "y":
            print("Build verified successfully.")
            upload_build_to_pypi()
            push_git_tags()
        else:
            print("Build not uploaded.")
            sys.exit(1)
    except subprocess.CalledProcessError as error:
        print(f"Failed to verify build: {error}")
        sys.exit(1)


def generate_github_release_notes_body(version) -> str:
    """Generate and grab release notes URL from Github."""
    try:
        command = [
            "curl",
            "-L",
            "-X",
            "POST",
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            f"Authorization: Bearer {GITHUB_TOKEN}",
            "-H",
            "X-GitHub-Api-Version: 2022-11-28",
            "https://api.github.com/repos/ekcorso/releasetestrepo2/releases/generate-notes",
            "-d",
            '{"tag_name":"${version_number}"}',
        ]
        response_json = subprocess.run(command, check=True, capture_output=True)
        parsed_json = json.loads(response_json)
        body = parsed_json["body"]
        return body
    except subprocess.CalledProcessError as error:
        print(f"Failed to generate release notes: {error}")
        return ""


def get_release_notes_url(body) -> str:
    """Parse the release notes content to get the changelog URL."""
    url_pattern = re.compile(r"\*\*Full Changelog\*\*: (.*?)\n")
    match = url_pattern.search(body)
    if match:
        return match.group(1)
    else:
        print("Failed to parse release notes URL from GitHub response.")
        return ""


# TODO: Refactor to use markdown parsing library instead of regex
def get_changelog_release_notes() -> str:
    """Get the changelog release notes."""
    changelog_text = None
    with open("../CHANGELOG.md", "r", encoding="utf-8") as file:
        changelog_text = file.read()
    pattern = re.compile(rf"## {version_number}(?:\n(.*?))?##", re.DOTALL)
    match = pattern.search(changelog_text)
    if match:
        return match.group(1)
    else:
        print("Failed to parse changelog release notes.")
        return ""


def create_release_notes_body() -> str:
    """Compile the release notes."""
    changelog_notes = get_changelog_release_notes()
    github_release_body = generate_github_release_notes_body(version_number)
    release_notes_url = get_release_notes_url(github_release_body)
    full_release_notes = (
        changelog_notes + "\n\n**Full Changelog**: " + release_notes_url
    )
    return full_release_notes



def upload_build_to_pypi() -> None:
    """Upload the build to PyPI."""
    try:
        # Note current version uses the testpypi repository
        subprocess.run(["twine", "upload", "--repository", "testpypi", "dist/*"], check=True)
        print("Build uploaded successfully.")
    except subprocess.CalledProcessError as error:
        print(f"Failed to upload build: {error}")
        sys.exit(1)

def push_git_tags() -> None:
    """Push all git tags to the remote."""
    try:
        subprocess.run(["git", "push", "--tags", "origin", "master"], check=True)
        print("Tags pushed successfully.")
    except subprocess.CalledProcessError as error:
        print(f"Failed to push tags: {error}")
        sys.exit(1)


version_number = input("Enter the version number: ")


def main() -> None:
    """Run the main program."""
    print("Starting the upload process...")

    add_git_tag_for_version(version_number)
    remove_previous_dist()
    create_build()
    verify_build()


if __name__ == "__main__":
    main()
