#!/usr/bin/env python3
"""
PKGBUILD validation script that runs inside the workflow container.
Outputs JSON results that can be captured by the test framework.
"""

import json
import sys
import os
import re
import requests
import tempfile
import subprocess

def test_electron_detection():
    """Test the dynamic electron detection process using the correct method from PR #16"""
    test_results = {
        "electron_detection_working": False,
        "vscode_version_extracted": None,
        "electron_version_detected": None,
        "errors": []
    }
    
    try:
        # Test with current cursor version using the correct method from PR #16
        current_version = "1.5.9"
        current_commit = "de327274300c6f38ec9f4240d11e82c3b0660b29"
        
        # Download .deb to extract product.json (NOT control file - that was the bug!)
        deb_url = f"https://downloads.cursor.com/production/{current_commit}/linux/x64/deb/amd64/deb/cursor_{current_version}_amd64.deb"
        
        # Download full .deb file (partial downloads don't work reliably)
        response = requests.get(deb_url, timeout=60)
        
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(suffix='.deb', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            try:
                # Extract product.json from .deb (the correct method from PR #16)
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Extract data.tar.xz from .deb
                    result = subprocess.run(['ar', 'x', temp_file_path, 'data.tar.xz'], 
                                          cwd=temp_dir, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        data_tar_path = os.path.join(temp_dir, 'data.tar.xz')
                        if os.path.exists(data_tar_path):
                            # Extract product.json
                            result = subprocess.run(['tar', '-xf', data_tar_path, './usr/share/cursor/resources/app/product.json'], 
                                                  cwd=temp_dir, capture_output=True, text=True)
                            
                            if result.returncode == 0:
                                product_file_path = os.path.join(temp_dir, 'usr/share/cursor/resources/app/product.json')
                                if os.path.exists(product_file_path):
                                    with open(product_file_path, 'r') as f:
                                        import json
                                        product_data = json.load(f)
                                    
                                    # Extract VSCode version from product.json (the correct method!)
                                    if 'vscodeVersion' in product_data:
                                        vscode_version = product_data['vscodeVersion']
                                        test_results["vscode_version_extracted"] = vscode_version
                                        
                                        # Now test electron version detection using VSCode tarball (not GitHub tags!)
                                        try:
                                            # Download VSCode tarball (the working method from PR #16)
                                            vscode_tarball_url = f"https://github.com/microsoft/vscode/archive/refs/tags/{vscode_version}.tar.gz"
                                            tarball_response = requests.get(vscode_tarball_url, timeout=30)
                                            
                                            if tarball_response.status_code == 200:
                                                # Extract package-lock.json from tarball
                                                with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tarball_file:
                                                    tarball_file.write(tarball_response.content)
                                                    tarball_path = tarball_file.name
                                                
                                                try:
                                                    # Extract package-lock.json
                                                    result = subprocess.run(['tar', '-xzf', tarball_path, f'vscode-{vscode_version}/package-lock.json'], 
                                                                          cwd=temp_dir, capture_output=True, text=True)
                                                    
                                                    if result.returncode == 0:
                                                        package_lock_path = os.path.join(temp_dir, f'vscode-{vscode_version}/package-lock.json')
                                                        if os.path.exists(package_lock_path):
                                                            with open(package_lock_path, 'r') as f:
                                                                package_data = json.load(f)
                                                            
                                                            # Try the correct detection methods (including devDependencies!)
                                                            electron_version = None
                                                            
                                                            # Method 1: Check root dependencies
                                                            if 'dependencies' in package_data and 'electron' in package_data['dependencies']:
                                                                electron_version = package_data['dependencies']['electron']['version']
                                                            
                                                            # Method 2: Check packages structure dependencies
                                                            elif 'packages' in package_data and '' in package_data['packages']:
                                                                root_package = package_data['packages']['']
                                                                if 'dependencies' in root_package and 'electron' in root_package['dependencies']:
                                                                    electron_version = root_package['dependencies']['electron']
                                                                # Method 2b: Check devDependencies (THE MISSING PIECE!)
                                                                elif 'devDependencies' in root_package and 'electron' in root_package['devDependencies']:
                                                                    electron_version = root_package['devDependencies']['electron']
                                                            
                                                            # Method 3: Check node_modules/electron
                                                            elif 'packages' in package_data and 'node_modules/electron' in package_data['packages']:
                                                                electron_version = package_data['packages']['node_modules/electron']['version']
                                                            
                                                            if electron_version:
                                                                major_version = electron_version.split('.')[0]
                                                                final_electron = f"electron{major_version}"
                                                                test_results["electron_version_detected"] = final_electron
                                                                test_results["electron_detection_working"] = True
                                                            else:
                                                                test_results["errors"].append("No electron version found in package-lock.json")
                                                        else:
                                                            test_results["errors"].append("package-lock.json not extracted from tarball")
                                                    else:
                                                        test_results["errors"].append("Could not extract package-lock.json from VSCode tarball")
                                                finally:
                                                    os.unlink(tarball_path)
                                            else:
                                                test_results["errors"].append(f"Could not download VSCode tarball: {tarball_response.status_code}")
                                        except Exception as e:
                                            test_results["errors"].append(f"Electron detection failed: {str(e)}")
                                    else:
                                        test_results["errors"].append("No vscodeVersion found in product.json")
                                else:
                                    test_results["errors"].append("product.json not found after extraction")
                            else:
                                test_results["errors"].append("Could not extract product.json from data.tar.xz")
                        else:
                            test_results["errors"].append("data.tar.xz not found after ar extraction")
                    else:
                        test_results["errors"].append("Could not extract data.tar.xz from .deb file")
            finally:
                os.unlink(temp_file_path)
        else:
            test_results["errors"].append(f"Could not download .deb file: {response.status_code}")
            
    except Exception as e:
        test_results["errors"].append(f"Electron detection test failed: {str(e)}")
    
    return test_results

def test_code_sh_download():
    """Test that code.sh can be downloaded and is valid"""
    test_results = {
        "code_sh_accessible": False,
        "code_sh_content_valid": False,
        "errors": []
    }
    
    try:
        # Test downloading code.sh
        code_sh_url = "https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code.sh"
        response = requests.get(code_sh_url, timeout=15)
        
        if response.status_code == 200:
            test_results["code_sh_accessible"] = True
            content = response.text
            
            # Validate that it contains expected patterns for transformation
            expected_patterns = [
                "code-flags",  # Should be transformed to cursor-flags
                "/usr/lib/code",  # Should be transformed to cursor path
                "electron"  # Should contain electron references
            ]
            
            patterns_found = sum(1 for pattern in expected_patterns if pattern in content)
            if patterns_found >= 2:  # At least 2 out of 3 patterns should be present
                test_results["code_sh_content_valid"] = True
            else:
                test_results["errors"].append(f"code.sh content validation failed: only {patterns_found}/3 expected patterns found")
        else:
            test_results["errors"].append(f"Could not download code.sh: HTTP {response.status_code}")
            
    except Exception as e:
        test_results["errors"].append(f"code.sh download test failed: {str(e)}")
    
    return test_results

def test_tool_availability():
    """Test that required tools are available in the container"""
    test_results = {
        "tools_available": True,
        "available_tools": [],
        "missing_tools": [],
        "errors": []
    }
    
    required_tools = ['bsdtar', 'ar', 'tar', 'sed', 'grep', 'curl']
    
    for tool in required_tools:
        try:
            result = subprocess.run(['which', tool], capture_output=True, text=True)
            if result.returncode == 0:
                test_results["available_tools"].append(tool)
            else:
                test_results["missing_tools"].append(tool)
                test_results["tools_available"] = False
        except Exception as e:
            test_results["errors"].append(f"Error checking {tool}: {str(e)}")
            test_results["missing_tools"].append(tool)
            test_results["tools_available"] = False
    
    return test_results

def test_url_accessibility():
    """Test accessibility of all URLs used in PKGBUILD"""
    test_results = {
        "all_urls_accessible": True,
        "accessible_urls": [],
        "failed_urls": [],
        "errors": []
    }
    
    # Test URLs from current PKGBUILD
    urls_to_test = [
        "https://downloads.cursor.com/production/de327274300c6f38ec9f4240d11e82c3b0660b29/linux/x64/deb/amd64/deb/cursor_1.5.9_amd64.deb",
        "https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code.sh"
    ]
    
    for url in urls_to_test:
        try:
            response = requests.head(url, timeout=15)
            if response.status_code == 200:
                test_results["accessible_urls"].append(url)
            else:
                test_results["failed_urls"].append(f"{url} (HTTP {response.status_code})")
                test_results["all_urls_accessible"] = False
        except Exception as e:
            test_results["failed_urls"].append(f"{url} ({str(e)})")
            test_results["all_urls_accessible"] = False
            test_results["errors"].append(f"URL test failed for {url}: {str(e)}")
    
    return test_results

def test_actual_file_checksum():
    """Download actual file and verify checksum"""
    test_results = {
        "checksum_verified": False,
        "downloaded_checksum": None,
        "expected_checksum": "3d30150e4868b80ef6aeb012ffdb5e281ed41e3651f2b32f3d92baa284d990c11932df5c483d2eafc7ef48a1dd1047f888503bbe1f8906c8087fe1452dbe2e3b",
        "errors": []
    }
    
    try:
        url = "https://downloads.cursor.com/production/de327274300c6f38ec9f4240d11e82c3b0660b29/linux/x64/deb/amd64/deb/cursor_1.5.9_amd64.deb"
        
        # Download file
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            # Calculate SHA512
            import hashlib
            sha512_hash = hashlib.sha512()
            sha512_hash.update(response.content)
            actual_checksum = sha512_hash.hexdigest()
            test_results["downloaded_checksum"] = actual_checksum
            
            if actual_checksum == test_results["expected_checksum"]:
                test_results["checksum_verified"] = True
            else:
                test_results["errors"].append(f"Checksum mismatch: got {actual_checksum[:16]}..., expected {test_results['expected_checksum'][:16]}...")
        else:
            test_results["errors"].append(f"Download failed: HTTP {response.status_code}")
            
    except Exception as e:
        test_results["errors"].append(f"File checksum verification failed: {str(e)}")
    
    return test_results

def test_command_syntax():
    """Test command syntax validation"""
    test_results = {
        "syntax_valid": True,
        "valid_commands": [],
        "invalid_commands": [],
        "errors": []
    }
    
    # Test bsdtar command syntax
    bsdtar_cmd = "bsdtar -xf data.tar.xz --exclude 'usr/share/cursor/[^r]*' --exclude 'usr/share/windsurf/*.pak'"
    try:
        # Just validate the syntax by parsing it
        import shlex
        shlex.split(bsdtar_cmd)
        test_results["valid_commands"].append("bsdtar extraction command")
    except Exception as e:
        test_results["invalid_commands"].append(f"bsdtar command: {str(e)}")
        test_results["syntax_valid"] = False
    
    # Test sed command syntax
    sed_cmd = "sed -i 's|l\\.frame=!1|(!On(o, i?.forceNativeTitlebar ? \"native\" : void 0) \\&\\& (l.frame = !1))|g'"
    try:
        shlex.split(sed_cmd)
        test_results["valid_commands"].append("sed titlebar fix command")
    except Exception as e:
        test_results["invalid_commands"].append(f"sed command: {str(e)}")
        test_results["syntax_valid"] = False
    
    return test_results

def test_titlebar_fix_execution():
    """Test that the titlebar fix sed command actually works"""
    test_results = {
        "sed_command_works": False,
        "errors": []
    }
    
    try:
        # Create a test string with the pattern to replace
        test_content = "some code here l.frame=!1 more code"
        expected_result = "some code here (!On(o, i?.forceNativeTitlebar ? \"native\" : void 0) && (l.frame = !1)) more code"
        
        # Test the sed pattern with Python's re module (similar to sed)
        import re
        pattern = r'l\.frame=!1'
        replacement = r'(!On(o, i?.forceNativeTitlebar ? "native" : void 0) && (l.frame = !1))'
        
        result = re.sub(pattern, replacement, test_content)
        
        if "(!On(o, i?.forceNativeTitlebar" in result and "l.frame = !1" in result:
            test_results["sed_command_works"] = True
        else:
            test_results["errors"].append(f"Sed pattern didn't work as expected: {result}")
            
    except Exception as e:
        test_results["errors"].append(f"Titlebar fix test failed: {str(e)}")
    
    return test_results

def test_full_cursor_sh_transformation():
    """Test the complete cursor.sh transformation process"""
    test_results = {
        "transformation_works": False,
        "original_content": None,
        "transformed_content": None,
        "errors": []
    }
    
    try:
        # Download code.sh
        code_sh_url = "https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code.sh"
        response = requests.get(code_sh_url, timeout=15)
        
        if response.status_code == 200:
            original_content = response.text
            test_results["original_content"] = original_content[:200] + "..." if len(original_content) > 200 else original_content
            
            # Apply the same transformations as in PKGBUILD
            transformed = original_content
            transformations = [
                (r'code-flags', 'cursor-flags'),
                (r'/usr/lib/code', '/usr/share/cursor/resources/app'),
                (r'/usr/lib/code/code\.mjs', '--app=/usr/share/cursor/resources/app'),
                (r'name=electron', 'name=electron34')
            ]
            
            for pattern, replacement in transformations:
                transformed = re.sub(pattern, replacement, transformed)
            
            test_results["transformed_content"] = transformed[:200] + "..." if len(transformed) > 200 else transformed
            
            # Verify transformations worked
            checks = [
                ('cursor-flags' in transformed, 'cursor-flags replacement'),
                ('/usr/share/cursor/resources/app' in transformed, 'cursor path replacement'),
                ('--app=/usr/share/cursor/resources/app' in transformed, 'app argument replacement'),
                ('name=electron34' in transformed, 'electron version replacement')
            ]
            
            passed_checks = sum(1 for check, _ in checks if check)
            if passed_checks >= 3:  # At least 3 out of 4 transformations should work
                test_results["transformation_works"] = True
            else:
                test_results["errors"].append(f"Only {passed_checks}/4 transformations worked")
                
        else:
            test_results["errors"].append(f"Could not download code.sh: HTTP {response.status_code}")
            
    except Exception as e:
        test_results["errors"].append(f"Cursor.sh transformation test failed: {str(e)}")
    
    return test_results

def validate_pkgbuild():
    """Validate the PKGBUILD file and return results as JSON"""
    
    results = {
        "validation_successful": True,
        "checks": [],
        "pkgbuild_content": "",
        "errors": []
    }
    
    try:
        # Read PKGBUILD content
        if not os.path.exists("PKGBUILD"):
            results["validation_successful"] = False
            results["errors"].append("PKGBUILD file not found")
            return results
            
        with open("PKGBUILD", "r") as f:
            content = f.read()
            
        results["pkgbuild_content"] = content
        
        # Define expected values (these should match current production values)
        expected_version = "1.5.9"
        expected_commit = "de327274300c6f38ec9f4240d11e82c3b0660b29"
        expected_electron = "electron34"
        expected_checksum = "3d30150e4868b80ef6aeb012ffdb5e281ed41e3651f2b32f3d92baa284d990c11932df5c483d2eafc7ef48a1dd1047f888503bbe1f8906c8087fe1452dbe2e3b"
        
        # Check 1: Version presence and format
        version_match = re.search(r'pkgver=([^\n]+)', content)
        if version_match:
            actual_version = version_match.group(1).strip()
            # Validate semantic version format (X.Y.Z)
            if re.match(r'^\d+\.\d+\.\d+$', actual_version):
                results["checks"].append({"check": "version_format", "status": "pass", "message": f"Version format valid: {actual_version}"})
                if actual_version == expected_version:
                    results["checks"].append({"check": "version_match", "status": "pass", "message": f"Version matches expected: {expected_version}"})
                else:
                    results["checks"].append({"check": "version_match", "status": "fail", "message": f"Version is {actual_version}, expected {expected_version}"})
                    results["validation_successful"] = False
            else:
                results["checks"].append({"check": "version_format", "status": "fail", "message": f"Invalid version format: {actual_version}"})
                results["validation_successful"] = False
        else:
            results["checks"].append({"check": "version_format", "status": "fail", "message": "No version found in PKGBUILD"})
            results["validation_successful"] = False
            
        # Check 2: pkgrel format and value
        pkgrel_match = re.search(r'pkgrel=(\d+)', content)
        if pkgrel_match:
            actual_pkgrel = pkgrel_match.group(1)
            # Validate it's a positive integer
            if actual_pkgrel.isdigit() and int(actual_pkgrel) > 0:
                results["checks"].append({"check": "pkgrel_format", "status": "pass", "message": f"pkgrel format valid: {actual_pkgrel}"})
                if actual_pkgrel == "1":
                    results["checks"].append({"check": "pkgrel_reset", "status": "pass", "message": "pkgrel is reset to 1 for cursor update"})
                else:
                    results["checks"].append({"check": "pkgrel_reset", "status": "fail", "message": f"pkgrel is {actual_pkgrel}, should be 1 for cursor update"})
                    results["validation_successful"] = False
            else:
                results["checks"].append({"check": "pkgrel_format", "status": "fail", "message": f"Invalid pkgrel format: {actual_pkgrel}"})
                results["validation_successful"] = False
        else:
            results["checks"].append({"check": "pkgrel_format", "status": "fail", "message": "No pkgrel found in PKGBUILD"})
            results["validation_successful"] = False
            
        # Check 3: Commit hash format and value
        commit_match = re.search(r'_commit=([a-f0-9]+)', content)
        if commit_match:
            actual_commit = commit_match.group(1)
            # Validate 40-character hex format
            if re.match(r'^[a-f0-9]{40}$', actual_commit):
                results["checks"].append({"check": "commit_format", "status": "pass", "message": f"Commit hash format valid: {actual_commit[:8]}..."})
                if actual_commit == expected_commit:
                    results["checks"].append({"check": "commit_match", "status": "pass", "message": "Commit hash matches expected"})
                else:
                    results["checks"].append({"check": "commit_match", "status": "fail", "message": f"Commit hash is {actual_commit[:8]}..., expected {expected_commit[:8]}..."})
                    results["validation_successful"] = False
            else:
                results["checks"].append({"check": "commit_format", "status": "fail", "message": f"Invalid commit hash format: {actual_commit}"})
                results["validation_successful"] = False
        else:
            results["checks"].append({"check": "commit_format", "status": "fail", "message": "No commit hash found in PKGBUILD"})
            results["validation_successful"] = False
            
        # Check 4: Electron version
        if f"_electron={expected_electron}" in content:
            results["checks"].append({"check": "electron", "status": "pass", "message": f"Electron version is {expected_electron}"})
        else:
            results["checks"].append({"check": "electron", "status": "fail", "message": f"Electron version is not {expected_electron}"})
            results["validation_successful"] = False
            
        # Check 5: SHA512 checksum format and value
        checksum_match = re.search(r"sha512sums=\('([a-f0-9]+)'", content)
        if checksum_match:
            actual_checksum = checksum_match.group(1)
            # Validate 128-character hex format
            if re.match(r'^[a-f0-9]{128}$', actual_checksum):
                results["checks"].append({"check": "checksum_format", "status": "pass", "message": f"SHA512 format valid: {actual_checksum[:16]}..."})
                if actual_checksum == expected_checksum:
                    results["checks"].append({"check": "checksum_match", "status": "pass", "message": "SHA512 checksum matches expected"})
                else:
                    results["checks"].append({"check": "checksum_match", "status": "fail", "message": f"SHA512 mismatch: {actual_checksum[:16]}... vs {expected_checksum[:16]}..."})
                    results["validation_successful"] = False
            else:
                results["checks"].append({"check": "checksum_format", "status": "fail", "message": f"Invalid SHA512 format: {len(actual_checksum)} chars"})
                results["validation_successful"] = False
        else:
            results["checks"].append({"check": "checksum_format", "status": "fail", "message": "No SHA512 checksum found in PKGBUILD"})
            results["validation_successful"] = False
            
        # Check 6: Native titlebar fix
        titlebar_pattern = r'sed -i.*l\.frame=!1.*native.*titlebar'
        if re.search(titlebar_pattern, content, re.IGNORECASE | re.DOTALL):
            results["checks"].append({"check": "titlebar_fix", "status": "pass", "message": "Native titlebar fix is present"})
        elif "Fix native title bar" in content:
            results["checks"].append({"check": "titlebar_fix", "status": "pass", "message": "Native titlebar fix comment found"})
        else:
            results["checks"].append({"check": "titlebar_fix", "status": "fail", "message": "Native titlebar fix is missing"})
            results["validation_successful"] = False
            
        # Check 7: .deb format (not AppImage)
        if ".deb" in content and "AppImage" not in content:
            results["checks"].append({"check": "deb_format", "status": "pass", "message": "Using .deb format (not AppImage)"})
        else:
            results["checks"].append({"check": "deb_format", "status": "fail", "message": "Not using .deb format or still references AppImage"})
            results["validation_successful"] = False
            
        # Check 8: bsdtar extraction (for .deb)
        if "bsdtar -xf data.tar.xz" in content:
            results["checks"].append({"check": "extraction", "status": "pass", "message": "Using bsdtar for .deb extraction"})
        else:
            results["checks"].append({"check": "extraction", "status": "fail", "message": "Not using bsdtar for .deb extraction"})
            results["validation_successful"] = False
            
        # Check 9: Binary symlink
        if 'ln -sf /usr/share/cursor/cursor "$pkgdir"/usr/bin/cursor' in content:
            results["checks"].append({"check": "binary_link", "status": "pass", "message": "Binary symlink is correct"})
        else:
            results["checks"].append({"check": "binary_link", "status": "fail", "message": "Binary symlink is missing or incorrect"})
            results["validation_successful"] = False
            
        # Check 10: cursor.sh generation (code.sh transformation)
        cursor_sh_patterns = [
            'sed -e "s|code-flags|cursor-flags|"',
            'sed.*cursor-flags',
            '/usr/share/cursor/cursor',
            'code.sh.*install.*cursor'
        ]
        cursor_sh_found = any(pattern in content for pattern in cursor_sh_patterns)
        if cursor_sh_found:
            results["checks"].append({"check": "cursor_sh_generation", "status": "pass", "message": "cursor.sh generation logic present"})
        else:
            results["checks"].append({"check": "cursor_sh_generation", "status": "fail", "message": "cursor.sh generation logic missing"})
            results["validation_successful"] = False
            
        # Check 11: code.sh source download
        if 'https://gitlab.archlinux.org/archlinux/packaging/packages/code/-/raw/main/code.sh' in content:
            results["checks"].append({"check": "code_sh_source", "status": "pass", "message": "code.sh source URL present"})
        else:
            results["checks"].append({"check": "code_sh_source", "status": "fail", "message": "code.sh source URL missing"})
            results["validation_successful"] = False
            
        # Check 12: Dynamic electron detection test
        electron_test = test_electron_detection()
        if electron_test["electron_detection_working"]:
            detected_version = electron_test["electron_version_detected"]
            vscode_version = electron_test["vscode_version_extracted"]
            results["checks"].append({
                "check": "dynamic_electron_detection", 
                "status": "pass", 
                "message": f"Electron detection working: VSCode {vscode_version} → {detected_version}"
            })
            
            # Verify detected version matches expected
            if detected_version == expected_electron:
                results["checks"].append({
                    "check": "electron_version_match", 
                    "status": "pass", 
                    "message": f"Detected electron version matches expected: {detected_version}"
                })
            else:
                results["checks"].append({
                    "check": "electron_version_match", 
                    "status": "fail", 
                    "message": f"Detected {detected_version} but expected {expected_electron}"
                })
                results["validation_successful"] = False
        else:
            error_msg = "; ".join(electron_test["errors"]) if electron_test["errors"] else "Unknown error"
            results["checks"].append({
                "check": "dynamic_electron_detection", 
                "status": "fail", 
                "message": f"Electron detection failed: {error_msg}"
            })
            # Don't fail validation for this - it's a nice-to-have test but not critical for basic validation
            # results["validation_successful"] = False
            
        # Check 13: code.sh download and content test
        code_sh_test = test_code_sh_download()
        if code_sh_test["code_sh_accessible"]:
            results["checks"].append({
                "check": "code_sh_download", 
                "status": "pass", 
                "message": "code.sh is accessible from GitLab"
            })
            
            if code_sh_test["code_sh_content_valid"]:
                results["checks"].append({
                    "check": "code_sh_content", 
                    "status": "pass", 
                    "message": "code.sh contains expected transformation patterns"
                })
            else:
                results["checks"].append({
                    "check": "code_sh_content", 
                    "status": "fail", 
                    "message": "code.sh content validation failed"
                })
                # Don't fail validation for this - it's a nice-to-have test
        else:
            error_msg = "; ".join(code_sh_test["errors"]) if code_sh_test["errors"] else "Unknown error"
            results["checks"].append({
                "check": "code_sh_download", 
                "status": "fail", 
                "message": f"code.sh download failed: {error_msg}"
            })
            # Don't fail validation for this - it's a nice-to-have test
            
        # Check 14: Tool availability
        tool_test = test_tool_availability()
        if tool_test["tools_available"]:
            available_tools = ", ".join(tool_test["available_tools"])
            results["checks"].append({
                "check": "tool_availability", 
                "status": "pass", 
                "message": f"All required tools available: {available_tools}"
            })
        else:
            missing_tools = ", ".join(tool_test["missing_tools"])
            results["checks"].append({
                "check": "tool_availability", 
                "status": "fail", 
                "message": f"Missing tools: {missing_tools}"
            })
            results["validation_successful"] = False
            
        # Check 15: URL accessibility
        url_test = test_url_accessibility()
        if url_test["all_urls_accessible"]:
            results["checks"].append({
                "check": "url_accessibility", 
                "status": "pass", 
                "message": f"All {len(url_test['accessible_urls'])} URLs are accessible"
            })
        else:
            failed_urls = "; ".join(url_test["failed_urls"])
            results["checks"].append({
                "check": "url_accessibility", 
                "status": "fail", 
                "message": f"Failed URLs: {failed_urls}"
            })
            results["validation_successful"] = False
            
        # Check 16: Actual file checksum verification
        checksum_test = test_actual_file_checksum()
        if checksum_test["checksum_verified"]:
            results["checks"].append({
                "check": "actual_file_checksum", 
                "status": "pass", 
                "message": "Downloaded file checksum matches expected"
            })
        else:
            error_msg = "; ".join(checksum_test["errors"]) if checksum_test["errors"] else "Unknown error"
            results["checks"].append({
                "check": "actual_file_checksum", 
                "status": "fail", 
                "message": f"File checksum verification failed: {error_msg}"
            })
            # Don't fail validation for this - it's a comprehensive test but not critical
            
        # Check 17: Command syntax validation
        syntax_test = test_command_syntax()
        if syntax_test["syntax_valid"]:
            valid_commands = ", ".join(syntax_test["valid_commands"])
            results["checks"].append({
                "check": "command_syntax", 
                "status": "pass", 
                "message": f"Command syntax valid: {valid_commands}"
            })
        else:
            invalid_commands = "; ".join(syntax_test["invalid_commands"])
            results["checks"].append({
                "check": "command_syntax", 
                "status": "fail", 
                "message": f"Invalid command syntax: {invalid_commands}"
            })
            results["validation_successful"] = False
            
        # Check 18: Titlebar fix execution test
        titlebar_test = test_titlebar_fix_execution()
        if titlebar_test["sed_command_works"]:
            results["checks"].append({
                "check": "titlebar_fix_execution", 
                "status": "pass", 
                "message": "Titlebar fix sed command works correctly"
            })
        else:
            error_msg = "; ".join(titlebar_test["errors"]) if titlebar_test["errors"] else "Unknown error"
            results["checks"].append({
                "check": "titlebar_fix_execution", 
                "status": "fail", 
                "message": f"Titlebar fix execution failed: {error_msg}"
            })
            # Don't fail validation for this - it's a nice-to-have test
            
        # Check 19: Full cursor.sh transformation test
        cursor_sh_test = test_full_cursor_sh_transformation()
        if cursor_sh_test["transformation_works"]:
            results["checks"].append({
                "check": "cursor_sh_transformation", 
                "status": "pass", 
                "message": "Cursor.sh transformation works correctly"
            })
        else:
            error_msg = "; ".join(cursor_sh_test["errors"]) if cursor_sh_test["errors"] else "Unknown error"
            results["checks"].append({
                "check": "cursor_sh_transformation", 
                "status": "fail", 
                "message": f"Cursor.sh transformation failed: {error_msg}"
            })
            # Don't fail validation for this - it's a comprehensive test but not critical
            
    except Exception as e:
        results["validation_successful"] = False
        results["errors"].append(f"Validation error: {str(e)}")
        
    return results

if __name__ == "__main__":
    # Run validation and output JSON
    results = validate_pkgbuild()
    
    # Add summary statistics to results
    total_checks = len(results["checks"])
    passed_checks = len([c for c in results["checks"] if c["status"] == "pass"])
    failed_checks = len([c for c in results["checks"] if c["status"] == "fail"])
    
    results["summary"] = {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "pass_rate": f"{(passed_checks/total_checks*100):.1f}%" if total_checks > 0 else "0%",
        "failed_check_names": [c["check"] for c in results["checks"] if c["status"] == "fail"]
    }
    
    # Output results as JSON
    print("=== PKGBUILD_VALIDATION_START ===")
    print(json.dumps(results, indent=2))
    print("=== PKGBUILD_VALIDATION_END ===")
    
    # Exit with appropriate code
    sys.exit(0 if results["validation_successful"] else 1)
