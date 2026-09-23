import pandas as pd
import pytest

@pytest.fixture
def valid_data():
    customer = {
        "customerID": "CLIENT-0",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "No",
        "Dependents": "No",
        "tenure": 1,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "DSL",
        "OnlineSecurity": "Yes",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "Yes",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 30.0,
        "TotalCharges": "30.0",
        "Churn": "No",
    }
    data = pd.DataFrame([customer.copy() for _ in range(4)])
    data["customerID"] = ["CLIENT-0", "CLIENT-1", "CLIENT-2", "CLIENT-3"]
    data["tenure"] = [1, 12, 24, 48]
    data["MonthlyCharges"] = [30.0, 50.0, 70.0, 90.0]
    data["TotalCharges"] = ["30.0", "600.0", "1680.0", "4320.0"]
    data["SeniorCitizen"] = [0, 0, 1, 0]
    data["Churn"] = ["No", "Yes", "No", "Yes"]
    return data

    

