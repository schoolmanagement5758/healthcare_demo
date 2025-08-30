# Copyright (c) 2025, me and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from healthcare_demo.healthcare_demo.doctype.patient_appointment_demo.patient_appointment_demo import calculate_end_time


class TestPatientAppointmentDemo(FrappeTestCase):
    def test_with_service_duration(self):
        # create a dummy Healthcare Service with 20 min duration
        service = frappe.get_doc({
            "doctype": "Healthcare Service",
            "service_name": "Test Service 20min",
            "durationmins": 20
        }).insert(ignore_permissions=True)

        result = calculate_end_time(service.name, "2025-08-30", "14:00:00")
        self.assertEqual(result, "14:20:00")

    def test_with_default_duration(self):
        # create a service with no duration
        service = frappe.get_doc({
            "doctype": "Healthcare Service",
            "service_name": "Quick Service"
        }).insert(ignore_permissions=True)

        result = calculate_end_time(service.name, "2025-08-30", "15:00:00")
        self.assertEqual(result, "15:03:00")

    def test_with_invalid_inputs(self):
        self.assertIsNone(calculate_end_time(None, None, None))
