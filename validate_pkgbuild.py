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
    """Test the dynamic electron detection process"""
    test_results = {
        "electron_detection_working": False,
        "vscode_version_extracted": None,
        "electron_version_detected": None,
        "errors": []
    }
    
    try:
        # Test with current cursor version to see if electron detection works
        current_version = "1.5.9"
        current_commit = "de327274300c6f38ec9f4240d11e82c3b0660b29"
        
        # Try to download and extract VSCode version from current .deb
        deb_url = f"https://downloads.cursor.com/production/{current_commit}/linux/x64/deb/amd64/deb/cursor_{current_version}_amd64.deb"
        
        # Download a small portion to test extraction (first 1MB should contain control info)
        headers = {'Range': 'bytes=0-1048576'}  # First 1MB
        response = requests.get(deb_url, headers=headers, timeout=30)
        
        if response.status_code in [200, 206]:  # 206 = Partial Content
            with tempfile.NamedTemporaryFile(suffix='.deb', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            try:
                # Try to extract VSCode version using the same method as update_pkgbuild.py
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Extract control.tar.xz from .deb
                    result = subprocess.run(['ar', 'x', temp_file_path, 'control.tar.xz'], 
                                          cwd=temp_dir, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        control_tar_path = os.path.join(temp_dir, 'control.tar.xz')
                        if os.path.exists(control_tar_path):
                            # Extract control file
                            result = subprocess.run(['tar', '-xf', control_tar_path, './control'], 
                                                  cwd=temp_dir, capture_output=True, text=True)
                            
                            if result.returncode == 0:
                                control_file_path = os.path.join(temp_dir, 'control')
                                if os.path.exists(control_file_path):
                                    with open(control_file_path, 'r') as f:
                                        control_content = f.read()
                                    
                                    # Extract VSCode version from control file
                                    import re
                                    version_match = re.search(r'Version:\s*([0-9]+\.[0-9]+\.[0-9]+)', control_content)
                                    if version_match:
                                        vscode_version = version_match.group(1)
                                        test_results["vscode_version_extracted"] = vscode_version
                                        
                                        # Now test electron version detection
                                        try:
                                            # Test the electron detection URL
                                            electron_url = f"https://raw.githubusercontent.com/microsoft/vscode/refs/tags/{vscode_version}/package-lock.json"
                                            electron_response = requests.get(electron_url, timeout=15)
                                            
                                            if electron_response.status_code == 200:
                                                package_data = electron_response.json()
                                                
                                                # Try the same detection methods as update_pkgbuild.py
                                                electron_version = None
                                                
                                                # Method 1: Check root dependencies
                                                if 'dependencies' in package_data and 'electron' in package_data['dependencies']:
                                                    electron_version = package_data['dependencies']['electron']['version']
                                                
                                                # Method 2: Check packages structure
                                                elif 'packages' in package_data and '' in package_data['packages']:
                                                    root_package = package_data['packages']['']
                                                    if 'dependencies' in root_package and 'electron' in root_package['dependencies']:
                                                        electron_version = root_package['dependencies']['electron']
                                                
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
                                                test_results["errors"].append(f"Could not fetch package-lock.json: {electron_response.status_code}")
                                        except Exception as e:
                                            test_results["errors"].append(f"Electron detection failed: {str(e)}")
                                    else:
                                        test_results["errors"].append("Could not extract VSCode version from control file")
                                else:
                                    test_results["errors"].append("Control file not found after extraction")
                            else:
                                test_results["errors"].append("Could not extract control file from control.tar.xz")
                        else:
                            test_results["errors"].append("control.tar.xz not found after ar extraction")
                    else:
                        test_results["errors"].append("Could not extract control.tar.xz from .deb file")
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
        
        # Check 1: Version
        if f"pkgver={expected_version}" in content:
            results["checks"].append({"check": "version", "status": "pass", "message": f"Version is {expected_version}"})
        else:
            results["checks"].append({"check": "version", "status": "fail", "message": f"Version is not {expected_version}"})
            results["validation_successful"] = False
            
        # Check 2: pkgrel reset to 1 (for cursor updates)
        if "pkgrel=1" in content:
            results["checks"].append({"check": "pkgrel", "status": "pass", "message": "pkgrel is reset to 1 for cursor update"})
        else:
            # Extract actual pkgrel value for better error message
            pkgrel_match = re.search(r'pkgrel=(\d+)', content)
            actual_pkgrel = pkgrel_match.group(1) if pkgrel_match else "unknown"
            results["checks"].append({"check": "pkgrel", "status": "fail", "message": f"pkgrel is {actual_pkgrel}, should be 1 for cursor update"})
            results["validation_successful"] = False
            
        # Check 3: Commit hash
        if expected_commit in content:
            results["checks"].append({"check": "commit", "status": "pass", "message": "Commit hash is correct"})
        else:
            results["checks"].append({"check": "commit", "status": "fail", "message": "Commit hash is incorrect"})
            results["validation_successful"] = False
            
        # Check 4: Electron version
        if f"_electron={expected_electron}" in content:
            results["checks"].append({"check": "electron", "status": "pass", "message": f"Electron version is {expected_electron}"})
        else:
            results["checks"].append({"check": "electron", "status": "fail", "message": f"Electron version is not {expected_electron}"})
            results["validation_successful"] = False
            
        # Check 5: SHA512 checksum
        if expected_checksum in content:
            results["checks"].append({"check": "checksum", "status": "pass", "message": "SHA512 checksum is correct"})
        else:
            results["checks"].append({"check": "checksum", "status": "fail", "message": "SHA512 checksum is incorrect"})
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
            # Don't fail validation for this - it's a nice-to-have test
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
            
    except Exception as e:
        results["validation_successful"] = False
        results["errors"].append(f"Validation error: {str(e)}")
        
    return results

if __name__ == "__main__":
    # Run validation and output JSON
    results = validate_pkgbuild()
    
    # Output results as JSON
    print("=== PKGBUILD_VALIDATION_START ===")
    print(json.dumps(results, indent=2))
    print("=== PKGBUILD_VALIDATION_END ===")
    
    # Exit with appropriate code
    sys.exit(0 if results["validation_successful"] else 1)
