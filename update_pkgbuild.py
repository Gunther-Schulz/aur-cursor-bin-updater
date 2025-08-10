import sys
import json
import os
import base64
import hashlib
import requests
import re
import tempfile
import subprocess

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"


def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def base64_to_hex(base64_string):
    return base64.b64decode(base64_string).hex()


def get_electron_version(vscode_version):
    """Get the Electron version from VSCode's package-lock.json."""
    debug_print(f"Starting get_electron_version for VSCode {vscode_version}")
    url = f"https://raw.githubusercontent.com/microsoft/vscode/refs/tags/{vscode_version}/package-lock.json"
    debug_print(f"URL: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }

    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            debug_print(f"Fetching Electron version for VSCode {vscode_version} (attempt {attempt + 1})")
            response = requests.get(url, headers=headers)
            debug_print(f"Response status: {response.status_code}")
            response.raise_for_status()
            debug_print("Response successful, parsing JSON...")

            # Parse the package-lock.json to find electron version
            data = response.json()
            debug_print("JSON parsed successfully")
            debug_print(f"JSON keys: {list(data.keys())}")

            # Try different possible locations for electron version
            electron_version = None

            # Method 1: Check root dependencies (old format)
            debug_print("Checking Method 1: root dependencies...")
            if 'dependencies' in data and 'electron' in data['dependencies']:
                electron_version = data['dependencies']['electron']['version']
                debug_print(f"Found electron in root dependencies: {electron_version}")
            else:
                debug_print("Method 1 failed: no root dependencies or electron not found")

            # Method 2: Check packages structure (new format)
            debug_print("Checking Method 2: packages root dependencies...")
            if 'packages' in data and '' in data['packages']:
                root_package = data['packages']['']
                if 'dependencies' in root_package and 'electron' in root_package['dependencies']:
                    electron_version = root_package['dependencies']['electron']
                    debug_print(f"Found electron in packages root dependencies: {electron_version}")
                else:
                    debug_print("Method 2 failed: no root package dependencies or electron not found")
            else:
                debug_print("Method 2 failed: no packages or no root package")

            # Method 3: Search in all packages
            if 'packages' in data:
                debug_print(f"Checking packages structure...")
                debug_print(f"Number of packages: {len(data['packages'])}")
                debug_print(f"Available packages (first 10): {list(data['packages'].keys())[:10]}...")
                if 'node_modules/electron' in data['packages']:
                    electron_version = data['packages']['node_modules/electron']['version']
                    debug_print(f"Found electron in packages: {electron_version}")
                else:
                    debug_print("node_modules/electron not found in packages")
                    # Search for any electron-related packages
                    electron_packages = [k for k in data['packages'].keys() if 'electron' in k.lower()]
                    debug_print(f"Electron-related packages found: {electron_packages[:5]}")
                    # Check if electron exists with different key format
                    all_keys = list(data['packages'].keys())
                    electron_keys = [k for k in all_keys if 'electron' in k]
                    debug_print(f"All electron keys: {electron_keys}")

            if electron_version:
                # Extract major version number
                major_version = electron_version.split('.')[0]
                return f"electron{major_version}"
            else:
                raise ValueError("Electron dependency not found in package-lock.json")

        except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError) as e:
            debug_print(f"Failed to get Electron version (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries:
                debug_print("Retrying in 2 seconds...")
                import time
                time.sleep(2)

    debug_print("Failed to determine Electron version after all retries")
    return None


def extract_vscode_version_from_appimage(temp_file_path):
    """Extract VSCode version from the AppImage using unsquashfs."""
    try:
        debug_print(f"Using existing temporary AppImage: {temp_file_path}")

        # Use AppImage's own extraction method
        debug_print("Extracting product.json using AppImage extraction...")
        # Make the AppImage executable
        os.chmod(temp_file_path, 0o755)

        # Use the AppImage's --appimage-extract option
        result = subprocess.run([
            temp_file_path, '--appimage-extract', 'usr/share/cursor/resources/app/product.json'
        ], capture_output=True, text=True, timeout=60)

        debug_print(f"AppImage extraction result: {result.returncode}")
        if result.stderr:
            debug_print(f"AppImage extraction stderr: {result.stderr}")

        if result.returncode == 0:
            product_json_path = 'squashfs-root/usr/share/cursor/resources/app/product.json'
            if os.path.exists(product_json_path):
                with open(product_json_path, 'r') as f:
                    product_data = json.load(f)
                vscode_version = product_data.get('vscodeVersion')
                if vscode_version:
                    debug_print(f"Found VSCode version: {vscode_version}")
                    return vscode_version
                else:
                    debug_print("vscodeVersion not found in product.json")
            else:
                debug_print(f"product.json not found at: {product_json_path}")
        else:
            debug_print("AppImage extraction failed")

    except Exception as e:
        debug_print(f"Error extracting VSCode version: {str(e)}")

    return None


def calculate_sha512(url):
    """Download file and calculate its SHA512."""
    print("::debug::Downloading file to calculate SHA512...")
    print(f"::debug::URL: {url}")

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        print(f"::debug::Download started, content-length: {response.headers.get('content-length', 'unknown')}")

        sha512_hash = hashlib.sha512()
        chunk_count = 0
        for chunk in response.iter_content(chunk_size=8192):
            sha512_hash.update(chunk)
            chunk_count += 1
            if chunk_count % 100 == 0:
                print(f"::debug::Processed {chunk_count} chunks...")

        print(f"::debug::Download completed, processed {chunk_count} chunks")
        return sha512_hash.hexdigest()
    except Exception as e:
        print(f"::debug::Error calculating SHA512: {str(e)}")
        raise


def update_pkgbuild(pkgbuild_lines, json_data):
    new_version = json_data["new_version"]
    new_rel = json_data["new_rel"]
    new_commit = json_data["new_commit"]

    # Download AppImage once and use it for both SHA512 and extraction
    appimage_url = f"https://downloads.cursor.com/production/{new_commit}/linux/x64/Cursor-{new_version}-x86_64.AppImage"
    debug_print(f"Downloading AppImage once for SHA512 and extraction: {appimage_url}")

    # Download the AppImage once and save to memory
    try:
        response = requests.get(appimage_url, timeout=60)
        response.raise_for_status()
        appimage_data = response.content
        response.close()
        debug_print(f"Successfully downloaded AppImage, size: {len(appimage_data)} bytes")
    except Exception as e:
        raise RuntimeError(f"Failed to download AppImage: {str(e)}")

    # Calculate SHA512
    debug_print("Calculating SHA512...")
    sha512_hash = hashlib.sha512()
    sha512_hash.update(appimage_data)
    appimage_sha512 = sha512_hash.hexdigest()
    debug_print(f"Calculated AppImage SHA512: {appimage_sha512}")

    # Save the AppImage to a temporary file for extraction
    debug_print("Saving AppImage to temporary file for extraction...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.AppImage', delete=False, mode='wb') as temp_file:
            temp_file.write(appimage_data)
            temp_file_path = temp_file.name
        debug_print(f"Saved AppImage to {temp_file_path}, size: {len(appimage_data)} bytes")
    except Exception as e:
        raise RuntimeError(f"Failed to save temporary AppImage: {str(e)}")

    # Determine Electron version
    debug_print("Starting Electron version determination...")
    vscode_version = extract_vscode_version_from_appimage(temp_file_path)
    debug_print(f"VSCode version determined: {vscode_version}")

    if vscode_version:
        debug_print("Getting Electron version from VSCode package-lock.json...")
        electron_version = get_electron_version(vscode_version)
        debug_print(f"Determined Electron version: {electron_version}")
        if electron_version is None:
            debug_print("Electron version is None, using fallback")
            electron_version = "electron28"  # Fallback version
    else:
        debug_print("Could not determine Electron version, using fallback")
        electron_version = "electron28"  # Fallback version

    # Clean up temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
        debug_print(f"Cleaned up temporary file: {temp_file_path}")

    updated_lines = []
    changes_made = {
        'pkgver': False,
        'pkgrel': False,
        '_commit': False,
        '_appimage': False,
        'electron': False,
        'source': False,
        'sha512sums': False
    }

    for line in pkgbuild_lines:
        # Update specific values while preserving everything else
        if line.startswith("pkgver="):
            updated_lines.append(f"pkgver={new_version}\n")
            changes_made['pkgver'] = True
        elif line.startswith("pkgrel="):
            updated_lines.append(f"pkgrel={new_rel}\n")
            changes_made['pkgrel'] = True
        elif line.startswith("_commit="):
            updated_lines.append(f"_commit={new_commit}\n")
            changes_made['_commit'] = True
        elif line.startswith("_appimage="):
            # Update the _appimage variable with new version
            updated_lines.append(f'_appimage="${{pkgname}}-{new_version}.AppImage"\n')
            changes_made['_appimage'] = True
        elif line.startswith("depends=("):
            # Start of depends array - preserve the line and check for electron
            if "electron" in line:
                # Single line depends with electron
                updated_line = re.sub(r"'electron\d+'", f"'{electron_version}'", line)
                updated_lines.append(updated_line)
                changes_made['electron'] = True
            else:
                updated_lines.append(line)
        elif "'electron" in line:
            # Any line containing electron dependency
            updated_line = re.sub(r"'electron\d+'", f"'{electron_version}'", line)
            updated_lines.append(updated_line)
            changes_made['electron'] = True
        elif line.startswith("source=("):
            # Update the source line with new version and commit
            updated_lines.append(f'source=("${{_appimage}}::https://downloads.cursor.com/production/{new_commit}/linux/x64/Cursor-{new_version}-x86_64.AppImage")\n')
            changes_made['source'] = True
        elif line.startswith("sha512sums=("):
            # Update the checksum
            updated_lines.append(f"sha512sums=('{appimage_sha512}')\n")
            changes_made['sha512sums'] = True
        else:
            # Preserve all other lines exactly as they are
            updated_lines.append(line)

    # Verify all expected changes were made
    debug_print("Verifying all expected changes were made...")
    for change, made in changes_made.items():
        if not made:
            debug_print(f"WARNING: Expected change '{change}' was not made")
        else:
            debug_print(f"✓ Change '{change}' was made successfully")

    # Verify the updated content contains expected values
    updated_content = ''.join(updated_lines)
    verification_errors = []

    if f"pkgver={new_version}" not in updated_content:
        verification_errors.append(f"pkgver not updated to {new_version}")

    if f"pkgrel={new_rel}" not in updated_content:
        verification_errors.append(f"pkgrel not updated to {new_rel}")

    if f"_commit={new_commit}" not in updated_content:
        verification_errors.append(f"_commit not updated to {new_commit}")

    if f"'{electron_version}'" not in updated_content:
        verification_errors.append(f"electron version not updated to {electron_version}")

    if appimage_sha512 not in updated_content:
        verification_errors.append("sha512sums not updated")

    if verification_errors:
        error_msg = "PKGBUILD verification failed:\n" + "\n".join(f"- {error}" for error in verification_errors)
        raise RuntimeError(error_msg)

    debug_print("✓ All PKGBUILD verifications passed")
    return updated_lines, electron_version


def download_and_transform_code_sh(electron_version):
    """Download code.sh from Arch Linux packaging and transform it to cursor.sh."""
    debug_print("Downloading code.sh from Arch Linux packaging...")

    code_sh_url = "https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code.sh"

    try:
        response = requests.get(code_sh_url, timeout=30)
        response.raise_for_status()
        code_sh_content = response.text

        debug_print("Successfully downloaded code.sh, transforming to cursor.sh...")

        # Transform the content using the same sed logic from PKGBUILD
        cursor_sh_content = code_sh_content

        # Apply all the transformations
        cursor_sh_content = re.sub(r'code-flags', 'cursor-flags', cursor_sh_content)
        cursor_sh_content = re.sub(r'/usr/lib/code', '/usr/share/cursor/resources/app', cursor_sh_content)
        cursor_sh_content = re.sub(r'/usr/lib/code/out/cli\.js', '/usr/share/cursor/resources/app/out/cli.js', cursor_sh_content)
        cursor_sh_content = re.sub(r'/usr/lib/code/code\.mjs', '--app=/usr/share/cursor/resources/app', cursor_sh_content)
        cursor_sh_content = re.sub(r'name=electron', f'name={electron_version}', cursor_sh_content)

        debug_print("Transformation completed successfully")

        # Verify the transformations were successful
        debug_print("Starting verification...")

        if not re.search(r'cursor-flags', cursor_sh_content):
            raise ValueError("cursor-flags replacement failed")
        debug_print("✓ cursor-flags verification passed")

        if not re.search(f'name={electron_version}', cursor_sh_content):
            raise ValueError(f"electron version replacement failed: expected {electron_version}")
        debug_print("✓ electron version verification passed")

        if not re.search(r'exec /usr/lib/\${name}/electron', cursor_sh_content):
            raise ValueError("exec path not found in generated script")
        debug_print("✓ exec path verification passed")

        if not re.search(r'/usr/share/cursor/resources/app/out/cli\.js', cursor_sh_content):
            raise ValueError("cli.js path replacement failed")
        debug_print("✓ cli.js path verification passed")

        if not re.search(r'/usr/share/cursor/resources/app/code\.mjs', cursor_sh_content):
            debug_print(f"app path verification failed. Looking for '/usr/share/cursor/resources/app/code.mjs'")
            debug_print(f"Content that might contain the path: {re.findall(r'/usr/share/cursor/resources/app/[^ ]*', cursor_sh_content)}")
            raise ValueError("app path replacement failed")
        debug_print("✓ app path verification passed")

        # Verify no old paths remain
        if re.search(r'/usr/lib/code', cursor_sh_content):
            raise ValueError("old /usr/lib/code paths still present")
        debug_print("✓ old paths verification passed")

        debug_print("All verifications passed")

        # Write the transformed cursor.sh file
        with open('cursor.sh', 'w') as f:
            f.write(cursor_sh_content)

        debug_print("cursor.sh file created successfully")
        return True

    except Exception as e:
        debug_print(f"Error downloading/transforming code.sh: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_pkgbuild.py <check_output_file>")
        sys.exit(1)

    try:
        debug_print(f"Reading check output from {sys.argv[1]}")
        with open(sys.argv[1], "r") as f:
            check_output = json.load(f)

        debug_print(f"Check output content: {json.dumps(check_output, indent=2)}")

        if check_output["update_needed"]:
            debug_print("Update needed, reading current PKGBUILD")
            try:
                with open("PKGBUILD", "r") as f:
                    current_pkgbuild = f.readlines()
                debug_print(f"Successfully read PKGBUILD with {len(current_pkgbuild)} lines")
            except Exception as e:
                raise RuntimeError(f"Failed to read PKGBUILD: {str(e)}")

            debug_print("Calling update_pkgbuild()")
            updated_pkgbuild, electron_version = update_pkgbuild(current_pkgbuild, check_output)

            # Verify the updated PKGBUILD has the expected number of lines
            if len(updated_pkgbuild) != len(current_pkgbuild):
                debug_print(f"WARNING: Line count changed from {len(current_pkgbuild)} to {len(updated_pkgbuild)}")

            # Write the changes to the file
            try:
                with open("PKGBUILD", "w") as f:
                    f.writelines(updated_pkgbuild)
                debug_print(f"Successfully wrote updated PKGBUILD to disk")
            except Exception as e:
                raise RuntimeError(f"Failed to write updated PKGBUILD: {str(e)}")

            # Verify the file was written correctly
            try:
                with open("PKGBUILD", "r") as f:
                    written_content = f.read()
                if f"pkgver={check_output['new_version']}" not in written_content:
                    raise RuntimeError("PKGBUILD was written but verification failed - pkgver not found")
                if f"pkgrel={check_output['new_rel']}" not in written_content:
                    raise RuntimeError("PKGBUILD was written but verification failed - pkgrel not found")
                debug_print("✓ PKGBUILD file verification passed")
            except Exception as e:
                raise RuntimeError(f"PKGBUILD verification failed after writing: {str(e)}")

            debug_print(
                f"PKGBUILD updated to version {check_output['new_version']} (release {check_output['new_rel']}) with commit {check_output['new_commit']}"
            )

            # Download and transform code.sh
            debug_print(f"Downloading and transforming code.sh for electron version: {electron_version}")
            if not download_and_transform_code_sh(electron_version):
                raise RuntimeError("Failed to download and transform code.sh")

            # Verify cursor.sh was created
            if not os.path.exists("cursor.sh"):
                raise RuntimeError("cursor.sh was not created after transformation")

            debug_print("✓ cursor.sh creation verified")

        else:
            print("No update needed.")
    except Exception as e:
        debug_print(f"Error in main execution: {str(e)}")
        import traceback
        debug_print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
