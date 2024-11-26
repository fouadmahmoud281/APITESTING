import urllib
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import json
import requests
from datetime import datetime
import logging
from prance import ResolvingParser
import logging
import requests
import json
import tempfile
import os
from faker import Faker
import random
import string
from itertools import combinations
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)




def analyze_endpoint_structure(endpoint):
    """
    Analyze the endpoint structure using OpenAPI documentation
    """
    logger.debug(f"Starting endpoint analysis for: {endpoint}")
    
    try:
        # Get the base URL
        base_url = '/'.join(endpoint.split('/')[:-2])
        openapi_url = f"{base_url}/openapi.json"
        
        logger.debug(f"Attempting to fetch OpenAPI doc from: {openapi_url}")
        
        # Fetch OpenAPI documentation
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'API-Tester/1.0'
        }
        
        response = requests.get(openapi_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            openapi_spec = response.json()
            
            # Extract relative path from endpoint
            relative_path = '/' + '/'.join(endpoint.split('/')[-2:])
            logger.debug(f"Looking for path: {relative_path}")
            
            if 'paths' in openapi_spec and relative_path in openapi_spec['paths']:
                path_info = openapi_spec['paths'][relative_path]
                
                # Get POST operation for signup
                if 'post' in path_info:
                    post_info = path_info['post']
                    
                    # Get schema reference
                    if ('requestBody' in post_info and 
                        'content' in post_info['requestBody'] and 
                        'application/json' in post_info['requestBody']['content'] and 
                        'schema' in post_info['requestBody']['content']['application/json']):
                        
                        schema_ref = post_info['requestBody']['content']['application/json']['schema'].get('$ref')
                        
                        if schema_ref:
                            # Extract schema name from reference
                            schema_name = schema_ref.split('/')[-1]
                            schema = openapi_spec['components']['schemas'][schema_name]
                            
                            if 'properties' in schema:
                                # Get required fields
                                required_fields = schema.get('required', [])
                                
                                # Process properties
                                processed_properties = {}
                                for field_name, field_info in schema['properties'].items():
                                    field_data = {
                                        "type": field_info.get('type', 'string'),
                                        "description": field_info.get('title', ''),
                                        "required": field_name in required_fields
                                    }
                                    
                                    # Handle format
                                    if 'format' in field_info:
                                        field_data['format'] = field_info['format']
                                    
                                    # Handle default value
                                    if 'default' in field_info:
                                        field_data['default'] = field_info['default']
                                    
                                    # Handle anyOf case
                                    if 'anyOf' in field_info:
                                        field_data['type'] = [t.get('type') for t in field_info['anyOf'] if 'type' in t]
                                        for type_info in field_info['anyOf']:
                                            if 'format' in type_info:
                                                field_data['format'] = type_info['format']
                                    
                                    # Add example
                                    if field_name.lower() == 'email':
                                        field_data['example'] = "user@gmail.com"
                                    elif 'password' in field_name.lower():
                                        field_data['example'] = "StrongPassword123!"
                                    elif field_data['type'] == 'string':
                                        field_data['example'] = f"Sample {field_name}"
                                    elif field_data['type'] == 'boolean':
                                        field_data['example'] = field_data.get('default', True)
                                    
                                    processed_properties[field_name] = field_data

                                return {
                                    "success": True,
                                    "sample_data": processed_properties,
                                    "structure": "object",
                                    "status_code": 200,
                                    "source": "openapi_doc",
                                    "endpoint_info": {
                                        "summary": post_info.get('summary', ''),
                                        "description": post_info.get('description', ''),
                                        "schema_name": schema_name,
                                        "responses": post_info.get('responses', {}),
                                        "tags": post_info.get('tags', [])
                                    }
                                }
            
            logger.debug("Endpoint or schema information not found in OpenAPI documentation")
            return {
                "success": False,
                "error": "Endpoint or schema information not found in documentation",
                "status_code": None
            }
            
        else:
            logger.error(f"Failed to fetch OpenAPI documentation. Status code: {response.status_code}")
            return {
                "success": False,
                "error": f"Failed to fetch OpenAPI documentation. Status code: {response.status_code}",
                "status_code": response.status_code
            }
            
    except Exception as e:
        logger.error(f"Error analyzing endpoint: {str(e)}")
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}",
            "status_code": None
        }

def get_default_request_body(requirements):
    """
    Create a default request body with valid values for all fields
    """
    default_body = {}
    
    # Add required fields with their default/example values
    for field, info in requirements.get('required_fields', {}).items():
        if 'example' in info:
            default_body[field] = info['example']
        elif info.get('format') == 'email':
            default_body[field] = "test@example.com"
        elif 'password' in field.lower():
            default_body[field] = "TestPassword123!"
        elif info['type'] == 'string':
            default_body[field] = f"Test{field}"
        elif info['type'] == 'boolean':
            default_body[field] = True
        elif info['type'] == 'integer':
            default_body[field] = 1
    
    # Add optional fields with their default values
    for field, info in requirements.get('optional_fields', {}).items():
        if 'default' in info:
            default_body[field] = info['default']
    
    return default_body

def select_fields_for_testing(requirements):
    """
    Display and select fields for testing
    """
    all_fields = {}
    
    # Combine required and optional fields
    if 'required_fields' in requirements:
        for field, info in requirements['required_fields'].items():
            all_fields[field] = {'info': info, 'required': True}
    
    if 'optional_fields' in requirements:
        for field, info in requirements['optional_fields'].items():
            all_fields[field] = {'info': info, 'required': False}
    
    # Display available fields
    print("\nAvailable fields for testing:")
    print("-----------------------------")
    for i, (field, info) in enumerate(all_fields.items(), 1):
        req_status = "Required" if info['required'] else "Optional"
        field_type = info['info']['type']
        print(f"{i}. {field} ({field_type}) - {req_status}")
    
    # Get user selection
    while True:
        print("\nSelect fields to test (comma-separated numbers, 'all' for all fields, or 'q' to quit):")
        selection = input("> ").strip().lower()
        
        if selection == 'q':
            return None
        elif selection == 'all':
            return list(all_fields.keys())
        else:
            try:
                selected_indices = [int(i.strip()) for i in selection.split(',')]
                field_names = list(all_fields.keys())
                selected_fields = [field_names[i-1] for i in selected_indices if 0 < i <= len(field_names)]
                if selected_fields:
                    return selected_fields
                print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas, 'all', or 'q'.")


def analyze_endpoint_requirements(endpoint):
    """
    Analyze endpoint requirements directly from OpenAPI spec
    """
    logger.debug("Starting endpoint requirements analysis")
    
    try:
        endpoint_analysis = analyze_endpoint_structure(endpoint)
        if not endpoint_analysis["success"]:
            return None

        # Extract the required fields and schema information
        sample_data = endpoint_analysis["sample_data"]
        endpoint_info = endpoint_analysis["endpoint_info"]
        
        # Build the requirements analysis
        requirements = {
            "endpoint_type": "users",  # For signup endpoint
            "required_fields": {},
            "optional_fields": {},
            "metadata": {
                "summary": endpoint_info["summary"],
                "description": endpoint_info["description"],
                "tags": endpoint_info["tags"]
            }
        }

        # Process fields
        for field_name, field_info in sample_data.items():
            field_data = {
                "type": field_info["type"],
                "description": field_info["description"],
                "required": field_info["required"]
            }
            
            # Add format if present
            if "format" in field_info:
                field_data["format"] = field_info["format"]
            
            # Add default if present
            if "default" in field_info:
                field_data["default"] = field_info["default"]
            
            # Add example
            if "example" in field_info:
                field_data["example"] = field_info["example"]
            
            # Add to appropriate category
            if field_info["required"]:
                requirements["required_fields"][field_name] = field_data
            else:
                requirements["optional_fields"][field_name] = field_data

        return requirements
        
    except Exception as e:
        logger.error(f"Error analyzing requirements: {str(e)}")
        return None

def generate_validation_rules(requirements, openai_api_key):
    """
    Generate validation rules based on the analyzed requirements
    """
    llm = ChatOpenAI(openai_api_key=openai_api_key, temperature=0.7, model_name="gpt-3.5-turbo")
    
    validation_template = """
You are a data validation expert. Based on the following API requirements and sample data:

{requirements}

Generate a comprehensive set of validation rules. Consider:
1. Data type validations
2. Format validations (especially for fields like email, phone, etc.)
3. Required field checks
4. Length/size restrictions based on sample data
5. Pattern matching for formatted strings
6. Nested object validations
7. Business logic validations
8. Common security considerations

Return the validation rules as a JSON object with the following structure:
{{
    "field_validations": {{
        "field_name": [
            {{
                "rule_type": "type of validation",
                "description": "description of the rule",
                "validation_criteria": "specific criteria to check",
                "example_pass": "example of valid data",
                "example_fail": "example of invalid data"
            }}
        ]
    }},
    "object_validations": {{
        "object_name": {{
            "rules": [
                {{
                    "rule_type": "type of validation",
                    "description": "description of the rule",
                    "validation_criteria": "specific criteria to check",
                    "example_pass": "example of valid data",
                    "example_fail": "example of invalid data"
                }}
            ]
        }}
    }}
}}
"""

    validation_prompt = PromptTemplate(
        input_variables=["requirements"],
        template=validation_template
    )
    
    validation_chain = validation_prompt | llm
    validation_message = validation_chain.invoke({
        "requirements": json.dumps(requirements, indent=2)
    })
    
    try:
        validation_rules = json.loads(validation_message.content)
        return validation_rules
    except json.JSONDecodeError as e:
        print(f"Error parsing validation rules: {e}")
        return None

def generate_test_cases(requirements, validation_rules, openai_api_key, selected_fields, default_body):
    """
    Generate test cases with realistic data variations using Faker and custom generators
    """
    faker = Faker()
    
    def generate_field_variations(field_name, field_info):
        """Generate various test values for a field based on its type and rules"""
        variations = []
        
        # Basic valid variations
        if 'type' in field_info:
            if field_info['type'] == 'string':
                if 'email' in field_name.lower():
                    variations.extend([
                        faker.email(),
                        faker.company_email(),
                        faker.free_email(),
                        f"{faker.user_name()}@{faker.domain_name()}",
                        # Invalid emails
                        "invalid.email",
                        "test@.com",
                        "@domain.com",
                        " @domain.com"
                    ])
                elif 'name' in field_name.lower():
                    variations.extend([
                        faker.first_name(),
                        faker.last_name(),
                        faker.name(),
                        # Edge cases
                        "A",  # Single character
                        "x" * 50,  # Very long name
                        "123",  # Numbers
                        "$pecial Ch@racters",
                        ""  # Empty string
                    ])
                elif 'password' in field_name.lower():
                    variations.extend([
                        # Valid passwords
                        faker.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True),
                        "P@ssw0rd123!",
                        "Str0ng!P@ss",
                        # Invalid passwords
                        "weak",
                        "12345678",
                        "password",
                        ""
                    ])
                elif 'phone' in field_name.lower():
                    variations.extend([
                        faker.phone_number(),
                        faker.msisdn(),
                        "+1234567890",
                        # Invalid formats
                        "123",
                        "abcdefghij",
                        ""
                    ])
            elif field_info['type'] == 'integer':
                variations.extend([
                    random.randint(1, 100),
                    0,
                    -1,
                    999999,
                    "not_a_number",
                    ""
                ])
            elif field_info['type'] == 'boolean':
                variations.extend([True, False, None, "true", "false", 0, 1])

        return variations

    def generate_combination_test_cases(selected_fields, field_variations):
        """Generate test cases with different combinations of field values"""
        test_cases = []
        
        # Generate single field variations
        for field in selected_fields:
            variations = field_variations[field]
            for value in variations:
                test_case = {
                    "name": f"Test {field} with value: {str(value)}",
                    "method": "POST",
                    "data": default_body.copy(),
                    "expected_status_code": 200 if value != "" else 400,
                    "expected_behavior": f"Testing {field} with specific value"
                }
                test_case["data"][field] = value
                test_cases.append(test_case)

        # Generate combinations of fields (2 and 3 fields at a time)
        for r in range(2, min(4, len(selected_fields) + 1)):
            for fields_combo in combinations(selected_fields, r):
                # Create a few random combinations
                for _ in range(3):
                    test_case = {
                        "name": f"Test combination of {', '.join(fields_combo)}",
                        "method": "POST",
                        "data": default_body.copy(),
                        "expected_status_code": 200,
                        "expected_behavior": "Testing multiple field combinations"
                    }
                    
                    for field in fields_combo:
                        test_case["data"][field] = random.choice(field_variations[field])
                    
                    test_cases.append(test_case)

        return test_cases

    # Enhanced prompt for GPT to understand field relationships and constraints
    test_cases_template = """
    You are a senior QA engineer specialized in API testing. Analyze these fields and their relationships:

    Requirements:
    {requirements}

    Validation Rules:
    {validation_rules}

    Selected Fields:
    {selected_fields}

    Default Body:
    {default_body}

    Provide additional test scenarios considering:
    1. Business logic relationships between fields
    2. Field dependencies and constraints
    3. Security considerations
    4. Edge cases and boundary conditions
    5. Common user behavior patterns
    6. Potential security vulnerabilities

    Return an array of additional test scenarios in this format:
    [
        {{
            "name": "Descriptive test name",
            "method": "POST",
            "data": {{ field values }},
            "expected_status_code": code,
            "expected_behavior": "Detailed expected behavior"
        }}
    ]
    Focus on realistic user scenarios and security implications.
    """

    try:
        # Generate field variations
        field_variations = {}
        for field in selected_fields:
            field_info = {}
            if field in requirements.get('required_fields', {}):
                field_info = requirements['required_fields'][field]
            elif field in requirements.get('optional_fields', {}):
                field_info = requirements['optional_fields'][field]
            
            field_variations[field] = generate_field_variations(field, field_info)

        # Generate automated test cases
        automated_test_cases = generate_combination_test_cases(selected_fields, field_variations)

        # Get additional test cases from GPT
        llm = ChatOpenAI(openai_api_key=openai_api_key, temperature=0.7, model_name="gpt-3.5-turbo")
        test_cases_prompt = PromptTemplate(
            input_variables=["requirements", "validation_rules", "selected_fields", "default_body"],
            template=test_cases_template
        )
        
        test_cases_chain = test_cases_prompt | llm
        gpt_response = test_cases_chain.invoke({
            "requirements": json.dumps(requirements, indent=2),
            "validation_rules": json.dumps(validation_rules, indent=2),
            "selected_fields": json.dumps(selected_fields, indent=2),
            "default_body": json.dumps(default_body, indent=2)
        })
        
        gpt_test_cases = json.loads(gpt_response.content)

        # Combine and deduplicate test cases
        all_test_cases = automated_test_cases + gpt_test_cases
        
        # Ensure complete request bodies
        for case in all_test_cases:
            complete_body = default_body.copy()
            if 'data' in case:
                for field in selected_fields:
                    if field in case['data']:
                        complete_body[field] = case['data'][field]
            case['data'] = complete_body

        return all_test_cases

    except Exception as e:
        print(f"Error generating test cases: {e}")
        return None

def execute_test_cases(endpoint, test_cases):
    """
    Execute the generated test cases against the endpoint
    """
    results = []
    
    for case in test_cases:
        try:
            method = case["method"].lower()
            data = case["data"]
            headers = {'Content-Type': 'application/json'}

            if method == "get":
                if "id" in data:
                    specific_endpoint = f"{endpoint}/{data['id']}"
                    response = requests.get(specific_endpoint)
                else:
                    response = requests.get(endpoint, params=data)
            elif method == "post":
                response = requests.post(endpoint, json=data, headers=headers)
            elif method == "put":
                if "id" in data:
                    specific_endpoint = f"{endpoint}/{data['id']}"
                    response = requests.put(specific_endpoint, json=data, headers=headers)
                else:
                    response = requests.put(endpoint, json=data, headers=headers)
            elif method == "delete":
                if "id" in data:
                    specific_endpoint = f"{endpoint}/{data['id']}"
                    response = requests.delete(specific_endpoint)
                else:
                    response = requests.delete(endpoint)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Record response details
            case["actual_status_code"] = response.status_code
            try:
                case["actual_response"] = response.json()
            except json.JSONDecodeError:
                case["actual_response"] = response.text
            
            # Add test result
            case["test_result"] = {
                "passed": case["expected_status_code"] == response.status_code,
                "status_code_match": case["expected_status_code"] == response.status_code,
                "timestamp": datetime.now().isoformat(),
                "notes": f"Expected {case['expected_status_code']}, got {response.status_code}"
            }
            
            results.append(case)

        except Exception as e:
            case["actual_status_code"] = "Error"
            case["actual_response"] = str(e)
            case["test_result"] = {
                "passed": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            results.append(case)

    return results

def generate_test_report(results):
    """
    Generate a summary report of the test execution
    """
    total_tests = len(results)
    passed_tests = sum(1 for test in results if test.get("test_result", {}).get("passed", False))
    failed_tests = total_tests - passed_tests

    report = {
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.2f}%" if total_tests > 0 else "0%"
        },
        "timestamp": datetime.now().isoformat(),
        "test_results": results,
        "failed_tests_summary": [
            {
                "name": test["name"],
                "expected_status": test["expected_status_code"],
                "actual_status": test["actual_status_code"],
                "error": test.get("test_result", {}).get("error", "No error message")
            }
            for test in results if not test.get("test_result", {}).get("passed", False)
        ]
    }
    return report

def run_complete_test_suite(endpoint, openai_api_key):
    """
    Run the complete test suite including analysis, validation, and test execution
    """
    print(f"\n🚀 Starting API Test Suite for: {endpoint}")
    
    # Step 1: Analyze endpoint requirements
    print("\n1️⃣ Analyzing endpoint requirements...")
    requirements = analyze_endpoint_requirements(endpoint)
    if not requirements:
        return "Failed to analyze endpoint requirements"
    print("✅ Requirements analysis complete")
    
    # Step 1.5: Select fields for testing
    selected_fields = select_fields_for_testing(requirements)
    if not selected_fields:
        return "No fields selected for testing"
    
    # Get default request body
    default_body = get_default_request_body(requirements)
    print("\n📋 Default request body:")
    print(json.dumps(default_body, indent=2))
    
    # Step 2: Generate validation rules
    print("\n2️⃣ Generating validation rules...")
    validation_rules = generate_validation_rules(requirements, openai_api_key)
    if not validation_rules:
        return "Failed to generate validation rules"
    print("✅ Validation rules generated")
    
    # Step 3: Generate test cases
    print("\n3️⃣ Generating test cases...")
    test_cases = generate_test_cases(requirements, validation_rules, openai_api_key, selected_fields, default_body)
    if not test_cases:
        return "Failed to generate test cases"
    print(f"✅ Generated {len(test_cases)} test cases")
    
    # Step 4: Execute test cases
    print("\n4️⃣ Executing test cases...")
    test_results = execute_test_cases(endpoint, test_cases)
    print("✅ Test execution complete")
    
    # Step 5: Generate report
    print("\n5️⃣ Generating test report...")
    final_report = generate_test_report(test_results)
    print("✅ Test report generated")
    
    return {
        "selected_fields": selected_fields,
        "default_body": default_body,
        "requirements_analysis": requirements,
        "validation_rules": validation_rules,
        "test_report": final_report
    }

# Example usage
if __name__ == "__main__":
    endpoint = "https://heart-dev-api.obelion.ai/api/signup"
    openai_api_key = "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"
    
    results = run_complete_test_suite(endpoint, openai_api_key)
    
    # Save results to a file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"api_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📝 Complete test results saved to: {filename}")
    
    # Print summary
    if "test_report" in results:
        summary = results["test_report"]["summary"]
        print("\n📊 Test Summary:")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']}")