from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_invoice_pdf(invoice):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=24, textColor=colors.hexColor("#2563EB"), spaceAfter=20)
    label_style = ParagraphStyle('LabelStyle', parent=styles['Normal'], fontSize=10, textColor=colors.grey, leading=12)
    value_style = ParagraphStyle('ValueStyle', parent=styles['Normal'], fontSize=11, textColor=colors.black, leading=14, fontName='Helvetica-Bold')
    
    elements = []

    # Header Section (Company Info & Invoice Title)
    data = [
        [Paragraph("INVOICE", title_style), ""],
        [Paragraph("Invoice #: " + invoice.invoice_number, value_style), ""],
        [Paragraph("Date: " + str(invoice.invoice_date), styles['Normal']), ""],
        [Paragraph("Due Date: " + str(invoice.due_date), ParagraphStyle('Due', textColor=colors.red, parent=styles['Normal'])), ""]
    ]
    t = Table(data, colWidths=[3*inch, 2.5*inch])
    t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT')]))
    elements.append(t)
    elements.append(Spacer(1, 0.4*inch))

    # Billing Section
    bill_data = [
        [Paragraph("BILL TO", label_style), Paragraph("COMPANY DETAILS", label_style)],
        [Paragraph(invoice.customer.company_name, value_style), Paragraph("Your Factory Name", value_style)],
        [Paragraph(invoice.customer.contact_person, styles['Normal']), Paragraph("123 Industrial Way", styles['Normal'])],
        [Paragraph(invoice.customer.email, styles['Normal']), Paragraph("factory@example.com", styles['Normal'])],
        [Paragraph(invoice.customer.phone, styles['Normal']), Paragraph("+1 234 567 890", styles['Normal'])]
    ]
    bill_table = Table(bill_data, colWidths=[2.75*inch, 2.75*inch])
    bill_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,0), 5),
    ]))
    elements.append(bill_table)
    elements.append(Spacer(1, 0.5*inch))

    # Items Table
    header = ["Description", "Quantity", "Unit Price", "Total"]
    table_data = [header]
    
    if invoice.sales_order:
        for line in invoice.sales_order.lines.all():
            table_data.append([
                line.product.name,
                str(line.quantity_ordered),
                f"${line.unit_price}",
                f"${line.line_total}"
            ])
    else:
        table_data.append(["General Services", "1", f"${invoice.total_amount}", f"${invoice.total_amount}"])

    item_table = Table(table_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.hexColor("#F3F4F6")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.hexColor("#1F2937")),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.hexColor("#E5E7EB")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 0.3*inch))

    # Totals
    total_data = [
        ["", "Total Amount:", f"${invoice.total_amount}"],
        ["", "Amount Paid:", f"${invoice.amount_paid}"],
        ["", Paragraph("Balance Due:", value_style), Paragraph(f"${invoice.balance_due}", value_style)]
    ]
    total_table = Table(total_data, colWidths=[3.5*inch, 1*inch, 1*inch])
    total_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (1,0), (1,1), 'Helvetica'),
        ('FONTSIZE', (1,0), (-1,-1), 10),
    ]))
    elements.append(total_table)
    
    # Footer
    elements.append(Spacer(1, 1*inch))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=9, textColor=colors.grey)
    elements.append(Paragraph("Thank you for your business!", footer_style))
    elements.append(Paragraph("Payment Terms: " + invoice.customer.payment_terms, footer_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_quotation_pdf(quotation):
    # Similar professional logic for quotation
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=24, textColor=colors.hexColor("#2563EB"), spaceAfter=20)
    value_style = ParagraphStyle('ValueStyle', parent=styles['Normal'], fontSize=11, textColor=colors.black, leading=14, fontName='Helvetica-Bold')
    
    elements = []
    elements.append(Paragraph("QUOTATION", title_style))
    elements.append(Paragraph(f"Quote #: {quotation.quote_number}", value_style))
    elements.append(Paragraph(f"Valid Until: {quotation.valid_until}", styles['Normal']))
    elements.append(Spacer(1, 0.4*inch))
    
    # Customer and Items... (Simplified for brevity, similar to Invoice)
    data = [["Product", "Quantity", "Price", "Discount", "Total"]]
    for line in quotation.lines.all():
        data.append([line.product.name, str(line.quantity), f"${line.unit_price}", f"{line.discount_percentage}%", f"${line.line_total}"])
    
    t = Table(data, colWidths=[2*inch, 0.75*inch, 0.75*inch, 0.75*inch, 1*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.hexColor("#F3F4F6")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"Total: ${quotation.total_amount}", value_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
