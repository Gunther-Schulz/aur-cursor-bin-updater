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


def extract_vscode_version_from_deb(temp_file_path):
    """Extract VSCode version from the .deb file using ar and tar."""
    try:
        debug_print(f"Using existing temporary .deb file: {temp_file_path}")

        # Extract the .deb file using ar and tar
        debug_print("Extracting product.json using .deb extraction...")
        
        # Create a temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            debug_print(f"Created temporary directory: {temp_dir}")
            
            # Extract data.tar.xz from the .deb file
            result = subprocess.run([
                'ar', 'x', temp_file_path, 'data.tar.xz'
            ], cwd=temp_dir, capture_output=True, text=True, timeout=60)

            debug_print(f"ar extraction result: {result.returncode}")
            if result.stderr:
                debug_print(f"ar extraction stderr: {result.stderr}")

            if result.returncode == 0:
                data_tar_path = os.path.join(temp_dir, 'data.tar.xz')
                if os.path.exists(data_tar_path):
                    # Extract product.json from data.tar.xz
                    result = subprocess.run([
                        'tar', '-xf', data_tar_path, './usr/share/cursor/resources/app/product.json'
                    ], cwd=temp_dir, capture_output=True, text=True, timeout=60)
                    
                    debug_print(f"tar extraction result: {result.returncode}")
                    if result.returncode == 0:
                        product_json_path = os.path.join(temp_dir, 'usr/share/cursor/resources/app/product.json')
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
                        debug_print("tar extraction failed")
                else:
                    debug_print(f"data.tar.xz not found at: {data_tar_path}")
            else:
                debug_print("ar extraction failed")

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

    # Download .deb file once and use it for both SHA512 and extraction
    deb_url = f"https://downloads.cursor.com/production/{new_commit}/linux/x64/deb/amd64/deb/cursor_{new_version}_amd64.deb"
    debug_print(f"Downloading .deb file once for SHA512 and extraction: {deb_url}")

    # Download the .deb file once and save to memory
    response = requests.get(deb_url, timeout=60)
    response.raise_for_status()
    deb_data = response.content
    response.close()

    # Calculate SHA512
    debug_print("Calculating SHA512...")
    sha512_hash = hashlib.sha512()
    sha512_hash.update(deb_data)
    deb_sha512 = sha512_hash.hexdigest()
    debug_print(f"Calculated .deb SHA512: {deb_sha512}")

    # Save the .deb file to a temporary file for extraction
    debug_print("Saving .deb file to temporary file for extraction...")
    with tempfile.NamedTemporaryFile(suffix='.deb', delete=False, mode='wb') as temp_file:
        temp_file.write(deb_data)
        temp_file_path = temp_file.name
    debug_print(f"Saved .deb file to {temp_file_path}, size: {len(deb_data)} bytes")

    # Determine Electron version
    debug_print("Starting Electron version determination...")
    vscode_version = extract_vscode_version_from_deb(temp_file_path)
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

    updated_lines = []
    in_sha = False

    for line in pkgbuild_lines:
        if line.startswith("pkgver="):
            updated_lines.append(f"pkgver={new_version}\n")
        elif line.startswith("pkgrel="):
            updated_lines.append(f"pkgrel={new_rel}\n")
        elif line.startswith("_commit="):
            updated_lines.append(f"_commit={new_commit} # sed'ded at GitHub WF\n")
        elif line.startswith("source="):
            # Update the source line with the new commit and version (.deb format)
            updated_lines.append(f'source=("https://downloads.cursor.com/production/{new_commit}/linux/x64/deb/amd64/deb/cursor_{new_version}_amd64.deb"\n')
        elif line.startswith("https://gitlab.archlinux.org"):
            # This is the second source line (code.sh)
            updated_lines.append(line)
        elif line.startswith("sha512sums="):
            updated_lines.append(f"sha512sums=('{deb_sha512}'\n")
            in_sha = True
        elif in_sha and line.strip().endswith(")"):
            # This is the last line of sha512sums, add the second checksum
            updated_lines.append(f"            '937299c6cb6be2f8d25f7dbc95cf77423875c5f8353b8bd6cd7cc8e5603cbf8405b14dbf8bd615db2e3b36ed680fc8e1909410815f7f8587b7267a699e00ab37')\n")
            in_sha = False
        elif line.startswith("  # Electron version determined during build process"):
            # Keep the comment
            updated_lines.append(line)
        elif line.startswith("  _electron="):
            # Update the electron version
            updated_lines.append(f"  _electron={electron_version}\n")
        elif line.startswith("  echo $_electron"):
            # Keep the echo line
            updated_lines.append(line)
        elif not in_sha:
            updated_lines.append(line)

    # Clean up temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
        debug_print(f"Cleaned up temporary file: {temp_file_path}")

    return updated_lines


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
            with open("PKGBUILD", "r") as f:
                current_pkgbuild = f.readlines()

            debug_print("Calling update_pkgbuild()")
            updated_pkgbuild = update_pkgbuild(current_pkgbuild, check_output)

            # Write the changes to the file
            with open("PKGBUILD", "w") as f:
                f.writelines(updated_pkgbuild)
            debug_print(
                f"PKGBUILD updated to version {check_output['new_version']} (release {check_output['new_rel']}) with commit {check_output['new_commit']}"
            )
        else:
            print("No update needed.")
    except Exception as e:
        debug_print(f"Error in main execution: {str(e)}")
        import traceback
        debug_print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
