# Copyright (c) 2025, me and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe import ValidationError
from healthcare_demo.healthcare_demo.doctype.patient_appointment_demo.patient_appointment_demo import calculate_end_time, get_service_price

class TestPatientAppointmentDemo(FrappeTestCase):

    def setUp(self):
        # Ensure clinic working hours
        settings = frappe.get_single("Clinic Settings")
        settings.working_hours_start = "09:00:00"
        settings.working_hours_end = "17:00:00"
        settings.save()

        # Create an Item for Healthcare Services if not exists
        if not frappe.db.exists("Item", "Operation"):
            self.item = frappe.get_doc({
                "doctype": "Item",
                "item_code": "Operation",
                "item_name": "Operation",
                "stock_uom": "Nos",
                "is_stock_item": 0
            }).insert(ignore_permissions=True)
        else:
            self.item = frappe.get_doc("Item", "Operation")

    def create_service(self, service_name="Operation", duration=60, price=1000):
        """Helper to create Healthcare Service linked to Item"""
        if not frappe.db.exists("Healthcare Service", service_name):
            return frappe.get_doc({
                "doctype": "Healthcare Service",
                "service_name": service_name,
                "durationmins": duration,
                "price": price,
                "linked_item": self.item.name
            }).insert(ignore_permissions=True)
        else:
            return frappe.get_doc("Healthcare Service", service_name)

    def test_calculate_end_time(self):
        service = self.create_service()
        result = calculate_end_time(
            service=service.name,
            appointment_date="2025-08-30",
            appointment_time="10:00:00"
        )
        # 60 minutes from 10:00
        self.assertEqual(result, "11:00:00")

    def test_total_amount_calculation(self):
        service = self.create_service(service_name="Test Service Amount", duration=10, price=200)
        price = get_service_price(service.name)
        quantity = 3
        total = price * quantity
        self.assertEqual(total, 600)  # 200 * 3

    def test_non_overlapping_appointment_creation(self):
        service = self.create_service()

        appt1 = frappe.get_doc({
            "doctype": "Patient Appointment Demo",
            "appointment_date": "2025-10-30",
            "appointment_time": "10:00:00",
            "estimated_end_time": calculate_end_time(service.name, "2025-10-30", "10:00:00"),
            "patient_contact": "9999999999",
            "status": "Scheduled",
            "service": service.name,
            "total_amount": service.price  
        }).insert(ignore_permissions=True)

        appt2 = frappe.get_doc({
            "doctype": "Patient Appointment Demo",
            "appointment_date": "2025-10-30",
            "appointment_time": "12:30:00",
            "estimated_end_time": calculate_end_time(service.name, "2025-10-30", "12:30:00"),
            "patient_contact": "9999999999",
            "status": "Scheduled",
            "service": service.name,
            "total_amount": service.price
        }).insert(ignore_permissions=True)

        self.assertTrue(appt2.name)

    def test_fail_outside_working_hours(self):
        service = self.create_service()
        appointment = frappe.get_doc({
            "doctype": "Patient Appointment Demo",
            "patient": "Test Patient",
            "appointment_date": "2025-08-31",
            "appointment_time": "08:30:00",
            "estimated_end_time": calculate_end_time(service.name, "2025-08-31", "08:30:00"),
            "status": "Scheduled",
            "service": service.name,
            "total_amount": service.price
        })

        with self.assertRaises(ValidationError):
            appointment.insert()

    def test_webform_booking(self):
        """Simulate public Web Form booking with pre-calculated estimated_end_time"""
        service = self.create_service(duration=60, price=1000)

        appointment_time = "11:00:00"
        appointment_date = "2025-09-02"

        # Pre-calculate estimated end time
        estimated_end_time = calculate_end_time(
            service=service.name,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        )

        # Simulate Web Form submission
        appointment_data = {
            "doctype": "Patient Appointment Demo",
            "patient": "Test Patient Web",
            "patient_contact": "9999999999",
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "service": service.name,
            "status": "Scheduled",
            "total_amount": service.price,
            "estimated_end_time": estimated_end_time  # <-- set here
        }

        # Insert appointment 
        appointment = frappe.get_doc(appointment_data).insert(ignore_permissions=True)

        # Assert appointment exists
        self.assertTrue(frappe.db.exists("Patient Appointment Demo", appointment.name))

        # Assert estimated_end_time matches expected value
        self.assertEqual(appointment.estimated_end_time, estimated_end_time)
