import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to draw running headers, footers with page numbers, and watermarks."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # 1. Draw Watermark Background
        self.setFont("Helvetica-Bold", 60)
        self.setFillColor(colors.HexColor('#F5F5F5'))  # very light grey
        self.saveState()
        self.translate(297.5, 420.5)  # Center of A4
        self.rotate(45)
        self.drawCentredString(0, 0, "ADVANCE CARE PLANNING")
        self.restoreState()

        # 2. Running Header (omitted on page 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor('#555555'))
            self.drawString(54, 795, "ADVANCE MEDICAL DIRECTIVE (LIVING WILL)")
            self.setStrokeColor(colors.HexColor('#CCCCCC'))
            self.setLineWidth(0.5)
            self.line(54, 788, 541.27, 788) # A4 width is 595.27. Margin 54 on each side -> max X is 541.27

        # 3. Running Footer
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#555555'))
        self.drawString(54, 40, "Confidential - Advance Care Planning System")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(541.27, 40, page_text)
        
        self.setStrokeColor(colors.HexColor('#CCCCCC'))
        self.setLineWidth(0.5)
        self.line(54, 52, 541.27, 52)
        
        self.restoreState()


def generate_amd_pdf(patient, preferences, dhrs, witnesses, notary_name, notary_place, executor_place, output_path):
    """Generate a highly polished, professional AMD PDF matching the legal layout of the reference document."""
    # A4 dimensions are 595.27 x 841.89 points.
    # Margins: 0.75 in (54 pt) on left and right, 1 in (72 pt) on top and bottom.
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        alignment=1, # Center
        textColor=colors.HexColor('#1E3A8A'), # Navy Primary
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0F766E'), # Teal Primary
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'MainBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#222222'),
        spaceAfter=8
    )

    body_bold = ParagraphStyle(
        'MainBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    italic_style = ParagraphStyle(
        'ItalicText',
        parent=body_style,
        fontName='Helvetica-Oblique',
        textColor=colors.HexColor('#555555')
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        fontSize=9
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=body_style,
        fontSize=8.5,
        leading=11,
        spaceAfter=0
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # Title & Header Block
    story.append(Paragraph("ADVANCE MEDICAL DIRECTIVE", title_style))
    story.append(Spacer(1, 10))

    # SECTION 1: Personal Details
    story.append(Paragraph("Section 1: Personal details", h1_style))
    story.append(Paragraph("This advance medical directive (living will) and the designation of healthcare representative(s) is made by me:", body_style))
    story.append(Spacer(1, 5))

    # Formatted Table for Section 1
    # Max printable width = 595.27 - 108 = 487.27 points.
    col_widths_s1 = [137.27, 350.0]
    dob_str = patient.date_of_birth.strftime('%d/%m/%Y') if patient.date_of_birth else 'N/A'
    
    s1_data = [
        [Paragraph("Full name", table_cell_bold), Paragraph(patient.user.full_name, table_cell_style)],
        [Paragraph("Gender", table_cell_bold), Paragraph(patient.gender or 'N/A', table_cell_style)],
        [Paragraph("Date of Birth", table_cell_bold), Paragraph(dob_str, table_cell_style)],
        [Paragraph("Government ID", table_cell_bold), Paragraph(f"1. Document Name: {patient.government_id_type or 'N/A'}<br/>2. ID No.: {patient.government_id_number or 'N/A'}", table_cell_style)],
        [Paragraph("Full permanent residential address", table_cell_bold), Paragraph(patient.permanent_address or 'N/A', table_cell_style)],
        [Paragraph("Full current residential address", table_cell_bold), Paragraph(patient.current_address or 'N/A', table_cell_style)],
        [Paragraph("Municipality/Panchayat", table_cell_bold), Paragraph(patient.municipality_panchayat or 'N/A', table_cell_style)]
    ]
    
    t1 = Table(s1_data, colWidths=col_widths_s1)
    t1.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    # Preamble statement
    story.append(Paragraph("<i>If and when the time comes that I can no longer participate in decision-making regarding my own health and medical treatment, this directive should be treated as the final expression of my wishes.</i>", italic_style))
    story.append(Spacer(1, 5))

    if patient.beliefs_values:
        story.append(Paragraph("<b>Personal Beliefs & Values:</b>", body_style))
        story.append(Paragraph(patient.beliefs_values, italic_style))
        story.append(Spacer(1, 10))

    story.append(Paragraph("I request that all concerned (including my designated healthcare representative(s), my treating team, and the others involved) must treat my wishes in this document as the primary basis for any decision regarding my medical treatment, particularly decisions relating to life-sustaining treatment.", body_style))
    story.append(Spacer(1, 10))
    story.append(PageBreak()) # Clean break to Section 2

    # SECTION 2: Directions relating to life-sustaining treatment
    story.append(Paragraph("Section 2: Directions relating to life-sustaining treatment", h1_style))
    story.append(Paragraph("In situations where my treating physician or team have determined that:", body_style))
    
    # Bullet points
    story.append(Paragraph("• There is no reasonable medical probability of recovery from a terminal condition, end-stage condition, or vegetative state, and", body_style))
    story.append(Paragraph("• Any further medical intervention or course of treatment would only serve the purpose of artificially prolonging the process of dying.", body_style))
    story.append(Paragraph("<b>I direct that any life-prolonging medical procedure/treatment be withheld or withdrawn, and the course of natural death be permitted.</b>", body_bold))
    story.append(Spacer(1, 5))

    story.append(Paragraph("Specifically, my directives regarding clinical withholding/withdrawal (I DO NOT WANT) and clinical continuation (I WANT) are detailed below:", body_style))
    
    # Create Table of Preferences
    pref_headers = [
        Paragraph("Medical Intervention / Form of Treatment", table_header_style),
        Paragraph("Patient Preference", table_header_style),
        Paragraph("Directive Status", table_header_style)
    ]
    
    def format_directive(db_pref):
        if db_pref == 'WANT':
            return Paragraph("<font color='#0F766E'><b>PROVIDE / CONTINUE</b></font>", table_cell_style)
        elif db_pref == 'DO NOT WANT':
            return Paragraph("<font color='#DC2626'><b>WITHHOLD / WITHDRAW</b></font>", table_cell_style)
        return Paragraph("<font color='#6B7280'>NOT SPECIFIED</font>", table_cell_style)

    pref_data = [
        pref_headers,
        [Paragraph("1. Cardio-pulmonary resuscitation (CPR)", table_cell_style), Paragraph("DO NOT WANT CPR if heartbeat stops", table_cell_style), format_directive(preferences.cpr_preference)],
        [Paragraph("2. Dialysis", table_cell_style), Paragraph("Withhold kidney filtering in terminal states", table_cell_style), format_directive(preferences.dialysis_preference)],
        [Paragraph("3. Ventilation (Artificial Life Support)", table_cell_style), Paragraph("Withhold invasive machine breathing", table_cell_style), format_directive(preferences.ventilator_preference)],
        [Paragraph("4. Chemotherapy", table_cell_style), Paragraph("Withhold cancer drugs to extend dying process", table_cell_style), format_directive(preferences.chemotherapy_preference)],
        [Paragraph("5. Radiotherapy", table_cell_style), Paragraph("Withhold radiation treatment in terminal state", table_cell_style), format_directive(preferences.radiotherapy_preference)],
        [Paragraph("6. Invasive Surgery", table_cell_style), Paragraph("Withhold unless purely for pain/comfort control", table_cell_style), format_directive(preferences.surgery_preference)],
        [Paragraph("7. Intravenous Fluids / Meds (Invasive)", table_cell_style), Paragraph("Withhold unless providing comfort/pain relief", table_cell_style), format_directive(preferences.iv_fluids_preference)],
        [Paragraph("8. Artificial Nutrition & Hydration (Feeding Tubes)", table_cell_style), Paragraph("Withhold if it artificially prolongs active dying", table_cell_style), format_directive(preferences.nutrition_hydration_preference)]
    ]

    t_pref = Table(pref_data, colWidths=[207.27, 150.0, 130.0])
    t_pref.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F766E')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_pref)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Comfort Care Directive:</b> Even when life-sustaining treatment is withheld or withdrawn, I direct the administration of medication and performance of medical procedures to provide comfort, alleviate pain, distress, or mental confusion.", body_bold))
    story.append(Paragraph(f"Additional pain management directives: <i>{preferences.pain_management or 'Standard comfort care protocols to be followed.'}</i>", italic_style))
    story.append(Spacer(1, 10))
    story.append(PageBreak())

    # SECTION 3: Wishes or desires during end-of-life care
    story.append(Paragraph("Section 3 (Optional): Wishes or desires during end-of-life care", h1_style))
    story.append(Paragraph("Below are my specific guidelines regarding my care preferences during palliative and end-of-life care:", body_style))
    story.append(Spacer(1, 5))

    s3_data = []
    if preferences.preferred_place_of_care:
        s3_data.append([Paragraph("<b>Preferred Place of Care:</b>", table_cell_bold), Paragraph(f"I wish to stay at a {preferences.preferred_place_of_care} (Preferred Facility: {preferences.preferred_hospital or 'Not Specified'})", table_cell_style)])
    if preferences.preferred_physician_name:
        s3_data.append([Paragraph("<b>Preferred Physician:</b>", table_cell_bold), Paragraph(f"{preferences.preferred_physician_name} ({preferences.preferred_physician_designation or 'Physician'}), {preferences.preferred_physician_institution or 'Hospital'}", table_cell_style)])
    if preferences.special_focus_priority:
        s3_data.append([Paragraph("<b>Special Focus / Care Priority:</b>", table_cell_bold), Paragraph(preferences.special_focus_priority, table_cell_style)])
    if preferences.gender_identity_instructions:
        s3_data.append([Paragraph("<b>Gender Identity:</b>", table_cell_bold), Paragraph(preferences.gender_identity_instructions, table_cell_style)])
    if preferences.relationship_instructions:
        s3_data.append([Paragraph("<b>Relationship Disclosures:</b>", table_cell_bold), Paragraph(preferences.relationship_instructions, table_cell_style)])
    if preferences.additional_wishes:
        s3_data.append([Paragraph("<b>Additional Wishes:</b>", table_cell_bold), Paragraph(preferences.additional_wishes, table_cell_style)])

    if s3_data:
        t_s3 = Table(s3_data, colWidths=[150, 337.27])
        t_s3.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F9FAFB')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t_s3)
    else:
        story.append(Paragraph("No special wishes or desires during end-of-life care were recorded.", italic_style))
    story.append(Spacer(1, 15))

    # SECTION 4: Authorisation of the Designated Healthcare Representative (DHR)
    story.append(Paragraph("Section 4: Authorisation of the Designated Healthcare Representative (DHR)", h1_style))
    story.append(Paragraph(f"In order to make decisions on my behalf for my medical treatment, I have nominated <b>{len(dhrs)}</b> designated healthcare representative(s) (DHRs) below.", body_style))
    story.append(Spacer(1, 5))

    # Render DHR details
    for dhr in dhrs:
        role_label = "PRIMARY DHR" if dhr.preference_order == 1 else f"ALTERNATE DHR (Rank {dhr.preference_order - 1})"
        story.append(Paragraph(f"<b>{role_label} details:</b>", body_bold))
        story.append(Spacer(1, 2))
        
        dhr_dob_str = dhr.date_of_birth.strftime('%d/%m/%Y') if dhr.date_of_birth else 'N/A'
        dhr_data = [
            [Paragraph("Full Name", table_cell_bold), Paragraph(dhr.full_name, table_cell_style)],
            [Paragraph("Relationship with Executor", table_cell_bold), Paragraph(dhr.relationship, table_cell_style)],
            [Paragraph("Date of Birth", table_cell_bold), Paragraph(dhr_dob_str, table_cell_style)],
            [Paragraph("Government ID", table_cell_bold), Paragraph(f"Document Name: {dhr.government_id_type or 'N/A'} | ID No.: {dhr.government_id_number or 'N/A'}", table_cell_style)],
            [Paragraph("Mobile Number(s)", table_cell_bold), Paragraph(f"Primary: {dhr.mobile_primary or 'N/A'} | Secondary: {dhr.mobile_secondary or 'N/A'}", table_cell_style)],
            [Paragraph("Email ID(s)", table_cell_bold), Paragraph(f"Primary: {dhr.email_primary or 'N/A'} | Secondary: {dhr.email_secondary or 'N/A'}", table_cell_style)],
            [Paragraph("Permanent Residential Address", table_cell_bold), Paragraph(dhr.permanent_address or 'N/A', table_cell_style)],
            [Paragraph("Signing Address", table_cell_bold), Paragraph(dhr.signing_address or 'N/A', table_cell_style)]
        ]
        
        t_dhr = Table(dhr_data, colWidths=[150, 337.27])
        t_dhr.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t_dhr)
        story.append(Spacer(1, 10))
    story.append(PageBreak())

    # SECTION 5: Directions to be followed upon my death
    story.append(Paragraph("Section 5 (Optional): Directions to be followed upon my death", h1_style))
    s5_data = [
        [Paragraph("<b>Organ Donation:</b>", table_cell_bold), Paragraph(f"Choices noted: {preferences.organ_donation}", table_cell_style)],
        [Paragraph("<b>Body / Cadaver Donation:</b>", table_cell_bold), Paragraph(f"Choices noted: {preferences.body_donation}", table_cell_style)],
        [Paragraph("<b>Last Rites / Funeral:</b>", table_cell_bold), Paragraph(preferences.last_rites or 'Not Specified', table_cell_style)]
    ]
    t_s5 = Table(s5_data, colWidths=[150, 337.27])
    t_s5.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F9FAFB')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_s5)
    story.append(Spacer(1, 12))

    # DECLARATION AND SIGNATURES
    story.append(Paragraph("Declaration & Signatures", h1_style))
    story.append(Paragraph("I declare that at the time of signing and executing this document, I have the capacity and competence to understand the meaning and implications of everything mentioned in this document. I have given careful thought and consideration, and I have willingly and voluntarily articulated and consented to everything mentioned in this document, without any coercion, duress, or undue influence.", body_style))
    story.append(Spacer(1, 8))

    # Keep signatures block together to avoid awkward layout breaks
    sig_elements = []
    
    # Signature of Executor Table
    sig_headers = [
        Paragraph("<b>Signature of the Executor (Patient)</b>", body_bold),
        Spacer(1, 5)
    ]
    sig_elements.append(Paragraph("<b>Executor Signature Panel:</b>", body_bold))
    
    exec_data = [
        [Paragraph("Full Name:", table_cell_bold), Paragraph(patient.user.full_name, table_cell_style)],
        [Paragraph("Signature / Thumb impression:", table_cell_bold), Paragraph("<br/><br/>_____________________________________", table_cell_style)],
        [Paragraph("Date & Time of Signing:", table_cell_bold), Paragraph(datetime.now().strftime('%d/%m/%Y %H:%M'), table_cell_style)],
        [Paragraph("Place of Signing:", table_cell_bold), Paragraph(executor_place, table_cell_style)]
    ]
    t_exec = Table(exec_data, colWidths=[150, 337.27])
    t_exec.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    sig_elements.append(t_exec)
    sig_elements.append(Spacer(1, 15))

    # Witness signature headers
    sig_elements.append(Paragraph("<b>Witnesses Attestation:</b>", body_bold))
    sig_elements.append(Paragraph("<i>We, as witnesses, record our satisfaction that the document has been executed voluntarily and without any coercion, duress, inducement, or compulsion.</i>", italic_style))
    sig_elements.append(Spacer(1, 5))

    # Witness 1 and Witness 2 side-by-side or tables
    for idx, wit in enumerate(witnesses, start=1):
        sig_elements.append(Paragraph(f"<b>Witness {idx} details:</b>", body_bold))
        wit_data = [
            [Paragraph("Name:", table_cell_bold), Paragraph(wit['name'], table_cell_style), Paragraph("Signature Box:", table_cell_bold)],


            [Paragraph("Email ID:", table_cell_bold), Paragraph(wit['email'], table_cell_style), Paragraph("", table_cell_style)],
            [Paragraph("Mobile No:", table_cell_bold), Paragraph(wit['mobile'], table_cell_style), Paragraph("", table_cell_style)]
        ]
        t_wit = Table(wit_data, colWidths=[100, 237.27, 150])
        t_wit.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('SPAN', (2, 1), (2, 2)),  # Span signature box across contact rows
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        sig_elements.append(t_wit)
        sig_elements.append(Spacer(1, 10))

    story.append(KeepTogether(sig_elements))
    story.append(PageBreak())

    # NOTARISATION
    notary_elements = []
    notary_elements.append(Paragraph("Notarisation", h1_style))
    notary_elements.append(Paragraph("This directive and authorisation of designated healthcare representative(s) has been signed in the presence of the undersigned by the Declarant, and I record my satisfaction that the document has been executed voluntarily and without any coercion, inducement, or compulsion.", body_style))
    notary_elements.append(Spacer(1, 15))

    notary_data = [
        [Paragraph("<b>SIGNED BEFORE ME</b>", body_bold), Paragraph("<b>APPROPRIATE AUTHORITY STAMP / SEAL</b>", body_bold)],
        [Paragraph(f"<br/><br/>_____________________________________<br/>(Full name of Notary Public: <b>{notary_name}</b>)", table_cell_style), Paragraph("<br/><br/><br/><br/>_____________________________________", table_cell_style)],
        [Paragraph(f"Date: <b>{datetime.now().strftime('%d/%m/%Y')}</b>", table_cell_style), Paragraph("", table_cell_style)],
        [Paragraph(f"Place: <b>{notary_place}</b>", table_cell_style), Paragraph("", table_cell_style)]
    ]
    t_notary = Table(notary_data, colWidths=[243.6, 243.6])
    t_notary.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (1, 1), (1, 3)), # Stamp seal span
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    notary_elements.append(t_notary)
    
    story.append(KeepTogether(notary_elements))

    # Build the document using our custom canvas for page counting
    doc.build(story, canvasmaker=NumberedCanvas)
