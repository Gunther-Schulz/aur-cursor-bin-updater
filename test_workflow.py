#!/usr/bin/env python3
"""
Test script to simulate a Cursor update and test the full workflow.

This script:
1. Backs up the current PKGBUILD
2. Temporarily downgrades it to simulate being behind
3. Runs the workflow with 'act' to test the full update process
4. Validates the results
5. Restores the original PKGBUILD
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import requests
from pathlib import Path

class WorkflowTester:
    def __init__(self):
        self.backup_file = "PKGBUILD.test_backup"
        self.original_pkgbuild = None
        self.current_version = None
        self.current_commit = None
        self.current_pkgrel = None
        self.test_version = None
        self.test_pkgrel = "1"
        self.test_commit = None
        
    def log(self, message, level="INFO"):
        print(f"[{level}] {message}")
        
    def parse_current_pkgbuild(self):
        """Parse current PKGBUILD to extract version, commit, and pkgrel"""
        self.log("Parsing current PKGBUILD...")
        
        with open("PKGBUILD", "r") as f:
            content = f.read()
            
        # Extract current values
        for line in content.split('\n'):
            if line.startswith("pkgver="):
                self.current_version = line.split('=', 1)[1].strip()
            elif line.startswith("pkgrel="):
                self.current_pkgrel = line.split('=', 1)[1].strip()
            elif line.startswith("_commit="):
                # Extract just the commit hash (before any comments)
                commit_part = line.split('=', 1)[1].strip()
                self.current_commit = commit_part.split()[0]  # Take first part before any comments
                
        self.log(f"Current: version={self.current_version}, pkgrel={self.current_pkgrel}, commit={self.current_commit}")
        
        if not all([self.current_version, self.current_commit, self.current_pkgrel]):
            raise ValueError("Could not parse current PKGBUILD values")
            
    def determine_test_version(self):
        """Automatically determine what version to downgrade to for testing"""
        self.log("Determining test version...")
        
        # Parse current version (e.g., "1.5.9" -> [1, 5, 9])
        try:
            version_parts = [int(x) for x in self.current_version.split('.')]
        except ValueError:
            raise ValueError(f"Cannot parse version: {self.current_version}")
            
        # Try different downgrade strategies
        test_versions = []
        
        # Strategy 1: Decrease patch version (1.5.9 -> 1.5.8)
        if version_parts[2] > 0:
            test_parts = version_parts.copy()
            test_parts[2] -= 1
            test_versions.append('.'.join(map(str, test_parts)))
            
        # Strategy 2: Decrease minor version (1.5.9 -> 1.4.9)
        if version_parts[1] > 0:
            test_parts = version_parts.copy()
            test_parts[1] -= 1
            test_versions.append('.'.join(map(str, test_parts)))
            
        # Strategy 3: Use git history to find a previous version
        try:
            result = subprocess.run(["git", "log", "--oneline", "-10", "--grep=version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower():
                        # Try to extract version from commit message
                        import re
                        version_match = re.search(r'(\d+\.\d+\.\d+)', line)
                        if version_match:
                            found_version = version_match.group(1)
                            if found_version != self.current_version:
                                test_versions.append(found_version)
        except Exception as e:
            self.log(f"Could not check git history: {e}")
            
        # Remove duplicates and current version
        test_versions = list(set(test_versions))
        test_versions = [v for v in test_versions if v != self.current_version]
        
        if not test_versions:
            # Fallback: just decrease patch version by 1
            if version_parts[2] > 0:
                version_parts[2] -= 1
                self.test_version = '.'.join(map(str, version_parts))
            else:
                raise ValueError("Cannot determine a test version to downgrade to")
        else:
            # Use the first viable test version
            self.test_version = test_versions[0]
            
        self.log(f"Will test with version: {self.test_version}")
        
    def find_real_previous_version(self):
        """Find an actual previous version by examining git history"""
        self.log("Searching git history for real previous versions...")
        
        try:
            # Get git log with more commits to search through
            result = subprocess.run(["git", "log", "--oneline", "-50"], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError("Cannot access git history")
                
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    commit_hash = line.split()[0]
                    commits.append(commit_hash)
                    
            self.log(f"Examining {len(commits)} recent commits...")
            
            # Check each commit's PKGBUILD for different versions
            for i, commit_hash in enumerate(commits):
                try:
                    # Get PKGBUILD content from this commit
                    result = subprocess.run(["git", "show", f"{commit_hash}:PKGBUILD"], 
                                          capture_output=True, text=True)
                    if result.returncode != 0:
                        continue
                        
                    pkgbuild_content = result.stdout
                    
                    # Parse version and commit from this historical PKGBUILD
                    historical_version = None
                    historical_commit = None
                    historical_pkgrel = None
                    
                    for line in pkgbuild_content.split('\n'):
                        if line.startswith("pkgver="):
                            historical_version = line.split('=', 1)[1].strip()
                        elif line.startswith("_commit="):
                            commit_part = line.split('=', 1)[1].strip()
                            historical_commit = commit_part.split()[0]
                        elif line.startswith("pkgrel="):
                            historical_pkgrel = line.split('=', 1)[1].strip()
                            
                    # Check if this is a different version than current
                    if (historical_version and historical_commit and 
                        historical_version != self.current_version):
                        
                        self.log(f"Found previous version in commit {commit_hash[:8]}: {historical_version}")
                        self.test_version = historical_version
                        self.test_commit = historical_commit
                        self.test_pkgrel = historical_pkgrel or "1"
                        
                        # Verify this version actually exists by checking if URL is accessible
                        test_url = f"https://downloads.cursor.com/production/{historical_commit}/linux/x64/deb/amd64/deb/cursor_{historical_version}_amd64.deb"
                        
                        self.log(f"Verifying URL exists: {test_url}")
                        try:
                            import requests
                            response = requests.head(test_url, timeout=10)
                            if response.status_code == 200:
                                self.log(f"✅ Verified: Version {historical_version} exists and is downloadable")
                                return True
                            else:
                                self.log(f"⚠️  Version {historical_version} URL returns {response.status_code}")
                        except Exception as e:
                            self.log(f"⚠️  Cannot verify {historical_version}: {e}")
                            
                        # Even if URL check fails, we can still use this for testing
                        # The workflow will handle the download failure gracefully
                        self.log(f"Using version {historical_version} anyway (workflow will handle any download issues)")
                        return True
                        
                except Exception as e:
                    self.log(f"Error checking commit {commit_hash[:8]}: {e}")
                    continue
                    
            # If we get here, no different version was found
            raise ValueError("No previous version found in git history")
            
        except Exception as e:
            self.log(f"Error searching git history: {e}")
            raise
        
    def backup_pkgbuild(self):
        """Backup the current PKGBUILD"""
        self.log("Backing up current PKGBUILD...")
        shutil.copy("PKGBUILD", self.backup_file)
        
        # Also read it into memory
        with open("PKGBUILD", "r") as f:
            self.original_pkgbuild = f.read()
        self.log("✅ PKGBUILD backed up")
        
    def restore_pkgbuild(self):
        """Restore the original PKGBUILD"""
        self.log("Restoring original PKGBUILD...")
        if os.path.exists(self.backup_file):
            shutil.copy(self.backup_file, "PKGBUILD")
            os.remove(self.backup_file)
            self.log("✅ PKGBUILD restored")
        else:
            self.log("❌ Backup file not found!", "ERROR")
            
    def get_test_checksum(self):
        """Verify test version exists and return placeholder checksum"""
        self.log(f"Verifying test version {self.test_version} is accessible...")
        
        # Try to get checksum for the test version
        test_url = f"https://downloads.cursor.com/production/{self.test_commit}/linux/x64/deb/amd64/deb/cursor_{self.test_version}_amd64.deb"
        
        try:
            self.log("Checking if test version URL is accessible (HEAD request)...")
            # Check if the URL exists (quick HEAD request, no download)
            response = requests.head(test_url, timeout=15)
            if response.status_code == 200:
                file_size = response.headers.get('content-length', 'unknown')
                if file_size != 'unknown':
                    file_size_mb = int(file_size) / (1024*1024)
                    self.log(f"✅ Test version URL exists: {file_size_mb:.1f} MB")
                else:
                    self.log(f"✅ Test version URL exists")
                self.log("Using placeholder checksum - workflow will download and recalculate")
                return "placeholder_checksum_will_be_recalculated_by_workflow"
            else:
                self.log(f"⚠️  Test version URL returned {response.status_code}")
                self.log("Using placeholder checksum anyway - workflow will handle download issues")
                return "placeholder_checksum_will_be_recalculated_by_workflow"
        except Exception as e:
            self.log(f"⚠️  Error checking test URL: {e}")
            self.log("Using placeholder checksum anyway - workflow will handle download issues")
            return "placeholder_checksum_will_be_recalculated_by_workflow"
            
    def create_test_pkgbuild(self):
        """Create a downgraded PKGBUILD to simulate being behind"""
        self.log(f"Creating test PKGBUILD (downgraded to {self.test_version})...")
        
        # Read current PKGBUILD
        with open("PKGBUILD", "r") as f:
            content = f.read()
        
        # Get test checksum
        test_checksum = self.get_test_checksum()
        
        # Replace version, pkgrel, commit, and checksum
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            if line.startswith("pkgver="):
                new_lines.append(f"pkgver={self.test_version}")
            elif line.startswith("pkgrel="):
                new_lines.append(f"pkgrel={self.test_pkgrel}")
            elif line.startswith("_commit="):
                new_lines.append(f"_commit={self.test_commit} # sed'ded at GitHub WF")
            elif line.startswith("source=("):
                # Update source URL to use test version
                new_lines.append(f'source=("https://downloads.cursor.com/production/${{_commit}}/linux/x64/deb/amd64/deb/cursor_${{pkgver}}_amd64.deb"')
            elif line.startswith("sha512sums=("):
                # Use placeholder checksum - workflow will recalculate
                new_lines.append(f"sha512sums=('{test_checksum}'")
            else:
                new_lines.append(line)
        
        # Write the test PKGBUILD
        with open("PKGBUILD", "w") as f:
            f.write('\n'.join(new_lines))
            
        self.log("✅ Test PKGBUILD created")
        
    def validate_current_state(self):
        """Validate that we're in a good state to run the test"""
        self.log("Validating current state...")
        
        # Check we're on development branch
        result = subprocess.run(["git", "branch", "--show-current"], 
                              capture_output=True, text=True)
        if result.returncode != 0 or result.stdout.strip() != "development":
            self.log("❌ Not on development branch!", "ERROR")
            return False
            
        # Check git status is clean
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            self.log("❌ Git working directory not clean!", "ERROR")
            return False
            
        # Check act is available
        result = subprocess.run(["act", "--version"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            self.log("❌ 'act' not available!", "ERROR")
            return False
            
        # Check docker is running
        result = subprocess.run(["docker", "info"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            self.log("❌ Docker not running!", "ERROR")
            return False
            
        self.log("✅ All validations passed")
        return True
        
    def run_workflow_test(self):
        """Run the workflow using act with real-time output"""
        self.log("Running workflow with act...")
        self.log("This will take a few minutes as it downloads Docker images and processes files...")
        self.log("DEBUG mode is active - git push will be skipped for safe testing")
        self.log("You'll see real-time output below - watch for download progress and any errors...")
        
        # Run act with workflow_dispatch event
        cmd = ["act", "workflow_dispatch", "--verbose"]
        
        self.log(f"Executing: {' '.join(cmd)}")
        self.log("=" * 60)
        
        try:
            # Run with real-time output instead of capturing
            result = subprocess.run(cmd, timeout=1800)  # 30 min timeout, show output live
            
            self.log("=" * 60)
            if result.returncode == 0:
                self.log("✅ Workflow completed successfully")
                return True
            else:
                self.log(f"❌ Workflow failed with exit code {result.returncode}", "ERROR")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("❌ Workflow timed out after 30 minutes", "ERROR")
            return False
        except KeyboardInterrupt:
            self.log("❌ Workflow interrupted by user", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ Error running workflow: {e}", "ERROR")
            return False
            
    def validate_results(self):
        """Validate that the workflow updated things correctly"""
        self.log("Validating workflow results...")
        
        # Check if PKGBUILD was updated back to current version
        with open("PKGBUILD", "r") as f:
            content = f.read()
            
        # Look for expected updates
        checks = []
        
        # Should be back to current version
        if f"pkgver={self.current_version}" in content:
            checks.append(f"✅ Version updated to {self.current_version}")
        else:
            checks.append(f"❌ Version not updated correctly (expected {self.current_version})")
            
        # Should have correct commit
        if self.current_commit in content:
            checks.append("✅ Commit hash updated")
        else:
            checks.append("❌ Commit hash not updated")
            
        # Should have native titlebar fix
        if "Fix native title bar" in content:
            checks.append("✅ Native titlebar fix present")
        else:
            checks.append("❌ Native titlebar fix missing")
            
        # Check git log for new commit (local commit should exist)
        result = subprocess.run(["git", "log", "--oneline", "-1"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            last_commit = result.stdout.strip()
            if self.current_version in last_commit:
                checks.append("✅ Git commit created (local)")
            else:
                # Check if it's our test commit - that's also valid
                if "test script" in last_commit.lower() or "workflow test" in last_commit.lower():
                    checks.append("✅ Git commit created (test-related)")
                else:
                    checks.append(f"❌ Unexpected git commit: {last_commit}")
        else:
            checks.append("❌ Could not check git log")
            
        # Print all checks
        for check in checks:
            self.log(check)
            
        # Return True if all checks passed
        return all("✅" in check for check in checks)
        
    def run_test(self):
        """Run the complete test"""
        self.log("🚀 Starting workflow test...")
        
        try:
            # Validate environment
            if not self.validate_current_state():
                return False
                
            # Parse current PKGBUILD and find real previous version
            self.parse_current_pkgbuild()
            self.find_real_previous_version()
                
            # Backup current state
            self.backup_pkgbuild()
            
            # Create test scenario
            self.create_test_pkgbuild()
            
            # Run the workflow
            if not self.run_workflow_test():
                self.log("❌ Workflow test failed", "ERROR")
                return False
                
            # Validate results
            if not self.validate_results():
                self.log("❌ Result validation failed", "ERROR")
                return False
                
            self.log("🎉 All tests passed!")
            return True
            
        except KeyboardInterrupt:
            self.log("❌ Test interrupted by user", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ Unexpected error: {e}", "ERROR")
            return False
        finally:
            # Always restore the original PKGBUILD
            self.restore_pkgbuild()
            
    def dry_run(self):
        """Show what the test would do without actually doing it"""
        self.log("🔍 DRY RUN - showing what would happen:")
        
        try:
            # Parse current state to show what we would do
            self.parse_current_pkgbuild()
            self.find_real_previous_version()
            
            self.log(f"1. Backup current PKGBUILD")
            self.log(f"2. Downgrade PKGBUILD: {self.current_version} → {self.test_version}")
            self.log(f"3. Reset pkgrel: {self.current_pkgrel} → {self.test_pkgrel}")
            self.log(f"4. Change commit: {self.current_commit} → {self.test_commit}")
            self.log(f"5. Run 'act workflow_dispatch --verbose'")
            self.log(f"6. Validate that PKGBUILD gets updated back to {self.current_version}")
            self.log(f"7. Check that git commit was created")
            self.log(f"8. Restore original PKGBUILD")
            self.log("Use --run to actually execute the test")
            
        except Exception as e:
            self.log(f"❌ Error during dry run analysis: {e}", "ERROR")
            self.log("This indicates the test might not work with current PKGBUILD state")

if __name__ == "__main__":
    tester = WorkflowTester()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        success = tester.run_test()
        sys.exit(0 if success else 1)
    else:
        tester.dry_run()
