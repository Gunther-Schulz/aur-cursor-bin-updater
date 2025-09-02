#!/usr/bin/env python
import requests
import re
import sys
import os
import json
import time

import hashlib
from packaging import version



def get_latest_commit_and_version():
    """Get the latest commit hash and version from Cursor's API."""
    cursor_url = "https://cursor.com/api/download?platform=linux-x64&releaseTrack=stable"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            print("::debug::Making request to:", cursor_url)
            response = requests.get(cursor_url, headers=headers)
            print(f"::debug::API status code: {response.status_code}")
            print(f"::debug::API raw response: {response.text}")

            if response.status_code == 200 and response.text.strip():
                data = response.json()
                print("::debug::API response:", json.dumps(data, indent=2))
                response.raise_for_status()

                download_url = data["downloadUrl"]
                version = data["version"]
                commit = data["commitSha"]

                print(f"::debug::Extracted version: {version}, commit: {commit}")
                return commit, version, download_url

            else:
                print("::warning::Invalid response from Cursor API")
                raise requests.exceptions.RequestException(
                    "Invalid response from Cursor API"
                )

        except requests.exceptions.RequestException as e:
            print(f"::warning::Request failed: {str(e)}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"::warning::Failed to parse JSON or extract data: {str(e)}")
        except ValueError as e:
            print(f"::warning::{str(e)}")

        if attempt < max_retries:
            print("::debug::Retrying in 5 seconds...")
            time.sleep(5)

    print("::error::Failed to get download link after all retry attempts")
    return None, None, None


def get_local_pkgbuild_info():
    with open("PKGBUILD", "r") as file:
        content = file.read()
    version_match = re.search(r"pkgver=([^\n]+)", content)
    rel_match = re.search(r"pkgrel=(\d+)", content)
    commit_match = re.search(r"_commit=([a-f0-9]+)", content)
    if version_match and rel_match and commit_match:
        return version_match.group(1).strip(), rel_match.group(1), commit_match.group(1)
    else:
        print(
            f"::error::Unable to find current version, release, or commit in local PKGBUILD"
        )
        return None, None, None


def get_aur_pkgbuild_info():
    url = "https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=cursor-bin"
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
        version_match = re.search(r"pkgver=([^\n]+)", content)
        rel_match = re.search(r"pkgrel=(\d+)", content)
        commit_match = re.search(r"_commit=([a-f0-9]+)", content)
        if version_match and rel_match and commit_match:
            return version_match.group(1).strip(), rel_match.group(1), commit_match.group(1)
        else:
            print(f"::warning::Unable to find version, release, or commit in AUR PKGBUILD")
            return None, None, None
    except Exception as e:
        print(f"::warning::Error fetching AUR PKGBUILD: {str(e)}")
        return None, None, None


def compare_versions(version1, version2):
    """Compare two version strings and return True if version1 is higher than version2."""
    try:
        return version.parse(version1) > version.parse(version2)
    except version.InvalidVersion:
        print(f"::warning::Invalid version format: {version1} or {version2}")
        return False


try:
    # Check if DEBUG is set to true
    debug_mode = os.environ.get("DEBUG", "").lower() == "true"

    # Check if version comparison protection is enabled (default: false)
    version_protection = os.environ.get("VERSION_PROTECTION", "").lower() == "true"

    # Check if commit-based update detection is enabled (default: true)
    commit_based_updates = os.environ.get("COMMIT_BASED_UPDATES", "true").lower() == "true"

    # Get the latest commit, version, and download URL
    latest_commit, latest_version, download_url = get_latest_commit_and_version()
    if not latest_commit or not latest_version:
        raise ValueError("Failed to get latest commit and version after retries")

    print(f"::debug::Latest commit: {latest_commit}")
    print(f"::debug::Latest version: {latest_version}")
    print(f"::debug::Download URL: {download_url}")

    local_version, local_rel, local_commit = get_local_pkgbuild_info()
    if local_version is None or local_rel is None or local_commit is None:
        raise ValueError("Failed to get local version, release, or commit")

    print(
        f"::debug::Local version: {local_version}, release: {local_rel}, commit: {local_commit}"
    )
    print(f"::debug::Version protection enabled: {version_protection}")
    print(f"::debug::Commit-based updates enabled: {commit_based_updates}")

    # Determine if update is needed
    aur_version, aur_rel, aur_commit = get_aur_pkgbuild_info()
    print(f"::debug::AUR version: {aur_version}, release: {aur_rel}, commit: {aur_commit}")

    # Check if this is a manual release update
    is_manual_rel_update = (
        aur_version == local_version
        and aur_commit == local_commit
        and aur_rel
        and local_rel
        and int(local_rel) > int(aur_rel)
    )

    # Check if update is needed based on commit hash or version
    if commit_based_updates:
        # Primary update detection: commit hash changes OR manual release bump
        # Compare against local commit to determine if local repo needs updating
        commit_update_needed = latest_commit and latest_commit != local_commit
        update_needed = commit_update_needed or is_manual_rel_update
        print(f"::debug::Commit-based update detection: {update_needed}")
        print(f"::debug::Commit update needed: {commit_update_needed}")
        print(f"::debug::Manual release update needed: {is_manual_rel_update}")
    else:
        # Fallback to version-based detection
        if version_protection:
            # Only update if latest version is higher than local version
            version_update_needed = (
                latest_version
                and latest_version != local_version
                and compare_versions(latest_version, local_version)
            )
        else:
            # Update if version is different (regardless of higher/lower)
            version_update_needed = (
                latest_version
                and latest_version != local_version
            )

        commit_update_needed = latest_commit and latest_commit != local_commit
        update_needed = version_update_needed or commit_update_needed or is_manual_rel_update
        print(f"::debug::Version-based update detection: {update_needed}")

    # Determine new_version, new_rel, and new_commit
    if update_needed:
        if commit_based_updates:
            if is_manual_rel_update:
                # For manual release updates, keep current version and commit, use current release
                new_version = local_version
                new_commit = local_commit
                new_rel = local_rel  # Keep the manually set release number
            else:
                # For commit-based updates, always use latest version and commit
                new_version = latest_version
                new_commit = latest_commit
                # Reset pkgrel to 1 for version changes, increment for same version with different commit
                if latest_version != local_version:
                    new_rel = "1"  # New version, reset pkgrel
                else:
                    new_rel = str(int(local_rel) + 1)  # Same version, different commit, increment pkgrel
        else:
            # Fallback to version-based logic
            if version_update_needed:
                new_version = latest_version
                new_commit = latest_commit
                new_rel = "1"
            elif commit_update_needed:
                new_version = local_version
                new_commit = latest_commit
                new_rel = str(int(local_rel) + 1)
            elif is_manual_rel_update:
                new_version = local_version
                new_commit = local_commit
                new_rel = local_rel  # Keep the manually set release number
    else:
        new_version = local_version
        new_rel = local_rel
        new_commit = local_commit

    print(f"::debug::New version: {new_version}, new release: {new_rel}, new commit: {new_commit}")

    # Create output as JSON
    output = {
        "update_needed": update_needed,
        "local_version": local_version,
        "local_rel": local_rel,
        "local_commit": local_commit,
        "download_url": download_url,
        "new_version": new_version,
        "new_rel": new_rel,
        "new_commit": new_commit,
        "latest_version": latest_version,
        "latest_commit": latest_commit,
        "aur_version": aur_version,
        "aur_rel": aur_rel,
        "aur_commit": aur_commit,
    }

    # Write JSON to file
    with open("check_output.json", "w") as f:
        json.dump(output, f)

    print(f"::debug::Check output written to check_output.json")
    print(f"::debug::Final new_version: {new_version}, new_rel: {new_rel}, new_commit: {new_commit}")

except Exception as e:
    print(f"::error::Error in main execution: {str(e)}")
    sys.exit(1)
