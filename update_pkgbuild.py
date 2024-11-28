import sys
import json
import os
import base64

DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def base64_to_hex(base64_string):
    return base64.b64decode(base64_string).hex()

def update_pkgbuild(pkgbuild_lines, json_data):
    download_link = json_data['download_link']
    new_version = json_data['new_version']
    new_rel = json_data['new_rel']
    download_sha512 = base64_to_hex(json_data['download_sha512'])
    cursor_png_checksum = 'f948c5718c2df7fe2cae0cbcd95fd3010ecabe77c699209d4af5438215daecd74b08e03d18d07a26112bcc5a80958105fda724768394c838d08465fce5f473e7'
    cursor_desktop_checksum = 'e7e355524db7ddca2e02351f5af6ade791646b42434400f03f84e1068a43aadaa469ba6d5acbc16e6a3a7e52be4807b498585bea3f566e19b66414f6c3095154'
    cursor_launcher_checksum = 'ec3fa93a7df3ac97720d57e684f8745e3e34f39d9976163ea0001147961ca4caeb369de9d1e80c877bb417a0f1afa49547d154dde153be7fe6615092894cff47'

    updated_lines = []
    in_sha = False

    for line in pkgbuild_lines:
        if line.startswith('pkgver='):
            updated_lines.append(f'pkgver={new_version}\n')
        elif line.startswith('pkgrel='):
            updated_lines.append(f'pkgrel={new_rel}\n')
        elif line.startswith('source_x86_64='):
            updated_lines.append(f'source_x86_64=("${{_appimage}}::{download_link}" "cursor.png" "${{pkgname}}.desktop.in" "${{pkgname}}.sh")\n')
        elif line.startswith('sha512sums_x86_64='):
            updated_lines.append(f"sha512sums_x86_64=('{download_sha512}'\n")
            in_sha = True
        elif in_sha and line.strip().endswith(')'):
            updated_lines.append(f"                   '{cursor_png_checksum}'\n")
            updated_lines.append(f"                   '{cursor_desktop_checksum}'\n")
            updated_lines.append(f"                   '{cursor_launcher_checksum}')\n")
            in_sha = False
        elif not in_sha:
            updated_lines.append(line)

    return updated_lines

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_pkgbuild.py <check_output_file>")
        sys.exit(1)
    
    debug_print(f"Reading check output from {sys.argv[1]}")
    with open(sys.argv[1], 'r') as f:
        check_output = json.load(f)
    
    debug_print(f"Check output content: {json.dumps(check_output, indent=2)}")
    
    if check_output["update_needed"]:
        debug_print("Update needed, reading current PKGBUILD")
        with open('PKGBUILD', 'r') as f:
            current_pkgbuild = f.readlines()
        
        debug_print("Calling update_pkgbuild()")
        updated_pkgbuild = update_pkgbuild(current_pkgbuild, check_output)
        
        # Write the changes to the file
        with open('PKGBUILD', 'w') as f:
            f.writelines(updated_pkgbuild)
        debug_print(f"PKGBUILD updated to version {check_output['new_version']} (release {check_output['new_rel']}) with new download link and SHA512")
    else:
        print("No update needed.")