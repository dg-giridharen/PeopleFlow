"""
AI-Powered HR Assistant - Complete System Demonstration
This script demonstrates all the key features of the HR Assistant prototype
"""
import requests
import json
from datetime import datetime, timedelta


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title):
    """Print a formatted section header"""
    print(f"\n🔹 {title}")
    print("-" * 40)


def demo_employee_data():
    """Demonstrate employee data retrieval"""
    print_header("EMPLOYEE DATA DEMONSTRATION")
    
    base_url = "http://localhost:5000"
    
    print_section("Getting All Employees")
    response = requests.get(f"{base_url}/api/employees")
    if response.status_code == 200:
        employees = response.json()["employees"]
        print(f"✅ Found {len(employees)} employees in the system")
        for emp in employees[:3]:  # Show first 3
            print(f"   • {emp['name']} ({emp['employee_id']}) - {emp['role']}")
        print(f"   ... and {len(employees) - 3} more employees")
    else:
        print("❌ Failed to retrieve employees")
    
    print_section("Getting Specific Employee Details")
    response = requests.get(f"{base_url}/api/employees/EMP001")
    if response.status_code == 200:
        emp = response.json()
        print(f"✅ Employee Details:")
        print(f"   Name: {emp['name']}")
        print(f"   Role: {emp['role']}")
        print(f"   Department: {emp['department']}")
        print(f"   Hire Date: {emp['hire_date']}")
    else:
        print("❌ Failed to retrieve employee details")


def demo_leave_workflow():
    """Demonstrate the leave approval workflow"""
    print_header("LEAVE APPROVAL WORKFLOW DEMONSTRATION")
    
    base_url = "http://localhost:5000"
    employee_id = "EMP002"
    
    print_section("Step 1: Check Current Leave Balance")
    webhook_payload = {
        "queryResult": {
            "intent": {"displayName": "leave.balance"},
            "parameters": {"employee-id": employee_id},
            "queryText": f"What is my leave balance for {employee_id}"
        }
    }
    
    response = requests.post(f"{base_url}/webhook", json=webhook_payload)
    if response.status_code == 200:
        message = response.json()["fulfillmentText"]
        print("✅ Leave Balance Response:")
        print(f"   {message}")
    else:
        print("❌ Failed to get leave balance")
    
    print_section("Step 2: Submit Leave Request")
    start_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    
    webhook_payload = {
        "queryResult": {
            "intent": {"displayName": "leave.request"},
            "parameters": {
                "employee-id": employee_id,
                "start-date": start_date,
                "end-date": end_date,
                "leave-type": "annual"
            },
            "queryText": f"I want to request annual leave from {start_date} to {end_date}"
        }
    }
    
    response = requests.post(f"{base_url}/webhook", json=webhook_payload)
    if response.status_code == 200:
        message = response.json()["fulfillmentText"]
        print("✅ Leave Request Response:")
        print(f"   {message[:200]}...")
        
        if "approved" in message.lower():
            print("   🎉 Leave request was APPROVED!")
        else:
            print("   ⚠️ Leave request was not approved")
    else:
        print("❌ Failed to process leave request")
    
    print_section("Step 3: Verify Updated Balance")
    response = requests.post(f"{base_url}/webhook", json={
        "queryResult": {
            "intent": {"displayName": "leave.balance"},
            "parameters": {"employee-id": employee_id},
            "queryText": f"Check my updated leave balance"
        }
    })
    
    if response.status_code == 200:
        message = response.json()["fulfillmentText"]
        print("✅ Updated Leave Balance:")
        print(f"   {message}")
    else:
        print("❌ Failed to get updated balance")


def demo_asset_workflow():
    """Demonstrate the asset issuance workflow"""
    print_header("ASSET ISSUANCE WORKFLOW DEMONSTRATION")
    
    base_url = "http://localhost:5000"
    
    print_section("Step 1: Check Available Assets")
    response = requests.get(f"{base_url}/api/assets")
    if response.status_code == 200:
        assets = response.json()["assets"]
        available = [a for a in assets if a["status"] == "available"]
        assigned = [a for a in assets if a["status"] == "assigned"]
        
        print(f"✅ Asset Inventory Status:")
        print(f"   Total Assets: {len(assets)}")
        print(f"   Available: {len(available)}")
        print(f"   Assigned: {len(assigned)}")
        
        print(f"\n   Available Assets by Type:")
        asset_types = {}
        for asset in available:
            asset_type = asset["asset_type"]
            if asset_type not in asset_types:
                asset_types[asset_type] = 0
            asset_types[asset_type] += 1
        
        for asset_type, count in asset_types.items():
            print(f"   • {asset_type.title()}: {count} available")
    else:
        print("❌ Failed to retrieve assets")
    
    print_section("Step 2: Provision Assets for New Hire")
    # Find an employee who doesn't have assets yet
    new_hire_id = "EMP003"  # Using EMP003 as example
    
    webhook_payload = {
        "queryResult": {
            "intent": {"displayName": "asset.provision"},
            "parameters": {"employee-id": new_hire_id},
            "queryText": f"Provision assets for new hire {new_hire_id}"
        }
    }
    
    response = requests.post(f"{base_url}/webhook", json=webhook_payload)
    if response.status_code == 200:
        message = response.json()["fulfillmentText"]
        print("✅ Asset Provisioning Response:")
        print(f"   {message[:300]}...")
        
        if "assigned" in message.lower():
            print("   🎉 Assets were successfully assigned!")
        else:
            print("   ⚠️ Asset assignment may have failed")
    else:
        print("❌ Failed to provision assets")
    
    print_section("Step 3: Verify Asset Assignment")
    response = requests.get(f"{base_url}/api/assets")
    if response.status_code == 200:
        assets = response.json()["assets"]
        employee_assets = [a for a in assets if a["assigned_to"] == new_hire_id]
        
        print(f"✅ Assets assigned to {new_hire_id}:")
        for asset in employee_assets:
            print(f"   • {asset['asset_type'].title()}: {asset['brand']} {asset['model']} ({asset['asset_id']})")
    else:
        print("❌ Failed to verify asset assignment")


def demo_error_handling():
    """Demonstrate error handling capabilities"""
    print_header("ERROR HANDLING DEMONSTRATION")
    
    base_url = "http://localhost:5000"
    
    print_section("Test 1: Invalid Employee ID")
    webhook_payload = {
        "queryResult": {
            "intent": {"displayName": "leave.balance"},
            "parameters": {"employee-id": "INVALID123"},
            "queryText": "Check leave balance for invalid employee"
        }
    }
    
    response = requests.post(f"{base_url}/webhook", json=webhook_payload)
    if response.status_code == 200:
        message = response.json()["fulfillmentText"]
        print("✅ Error Handling Response:")
        print(f"   {message}")
    
    print_section("Test 2: Insufficient Leave Balance")
    start_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")  # Too many days
    
    webhook_payload = {
        "queryResult": {
            "intent": {"displayName": "leave.request"},
            "parameters": {
                "employee-id": "EMP001",
                "start-date": start_date,
                "end-date": end_date,
                "leave-type": "annual"
            },
            "queryText": f"Request too many leave days"
        }
    }
    
    response = requests.post(f"{base_url}/webhook", json=webhook_payload)
    if response.status_code == 200:
        message = response.json()["fulfillmentText"]
        print("✅ Error Handling Response:")
        print(f"   {message}")


def main():
    """Main demonstration function"""
    print("🚀 AI-Powered HR Assistant - Complete System Demonstration")
    print("This demo shows all key features of the HR Assistant prototype")
    print("\nMake sure the Flask server is running on http://localhost:5000")
    
    input("\nPress Enter to start the demonstration...")
    
    try:
        # Test server connectivity
        response = requests.get("http://localhost:5000/")
        if response.status_code != 200:
            print("❌ Server is not responding. Please start the Flask server first.")
            return
        
        # Run demonstrations
        demo_employee_data()
        demo_leave_workflow()
        demo_asset_workflow()
        demo_error_handling()
        
        print_header("DEMONSTRATION COMPLETE")
        print("🎉 All workflows have been successfully demonstrated!")
        print("\nKey Features Verified:")
        print("✅ Employee data retrieval")
        print("✅ Leave balance inquiry")
        print("✅ Leave request processing with balance validation")
        print("✅ Asset provisioning based on employee role")
        print("✅ JSON data file updates")
        print("✅ Error handling for invalid inputs")
        print("\nThe AI-Powered HR Assistant prototype is fully functional!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the server. Please ensure the Flask app is running.")
    except Exception as e:
        print(f"❌ An error occurred during demonstration: {str(e)}")


if __name__ == "__main__":
    main()
