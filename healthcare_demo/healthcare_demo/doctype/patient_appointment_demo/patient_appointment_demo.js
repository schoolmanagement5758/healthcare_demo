frappe.ui.form.on("Patient Appointment Demo", {
    service: function(frm) {
        
        frm.trigger("update_end_time");

        // Fetch price and update total_amount when service changes
        if (frm.doc.service) {
            frappe.call({
                method: "healthcare_demo.healthcare_demo.doctype.patient_appointment_demo.patient_appointment_demo.get_service_price",
                args: {
                    service: frm.doc.service
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("total_amount", r.message);
                    } else {
                        frm.set_value("total_amount", 0);
                    }
                }
            });
        } else {
            frm.set_value("total_amount", 0);
        }
    },

    appointment_date: function(frm) {
        frm.trigger("update_end_time");
    },

    appointment_time: function(frm) {
        frm.trigger("update_end_time");
    },

    update_end_time: function(frm) {
        if (frm.doc.service && frm.doc.appointment_date && frm.doc.appointment_time) {
            frappe.call({
                method: "healthcare_demo.healthcare_demo.doctype.patient_appointment_demo.patient_appointment_demo.calculate_end_time",
                args: {
                    service: frm.doc.service,
                    appointment_date: frm.doc.appointment_date,
                    appointment_time: frm.doc.appointment_time
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("estimated_end_time", r.message);
                    }
                }
            });
        }
    }
});
