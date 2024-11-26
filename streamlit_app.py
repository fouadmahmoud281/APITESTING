# streamlit_app.py
import streamlit as st
import json
from datetime import datetime
import logging
import urllib
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import requests
from prance import ResolvingParser
import tempfile
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from main import analyze_endpoint_requirements, get_default_request_body, run_complete_test_suite, generate_test_report, generate_validation_rules, generate_test_cases, execute_test_cases




# Add this helper function for validation rules display
def display_validation_rules(validation_rules):
    st.markdown("""
        <style>
        .field-header {
            background-color: #f8f9fa;
            padding: 15px 20px;
            border-radius: 10px 10px 0 0;
            border-bottom: 3px solid #3498db;
            margin-bottom: 0;
        }
        
        .field-name {
            font-size: 1.4em;
            color: #2c3e50;
            font-weight: 600;
            margin: 0;
        }
        
        .validation-container {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 25px;
            border: 1px solid #e0e0e0;
        }
        
        .rule-container {
            padding: 20px;
            border-bottom: 1px solid #eee;
        }
        
        .rule-container:last-child {
            border-bottom: none;
        }
        
        .rule-type-badge {
            display: inline-block;
            background-color: #e8f4f8;
            color: #2980b9;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.9em;
            margin-bottom: 10px;
            font-weight: 500;
        }
        
        .rule-description {
            color: #2c3e50;
            margin: 10px 0;
            font-size: 1.1em;
        }
        
        .criteria-box {
            background-color: #f7f9fc;
            padding: 10px 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            font-family: monospace;
            margin: 10px 0;
        }
        
        .examples-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        
        .example-box {
            padding: 12px;
            border-radius: 8px;
            position: relative;
        }
        
        .example-valid {
            background-color: #e8f8f5;
            border: 1px solid #27ae60;
        }
        
        .example-invalid {
            background-color: #fdf2f2;
            border: 1px solid #e74c3c;
        }
        
        .example-label {
            position: absolute;
            top: -10px;
            left: 10px;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 500;
        }
        
        .valid-label {
            background-color: #27ae60;
            color: white;
        }
        
        .invalid-label {
            background-color: #e74c3c;
            color: white;
        }
        
        .example-content {
            margin-top: 8px;
            font-family: monospace;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 🔍 Validation Rules")

    if 'field_validations' in validation_rules:
        for field_name, rules in validation_rules['field_validations'].items():
            st.markdown(f"""
                <div class="validation-container">
                    <div class="field-header">
                        <h3 class="field-name">{field_name}</h3>
                    </div>
            """, unsafe_allow_html=True)
            
            for rule in rules:
                st.markdown(f"""
                    <div class="rule-container">
                        <div class="rule-type-badge">
                            {rule['rule_type']}
                        </div>
                        <div class="rule-description">
                            {rule['description']}
                        </div>
                        <div class="criteria-box">
                            <strong>Validation Criteria:</strong> {rule['validation_criteria']}
                        </div>
                        <div class="examples-grid">
                            <div class="example-box example-valid">
                                <span class="example-label valid-label">VALID</span>
                                <div class="example-content">
                                    ✅ {rule['example_pass']}
                                </div>
                            </div>
                            <div class="example-box example-invalid">
                                <span class="example-label invalid-label">INVALID</span>
                                <div class="example-content">
                                    ❌ {rule['example_fail']}
                                </div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

    if 'object_validations' in validation_rules:
        st.markdown("### 📦 Object-Level Validations")
        for object_name, validation_info in validation_rules['object_validations'].items():
            with st.expander(f"Object: {object_name}"):
                for rule in validation_info['rules']:
                    st.markdown(f"""
                        <div class="validation-container">
                            <div class="rule-container">
                                <div class="rule-type-badge">
                                    {rule['rule_type']}
                                </div>
                                <div class="rule-description">
                                    {rule['description']}
                                </div>
                                <div class="criteria-box">
                                    <strong>Validation Criteria:</strong> {rule['validation_criteria']}
                                </div>
                                <div class="examples-grid">
                                    <div class="example-box example-valid">
                                        <span class="example-label valid-label">VALID</span>
                                        <div class="example-content">
                                            ✅ {rule['example_pass']}
                                        </div>
                                    </div>
                                    <div class="example-box example-invalid">
                                        <span class="example-label invalid-label">INVALID</span>
                                        <div class="example-content">
                                            ❌ {rule['example_fail']}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

# Helper function to display test case results
def display_test_case_results(test_case):
    """Display a single test case result in a formatted way"""
    st.markdown(f"### {test_case['name']}")
    
    # Create columns for test details
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Method:** `{test_case['method']}`")
        st.markdown(f"**Expected Status:** `{test_case['expected_status_code']}`")
        st.markdown(f"**Actual Status:** `{test_case['actual_status_code']}`")
    
    with col2:
        status = "✅ PASSED" if test_case['test_result']['passed'] else "❌ FAILED"
        st.markdown(f"**Status:** {status}")
        st.markdown(f"**Expected Behavior:** {test_case.get('expected_behavior', 'N/A')}")

    # Show request and response data in expandable sections
    col3, col4 = st.columns(2)
    with col3:
        with st.expander("Request Data"):
            st.json(test_case["data"])
    
    with col4:
        with st.expander("Response Data"):
            st.json(test_case.get("actual_response", {}))
    
    st.markdown("---")

# Helper function to display requirements analysis
def display_requirements_analysis(requirements):
    st.markdown("""
        <style>
        .requirement-card {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            border-left: 5px solid #1f77b4;
        }
        .required-field {
            border-left-color: #ff4b4b !important;
        }
        .optional-field {
            border-left-color: #00cc96 !important;
        }
        .field-type {
            background-color: #e9ecef;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
        }
        .field-example {
            background-color: #e9ecef;
            padding: 8px;
            border-radius: 4px;
            font-family: monospace;
            margin-top: 5px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Display endpoint information
    st.markdown("### 📡 Endpoint Information")
    st.markdown(f"**Type:** `{requirements.get('endpoint_type', 'Not specified')}`")
    
    # Required Fields Section
    st.markdown("### 🔒 Required Fields")
    if 'required_fields' in requirements:
        for field_name, field_info in requirements['required_fields'].items():
            st.markdown(f"""
                <div class="requirement-card required-field">
                    <h4>{field_name}</h4>
                    <p><span class="field-type">{field_info['type']}</span></p>
                    <p>{field_info.get('description', 'No description available')}</p>
                    <div class="field-example">
                        Example: {field_info.get('example', 'No example available')}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No required fields specified")

    # Optional Fields Section
    st.markdown("### 📎 Optional Fields")
    if 'optional_fields' in requirements:
        for field_name, field_info in requirements['optional_fields'].items():
            st.markdown(f"""
                <div class="requirement-card optional-field">
                    <h4>{field_name}</h4>
                    <p><span class="field-type">{field_info['type']}</span></p>
                    <p>{field_info.get('description', 'No description available')}</p>
                    <div class="field-example">
                        Example: {field_info.get('example', 'No example available')}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No optional fields specified")

    # Metadata Section if available
    if 'metadata' in requirements:
        st.markdown("### ℹ️ Additional Information")
        with st.expander("View Metadata"):
            if 'summary' in requirements['metadata']:
                st.markdown(f"**Summary:** {requirements['metadata']['summary']}")
            if 'description' in requirements['metadata']:
                st.markdown(f"**Description:** {requirements['metadata']['description']}")
            if 'tags' in requirements['metadata']:
                st.markdown("**Tags:**")
                for tag in requirements['metadata']['tags']:
                    st.markdown(f"- {tag}")

# Custom CSS for better styling
def load_custom_css():
    st.markdown("""
        <style>
        .stMetric .metric-label {
            font-size: 1.2rem !important;
        }
        .stMetric .metric-value {
            font-size: 2rem !important;
            font-weight: bold !important;
        }
        .json-container {
            background-color: #f0f2f6;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
        }
        .status-passed {
            color: #00c853;
            font-weight: bold;
        }
        .status-failed {
            color: #ff1744;
            font-weight: bold;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #f8f9fa;
            border-radius: 4px;
            color: #0e1117;
            font-size: 14px;
            font-weight: 500;
            padding: 8px 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1f77b4 !important;
            color: white !important;
        }
        h4 {
            color: #1f77b4;
            margin-bottom: 8px;
        }
        .field-metadata {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .requirement-card:hover {
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transform: translateY(-2px);
            transition: all 0.2s ease;
        }
        .field-description {
            margin: 8px 0;
        }
        </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'requirements' not in st.session_state:
    st.session_state.requirements = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'selected_fields' not in st.session_state:
    st.session_state.selected_fields = []

def main():
    load_custom_css()
    st.title("API Testing Suite - Obelion.Ai")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    endpoint = st.sidebar.text_input(
        "API Endpoint",
        value="https://heart-dev-api.obelion.ai/api/signup",
        help="Enter the API endpoint URL"
    )
    
    openai_api_key = st.sidebar.text_input(
        "OpenAI API Key",
        type="password",
        help="Enter your OpenAI API key"
    )

    # Initialize session state for tabs
    if 'validation_rules' not in st.session_state:
        st.session_state.validation_rules = None
    if 'test_results' not in st.session_state:
        st.session_state.test_results = None

    # Create three main tabs
    tab1, tab2, tab3 = st.tabs(["Requirements Analysis", "Field Selection & Validation", "Test Results"])

    with tab1:
        st.header("API Requirements Analysis")
        if not st.session_state.analysis_complete:
            if st.button("Start Analysis"):
                if not endpoint or not openai_api_key:
                    st.error("Please provide both the API endpoint and OpenAI API key")
                else:
                    try:
                        with st.spinner("Analyzing endpoint requirements..."):
                            st.session_state.requirements = analyze_endpoint_requirements(endpoint)
                            if st.session_state.requirements:
                                st.session_state.analysis_complete = True
                                st.success("✅ Requirements analysis complete")
                                st.experimental_rerun()
                            else:
                                st.error("Failed to analyze endpoint requirements")
                    except Exception as e:
                        st.error(f"An error occurred during analysis: {str(e)}")

        if st.session_state.analysis_complete:
            display_requirements_analysis(st.session_state.requirements)

    with tab2:
        if st.session_state.analysis_complete:
            st.header("Field Selection & Validation Rules")
            # Display available fields
            available_fields = []
            if 'required_fields' in st.session_state.requirements:
                for field in st.session_state.requirements['required_fields'].keys():
                    available_fields.append((field, "Required"))
            if 'optional_fields' in st.session_state.requirements:
                for field in st.session_state.requirements['optional_fields'].keys():
                    available_fields.append((field, "Optional"))

            # Field selection
            selected_fields = st.multiselect(
                "Select fields to test",
                options=[field[0] for field in available_fields],
                default=[field[0] for field in available_fields if field[1] == "Required"],
                key="field_selector"
            )

            if selected_fields:
                st.session_state.selected_fields = selected_fields
                
                # Get default request body
                default_body = get_default_request_body(st.session_state.requirements)
                
                with st.expander("View Default Request Body", expanded=False):
                    st.json(default_body)

                # Generate and Run Tests button
                if st.button("Generate Validation Rules and Run Tests"):
                    try:
                        # Generate validation rules with improved display
                        with st.spinner("Generating validation rules..."):
                            st.session_state.validation_rules = generate_validation_rules(
                                st.session_state.requirements, 
                                openai_api_key
                            )
                            if st.session_state.validation_rules:
                                st.success("✅ Validation rules generated")
                                display_validation_rules(st.session_state.validation_rules)

                                # Generate and execute test cases
                                with st.spinner("Generating and executing test cases..."):
                                    test_cases = generate_test_cases(
                                        st.session_state.requirements,
                                        st.session_state.validation_rules,
                                        openai_api_key,
                                        st.session_state.selected_fields,
                                        default_body
                                    )
                                    if test_cases:
                                        test_results = execute_test_cases(endpoint, test_cases)
                                        st.session_state.test_results = generate_test_report(test_results)
                                        st.success("✅ Test cases executed successfully")
                                    else:
                                        st.error("Failed to generate test cases")
                            else:
                                st.error("Failed to generate validation rules")

                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please select at least one field to test")
        else:
            st.info("Please complete the requirements analysis first (Tab 1)")

    with tab3:
        if st.session_state.test_results:
            st.header("Test Results")
            summary = st.session_state.test_results["summary"]
            
            # Create metrics with custom styling
            metrics_container = st.container()
            with metrics_container:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Tests", summary["total_tests"])
                col2.metric("Passed Tests", summary["passed_tests"], 
                         delta=f"+{summary['passed_tests']}")
                col3.metric("Failed Tests", summary["failed_tests"], 
                         delta=f"-{summary['failed_tests']}", 
                         delta_color="inverse")
                col4.metric("Success Rate", summary["success_rate"])

            # Create tabs for results display
            results_tab1, results_tab2 = st.tabs(["Test Cases", "Raw JSON"])
            
            with results_tab1:
                for test_case in st.session_state.test_results["test_results"]:
                    display_test_case_results(test_case)
            
            with results_tab2:
                st.json(st.session_state.test_results)

            # Save and download results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"api_test_results_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(st.session_state.test_results, f, indent=2)
            
            with open(filename, 'r') as f:
                st.download_button(
                    label="📥 Download Test Results",
                    data=f.read(),
                    file_name=filename,
                    mime="application/json",
                    key="download-results"
                )
        else:
            st.info("No test results available yet. Please run tests in Tab 2.")

    # Reset button
    if st.session_state.analysis_complete:
        if st.sidebar.button("Reset Analysis"):
            st.session_state.analysis_complete = False
            st.session_state.requirements = None
            st.session_state.selected_fields = []
            st.session_state.validation_rules = None
            st.session_state.test_results = None
            st.experimental_rerun()

if __name__ == "__main__":
    main()
