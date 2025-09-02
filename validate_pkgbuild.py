#!/usr/bin/env python3
"""
PKGBUILD validation script that runs inside the workflow container.
Outputs JSON results that can be captured by the test framework.
"""

import json
import sys
import os
import re

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
