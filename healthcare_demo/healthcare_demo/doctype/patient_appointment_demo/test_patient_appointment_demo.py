# Copyright (c) 2025, me and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from healthcare_demo.healthcare_demo.doctype.patient_appointment_demo.patient_appointment_demo import calculate_end_time
from healthcare_demo.healthcare_demo.doctype.patient_appointment_demo.patient_appointment_demo import get_service_price


class TestPatientAppointmentDemo(FrappeTestCase):
        
    def test_calculate_end_time(self):
        #Create Healthcare Service
        service = frappe.get_doc({
            "doctype": "Healthcare Service",
            "service_name": "Operation",
            "durationmins": 100,
            "price": 10000
        }).insert(ignore_permissions=True)

        # Calling  method
        result = calculate_end_time(
            service=service.name,
            appointment_date="2025-08-30",
            appointment_time="10:00:00"
        )

        #Verify result
        assert result == "11:40:00"


    def test_total_amount_calculation(self):
        # Create a Healthcare Service with price 200
        service = frappe.get_doc({
            "doctype": "Healthcare Service",
            "service_name": "Test Service Amount",
            "durationmins": 10,
            "price": 200
        }).insert(ignore_permissions=True)

        # Fetch service price using our function
        price = get_service_price(service.name)
        
        # Suppose quantity = 3
        quantity = 3
        total = price * quantity

        # Assert calculation is correct
        self.assertEqual(total, 600)  # 200 * 3

