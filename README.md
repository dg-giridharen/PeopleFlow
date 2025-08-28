# AI-Powered HR Assistant for Employee Lifecycle Automation

## Project Overview
This prototype demonstrates an AI-powered, self-service HR assistant designed to automate and streamline common employee lifecycle tasks using a conversational UI.

## Features
- **Conversational UI**: Chat-based interface for natural language HR requests
- **Workflow Automation**: Automated leave approval and asset issuance processes
- **Static Data Simulation**: JSON-based data storage simulating HRIS database

## Technology Stack
- **Backend**: Python Flask
- **Conversational AI**: Google Dialogflow
- **Development**: VS Code, Thunder Client, NGROK
- **Data Storage**: JSON files (employees.json, leave_balances.json, assets.json)

## Project Structure
```
datasprint/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── workflows/          # HR workflow implementations
│   │   ├── __init__.py
│   │   ├── leave_approval.py
│   │   └── asset_issuance.py
│   └── utils/              # Utility functions
│       ├── __init__.py
│       └── data_manager.py
├── data/
│   ├── employees.json      # Employee data
│   ├── leave_balances.json # Leave balance data
│   └── assets.json         # Company assets data
├── dialogflow/
│   └── intents/            # Dialogflow intent configurations
├── tests/
│   └── test_workflows.py   # Unit tests
├── requirements.txt        # Python dependencies
└── README.md
```

## Automated Workflows

### 1. Employee Leave Approval
- Collects leave request details (dates, type)
- Validates against available balance
- Approves and deducts from balance
- Provides confirmation with updated balance

### 2. New Hire Asset Issuance
- Collects new hire employee ID
- Determines required assets based on role
- Assigns available assets from inventory
- Confirms asset assignment details

## Setup Instructions
1. Install dependencies: `pip install -r requirements.txt`
2. Run Flask app: `python backend/app.py`
3. Use NGROK to expose local server for Dialogflow webhook
4. Configure Dialogflow intents and webhook URL

## Testing
- Use Thunder Client or Postman for API testing
- Test workflows with sample data
- Verify Dialogflow integration
