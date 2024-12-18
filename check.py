#!/usr/bin/env python
import requests
import re
import sys
import os
import json
import time
import yaml

def get_download_link(max_retries=2):
    url = 'https://download.todesktop.com/230313mzl4w4u92/latest-linux.yml'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    }
    
    for attempt in range(max_retries + 1):
        try:
            print(f"::debug::Attempt {attempt + 1} to get download link")
            print(f"::debug::URL: {url}")
            
            response = requests.get(url, headers=headers)
            print(f"::debug::Response status code: {response.status_code}")
            print(f"::debug::Response content: {response.text}")
            
            response.raise_for_status()
            
            yaml_data = yaml.safe_load(response.text)
            file_name = yaml_data['files'][0]['url']
            download_url = f"https://download.todesktop.com/230313mzl4w4u92/{file_name}"
            version = yaml_data['version']
            sha512 = yaml_data['files'][0]['sha512']
            
            return download_url, version, sha512
        except requests.exceptions.RequestException as e:
            print(f"::warning::Request failed: {str(e)}")
        except (yaml.YAMLError, KeyError) as e:
            print(f"::warning::Failed to parse YAML or extract data: {str(e)}")
        
        if attempt < max_retries:
            print(f"::debug::Retrying in 5 seconds...")
            time.sleep(5)
    
    print("::error::Failed to get download link after all retry attempts")
    return None, None, None

def get_local_pkgbuild_info():
    with open('PKGBUILD', 'r') as file:
        content = file.read()
    version_match = re.search(r'pkgver=([^\n]+)', content)
    rel_match = re.search(r'pkgrel=(\d+)', content)
    source_match = re.search(r'source_x86_64=\(".*?::([^"]+)"', content)
    if version_match and rel_match and source_match:
        return version_match.group(1).strip(), rel_match.group(1), source_match.group(1)
    else:
        print(f"::error::Unable to find current version, release, or source in local PKGBUILD")
        return None, None, None

def get_aur_pkgbuild_info():
    url = 'https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=cursor-bin'
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
        version_match = re.search(r'pkgver=([^\n]+)', content)
        rel_match = re.search(r'pkgrel=(\d+)', content)
        if version_match and rel_match:
            return version_match.group(1).strip(), rel_match.group(1)
        else:
            print(f"::warning::Unable to find version or release in AUR PKGBUILD")
            return None, None
    except Exception as e:
        print(f"::warning::Error fetching AUR PKGBUILD: {str(e)}")
        return None, None

try:
    # Check if DEBUG is set to true
    debug_mode = os.environ.get('DEBUG', '').lower() == 'true'

    # Get the download link, version, and sha512
    download_link, download_version, download_sha512 = get_download_link()
    if not download_link:
        raise ValueError("Failed to get download link after retries")
    
    print(f"::debug::Download link: {download_link}")
    print(f"::debug::Download version: {download_version}")
    print(f"::debug::Download SHA512: {download_sha512}")

    local_version, local_rel, local_source = get_local_pkgbuild_info()
    if local_version is None or local_rel is None or local_source is None:
        raise ValueError("Failed to get local version, release, or source")

    print(f"::debug::Local version: {local_version}, release: {local_rel}, source: {local_source}")

    # Determine if update is needed
    aur_version, aur_rel = get_aur_pkgbuild_info()
    print(f"::debug::AUR version: {aur_version}, release: {aur_rel}")
    update_needed = (
        debug_mode or 
        (download_version and download_version != local_version) or 
        (download_link != local_source) or
        (aur_version == local_version and aur_rel and local_rel and int(local_rel) > int(aur_rel))
    )

    # Determine new_version and new_rel
    if update_needed:
        new_version = download_version if download_version else local_version
        if new_version == local_version:
            new_rel = str(int(local_rel) + 1)
        else:
            new_rel = "1"
    else:
        new_version = local_version
        new_rel = local_rel

    print(f"::debug::New version: {new_version}, new release: {new_rel}")

    # Create output as JSON
    output = {
        "update_needed": update_needed,
        "local_version": local_version,
        "local_rel": local_rel,
        "local_source": local_source,
        "download_link": download_link,
        "new_version": new_version,
        "new_rel": new_rel,
        "download_version": download_version,
        "download_sha512": download_sha512,
        "aur_version": aur_version,
        "aur_rel": aur_rel
    }

    # Write JSON to file
    with open('check_output.json', 'w') as f:
        json.dump(output, f)

    print(f"::debug::Check output written to check_output.json")
    print(f"::debug::Final new_version: {new_version}, new_rel: {new_rel}")

except Exception as e:
    print(f"::error::Error in main execution: {str(e)}")
    sys.exit(1)