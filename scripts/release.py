import subprocess
import sys
import json
import re
from getpass import getpass
import os

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


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
        if len(os.listdir("dist")) != 2:
            print("WARNING: dist folder contains incorrect number of files.")
        print("Contents of dist folder:")
        subprocess.run(["ls", "-l", "dist/"], check=True)
        try:
            print("Contents of tar files in dist folder:")
            for dir in os.listdir("dist"):
                subprocess.run(["tar", "tvf", "dist/" + dir], check=True)
            confirmation = input("Does the build look correct? (y/n): ")
            if confirmation == "y":
                print("Build verified successfully.")
                upload_build_to_pypi()
                push_git_tags()
            else:
                print("Could not verify. Build was not uploaded.")
                sys.exit(1)
        except subprocess.CalledProcessError as error:
            print(f"Failed to verify build: {error}")
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
            f'{{"tag_name":"{version_number}"}}',
        ]
        response_json = subprocess.run(command, check=True, capture_output=True)
        parsed_json = json.loads(response_json.stdout)
        body = parsed_json["body"]
        return body
    except subprocess.CalledProcessError as error:
        print(f"Failed to generate release notes: {error}")
        return ""


def get_release_notes_url(body) -> str:
    """Parse the release notes content to get the changelog URL."""
    url_pattern = re.compile(r"\*\*Full Changelog\*\*: (.*)$")
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
    with open("CHANGELOG.md", "r", encoding="utf-8") as file:
        changelog_text = file.read()
    pattern = re.compile(rf"## {re.escape(version_number)}[^\n]*(.*?)##", re.DOTALL)
    match = pattern.search(changelog_text)
    if match:
        return str(match.group(1)).strip()
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


def create_github_release_draft() -> None:
    """Create a release on GitHub."""
    release_body = create_release_notes_body()
    release_body = release_body.replace("\n", "\\n")
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
            "https://api.github.com/repos/ekcorso/releasetestrepo2/releases",
            "-d",
            f'{{"tag_name":"{version_number}","name":"{version_number}","body":"{release_body}","draft":true,"prerelease":false}}',
        ]
        response_json = subprocess.run(command, check=True, capture_output=True)
        parsed_json = json.loads(response_json.stdout)
        if "html_url" in parsed_json:
            print("Release created successfully: " + parsed_json["html_url"])
        else:
            print("There may have been an error creating this release. Visit https://github.com/john-kurkowski/tldextract/releases to confirm release was created.")
    except subprocess.CalledProcessError as error:
        print(f"Failed to create release: {error}")


def upload_build_to_pypi() -> None:
    """Upload the build to PyPI."""
    try:
        # Note current version uses the testpypi repository
        subprocess.run(
            ["twine", "upload", "--repository", "testpypi", "dist/*"], check=True
        )
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
        print(f"Failed to push tag(s) to Github: {error}")


version_number = input("Enter the version number: ")


def main() -> None:
    """Run the main program."""
    print("Starting the upload process...")

    add_git_tag_for_version(version_number)
    remove_previous_dist()
    create_build()
    verify_build()
    create_github_release_draft()

    print("Upload process complete.")


if __name__ == "__main__":
    main()
