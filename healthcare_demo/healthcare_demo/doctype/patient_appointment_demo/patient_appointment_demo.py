import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date, get_time
from frappe.utils import get_datetime
from datetime import datetime, timedelta



class PatientAppointmentDemo(Document):
    def before_save(self):
        validate_overlap(self)
        validate_working_hours(self)

def get_clinic_hours():
    settings = frappe.get_single("Clinic Settings")
    return str(settings.working_hours_start), str(settings.working_hours_end)


def validate_working_hours(doc):
    if not (doc.appointment_date and doc.appointment_time and doc.estimated_end_time):
        return

    start_dt = get_datetime(f"{doc.appointment_date} {doc.appointment_time}")
    end_dt = get_datetime(f"{doc.appointment_date} {doc.estimated_end_time}")

    clinic_start, clinic_end = get_clinic_hours()

    clinic_start_dt = get_datetime(f"{doc.appointment_date} {clinic_start}")
    clinic_end_dt = get_datetime(f"{doc.appointment_date} {clinic_end}")

    if start_dt < clinic_start_dt or end_dt > clinic_end_dt:
        frappe.throw(
            f"Appointment must be scheduled between {clinic_start[:-3]} and {clinic_end[:-3]} only.",
            frappe.ValidationError
        )



def validate_overlap(doc):
    """
    Prevent overlapping appointments (for any patient).
    """

    if not (doc.appointment_date and doc.appointment_time and doc.estimated_end_time):
        return

    
    start_dt = get_datetime(f"{doc.appointment_date} {doc.appointment_time}")
    end_dt = get_datetime(f"{doc.appointment_date} {doc.estimated_end_time}")

    # Fetch all scheduled appointments (except current one)
    overlaps = frappe.db.sql("""
        SELECT name, appointment_date, appointment_time, estimated_end_time
        FROM `tabPatient Appointment Demo`
        WHERE status = 'Scheduled'
          AND name != %s
          AND appointment_date = %s
    """, (doc.name or "new", doc.appointment_date), as_dict=True)

    for appt in overlaps:
        existing_start = get_datetime(f"{appt.appointment_date} {appt.appointment_time}")
        existing_end = get_datetime(f"{appt.appointment_date} {appt.estimated_end_time}")

        # Overlap check
        if (start_dt < existing_end) and (end_dt > existing_start):
            frappe.throw(
                f"Appointment overlaps with existing appointment {appt.name} "
                f"from {existing_start.strftime('%H:%M')} to {existing_end.strftime('%H:%M')}",
                frappe.ValidationError
            )


@frappe.whitelist()
def calculate_end_time(service, appointment_date, appointment_time):
    """
    Calculate estimated end time for appointment.
    """
    if not service or not appointment_time or not appointment_date:
        return None

    
    service_doc = frappe.get_doc("Healthcare Service", service)
    duration = service_doc.durationmins or 3

     # Parse start datetime from date + time
    start_dt = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M:%S")

    # Add minutes using timedelta
    end_dt = start_dt + timedelta(minutes=duration)

    # Return only the time part
    return end_dt.strftime("%H:%M:%S")



@frappe.whitelist()
def get_service_price(service):
    """
    Fetch price for selected Healthcare Service
    """
    if not service:
        return 0

    service_doc = frappe.get_doc("Healthcare Service", service)

    
    return service_doc.price or 0

def appointment_status_logger(doc, method):
    if doc.status == "Completed":
        frappe.logger().info(f"Patient Appointment {doc.name} has been marked as Completed.")
        
        print(f"[LOG] Patient Appointment {doc.name} marked as Completed.")

def create_sales_invoice(doc, method):
    frappe.logger().info(f"Hook triggered for {doc.name}")
    try:
        # Ensure customer exists
        customer = "Walk-in Customer"
        if not frappe.db.exists("Customer", customer):
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": customer,
                "customer_group": "All Customer Groups",
                "territory": "All Territories"
            }).insert(ignore_permissions=True)

        # Get linked Item for the service
        service_item = frappe.db.get_value("Healthcare Service", doc.service, "linked_item")
        if not service_item:
            frappe.throw(f"No linked Item found for Healthcare Service {doc.service}")

        # Ensure total_amount exists
        if not getattr(doc, "total_amount", None) or doc.total_amount == 0:
            service_price = frappe.db.get_value("Healthcare Service", doc.service, "price") or 0
            doc.total_amount = service_price
            doc.save(ignore_permissions=True)

        # Create Sales Invoice
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": customer,
            "appointment": doc.name,
            "items": [
                {
                    "item_code": service_item,
                    "qty": 1,
                    "rate": doc.total_amount,
                    "amount": doc.total_amount
                }
            ]
        })
        invoice.insert(ignore_permissions=True)
        invoice.submit()
        print(f"Invoice created: {invoice.name}")

        # Create Payment Entry only if amount > 0
        if doc.total_amount > 0:
            try:
                company = "Parvati"
                default_cash = frappe.db.get_value("Company", company, "default_cash_account")
                payment_entry = frappe.get_doc({
                    "doctype": "Payment Entry",
                    "payment_type": "Receive",
                    "party_type": "Customer",
                    "party": customer,
                    "paid_amount": doc.total_amount,
                    "received_amount": doc.total_amount,
                    "reference_no": f"PAY-{doc.name}",
                    "reference_date": doc.appointment_date,
                    "mode_of_payment": "Cash",
                    "paid_to": default_cash,
                    "references": [
                        {
                            "reference_doctype": "Sales Invoice",
                            "reference_name": invoice.name,
                            "allocated_amount": doc.total_amount
                        }
                    ]
                })
                payment_entry.insert(ignore_permissions=True)
                payment_entry.submit()
                print(f"Payment Entry created: {payment_entry.name}")
            except Exception as pe:
                frappe.log_error(title="Payment Entry Failed", message=str(pe))
                print(f"[INFO] Payment Entry skipped: {str(pe)}")
        else:
            print(f"[INFO] Payment Entry skipped for appointment {doc.name} (total_amount = 0)")

    except Exception as e:
        frappe.log_error(title="Sales Invoice Creation Failed", message=str(e))
        print(f"[ERROR] {str(e)}")
