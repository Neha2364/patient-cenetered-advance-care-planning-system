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
    """Two-pass canvas to draw running headers, footers with page numbers, and non-intrusive watermarks."""
    
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
        
        # 1. Subtle, Non-Obstructive Watermark Background
        # Uses low fill alpha so it never interferes with text or table readability
        try:
            self.setFillAlpha(0.06)
            self.setStrokeAlpha(0.06)
        except Exception:
            pass
        self.setFont("Helvetica-Bold", 40)
        self.setFillColor(colors.HexColor('#94A3B8'))  # Soft slate
        self.saveState()
        self.translate(297.64, 420.94)  # Center of A4 (595.27 / 2, 841.89 / 2)
        self.rotate(45)
        self.drawCentredString(0, 0, "ADVANCE MEDICAL DIRECTIVE")
        self.restoreState()

        # Reset alpha for running headers and footers
        try:
            self.setFillAlpha(1.0)
            self.setStrokeAlpha(1.0)
        except Exception:
            pass

        # 2. Running Header (omitted on page 1 for clean legal document presentation)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(colors.HexColor('#475569'))
            self.drawString(54, 802, "ADVANCE MEDICAL DIRECTIVE (LIVING WILL)")
            self.setFont("Helvetica", 7.5)
            self.drawRightString(541.27, 802, "Model Framework · Supreme Court of India Order (2023)")
            self.setStrokeColor(colors.HexColor('#CBD5E1'))
            self.setLineWidth(0.5)
            self.line(54, 796, 541.27, 796)

        # 3. Running Footer (included on all pages with dynamic page count)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor('#64748B'))
        self.drawString(54, 32, "Confidential · Patient-Centered Advance Care Planning (ACP) System")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(541.27, 32, page_text)
        
        self.setStrokeColor(colors.HexColor('#CBD5E1'))
        self.setLineWidth(0.5)
        self.line(54, 42, 541.27, 42)
        
        self.restoreState()


def safe_display(val, fallback="Not provided", blank_line=False):
    """
    Format missing or placeholder values cleanly without repeating 'N/A'.
    Optionally returns a blank signature/completion line.
    """
    if val is None:
        return "____________________________________" if blank_line else fallback
    s = str(val).strip()
    if not s or s.upper() in ('N/A', 'NONE', 'NOT SPECIFIED', 'PENDING', 'NOT_SPECIFIED', 'PENDING@EXAMPLE.COM'):
        return "____________________________________" if blank_line else fallback
    return s


def evaluate_treatment_preference(pref_value, treatment_key):
    """
    Safely evaluate a patient's saved treatment preference without fabricating or inverting intent.
    Accurately maps WANT, DO NOT WANT, UNSURE, and unrecorded choices to clinical explanations
    and distinct visual directive statuses.
    """
    normalized = (pref_value or '').strip().upper()
    
    explanations = {
        'cpr': {
            'WANT': "Desires cardiopulmonary resuscitation (CPR) to be attempted if heartbeat or breathing stops.",
            'DO_NOT_WANT': "Directs that cardiopulmonary resuscitation (CPR) be withheld or withdrawn; permit natural death.",
            'UNSURE': "Uncertain / Undecided; to be determined by DHR in consultation with treating medical team.",
            'NOT_SPECIFIED': "Preference not specified by patient in advance care record."
        },
        'ventilator': {
            'WANT': "Desires invasive mechanical ventilation / artificial life support to be initiated and maintained.",
            'DO_NOT_WANT': "Directs withholding or withdrawal of invasive mechanical ventilation / artificial life support.",
            'UNSURE': "Uncertain / Undecided; to be determined by DHR in consultation with treating medical team.",
            'NOT_SPECIFIED': "Preference not specified by patient in advance care record."
        },
        'dialysis': {
            'WANT': "Desires renal dialysis (hemodialysis or peritoneal) to support kidney function.",
            'DO_NOT_WANT': "Directs withholding or withdrawal of renal dialysis in end-stage or terminal condition.",
            'UNSURE': "Uncertain / Undecided; to be determined by DHR in consultation with treating medical team.",
            'NOT_SPECIFIED': "Preference not specified by patient in advance care record."
        },
        'chemotherapy': {
            'WANT': "Desires chemotherapy to be administered if recommended by treating oncologist.",
            'DO_NOT_WANT': "Directs withholding or cessation of chemotherapy aimed solely at prolonging active dying.",
            'UNSURE': "Uncertain / Undecided; to be determined by DHR in consultation with treating medical team.",
            'NOT_SPECIFIED': "Preference not specified by patient in advance care record."
        },
        'radiotherapy': {
            'WANT': "Desires radiation therapy to be administered if recommended by treating clinical team.",
            'DO_NOT_WANT': "Directs withholding of radiation therapy, unless required for palliative symptom control.",
            'UNSURE': "Uncertain / Undecided; to be determined by DHR in consultation with treating medical team.",
            'NOT_SPECIFIED': "Preference not specified by patient in advance care record."
        },
        'surgery': {
            'WANT': "Desires surgical intervention if deemed necessary by treating surgical team.",
            'DO_NOT_WANT': "Directs withholding of invasive surgeries, unless strictly for comfort or pain alleviation.",
            'UNSURE': "Uncertain / Undecided; to be determined by DHR in consultation with treating medical team.",
            'NOT_SPECIFIED': "Preference not specified by patient in advance care record."
        },
        'iv_fluids': {
            'WANT': "Desires intravenous fluids and intravenous medications to be provided/maintained.",
            'DO_NOT_WANT': "Directs withholding of invasive IV fluids/meds, excluding those needed for comfort/pain relief.",
            'UNSURE': "Uncertain / Undecided; to be determined by DHR in consultation with treating medical team.",
            'NOT_SPECIFIED': "Preference not specified by patient in advance care record."
        },
        'nutrition_hydration': {
            'WANT': "Desires artificial nutrition and hydration (feeding tubes / TPN) to be administered.",
            'DO_NOT_WANT': "Directs withholding/withdrawal of artificial feeding tubes if only artificially prolonging dying.",
            'UNSURE': "Uncertain / Undecided; to be determined by DHR in consultation with treating medical team.",
            'NOT_SPECIFIED': "Preference not specified by patient in advance care record."
        }
    }
    
    item_dict = explanations.get(treatment_key, {})
    
    if normalized in ('WANT', 'YES', 'PROVIDE', 'CONTINUE'):
        explanation = item_dict.get('WANT', "Desires this treatment to be provided / continued.")
        badge = "<font color='#0D9488'><b>PROVIDE / CONTINUE</b></font>"
    elif normalized in ('DO NOT WANT', 'NO', 'WITHHOLD', 'WITHDRAW'):
        explanation = item_dict.get('DO_NOT_WANT', "Directs this treatment to be withheld or withdrawn.")
        badge = "<font color='#DC2626'><b>WITHHOLD / WITHDRAW</b></font>"
    elif normalized in ('UNSURE', 'UNDECIDED', 'NOT SURE', 'CONSIDER'):
        explanation = item_dict.get('UNSURE', "Uncertain / Undecided; to be determined by DHR and medical team.")
        badge = "<font color='#D97706'><b>UNSURE / UNDECIDED</b></font>"
    else:
        explanation = item_dict.get('NOT_SPECIFIED', "Preference not specified by patient.")
        badge = "<font color='#64748B'><b>NOT SPECIFIED</b></font>"
        
    return explanation, badge


def count_to_words(n):
    """Convert small integer count to English words."""
    words = {0: "Zero", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
    return words.get(n, str(n))


def generate_amd_pdf(patient, preferences, dhrs, witnesses, notary_name, notary_place, executor_place, output_path):
    """
    Generate an authentic, legally structured Advance Medical Directive (Living Will) PDF.
    Faithfully implements the Vidhi Centre for Legal Policy model directive and the
    Hon'ble Supreme Court of India guidelines (Order dated January 24, 2023).
    """
    # A4 dimensions: 595.27 x 841.89 points
    # Margins: 54 pt (0.75 in) Left/Right, 54 pt Top/Bottom -> Printable width: 487.27 pt
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1,  # Center
        textColor=colors.HexColor('#1E3A8A'),  # Navy Primary
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        alignment=1,  # Center
        textColor=colors.HexColor('#64748B'),
        spaceAfter=12
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor('#0F766E'),  # Teal Accent
        spaceBefore=8,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SubSectionHeader',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=6,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'MainBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6
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
        textColor=colors.HexColor('#475569')
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        fontSize=8.5,
        leading=11
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=body_style,
        fontSize=8,
        leading=10.5,
        spaceAfter=0
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold'
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=body_style,
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor('#64748B')
    )

    story = []

    # Safe patient fields
    user_obj = getattr(patient, 'user', None)
    patient_name = user_obj.full_name if user_obj else safe_display(getattr(patient, 'full_name', None), "Not provided")
    gender_str = safe_display(patient.gender)
    dob_str = patient.date_of_birth.strftime('%d/%m/%Y') if getattr(patient, 'date_of_birth', None) else None
    if dob_str:
        age_str = f" (Age: {patient.age})" if getattr(patient, 'age', None) else ""
        dob_display = f"{dob_str}{age_str}"
    else:
        dob_display = f"Age: {patient.age}" if getattr(patient, 'age', None) else "Not provided"

    gov_doc = safe_display(patient.government_id_type)
    gov_no = safe_display(patient.government_id_number)
    if gov_doc != "Not provided" or gov_no != "Not provided":
        gov_id_str = f"1. Document Name: {gov_doc}<br/>2. ID No.: {gov_no}"
    else:
        gov_id_str = "Not provided"

    perm_addr = safe_display(patient.permanent_address or patient.address)
    curr_addr = safe_display(patient.current_address or patient.address)
    muni_str = safe_display(patient.municipality_panchayat)

    # -------------------------------------------------------------------------
    # PAGE 1: TITLE & SECTION 1: PERSONAL DETAILS
    # -------------------------------------------------------------------------
    story.append(Paragraph("ADVANCE MEDICAL DIRECTIVE", title_style))

    story.append(Paragraph("Section 1: Personal details", h1_style))
    story.append(Spacer(1, 3))

    col_widths_s1 = [140.0, 347.27]
    s1_data = [
        [Paragraph("Full name", table_cell_bold), Paragraph(patient_name, table_cell_style)],
        [Paragraph("Gender", table_cell_bold), Paragraph(gender_str, table_cell_style)],
        [Paragraph("Date of Birth / Age", table_cell_bold), Paragraph(dob_display, table_cell_style)],
        [Paragraph("Government ID", table_cell_bold), Paragraph(gov_id_str, table_cell_style)],
        [Paragraph("Full permanent residential address", table_cell_bold), Paragraph(perm_addr, table_cell_style)],
        [Paragraph("Full current residential address", table_cell_bold), Paragraph(curr_addr, table_cell_style)],
        [Paragraph("Municipality / Panchayat / Local Body", table_cell_bold), Paragraph(muni_str, table_cell_style)]
    ]
    
    t1 = Table(s1_data, colWidths=col_widths_s1)
    t1.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t1)
    story.append(Spacer(1, 8))

    # Preamble statement
    story.append(Paragraph("<i>If and when the time comes that I can no longer participate in decision-making regarding my own health and medical treatment, this directive should be treated as the final expression of my wishes.</i>", italic_style))
    story.append(Spacer(1, 4))

    # Beliefs and Values
    background_items = [
        ("Personal values and goals", getattr(patient, "personal_values", None) or (patient.beliefs_values if "[" not in (patient.beliefs_values or "") else None)),
        ("Chronic medical conditions", getattr(patient, "chronic_conditions", None)),
        ("Major illness or hospitalization", getattr(patient, "serious_hospitalization", None)),
        ("Long-term medications", getattr(patient, "long_term_medications", None)),
        ("Known allergies", getattr(patient, "allergies", None)),
    ]
    background_items = [(label, safe_display(value, fallback=None)) for label, value in background_items]
    background_items = [(label, value) for label, value in background_items if value]
    if background_items:
        story.append(Paragraph("<b>Relevant Personal Values & Health Background:</b>", body_style))
        for label, value in background_items:
            story.append(Paragraph(f"<b>{label}:</b> {value}", italic_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("I request that all concerned (including my designated healthcare representative(s), my treating team, and the others involved) must treat my wishes in this document as the primary basis for any decision regarding my medical treatment, particularly decisions relating to life-sustaining treatment.", body_style))
    
    # Page 1 Break
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 2: SECTION 2: DIRECTIONS RELATING TO LIFE-SUSTAINING TREATMENT
    # -------------------------------------------------------------------------
    story.append(Paragraph("Section 2: Directions relating to life-sustaining treatment", h1_style))
    story.append(Paragraph("In situations where my treating physician or medical team have determined that:", body_style))
    
    story.append(Paragraph("• There is no reasonable medical probability of recovery from a terminal condition, end-stage condition [1], or vegetative state [2], and", body_style))
    story.append(Paragraph("• Any further medical intervention or course of treatment would only serve the purpose of artificially prolonging the process of dying.", body_style))
    story.append(Paragraph("<b>I direct that any life-prolonging medical procedure/treatment be withheld or withdrawn, and the course of natural death be permitted, in accordance with the specific directives set forth below:</b>", body_bold))
    story.append(Spacer(1, 4))

    # Treatment Preferences Table - Dynamically Evaluated (NO HARDCODED CONTRADICTIONS)
    pref_headers = [
        Paragraph("Medical Intervention / Treatment", table_header_style),
        Paragraph("Patient Preference & Explanation", table_header_style),
        Paragraph("Directive Status", table_header_style)
    ]

    treatments = [
        ("1. Cardio-pulmonary resuscitation (CPR)", preferences.cpr_preference, 'cpr'),
        ("2. Mechanical Ventilation (Artificial Life Support)", preferences.ventilator_preference, 'ventilator'),
        ("3. Dialysis (Renal Replacement Therapy)", preferences.dialysis_preference, 'dialysis'),
        ("4. Chemotherapy (Cancer Therapy)", preferences.chemotherapy_preference, 'chemotherapy'),
        ("5. Radiotherapy (Radiation Therapy)", preferences.radiotherapy_preference, 'radiotherapy'),
        ("6. Invasive Surgery (Major Operations)", preferences.surgery_preference, 'surgery'),
        ("7. Artificial Hydration (IV / Tube Fluids)", preferences.iv_fluids_preference, 'iv_fluids'),
        ("8. Artificial Nutrition (Feeding Tubes)", preferences.nutrition_hydration_preference, 'nutrition_hydration')
    ]

    pref_rows = [pref_headers]
    for label, val, key in treatments:
        expl, status_html = evaluate_treatment_preference(val, key)
        pref_rows.append([
            Paragraph(label, table_cell_bold),
            Paragraph(expl, table_cell_style),
            Paragraph(status_html, table_cell_style)
        ])

    t_pref = Table(pref_rows, colWidths=[167.27, 200.0, 120.0])
    t_pref.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F766E')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_pref)
    story.append(Spacer(1, 6))

    # Definitions / Clinical Footnotes from Vidhi reference
    story.append(Paragraph("<b>Statutory & Clinical Definitions:</b><br/>"
                           "<font size='7' color='#475569'>[1] <i>'End-stage condition'</i> means an irreversible condition caused by injury, disease, or illness resulting in progressively severe and permanent deterioration, where, to a reasonable degree of medical probability, treatment would be ineffective.<br/>"
                           "[2] <i>'Vegetative state'</i> is one where a person is awake but shows no signs of awareness (persisting beyond clinical thresholds established by authoritative medical bodies).</font>", disclaimer_style))
    story.append(Spacer(1, 6))

    # Comfort Care Directive
    story.append(Paragraph("<b>Comfort Care & Pain Alleviation Directive:</b> Even when life-sustaining treatment is withheld or withdrawn, I explicitly direct the administration of medication and performance of medical procedures for providing me with comfort care or to alleviate suffering in the form of pain, distress, or mental confusion (or to facilitate organ or body donation).", body_bold))
    pain_dir = safe_display(preferences.pain_management, fallback="Standard comfort care, palliative pain alleviation, and symptom management protocols to be administered.")
    story.append(Paragraph(f"Specific pain management directives: <i>{pain_dir}</i>", italic_style))
    
    # Page 2 Break
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 3: SECTION 3 (EOL WISHES) & SECTION 4 (DHR NOMINATION & PRIMARY DHR)
    # -------------------------------------------------------------------------
    story.append(Paragraph("Section 3 (Optional): Wishes or desires during end-of-life care", h1_style))
    story.append(Paragraph("Below are my specific guidelines regarding personal preferences during palliative and end-of-life care:", body_style))
    story.append(Spacer(1, 3))

    s3_data = []
    goals_care = safe_display(getattr(preferences, "goals_of_care", None))
    if goals_care != "Not provided":
        s3_data.append([Paragraph("Goals of Care", table_cell_bold), Paragraph(goals_care, table_cell_style)])
    # 1. Place of care
    place_care = safe_display(preferences.preferred_place_of_care)
    hosp_care = safe_display(preferences.preferred_hospital)
    if place_care != "Not provided" or hosp_care != "Not provided":
        s3_data.append([
            Paragraph("Preferred Place of Care", table_cell_bold),
            Paragraph(f"Preferred setting: <b>{place_care}</b> (Preferred facility / institution: {hosp_care})", table_cell_style)
        ])
    else:
        s3_data.append([Paragraph("Preferred Place of Care", table_cell_bold), Paragraph("Not provided", table_cell_style)])

    # 2. Treating physician
    phys_name = safe_display(preferences.preferred_physician_name)
    phys_desig = safe_display(preferences.preferred_physician_designation)
    phys_inst = safe_display(preferences.preferred_physician_institution)
    if phys_name != "Not provided":
        desig_part = f" ({phys_desig})" if phys_desig != "Not provided" else ""
        inst_part = f", {phys_inst}" if phys_inst != "Not provided" else ""
        s3_data.append([
            Paragraph("Preferred Treating Physician", table_cell_bold),
            Paragraph(f"{phys_name}{desig_part}{inst_part} (Subject to availability & feasibility)", table_cell_style)
        ])
    else:
        s3_data.append([Paragraph("Preferred Treating Physician", table_cell_bold), Paragraph("Not provided / To be determined by attending facility", table_cell_style)])

    # 3. Special focus
    s3_data.append([Paragraph("Special Focus / Care Priority", table_cell_bold), Paragraph(safe_display(preferences.special_focus_priority), table_cell_style)])

    # 4. Additional wishes
    s3_data.append([Paragraph("Additional Wishes", table_cell_bold), Paragraph(safe_display(preferences.additional_wishes), table_cell_style)])

    t_s3 = Table(s3_data, colWidths=[150.0, 337.27])
    t_s3.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_s3)
    story.append(Spacer(1, 8))

    # SECTION 4: Authorisation of the Designated Healthcare Representative (DHR)
    dhr_count = len(dhrs)
    dhr_count_words = count_to_words(dhr_count)
    story.append(Paragraph("Section 4: Authorisation of Designated Healthcare Representative(s) (DHR)", h1_style))
    story.append(Paragraph(
        f"In order to ensure that my wishes here are the primary basis for taking any treatment decisions, "
        f"and to make decisions on my behalf for my medical treatment as may be needed from time to time, "
        f"I have nominated <b>{dhr_count_words} ({dhr_count})</b> designated healthcare representative(s) (DHR) "
        f"in the stated order of preference below.",
        body_style
    ))
    story.append(Paragraph(
        "I have had extensive discussions with those named regarding my wishes, their responsibilities, and the "
        "situations which they may be expected to take decisions in. They have expressed that they are willing to be "
        "nominated as my designated healthcare representative(s).",
        body_style
    ))
    story.append(Paragraph(
        "<b>I authorise my DHR(s) to exercise the following powers:</b><br/>"
        "• They can obtain medical information from the treating team regarding my treatment, my health records, and communications with the treating team;<br/>"
        "• They can take decisions and act on my behalf regarding my wishes in this document as necessary, including providing consent, refusing, or withdrawing consent to any care, treatment, service, or procedure, guided primarily by my wishes as expressed in this directive.<br/>"
        "<i>The decisions taken by my DHRs should be respected regardless of any contrary views that any other person may hold.</i>",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Primary DHR
    primary_dhr = next((d for d in dhrs if getattr(d, 'preference_order', 1) == 1), dhrs[0] if dhrs else None)
    story.append(Paragraph("<b>I authorise the following person as my primary DHR:</b>", h2_style))
    
    if primary_dhr:
        p_dob = primary_dhr.date_of_birth.strftime('%d/%m/%Y') if getattr(primary_dhr, 'date_of_birth', None) else "Not provided"
        p_gov_type = safe_display(primary_dhr.government_id_type)
        p_gov_num = safe_display(primary_dhr.government_id_number)
        p_gov_str = f"1. Document Name: {p_gov_type} | 2. ID No.: {p_gov_num}" if (p_gov_type != "Not provided" or p_gov_num != "Not provided") else "Not provided"
        p_mob_pri = safe_display(primary_dhr.mobile_primary)
        p_mob_sec = safe_display(primary_dhr.mobile_secondary)
        p_mob_str = f"1. Primary: {p_mob_pri} | 2. Any other: {p_mob_sec}"
        p_email_pri = safe_display(primary_dhr.email_primary)
        p_email_sec = safe_display(primary_dhr.email_secondary)
        p_email_str = f"1. Primary: {p_email_pri} | 2. Any other: {p_email_sec}"

        primary_dhr_data = [
            [Paragraph("Full Name", table_cell_bold), Paragraph(safe_display(primary_dhr.full_name), table_cell_style)],
            [Paragraph("Relationship with Executor", table_cell_bold), Paragraph(safe_display(primary_dhr.relationship), table_cell_style)],
            [Paragraph("Date of Birth", table_cell_bold), Paragraph(p_dob, table_cell_style)],
            [Paragraph("Government ID", table_cell_bold), Paragraph(p_gov_str, table_cell_style)],
            [Paragraph("Mobile Number(s)", table_cell_bold), Paragraph(p_mob_str, table_cell_style)],
            [Paragraph("Email ID(s)", table_cell_bold), Paragraph(p_email_str, table_cell_style)],
            [Paragraph("Permanent Residential Address", table_cell_bold), Paragraph(safe_display(primary_dhr.permanent_address), table_cell_style)],
            [Paragraph("Residential Address on Date of Signing", table_cell_bold), Paragraph(safe_display(primary_dhr.signing_address or primary_dhr.permanent_address), table_cell_style)]
        ]
        t_pri = Table(primary_dhr_data, colWidths=[150.0, 337.27])
        t_pri.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t_pri)
    else:
        story.append(Paragraph("<i>No primary designated healthcare representative details were provided.</i>", italic_style))

    # Page 3 Break
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 4: SECONDARY/ALTERNATE DHR, SECTION 5 (DEATH DIRECTIONS) & LEGAL DECLARATIONS
    # -------------------------------------------------------------------------
    # Alternate DHR Section (Populated only when actually provided)
    alternate_appointed = getattr(preferences, 'alternate_dhr_appointed', None)
    alternate_dhrs = [d for d in dhrs if getattr(d, 'preference_order', 1) > 1]
    if alternate_appointed is False:
        alternate_dhrs = []
    
    story.append(Paragraph("Alternate Designated Healthcare Representative(s)", h2_style))
    story.append(Paragraph(
        "<i>If my primary DHR is not available, or unable or unwilling to take a decision, "
        "then I authorise the following person(s) to act as my designated healthcare representative(s) "
        "in the stated order of preference:</i>",
        italic_style
    ))
    story.append(Spacer(1, 3))

    if alternate_dhrs:
        for idx, alt_dhr in enumerate(alternate_dhrs, start=1):
            rank_label = f"Alternate DHR #{idx} (Preference Order Rank: {getattr(alt_dhr, 'preference_order', idx + 1)})"
            story.append(Paragraph(f"<b>{rank_label}:</b>", body_bold))
            story.append(Spacer(1, 2))

            a_dob = alt_dhr.date_of_birth.strftime('%d/%m/%Y') if getattr(alt_dhr, 'date_of_birth', None) else "Not provided"
            a_gov_type = safe_display(alt_dhr.government_id_type)
            a_gov_num = safe_display(alt_dhr.government_id_number)
            a_gov_str = f"1. Document Name: {a_gov_type} | 2. ID No.: {a_gov_num}" if (a_gov_type != "Not provided" or a_gov_num != "Not provided") else "Not provided"
            a_mob_pri = safe_display(alt_dhr.mobile_primary)
            a_mob_sec = safe_display(alt_dhr.mobile_secondary)
            a_mob_str = f"1. Primary: {a_mob_pri} | 2. Any other: {a_mob_sec}"
            a_email_pri = safe_display(alt_dhr.email_primary)
            a_email_sec = safe_display(alt_dhr.email_secondary)
            a_email_str = f"1. Primary: {a_email_pri} | 2. Any other: {a_email_sec}"

            alt_dhr_data = [
                [Paragraph("Full Name", table_cell_bold), Paragraph(safe_display(alt_dhr.full_name), table_cell_style)],
                [Paragraph("Relationship with Executor", table_cell_bold), Paragraph(safe_display(alt_dhr.relationship), table_cell_style)],
                [Paragraph("Date of Birth", table_cell_bold), Paragraph(a_dob, table_cell_style)],
                [Paragraph("Government ID", table_cell_bold), Paragraph(a_gov_str, table_cell_style)],
                [Paragraph("Mobile Number(s)", table_cell_bold), Paragraph(a_mob_str, table_cell_style)],
                [Paragraph("Email ID(s)", table_cell_bold), Paragraph(a_email_str, table_cell_style)],
                [Paragraph("Permanent Residential Address", table_cell_bold), Paragraph(safe_display(alt_dhr.permanent_address), table_cell_style)],
                [Paragraph("Residential Address on Date of Signing", table_cell_bold), Paragraph(safe_display(alt_dhr.signing_address or alt_dhr.permanent_address), table_cell_style)]
            ]
            t_alt = Table(alt_dhr_data, colWidths=[150.0, 337.27])
            t_alt.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(t_alt)
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph(
            "<b>No secondary or alternate designated healthcare representative has been appointed by the executor at this time.</b> "
            "<i>Should the primary designated representative be unavailable, unwilling, or unable to act, clinical decisions shall be governed by the instructions set forth in this directive and applicable medical protocols.</i>",
            italic_style
        ))
        story.append(Spacer(1, 6))

    # SECTION 5: Directions to be followed upon my death
    story.append(Paragraph("Section 5 (Optional): Directions to be followed upon my death", h1_style))
    
    organ_str = safe_display(preferences.organ_donation)
    body_str = safe_display(preferences.body_donation)
    
    organ_expl = "Registered donor / desires donation under the Transplantation of Human Organs and Tissues Act, 1994 (Form 7)." if organ_str == "YES" else ("Directs that organs not be donated upon death." if organ_str == "NO" else "Not specified")
    body_expl = "Desires cadaver / body donation for medical education and research." if body_str == "YES" else ("Directs that body not be donated for medical research." if body_str == "NO" else "Not specified")
    last_rites_str = safe_display(preferences.last_rites)

    s5_data = [
        [Paragraph("Organ Donation", table_cell_bold), Paragraph(f"<b>{organ_str}</b> — {organ_expl}", table_cell_style)],
        [Paragraph("Body / Cadaver Donation", table_cell_bold), Paragraph(f"<b>{body_str}</b> — {body_expl}", table_cell_style)],
        [Paragraph("Last Rites / Funeral", table_cell_bold), Paragraph(last_rites_str, table_cell_style)]
    ]
    t_s5 = Table(s5_data, colWidths=[150.0, 337.27])
    t_s5.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_s5)
    story.append(Spacer(1, 6))

    # SECTION 6 / ADMINISTRATIVE & LEGAL DECLARATION
    story.append(Paragraph("Declaration & Legal Framework", h1_style))
    story.append(Paragraph(
        "I declare that at the time of signing and executing this document:<br/>"
        "• This document has been drafted as per my directions, and its contents have been read out and explained to me;<br/>"
        "• I have the mental capacity and competence to understand the meaning and implications of everything mentioned in this document;<br/>"
        "• I have given careful thought and consideration to everything mentioned in this document;<br/>"
        "• I have willingly and voluntarily articulated and consented to everything mentioned in this document, without any coercion, duress, or undue influence from any person or entity.",
        body_style
    ))
    
    # Forwarding & Order alignment
    story.append(Paragraph(
        "<b>Supreme Court Alignment & Custody Distribution:</b><br/>"
        "This directive is executed in accordance with the order dated January 24, 2023, of the Hon’ble Supreme Court of India in MA No. 1699/ 2019 in WP (C) No. 215/ 2005 (SC Order). Further, copies of this executed directive shall be forwarded to and retained by:<br/>"
        f"• Designated healthcare representative(s) (DHRs) named in this directive ({'Confirmed' if preferences.forward_to_dhrs else 'To be furnished upon execution'});<br/>"
        f"• Treating physician / chosen healthcare facility ({'Confirmed' if preferences.forward_to_physician else 'To be furnished upon execution'});<br/>"
        f"• The Competent Officer / Custodian of the local government body (Panchayat, Municipality, or Municipal Corporation) ({'Confirmed' if preferences.forward_to_custodian else 'To be furnished upon execution'}).",
        body_style
    ))
    
    # Validity & Modification
    story.append(Paragraph(
        "<b>Validity, Modification & Revocation:</b><br/>"
        "I declare that this directive, and my authorisations for DHRs, shall be valid and remain in force throughout my lifetime, unless I modify or revoke them. "
        "I reserve the right at any time to execute a revised version of this document or revoke it in its entirety. I shall ensure copies of any revised directive or revocation are shared with the DHRs, treating physicians, and municipal custodians named above.",
        body_style
    ))

    # Legal Review Disclaimer (Proposing suitable wording for guide / legal counsel review)
    story.append(Paragraph(
        "<i>[Drafting & Review Note: This Advance Medical Directive has been generated using the model template formulated by the Vidhi Centre for Legal Policy pursuant to the Hon'ble Supreme Court of India's guidelines. It is presented for review by the project guide or a qualified legal professional prior to formal execution and notarisation. The system assists in document drafting and does not constitute statutory legal representation.]</i>",
        disclaimer_style
    ))

    # Page 4 Break
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # PAGE 5: SIGNATURES OF EXECUTOR, WITNESSES, AND NOTARISATION
    # -------------------------------------------------------------------------
    sig_block = []
    sig_block.append(Paragraph("Execution, Witness Attestations & Notarisation", h1_style))
    sig_block.append(Paragraph(
        "<b>Notice to Signatories:</b> Pre-filled details reflect patient identity and witness records captured in the Advance Care Planning System. Official signatures, thumb impressions, dates, places, and notarial stamps must be affixed in physical presence as required by law.",
        disclaimer_style
    ))
    sig_block.append(Spacer(1, 4))

    # Executor Signature Panel
    sig_block.append(Paragraph("<b>1. Signature of the Executor (Declarant / Patient):</b>", h2_style))
    exec_place_str = safe_display(executor_place, fallback="____________________________________", blank_line=True)
    exec_table_data = [
        [Paragraph("Full Name of Executor", table_cell_bold), Paragraph(f"<b>{patient_name}</b>", table_cell_style)],
        [
            Paragraph("Signature or Thumb Impression<br/><font size='7' color='#64748B'>(Sign in wet ink in presence of witnesses & notary)</font>", table_cell_bold),
            Paragraph("<br/><br/>____________________________________________________<br/>[Full Signature / Thumb Impression]", table_cell_style)
        ],
        [Paragraph("Date of Signing", table_cell_bold), Paragraph("Date: ______ / ______ / 20______", table_cell_style)],
        [Paragraph("Place of Signing", table_cell_bold), Paragraph(exec_place_str, table_cell_style)]
    ]
    t_exec = Table(exec_table_data, colWidths=[160.0, 327.27])
    t_exec.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    sig_block.append(t_exec)
    sig_block.append(Spacer(1, 6))

    # Signature of Witnesses Panel
    sig_block.append(Paragraph("<b>2. Attestation & Signatures of Witnesses:</b>", h2_style))
    sig_block.append(Paragraph(
        "<i>We, as independent witnesses, hereby record our satisfaction that this Advance Medical Directive has been executed voluntarily by the Declarant in our presence, without any coercion, duress, inducement, or compulsion.</i>",
        italic_style
    ))
    sig_block.append(Spacer(1, 3))

    wit_list = witnesses if (witnesses and isinstance(witnesses, list)) else []
    for w_idx in (1, 2):
        wit_item = wit_list[w_idx - 1] if len(wit_list) >= w_idx else {}
        w_name = safe_display(wit_item.get('name'), fallback="____________________________________", blank_line=True)
        w_email = safe_display(wit_item.get('email'), fallback="____________________________________", blank_line=True)
        w_mobile = safe_display(wit_item.get('mobile'), fallback="____________________________________", blank_line=True)
        w_addr = safe_display(wit_item.get('address'), fallback="____________________________________", blank_line=True)
        w_govid = safe_display(wit_item.get('government_id'), fallback="____________________________________", blank_line=True)

        w_table_data = [
            [
                Paragraph(f"<b>Witness #{w_idx} Particulars</b>", table_cell_bold),
                Paragraph(f"Name: <b>{w_name}</b><br/>Address: {w_addr}<br/>Govt ID: {w_govid}<br/>Mobile: {w_mobile} | Email: {w_email}", table_cell_style),
                Paragraph(f"<b>Witness #{w_idx} Signature:</b><br/><br/>_________________________________<br/>Date: ____/____/20____<br/>Place: ________________________", table_cell_style)
            ]
        ]
        t_w = Table(w_table_data, colWidths=[110.0, 237.27, 140.0])
        t_w.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        sig_block.append(t_w)
        sig_block.append(Spacer(1, 4))

    # Notarisation Block
    sig_block.append(Paragraph("<b>3. Notarisation / Judicial Attestation:</b>", h2_style))
    sig_block.append(Paragraph(
        f"This directive and authorisation of designated healthcare representative(s) has been signed in the presence of the undersigned by "
        f"<b>{patient_name}</b> (Declarant / Executor), and I record my satisfaction that the document has been executed voluntarily and without any coercion, inducement, or compulsion.",
        body_style
    ))
    sig_block.append(Spacer(1, 2))

    notary_name_str = safe_display(notary_name, fallback="____________________________________", blank_line=True)
    notary_place_str = safe_display(notary_place, fallback="____________________________________", blank_line=True)

    notary_data = [
        [
            Paragraph("<b>SIGNED BEFORE ME</b>", body_bold),
            Paragraph("<b>OFFICIAL NOTARIAL STAMP & SEAL</b>", body_bold)
        ],
        [
            Paragraph(
                "<br/>____________________________________________________<br/>"
                "(Signature of Notary Public / Judicial Magistrate First Class)<br/><br/>"
                f"Full Name of Notary: <b>{notary_name_str}</b><br/>"
                "Registration / Enrolment No.: ________________________<br/>"
                f"Date: <b>{datetime.now().strftime('%d/%m/%Y')}</b><br/>"
                f"Place: <b>{notary_place_str}</b>",
                table_cell_style
            ),
            Paragraph(
                "<br/><br/><br/><br/>"
                "____________________________________________________<br/>"
                "<font size='7' color='#64748B'>[Affix Official Stamp, Seal, and Notarial Register Serial Number here]</font>",
                table_cell_style
            )
        ]
    ]
    t_notary = Table(notary_data, colWidths=[243.6, 243.67])
    t_notary.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    sig_block.append(t_notary)

    # Keep all of Page 5 together
    story.append(KeepTogether(sig_block))

    # Build document with custom canvas
    doc.build(story, canvasmaker=NumberedCanvas)
