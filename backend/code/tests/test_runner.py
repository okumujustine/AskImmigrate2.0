#!/usr/bin/env python3
"""
AskImmigrate2.0 Test Runner
Author: Hillary Arinda
Purpose: Comprehensive test execution and reporting for production readiness

This script runs all test su        result = self.run_command([
            sys.executable, "-m", "coverage", "run",
            "--source", "backend/code",
            "-m", "pytest", "backend/code/tests/",
            "-v", "--tb=short"
        ])
        
        if result["success"]:
            # Generate HTML and JSON reports using .coveragerc configuration
            self.run_command([sys.executable, "-m", "coverage", "html"])
            self.run_command([sys.executable, "-m", "coverage", "json"])
            
            print("✅ Coverage report generated")
            print("   📄 HTML report: backend/code/tests/htmlcov/index.html")
            print(f"   📄 JSON report: backend/code/tests/coverage.json")rates reports for:
1. Manager Node Testing
2. Input Validation Testing
3. Retry Logic Testing
4. Integration Testing
5. Coverage Reports
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any

# Add backend code directory to path
backend_code_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_code_dir))

class ProductionTestRunner:
    """Comprehensive test runner for Hillary's responsibilities."""
    
    def __init__(self):
        # Project root is 3 levels up from tests directory
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.backend_code_dir = backend_code_dir
        self.tests_dir = Path(__file__).parent  # backend/code/tests directory
        self.test_results = {}
        self.start_time = time.time()
        
    def run_command(self, command: List[str], capture_output: bool = True) -> Dict[str, Any]:
        """Run a command and capture results."""
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                cwd=self.project_root  # Use actual project root for commands
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def install_test_dependencies(self) -> bool:
        """Install testing dependencies."""
        print("📦 Installing test dependencies...")
        
        result = self.run_command([
            sys.executable, "-m", "pip", "install", "-r", 
            str(self.project_root / "requirements-test.txt")
        ])
        
        if result["success"]:
            print("✅ Test dependencies installed successfully")
            return True
        else:
            print(f"❌ Failed to install dependencies: {result['stderr']}")
            return False
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests for Hillary's components."""
        print("\n🧪 Running Unit Tests...")
        print("=" * 50)
        
        test_files = [
            "backend/code/tests/test_manager_comprehensive.py",
            "backend/code/tests/test_input_validation.py", 
            "backend/code/tests/test_retry_logic.py"
        ]
        
        results = {}
        
        for test_file in test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                print(f"\n🔍 Running {test_file}...")
                
                result = self.run_command([
                    sys.executable, "-m", "pytest", 
                    str(test_path),
                    "-v", "--tb=short", "--no-header"
                ])
                
                results[test_file] = result
                
                if result["success"]:
                    print(f"✅ {test_file} - PASSED")
                else:
                    print(f"❌ {test_file} - FAILED")
                    print(f"   Error: {result['stderr'][:200]}...")
            else:
                print(f"⚠️  Test file not found: {test_file}")
                results[test_file] = {
                    "success": False,
                    "stdout": "",
                    "stderr": "File not found",
                    "returncode": -1
                }
        
        return results
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        print("\n🔗 Running Integration Tests...")
        print("=" * 50)
        
        # Run existing manager node test
        existing_test = self.project_root / "backend/code/tests/test_manager_node.py"
        
        results = {}
        
        if existing_test.exists():
            print(f"\n🔍 Running existing manager tests...")
            
            result = self.run_command([
                sys.executable, str(existing_test)
            ])
            
            results["existing_manager_test"] = result
            
            if result["success"]:
                print("✅ Existing manager tests - PASSED")
            else:
                print("❌ Existing manager tests - FAILED")
        
        return results
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security-focused tests."""
        print("\n🔒 Running Security Tests...")
        print("=" * 50)
        
        result = self.run_command([
            sys.executable, "-m", "pytest",
            "backend/code/tests/",
            "-v", "-m", "security",
            "--tb=short"
        ])
        
        if result["success"]:
            print("✅ Security tests - PASSED")
        else:
            print("❌ Security tests - FAILED")
            print(f"   Details: {result['stderr'][:200]}...")
        
        return {"security_tests": result}
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        print("\n⚡ Running Performance Tests...")
        print("=" * 50)
        
        result = self.run_command([
            sys.executable, "-m", "pytest",
            "backend/code/tests/",
            "-v", "-m", "performance",
            "--tb=short"
        ])
        
        if result["success"]:
            print("✅ Performance tests - PASSED")
        else:
            print("❌ Performance tests - FAILED")
            print(f"   Details: {result['stderr'][:200]}...")
        
        return {"performance_tests": result}
    
    def generate_coverage_report(self) -> Dict[str, Any]:
        """Generate code coverage report."""
        print("\n📊 Generating Coverage Report...")
        print("=" * 50)
        
        # Run tests with coverage using .coveragerc configuration
        result = self.run_command([
            sys.executable, "-m", "pytest",
            "backend/code/tests/",
            "--cov=backend/code",
            "--cov-report=term-missing"
        ])
        
        if result["success"]:
            # Generate HTML and JSON reports using .coveragerc paths
            self.run_command([sys.executable, "-m", "coverage", "html"])
            self.run_command([sys.executable, "-m", "coverage", "json"])
            
            print("✅ Coverage report generated")
            print("   📄 HTML report: backend/code/tests/htmlcov/index.html")
            print(f"   📄 JSON report: backend/code/tests/coverage.json")
            
            # Try to read coverage percentage
            try:
                coverage_file = self.tests_dir / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                    
                    total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                    print(f"   📈 Total Coverage: {total_coverage:.1f}%")
            except Exception as e:
                print(f"   ⚠️  Could not read coverage data: {e}")
        else:
            print("❌ Coverage report generation failed")
            print(f"   Error: {result['stderr'][:200]}...")
        
        return {"coverage": result}
    
    def run_linting(self) -> Dict[str, Any]:
        """Run code linting checks."""
        print("\n🧹 Running Code Quality Checks...")
        print("=" * 50)
        
        results = {}
        
        # Check if black is available
        black_result = self.run_command([
            sys.executable, "-m", "black", "--check", "--diff",
            "backend/code/input_validation.py",
            "backend/code/retry_logic.py",
            "backend/code/agent_nodes/enhanced_manager_node.py"
        ])
        
        results["formatting"] = black_result
        
        if black_result["success"]:
            print("✅ Code formatting - PASSED")
        else:
            print("⚠️  Code formatting issues found")
            print("   Run: python -m black backend/code/ to fix")
        
        return results
    
    def test_imports(self) -> Dict[str, Any]:
        """Test critical imports."""
        print("\n📥 Testing Critical Imports...")
        print("=" * 50)
        
        critical_imports = [
            "backend.code.input_validation",
            "backend.code.retry_logic",
            "backend.code.agent_nodes.enhanced_manager_node"
        ]
        
        results = {}
        
        for module in critical_imports:
            try:
                result = self.run_command([
                    sys.executable, "-c", f"import {module}; print('✅ {module}')"
                ])
                
                results[module] = result
                
                if result["success"]:
                    print(f"✅ {module}")
                else:
                    print(f"❌ {module} - Import failed")
                    print(f"   Error: {result['stderr']}")
                    
            except Exception as e:
                print(f"❌ {module} - Exception: {e}")
                results[module] = {
                    "success": False,
                    "stderr": str(e),
                    "returncode": -1
                }
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite."""
        print("🇺🇸" + "="*60 + "🇺🇸")
        print("   AskImmigrate2.0 - Hillary's Test Suite")
        print("   Production Readiness Testing")
        print("="*64)
        
        all_results = {}
        
        # Step 1: Install dependencies
        if not self.install_test_dependencies():
            print("❌ Cannot proceed without test dependencies")
            return {"error": "Dependencies installation failed"}
        
        # Step 2: Test imports
        all_results["imports"] = self.test_imports()
        
        # Step 3: Run unit tests
        all_results["unit_tests"] = self.run_unit_tests()
        
        # Step 4: Run integration tests
        all_results["integration_tests"] = self.run_integration_tests()
        
        # Step 5: Run security tests
        all_results["security_tests"] = self.run_security_tests()
        
        # Step 6: Run performance tests
        all_results["performance_tests"] = self.run_performance_tests()
        
        # Step 7: Generate coverage
        all_results["coverage"] = self.generate_coverage_report()
        
        # Step 8: Code quality
        all_results["code_quality"] = self.run_linting()
        
        return all_results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test execution summary."""
        print("\n📋 TEST EXECUTION SUMMARY")
        print("="*50)
        
        total_time = time.time() - self.start_time
        
        passed_categories = 0
        total_categories = 0
        
        for category, category_results in results.items():
            if category == "error":
                continue
                
            total_categories += 1
            category_passed = True
            
            if isinstance(category_results, dict):
                if "success" in category_results:
                    category_passed = category_results["success"]
                else:
                    # Check if all sub-tests passed
                    for test_name, test_result in category_results.items():
                        if isinstance(test_result, dict) and "success" in test_result:
                            if not test_result["success"]:
                                category_passed = False
                                break
            
            status = "✅ PASS" if category_passed else "❌ FAIL"
            print(f"{category:20} {status}")
            
            if category_passed:
                passed_categories += 1
        
        print(f"\nOverall: {passed_categories}/{total_categories} categories passed")
        print(f"Execution time: {total_time:.1f} seconds")
        
        if passed_categories == total_categories:
            print("\n🎉 All tests passed! Production readiness achieved.")
            print("✅ Hillary's action items successfully implemented:")
            print("   • Manager Node Testing - Complete")
            print("   • Input Validation & Sanitization - Complete")
            print("   • Tool Orchestration Logic - Complete")
            print("   • Retry Logic for LLM calls - Complete")
        else:
            print(f"\n⚠️  {total_categories - passed_categories} categories need attention")
            print("📝 Next steps:")
            print("   1. Review failed test outputs above")
            print("   2. Fix identified issues")
            print("   3. Re-run tests with: python test_runner.py")
    
    def save_results(self, results: Dict[str, Any]):
        """Save test results to file."""
        results_file = self.tests_dir / "test_results.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Test results saved to: {results_file}")
        except Exception as e:
            print(f"\n⚠️  Could not save results: {e}")

def main():
    """Main test execution."""
    runner = ProductionTestRunner()
    
    try:
        results = runner.run_all_tests()
        runner.print_summary(results)
        runner.save_results(results)
        
        # Exit with error code if tests failed
        if "error" in results:
            sys.exit(1)
        
        # Check if all critical tests passed
        critical_passed = True
        for category, category_results in results.items():
            if isinstance(category_results, dict):
                if "unit_tests" in category or "security" in category:
                    if not category_results.get("success", True):
                        critical_passed = False
                        break
        
        sys.exit(0 if critical_passed else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
