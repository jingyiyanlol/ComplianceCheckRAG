# ComplianceCheckRAG Test Prompts

Test prompts for the web application based on **Guidelines to MAS Notice 626 – Prevention of Money Laundering and Countering the Financing of Terrorism**. Each prompt includes expected answers grounded in the ingested document.

---

## Tier 1: Simple Factual Retrieval

### Prompt 1.1 – Money Laundering Definition
**Query:** "What are the three stages of money laundering?"

**Expected Answer (Key Points):**
- Placement: Physical or financial disposal of benefits derived from criminal conduct
- Layering: Separation of benefits from their original source by creating layers of financial transactions to disguise the ultimate source
- Integration: Provision of apparent legitimacy to the benefits so they re-enter the financial system appearing to be legitimate

**Category:** Definition | **Difficulty:** Easy | **Expected Retrieval:** Introduction section

---

### Prompt 1.2 – Terrorism Financing
**Query:** "What does terrorism financing mean?"

**Expected Answer (Key Points):**
- Terrorism financing is the act of providing funds to carry out acts of terrorism
- Funds may derive from criminal activities (robbery, drug-trafficking, kidnapping, extortion, fraud) or legitimate sources (donations, legitimate business, self-funding)
- Unlike money laundering, terrorism financing may involve small amounts and be hard to detect
- Singapore's primary legislation is the Terrorism (Suppression of Financing) Act 2002

**Category:** Definition | **Difficulty:** Easy | **Expected Retrieval:** Introduction section

---

### Prompt 1.3 – Proliferation Financing
**Query:** "Define proliferation financing as per the guidelines."

**Expected Answer (Key Points):**
- Refers to the raising, moving, or making available of funds or other economic resources
- Used to finance the proliferation of weapons of mass destruction, including their means of delivery
- Includes financing dual-use technology and dual-use goods for non-legitimate purposes
- Governed by FSM Sanctions Regulations

**Category:** Definition | **Difficulty:** Easy | **Expected Retrieval:** Introduction section

---

### Prompt 1.4 – Three Lines of Defence
**Query:** "Describe the three lines of defence in AML/CFT."

**Expected Answer (Key Points):**
- **First line:** Business units (front office, customer-facing) identify, assess, and control ML/TF risks
- **Second line:** AML/CFT compliance function and support functions (operations, HR, technology) monitor bank's fulfillment of AML/CFT duties
- **Third line:** Internal audit function independently evaluates AML/CFT risk management framework and controls
- **Board accountability:** Ultimate responsibility rests with board of directors and senior management

**Category:** Governance | **Difficulty:** Easy | **Expected Retrieval:** Introduction section

---

### Prompt 1.5 – CDD Measures
**Query:** "What does CDD stand for and what does it involve?"

**Expected Answer (Key Points):**
- CDD = Customer Due Diligence
- Required before establishing business relations with a customer
- Includes identifying and verifying customer identity
- Understanding purpose and intended nature of business relations
- Identifying beneficial owners
- Ongoing monitoring of customer accounts

**Category:** Customer Due Diligence | **Difficulty:** Easy | **Expected Retrieval:** CDD section

---

## Tier 2: Moderate Complexity – Understanding and Application

### Prompt 2.1 – When CDD is Required
**Query:** "When must a bank perform Customer Due Diligence?"

**Expected Answer (Key Points):**
- When establishing business relations with a customer
- When undertaking transactions for customers not yet in a business relationship
- When there is suspicion of ML/TF or doubts about information veracity
- When linked/related transactions exceed specified thresholds
- When there are material changes in customer profile or risk assessment

**Category:** CDD Requirements | **Difficulty:** Moderate | **Expected Retrieval:** CDD section (6-1 to 6-2A)

---

### Prompt 2.2 – Beneficial Owner Identification
**Query:** "What is the threshold for identifying beneficial owners of a legal person?"

**Expected Answer (Key Points):**
- Must identify natural persons owning more than 25% of the legal person
- Must account for aggregated ownership in companies with cross-shareholdings
- Must identify persons controlling the entity through significant influence (even if below 25%)
- For publicly listed companies on regulated stock exchanges: exemption from identifying beneficial owners if subject to disclosure requirements
- For majority-owned subsidiaries: identify beneficial owners of non-listed entities owning >25%

**Category:** CDD Requirements | **Difficulty:** Moderate | **Expected Retrieval:** CDD section (6-8)

---

### Prompt 2.3 – Non-Face-to-Face Verification
**Query:** "What additional checks should a bank apply for identity verification in non-face-to-face transactions?"

**Expected Answer (Key Points):**
- Robust anti-fraud checks to manage impersonation risk
- Telephone contact at independently verifiable residential or business number
- Confirmation of address through correspondence exchange
- Telephone confirmation of employment status with employer's HR
- Confirmation of salary details via statements from another bank
- Certified identification documents from lawyers or notaries
- Initial deposit from customer's account at another Singapore bank

**Category:** CDD Procedures | **Difficulty:** Moderate | **Expected Retrieval:** CDD Non-Face-to-Face section (6-11)

---

### Prompt 2.4 – Risk-Based Approach to Connected Parties
**Query:** "Can a bank verify connected parties using a risk-based approach?"

**Expected Answer (Key Points):**
- Yes, banks must identify all connected parties but may verify identities using risk-based approach
- Banks remain responsible for staying apprised of changes to connected parties
- Identification can use publicly available sources (registries, annual reports) or substantiated customer information
- For legal arrangements, must perform CDD on trust relevant parties

**Category:** CDD Requirements | **Difficulty:** Moderate | **Expected Retrieval:** CDD Legal Persons section (6-5)

---

### Prompt 2.5 – Ongoing Monitoring and Risk Profile Updates
**Query:** "How frequently should a bank update CDD information for different customer risk categories?"

**Expected Answer (Key Points):**
- **High-risk customers:** Obtain updated CDD on periodic basis (e.g., annually) or upon trigger events, whichever is earlier
- **Other customers:** Update upon occurrence of trigger events only
- **Trigger events include:** Significant transactions, material changes to account operation, policy changes, lack of sufficient information
- For COSMIC participants: Must update if informed through COSMIC that information is insufficient or outdated

**Category:** Ongoing Monitoring | **Difficulty:** Moderate | **Expected Retrieval:** Ongoing Monitoring section (6-10)

---

## Tier 3: Complex Understanding – Integration and Analysis

### Prompt 3.1 – Enterprise-Wide Risk Assessment
**Query:** "What factors must a bank consider in its enterprise-wide ML/TF risk assessment?"

**Expected Answer (Key Points):**
- **Customer factors:** Target segments, profile of high-risk customers, transaction volumes/sizes
- **Geographic factors:** Countries/jurisdictions of operations, corruption levels, AML/CFT compliance, FATF reports
- **Product/service factors:** Nature and complexity of business activities, products/services offered, delivery channels
- **Qualitative and quantitative analysis:** Should include both types
- **Review frequency:** At least once every two years or upon material trigger events
- Must be approved by senior management

**Category:** Risk Management | **Difficulty:** Complex | **Expected Retrieval:** Risk Assessment section (4-3 to 4-10)

---

### Prompt 3.2 – Suspicious Transaction Indicators
**Query:** "What are examples of suspicious transactions that a bank should monitor?"

**Expected Answer (Key Points):**
- Frequent and cumulatively large transactions without apparent or visible economic purpose
- Structured transactions: Multiple small transactions designed to avoid reporting thresholds
- Frequent transfers to same recipient over short period
- Multiple cash deposits not individually large but cumulatively substantial
- Transaction patterns inconsistent with customer's stated purpose or risk profile
- Transactions with parties in high-risk countries
- Payments to/from persons on sanctions lists
- Unusual size or frequency for customer or peer group

**Category:** Transaction Monitoring | **Difficulty:** Complex | **Expected Retrieval:** Ongoing Monitoring section (6-10)

---

### Prompt 3.3 – Managing Non-Face-to-Face Risks
**Query:** "What risks are specific to non-face-to-face business relations and how should banks address them?"

**Expected Answer (Key Points):**
- **Risks:** Ease of unauthorized access, multiple fictitious applications, absence of physical documents, speed of transactions
- **Mitigation:** Apply additional checks to manage impersonation risk
- **Specific measures:** Anti-fraud checks, telephone verification, address confirmation, employment/salary verification
- **Risk profile adjustment:** Verification measures depend on product/service characteristics and customer risk profile
- Internet transactions pose greater risks than other non-face-to-face channels

**Category:** Risk Mitigation | **Difficulty:** Complex | **Expected Retrieval:** Non-Face-to-Face section (6-11)

---

### Prompt 3.4 – Document Verification Standards
**Query:** "What documents should a bank use to verify customer identity and what quality standards apply?"

**Expected Answer (Key Points):**
- **Best documents:** Most difficult to obtain illicitly or counterfeit
- **Natural persons:** Government-issued ID/passport, national identity card with photograph
- **Legal persons:** Certificate of incorporation, good standing, partnership agreement, trust deed
- **Quality standards:** Clear and legible documents, current at time of provision
- **Foreign documents:** Must be translated to English by qualified translator
- **Rigor level:** Should be commensurate with customer risk profile

**Category:** CDD Documentation | **Difficulty:** Complex | **Expected Retrieval:** CDD Verification section (6-3 to 6-6)

---

### Prompt 3.5 – Fraud and Document Tampering
**Query:** "What are indicators of fraudulent or tampered documentation and how should banks respond?"

**Expected Answer (Key Points):**
- **Indicators:** Significant discrepancies in customer representations, anomalies in financial statements, lack of sign-off by certifying parties
- **Red flags:** Information that doesn't align with independent sources (e.g., corporate data reports)
- **Bank response:** Escalate indicators through established processes
- **Follow-up actions:** Apply appropriate ML/TF risk mitigation measures in timely manner
- **Staff training:** Banks should provide adequate guidance on fraud indicators

**Category:** AML/CFT Controls | **Difficulty:** Complex | **Expected Retrieval:** Reliability section (6-6-5A)

---

## Tier 4: Multi-Turn Conversations

### Conversation 4.1 – Enterprise Risk and Compliance

**Turn 1 - User:**
"What is an enterprise-wide ML/TF risk assessment and why is it important?"

**Expected Answer:**
- Assessment of ML/TF risks across all business units, product lines, and delivery channels
- Consolidated view of bank's ML/TF vulnerability
- Forms basis for risk-based approach
- Must be approved by senior management
- Must be reviewed at least every 2 years or on trigger events

**Turn 2 - User:**
"Who is responsible for overseeing this assessment and what should they consider?"

**Expected Answer:**
- Senior management and board of directors have ultimate responsibility
- Must consider customer factors (segments, volumes), geographic factors (country risks, FATF reports), product factors (complexity, delivery channels)
- Should incorporate Singapore's national risk assessment reports
- Must balance qualitative and quantitative analysis
- Results should guide allocation of AML/CFT resources

**Turn 3 - User:**
"What are the consequences if the assessment is inadequate?"

**Expected Answer:**
- Board and senior management must ensure adequate risk-mitigating measures
- MAS may adjust overall risk assessment of bank
- May impact assessment of board oversight, governance, internal controls
- Bank must put in place adequate policies, procedures, controls commensurate with identified risks
- Failure could lead to regulatory action

---

### Conversation 4.2 – Customer CDD and Ongoing Monitoring

**Turn 1 - User:**
"What information must a bank collect to establish a customer's identity?"

**Expected Answer:**
- For natural persons: Name, unique ID, date of birth, nationality (from passport/ID), residential address (from utility bill, bank statement, government correspondence)
- For legal persons: Legal form, proof of existence, certificate of incorporation, powers that regulate/bind entity
- Contact details (phone numbers)
- Additional background (occupation, employer, income, related accounts)
- Documentation must contain clear photograph for natural persons

**Turn 2 - User:**
"How does the bank stay updated on this information over time?"

**Expected Answer:**
- High-risk customers: Annual or periodic CDD review
- Other customers: Update upon trigger events
- Trigger events: Significant transactions, material changes in account operation, policy changes, insufficient/outdated information
- Must maintain relevant and up-to-date CDD data to identify changes in risk profile
- For COSMIC participants: Must update if new information received through COSMIC

**Turn 3 - User:**
"What should the bank do if it discovers discrepancies in the customer's background information?"

**Expected Answer:**
- Conduct further enquiries
- Implement commensurate risk mitigation measures
- Consider enhanced ongoing monitoring
- Perform pre-transaction checks
- May impose account restrictions
- Request additional information
- Conduct review of customer risk profile
- Determine if further CDD measures necessary

---

### Conversation 4.3 – Transaction Monitoring and Suspicious Activity

**Turn 1 - User:**
"How should a bank monitor customer transactions for potential ML/TF risks?"

**Expected Answer:**
- Ongoing monitoring of all business relations (depth/extent adjusted by risk profile)
- Monitor for suspicious, complex, unusually large, or unusual pattern transactions
- Monitor multiple accounts of customer holistically within and across business units
- Perform trend analyses to identify unusual transactions
- Monitor transactions with parties in high-risk countries
- Maintain parameters and thresholds properly documented and independently validated

**Turn 2 - User:**
"What specific transaction patterns should raise concerns?"

**Expected Answer:**
- Transactions without apparent/visible economic or lawful purpose
- Structured transactions (multiple small to avoid thresholds)
- Frequent transfers to same recipient over short period
- Multiple cash deposits cumulatively large
- Abnormal size or frequency for that customer
- Payments to/from persons on sanctions lists
- Geographic indicators (high-risk destinations/origins)

**Turn 3 - User:**
"If suspicious activity is detected in one business unit, what should happen?"

**Expected Answer:**
- Information should be shared across business units immediately
- Banks must have processes and safeguards to share customer info across units
- Sharing should include minimal CDD information and source of wealth data
- Holistic assessment of risk across customer groups
- Shared information enables better identification of potential ML/TF risks
- Facilitates reporting of suspicious transactions

---

## Tier 5: Edge Cases and Clarification Scenarios

### Prompt 5.1 – Portfolio Manager Beneficial Owners
**Query:** "If a customer is a portfolio manager with multiple underlying investors, does the bank need to perform CDD on all investors?"

**Expected Answer:**
- The underlying investors would technically be beneficial owners
- However, authority recognizes bank may not be able to perform CDD on all due to commercial confidentiality
- Bank should evaluate risks in each case and determine appropriate measures
- Bank may consider applying simplified CDD to underlying investors if criteria met
- Exception: If customer falls within paragraph 6.16 (certain regulated entities), bank is exempted from inquiring about underlying investors

**Category:** CDD Special Cases | **Difficulty:** Edge case | **Notes:** Tests nuanced understanding of beneficial owner rules

---

### Prompt 5.2 – Overseas Customer Account Management
**Query:** "Our Singapore branch manages accounts with a customer, but the account is booked with our overseas branch. Do we need to perform CDD?"

**Expected Answer:**
- Yes, if the relationship is managed in substance by Singapore staff
- MAS looks at substance of relationship management as a whole
- Even if account is booked overseas for bookkeeping, CDD is required if managed from Singapore
- Alternative: May rely on CDD performed by related entity or other branch if adequate
- The key is the substance of relationship management, not the technical booking location

**Category:** CDD Jurisdictional | **Difficulty:** Edge case | **Notes:** Tests understanding of practical CDD application

---

### Prompt 5.3 – Credit Card Customer Classification
**Query:** "Who is considered the 'customer' for CDD purposes when a bank issues corporate credit cards?"

**Expected Answer:**
- Principal cardholder
- Supplementary cardholders
- Employees to whom business cards are issued
- Sole proprietor or partnership liable for business card
- Employees/officers of body corporate to whom corporate card issued AND the body corporate itself
- Guarantor of guaranteed credit cards
- Merchant for whom bank opens/maintains account for goods/services purchase

**Category:** CDD Customer Scope | **Difficulty:** Edge case | **Notes:** Tests detailed understanding of customer definitions

---

### Prompt 5.4 – Verification with Copies Only
**Query:** "What should a bank do if a customer cannot provide original identity documents?"

**Expected Answer:**
- May accept certified copy from suitably qualified person (notary, lawyer, certified accountant)
- OR accept copy if independent bank staff has sighted original document
- Must record information the original document verified
- Must describe original document, including unique features/condition
- Must record reasons why copy couldn't be made
- Must document name of employee who verified and certification statement

**Category:** CDD Documentation | **Difficulty:** Edge case | **Notes:** Tests procedural knowledge for exceptional circumstances

---

## Tier 6: Negative Cases and "What NOT to Do"

### Prompt 6.1 – Insufficient CDD
**Query:** "A customer who is a publicly listed company on a regulated stock exchange is exempted from beneficial owner verification. Does this mean no further ML/TF risk analysis is needed?"

**Expected Answer (What NOT to do):**
- **Incorrect:** Assuming the exemption from beneficial owner verification equals automatic low-risk determination
- **Correct:** The exemption does NOT constitute adequate analysis of low ML/TF risks for applying simplified CDD
- **What to do instead:** Still perform full CDD and risk assessment; exemption is narrow and applies only to beneficial owner identification

**Category:** Common Misconceptions | **Difficulty:** Moderate

---

### Prompt 6.2 – Minimal Ongoing Monitoring
**Query:** "Our bank performs CDD once when a customer opens an account. Is that sufficient?"

**Expected Answer (What NOT to do):**
- **Incorrect:** One-time CDD with no ongoing monitoring
- **Correct:** Ongoing monitoring is fundamental to effective AML/CFT management
- **Requirements:** Continuous monitoring adjusted by risk profile, periodic CDD reviews (annual for high-risk), trigger event updates
- **Consequences:** Failure to maintain current CDD data prevents identification of risk profile changes

**Category:** Common Misconceptions | **Difficulty:** Easy

---

## Test Scenarios for Web App Manual Testing

### Scenario A: Simple Query with Clear Answer
1. Ask: "What are the three stages of money laundering?"
2. Verify: Response mentions Placement, Layering, Integration with brief explanations
3. Check: Citation shows document and relevant section

### Scenario B: Multi-Document Retrieval (if multiple docs ingested)
1. Ask: "What are the main AML/CFT compliance requirements for banks?"
2. Verify: Response covers multiple aspects from the guidelines
3. Check: Proper citations showing where information comes from

### Scenario C: Multi-Turn Conversation
1. Turn 1: "What is CDD?"
2. Turn 2: Follow-up: "When must it be performed?"
3. Turn 3: Follow-up: "What specific documents are needed?"
4. Verify: Each response builds on previous context while retrieving relevant information

### Scenario D: Scoped Query (Document-Specific)
1. Set document scope to only the MAS Notice 626 guidelines
2. Ask: "What are the risk factors for enterprise-wide assessment?"
3. Verify: Response stays within document scope
4. Compare with: Global scope result (if multiple docs available)

### Scenario E: PII Handling
1. Ask: "If a customer provides a passport as identification, what information should be captured?"
2. Verify: Response provides relevant info without returning PII itself
3. Check: Any customer names/identifiers in response are properly masked

---

## Performance Metrics to Track

When testing these prompts, monitor:

1. **Retrieval Quality**
   - Are the top-K chunks semantically relevant?
   - Does the retriever distinguish between different CDD requirements vs. other risk management?
   - Multi-turn: Does rewritten query capture conversation context?

2. **Generation Quality**
   - Does response directly answer the question?
   - Are multiple aspects covered for complex questions?
   - Response length appropriate for question complexity?

3. **Citation Accuracy**
   - Do cited sections actually contain the information provided?
   - Sections referenced are accurate?

4. **Edge Case Handling**
   - Nuanced questions answered correctly (not over-simplified)?
   - Negative cases properly qualified?
   - Exceptions explained clearly?

---

## Expected Retrieval and Generation Performance

### High Confidence (Should Get Right)
- Tier 1 prompts: 95%+ success
- Clear factual questions with direct document references

### Medium Confidence (May Need Refinement)
- Tier 2-3 prompts: 80-90% success
- Requires synthesis across multiple sections or understanding of nuance
- May need prompt engineering or reranking improvements

### Lower Confidence (Good for Drift Detection)
- Tier 4 multi-turn: 70-85% success
- Depends on query rewriting quality and multi-turn context handling
- Tier 5-6 edge cases: 60-80% success
- Tests system's ability to handle exceptions and nuance

---

## Suggested Testing Order

1. **Phase 1:** Run all Tier 1 prompts (simple retrieval baseline)
2. **Phase 2:** Run Tier 2 & 3 single-turn prompts (moderate complexity)
3. **Phase 3:** Run multi-turn conversations (Tier 4)
4. **Phase 4:** Edge cases and negative cases (Tier 5-6)
5. **Phase 5:** Manual testing with scenarios A-E

After initial run, use scores to identify:
- Weak sections of document (poor retrieval)
- LLM failure modes (poor generation despite good retrieval)
- Query rewriting issues (multi-turn failures)
- Document ingestion issues (chunking, metadata)
