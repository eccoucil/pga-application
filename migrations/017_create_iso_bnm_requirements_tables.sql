-- Create and populate ISO 27001:2022 and BNM RMIT requirements tables
-- This allows questionnaire generation to work with a unified data source

-- Create ISO 27001:2022 requirements table
CREATE TABLE IF NOT EXISTS iso_requirements (
  id BIGSERIAL PRIMARY KEY,
  identifier TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  clause_type TEXT NOT NULL, -- 'management' or 'domain'
  category_code TEXT, -- for Annex A: 'A.5', 'A.6', etc; for management: '4', '5', etc
  category TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create BNM RMIT requirements table
CREATE TABLE IF NOT EXISTS bnm_rmit_requirements (
  id BIGSERIAL PRIMARY KEY,
  reference_id TEXT NOT NULL UNIQUE,
  section_number INTEGER NOT NULL,
  section_title TEXT NOT NULL,
  subsection_title TEXT,
  requirement_type TEXT, -- 'standard' or 'guidance'
  requirement_text TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_iso_requirements_clause_type ON iso_requirements(clause_type);
CREATE INDEX IF NOT EXISTS idx_iso_requirements_category_code ON iso_requirements(category_code);
CREATE INDEX IF NOT EXISTS idx_bnm_rmit_requirements_section_number ON bnm_rmit_requirements(section_number);

-- Populate ISO 27001:2022 Management Clauses (4.1-10.2)
INSERT INTO iso_requirements (identifier, title, description, clause_type, category_code, category)
VALUES
  -- Clause 4: Context of the Organization
  ('4.1', 'Understanding the organization and its context', 'The organization shall determine external and internal issues that are relevant to its purpose and that affect its ability to achieve the intended outcome(s) of its information security management system.', 'management', '4', 'Context of the Organization'),
  ('4.2', 'Understanding the needs and expectations of interested parties', 'The organization shall determine interested parties that are relevant to the information security management system and their requirements.', 'management', '4', 'Context of the Organization'),
  ('4.3', 'Determining the scope of the information security management system', 'The organization shall determine the boundaries and applicability of the information security management system to establish its scope.', 'management', '4', 'Context of the Organization'),
  ('4.4', 'Information security management system', 'The organization shall establish, implement, maintain and continually improve an information security management system.', 'management', '4', 'Context of the Organization'),

  -- Clause 5: Leadership
  ('5.1', 'Leadership and commitment', 'Top management shall demonstrate leadership and commitment with respect to the information security management system.', 'management', '5', 'Leadership'),
  ('5.2', 'Policy', 'Top management shall establish an information security policy that is appropriate to the purpose of the organization.', 'management', '5', 'Leadership'),
  ('5.3', 'Organizational roles, responsibilities and authorities', 'Top management shall ensure that responsibilities and authorities for the information security management system are assigned and communicated throughout the organization.', 'management', '5', 'Leadership'),

  -- Clause 6: Planning
  ('6.1', 'Actions to address risks and opportunities', 'The organization shall plan actions to address risks and opportunities identified through the risk assessment process.', 'management', '6', 'Planning'),
  ('6.2', 'Information security objectives and planning to achieve them', 'The organization shall establish information security objectives at relevant functions, levels and processes.', 'management', '6', 'Planning'),
  ('6.3', 'Planning of changes', 'The organization shall plan, implement and control changes to information security processes or conditions in a coordinated manner.', 'management', '6', 'Planning'),

  -- Clause 7: Support
  ('7.1', 'Resources', 'The organization shall determine and provide the resources needed for the establishment, implementation, maintenance and continual improvement of the information security management system.', 'management', '7', 'Support'),
  ('7.2', 'Competence', 'The organization shall ensure that persons doing work under the organization''s control are competent on the basis of appropriate education, training, or experience.', 'management', '7', 'Support'),
  ('7.3', 'Awareness', 'The organization shall ensure that persons doing work under the organization''s control are aware of the information security policy and their contribution to the effectiveness of the information security management system.', 'management', '7', 'Support'),
  ('7.4', 'Communication', 'The organization shall establish and implement appropriate processes to communicate information security matters within the organization.', 'management', '7', 'Support'),
  ('7.5', 'Documented information', 'The organization shall establish and maintain documented information needed for the information security management system.', 'management', '7', 'Support'),

  -- Clause 8: Operation
  ('8.1', 'Operational planning and control', 'The organization shall plan, implement and control the processes needed to meet information security requirements.', 'management', '8', 'Operation'),
  ('8.2', 'Information security risk assessment', 'The organization shall conduct information security risk assessments at planned intervals or when significant changes occur.', 'management', '8', 'Operation'),
  ('8.3', 'Information security risk treatment', 'The organization shall select information security risk treatment options and plan risk treatment to implement those options.', 'management', '8', 'Operation'),

  -- Clause 9: Performance Evaluation
  ('9.1', 'Monitoring, measurement, analysis and evaluation', 'The organization shall determine what needs to be monitored and measured, the methods for monitoring, measurement, analysis and evaluation.', 'management', '9', 'Performance Evaluation'),
  ('9.2', 'Internal audit', 'The organization shall conduct internal audits at planned intervals to provide information on whether the information security management system conforms to the organization''s own requirements for information security management.', 'management', '9', 'Performance Evaluation'),
  ('9.3', 'Management review', 'Top management shall review the organization''s information security management system at planned intervals to ensure its continuing suitability, adequacy and effectiveness.', 'management', '9', 'Performance Evaluation'),

  -- Clause 10: Improvement
  ('10.1', 'Nonconformity and corrective action', 'The organization shall respond to nonconformities by taking actions to control and correct them and deal with the consequences.', 'management', '10', 'Improvement'),
  ('10.2', 'Continual improvement', 'The organization shall continually improve the suitability, adequacy and effectiveness of the information security management system.', 'management', '10', 'Improvement')

ON CONFLICT (identifier) DO NOTHING;

-- Populate ISO 27001:2022 Annex A Controls (A.5.1 through A.8.34)
INSERT INTO iso_requirements (identifier, title, description, clause_type, category_code, category)
VALUES
  -- A.5 Organizational Controls (37 controls)
  ('A.5.1', 'Policies for information security', 'Information security policy and topic-specific policies shall be defined, approved by management, published, communicated to and acknowledged by relevant personnel.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.2', 'Information security roles and responsibilities', 'Information security roles and responsibilities shall be defined and allocated according to the organization needs.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.3', 'Segregation of duties', 'Conflicting duties and conflicting areas of responsibility shall be segregated.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.4', 'Management responsibilities', 'Management shall require all personnel to apply information security in accordance with the established information security policy.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.5', 'Contact with authorities', 'The organization shall establish and maintain contact with relevant authorities.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.6', 'Contact with special interest groups', 'The organization shall establish and maintain contact with special interest groups or other specialist security forums.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.7', 'Threat intelligence', 'Information relating to information security threats shall be collected and analysed to produce threat intelligence.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.8', 'Information security in project management', 'Information security shall be integrated into project management.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.9', 'Inventory of information and other associated assets', 'An inventory of information and other associated assets, including owners, shall be developed and maintained.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.10', 'Acceptable use of information and other associated assets', 'Rules for the acceptable use and procedures for handling information and other associated assets shall be identified, documented and implemented.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.11', 'Return of assets', 'Personnel and other interested parties as appropriate shall return all the organization''s assets in their possession upon change or termination of employment.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.12', 'Classification of information', 'Information shall be classified according to the information security needs of the organization.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.13', 'Labelling of information', 'An appropriate set of procedures for information labelling shall be developed and implemented.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.14', 'Information transfer', 'Information transfer rules, procedures, or agreements shall be in place for all types of transfer facilities.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.15', 'Access control', 'Rules to control physical and logical access to information and other associated assets shall be established and implemented.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.16', 'Identity management', 'The full life cycle of identities shall be managed.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.17', 'Authentication information', 'Allocation and management of authentication information shall be controlled by a management process.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.18', 'Access rights', 'Access rights to information and other associated assets shall be provisioned, reviewed, modified and removed in accordance with the organization''s policy.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.19', 'Information security in supplier relationships', 'Processes and procedures shall be defined and implemented to manage the information security risks associated with the use of supplier''s products or services.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.20', 'Addressing information security within supplier agreements', 'Relevant information security requirements shall be established and agreed with each supplier based on the type of supplier relationship.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.21', 'Managing information security in the ICT supply chain', 'Processes and procedures shall be defined and implemented to manage the information security risks associated with the ICT products and services supply chain.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.22', 'Monitoring, review and change management of supplier services', 'The organization shall regularly monitor, review, evaluate and manage change in supplier information security practices and service delivery.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.23', 'Information security for use of cloud services', 'Processes for acquisition, use, management and exit from cloud services shall be established in accordance with the organization''s information security requirements.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.24', 'Information security incident management planning and preparation', 'The organization shall plan and prepare for managing information security incidents by defining, establishing and communicating information security incident management processes.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.25', 'Assessment and decision on information security events', 'The organization shall assess information security events and decide if they are to be categorized as information security incidents.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.26', 'Response to information security incidents', 'Information security incidents shall be responded to in accordance with the documented procedures.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.27', 'Learning from information security incidents', 'Knowledge gained from information security incidents shall be used to strengthen and improve the information security controls.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.28', 'Collection of evidence', 'The organization shall establish and implement procedures for the identification, collection, acquisition and preservation of evidence.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.29', 'Information security during disruption', 'The organization shall plan how to maintain information security at an appropriate level during disruption.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.30', 'ICT readiness for business continuity', 'ICT readiness shall be planned, implemented, maintained and tested based on business continuity objectives.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.31', 'Legal, statutory, regulatory and contractual requirements', 'Legal, statutory, regulatory and contractual requirements relevant to information security shall be identified, documented and kept up to date.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.32', 'Intellectual property rights', 'The organization shall implement appropriate procedures to protect intellectual property rights.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.33', 'Protection of records', 'Records shall be protected from loss, destruction, falsification, unauthorized access and unauthorized release.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.34', 'Privacy and protection of personal identifiable information (PII)', 'The organization shall identify and meet the requirements regarding the preservation of privacy and protection of PII.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.35', 'Independent review of information security', 'The organization''s approach to managing information security shall be reviewed independently at planned intervals.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.36', 'Compliance with policies, rules and standards for information security', 'Compliance with the organization''s information security policy, topic-specific policies, rules and standards shall be regularly reviewed.', 'domain', 'A.5', 'Organizational Controls'),
  ('A.5.37', 'Documented operating procedures', 'Operating procedures for information processing facilities shall be documented and made available to personnel who need them.', 'domain', 'A.5', 'Organizational Controls'),

  -- A.6 People Controls (8 controls)
  ('A.6.1', 'Screening', 'Background verification checks on all candidates to become personnel shall be carried out prior to joining the organization.', 'domain', 'A.6', 'People Controls'),
  ('A.6.2', 'Terms and conditions of employment', 'The employment contractual agreements shall state the personnel''s and the organization''s responsibilities for information security.', 'domain', 'A.6', 'People Controls'),
  ('A.6.3', 'Information security awareness, education and training', 'Personnel of the organization and relevant interested parties shall receive appropriate information security awareness, education and training.', 'domain', 'A.6', 'People Controls'),
  ('A.6.4', 'Disciplinary process', 'A disciplinary process shall be formalized and communicated to take actions against personnel who have committed an information security policy violation.', 'domain', 'A.6', 'People Controls'),
  ('A.6.5', 'Responsibilities after termination or change of employment', 'Information security responsibilities and duties that remain valid after termination or change of employment shall be defined and communicated.', 'domain', 'A.6', 'People Controls'),
  ('A.6.6', 'Confidentiality or non-disclosure agreements', 'Confidentiality or non-disclosure agreements reflecting the organization''s needs for the protection of information shall be identified, documented and signed.', 'domain', 'A.6', 'People Controls'),
  ('A.6.7', 'Remote working', 'Security measures shall be implemented when personnel are working remotely to protect information accessed, processed or stored.', 'domain', 'A.6', 'People Controls'),
  ('A.6.8', 'Information security event reporting', 'The organization shall provide a mechanism for personnel to report observed or suspected information security events.', 'domain', 'A.6', 'People Controls'),

  -- A.7 Physical Controls (14 controls)
  ('A.7.1', 'Physical security perimeters', 'Security perimeters shall be defined and used to protect areas that contain information and other associated assets.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.2', 'Physical entry', 'Secure areas shall be protected by appropriate entry controls and access points.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.3', 'Securing offices, rooms and facilities', 'Physical security for offices, rooms and facilities shall be designed and implemented.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.4', 'Physical security monitoring', 'Premises shall be continuously monitored for unauthorized physical access.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.5', 'Protecting against physical and environmental threats', 'Protection against physical and environmental threats shall be designed and implemented.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.6', 'Working in secure areas', 'Security measures for working in secure areas shall be designed and implemented.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.7', 'Clear desk and clear screen', 'Clear desk rules for papers and removable storage media and clear screen rules shall be defined and appropriately enforced.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.8', 'Equipment siting and protection', 'Equipment shall be sited securely and protected.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.9', 'Security of assets off-premises', 'Off-site assets shall be protected.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.10', 'Storage media', 'Storage media shall be managed through their life cycle of acquisition, use, transportation and disposal.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.11', 'Supporting utilities', 'Information processing facilities shall be protected from power failures and other disruptions caused by failures in supporting utilities.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.12', 'Cabling', 'Power and telecommunications cabling carrying information or supporting information processing facilities shall be protected from interception, interference and damage.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.13', 'Equipment maintenance', 'Equipment shall be correctly maintained to ensure its continued availability and integrity.', 'domain', 'A.7', 'Physical Controls'),
  ('A.7.14', 'Secure disposal or re-use of equipment', 'All equipment, storage media and other devices containing stored information shall be checked and securely disposed of or securely re-used.', 'domain', 'A.7', 'Physical Controls'),

  -- A.8 Technological Controls (34 controls)
  ('A.8.1', 'User endpoint devices', 'Devices used by users to access organizational information or information systems shall be managed to reduce the risk of unauthorized access.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.2', 'Privileged access rights', 'The allocation and use of privileged access rights shall be restricted and managed.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.3', 'Information access restriction', 'Access to information and other associated assets shall be restricted in accordance with the established access control policy.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.4', 'Access to cryptographic keys', 'The generation, use, storage, transport, and destruction of cryptographic keys shall be controlled.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.5', 'Information security in development and support processes', 'Information security shall be implemented in development and support processes for information systems.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.6', 'Information systems security testing', 'Testing of security functionality and security-related configuration changes to information systems shall be carried out.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.7', 'Test information', 'Test information shall be selected carefully, protected and controlled.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.8', 'Information systems monitoring', 'Information systems shall be monitored to detect anomalies, failures and potential information security events.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.9', 'Configuration management', 'Configuration management of information systems, including hardware, software, firmware, information systems, and associated components, shall be implemented.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.10', 'Information deletion', 'Information stored in information systems, devices or other storage media shall be securely deleted (rendered unrecoverable) when no longer required.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.11', 'Data masking', 'The application of data masking shall be considered to protect sensitive information in accordance with the organization''s data masking policy.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.12', 'Database activity monitoring', 'Database activity shall be monitored to detect unauthorized access and modifications.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.13', 'Separation of information systems', 'Information systems, assets and other functions supporting the delivery of critical information systems shall be separated based on trust levels.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.14', 'Segregation of duties', 'Duties and conflicting areas of responsibility with respect to information systems shall be segregated.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.15', 'Access control', 'Logical access to information and related information processing facilities shall be restricted in accordance with an established access control policy.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.16', 'Biometric authentication', 'Biometric authentication controls based on human biological characteristics shall be considered where appropriate given the security requirements and constraints.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.17', 'Multi-factor authentication', 'Multi-factor authentication shall be implemented for user access to privileged accounts and interfaces.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.18', 'Suspension and deactivation of access', 'Access by users and applications to information and information systems shall be suspended or deactivated upon change or termination of employment or contract.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.19', 'Rights of access review', 'Organizations shall review users'' rights of access to information systems at planned intervals.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.20', 'Cryptography', 'Information shall be protected using cryptography in accordance with the organization''s information classification and cryptography policy.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.21', 'Key management', 'Cryptographic key management shall be implemented throughout its life cycle to protect the organization''s information assets and systems.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.22', 'Accountability', 'The generation, receipt, communication and recording of cryptographic keys shall be controlled and protected against modification, loss, destruction or unauthorized disclosure.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.23', 'Encryption', 'Information shall be encrypted during transmission and at rest using appropriate encryption methods and standards to protect the confidentiality and integrity of information.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.24', 'Secure development life cycle', 'Information systems shall be developed following a secure development life cycle.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.25', 'Secure systems engineering principles', 'Principles for engineering secure systems shall be defined, documented and applied to any information system development activities.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.26', 'Secure development environment', 'Organizations shall establish and adequately protect secure development environments for information systems development and testing activities.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.27', 'Outsourced development', 'Organizations shall oversee and monitor the activity related to outsourced information systems development.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.28', 'Testing of security functionality', 'Security functionality shall be tested throughout the development life cycle of information systems.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.29', 'Outsourced system and service delivery', 'Organizations shall implement appropriate controls to protect the confidentiality, integrity and availability of information systems and services related to outsourced system and service delivery.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.30', 'Supply chain for information systems and services', 'Organizations shall implement appropriate controls to ensure the integrity of information and information processing facilities related to the supply chain.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.31', 'Software and firmware integrity', 'Software and firmware shall be protected against unauthorized modifications and malicious code insertion through appropriate controls.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.32', 'Change management', 'Changes to information systems and their environments shall be controlled and assessed to determine the potential impact on information security.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.33', 'Protection of information systems communications', 'Technical and organizational measures shall be implemented to protect information systems communications from unauthorized access and interference.', 'domain', 'A.8', 'Technological Controls'),
  ('A.8.34', 'Resource availability and capacity management', 'The organization shall monitor, control and protect organizational resources supporting information systems against unauthorized use, misuse or capacity management threats.', 'domain', 'A.8', 'Technological Controls')

ON CONFLICT (identifier) DO NOTHING;

-- Populate BNM RMIT requirements
INSERT INTO bnm_rmit_requirements (reference_id, section_number, section_title, subsection_title, requirement_type, requirement_text)
VALUES
  ('S 8.1', 8, 'Governance', 'Responsibilities of the Board of Directors', 'standard', 'The board must establish and approve the technology risk appetite which is aligned with the financial institution''s risk appetite statement. In doing so, the board must:

(a) approve the corresponding risk tolerances for technology-related events considering potential impact on business operations as well as its customers;

(b) identify risk owner to ensure clear accountability and establish criteria and approving authority for the acceptance of residual risks by the institution;

(c) ensure key risk indicators are identified to monitor existing and emerging risks against financial institution''s risk tolerance;

(d) ensure sufficiency and appropriate deployment of resources; and

(e) conduct review of the technology risk appetite at regular intervals with sufficient deliberation to ensure such risk appetite remains relevant with changing risk environment.'),
  ('S 8.2', 8, 'Governance', 'Responsibilities of the Board of Directors', 'standard', 'In discharging its oversight responsibility, the board must:

(a) approve and review the adequacy of the financial institution''s IT and cybersecurity strategic plans to meet business objectives covering a period of no less than three years;

(b) endorse and oversee the effective implementation of a sound and robust technology risk management framework (TRMF) and cyber resilience framework (CRF), as required to be developed under paragraphs 9.1 and 11.2, for the continuity of operations and delivery of financial services;

(c) require senior management to continuously demonstrate that risk assessments undertaken in relation to critical IT systems and use of emerging technology are robust and comprehensive, supported with adequate control measures and resources to mitigate IT and cyber risks arising from the execution of IT strategic plans;

(d) ensure IT-related framework, policies and guidelines are reviewed at least once every three years (unless otherwise stated in this policy document) and apply a depth of review that is commensurate with the complexity of the financial institution''s operations and changes in the risk environment; and

(e) ensure risk management framework provide support to robust risk assessments in relation to technology related applications submitted to the Bank.'),
  ('S 8.3', 8, 'Governance', 'Responsibilities of the Board of Directors', 'standard', 'The board must designate a board-level committee which shall be responsible for supporting the board in providing oversight over technology-related matters. The composition of the designated committee must include at least one member with technology experience and competencies.

**Note:** The board of a financial institution may either designate an existing board committee or establish a separate committee for this purpose. Where such a committee is separate from the Board Risk Committee (BRC), there must be appropriate interface between this committee and the BRC on technology risk-related matters to ensure effective oversight of all risks at the enterprise level.'),
  ('S 8.4', 8, 'Governance', 'Responsibilities of the Board of Directors', 'standard', 'To promote effective discussion at the board level amidst a rapidly evolving technology and cyber risk landscape, the board must:

(a) obtain regular updates on technology risk and cyber threats;

(b) allocate sufficient time to discuss cyber risks, including the strategic, reputational and liquidity risks and impact of operational disruption to stakeholders which could arise from an extreme cyber incident. This shall be supported by input from external experts where appropriate; and

(c) participate in relevant cybersecurity awareness and training programmes.'),
  ('S 8.5', 8, 'Governance', 'Responsibilities of the Board of Directors', 'standard', 'The board audit committee (BAC) shall be responsible for ensuring the effectiveness of the internal technology audit function. This shall include ensuring the adequate competence of the audit staff to perform technology audits. The BAC shall review and ensure appropriate audit scope, procedures and frequency of technology audits. The BAC shall also ensure effective oversight over the prompt closure of corrective actions to address technology control gaps.'),
  ('S 8.6', 8, 'Governance', 'Responsibilities of the Senior Management', 'standard', 'The senior management shall bear primary responsibility for the day-to-day management of technology risks including cyber risks. In fulfilling its responsibilities, senior management must:

(a) implement board approved TRMF and CRF into specific policies and procedures that are consistent with the approved risk appetite and risk tolerance;

(b) ensure that the crisis management plan for service disruptions provides for timely escalation of recovery action, taking into consideration the impact on customers, such as:
   - (i) duration of disruption;
   - (ii) number of customers affected by a disruption; and
   - (iii) number and value of financial transaction impacted; and

(c) provide regular updates to the board on the status of key performance indicators with pertinent information on the risk controls to facilitate informed performance review.'),
  ('S 8.7', 8, 'Governance', 'Responsibilities of the Senior Management', 'standard', 'The senior management must establish a cross-functional committee to provide guidance on the financial institution''s technology plans and operations. The members of the committee must include senior management from both cyber and technology functions, as well as major business units. The committee''s responsibilities shall include the following:

(a) oversee the formulation and effective implementation of the strategic technology plan and associated technology policies and procedures;

(b) provide timely updates to the board on key technology matters; and

(c) approve any deviation from technology-related policies after having carefully considered a robust assessment of related risks. Material deviations shall be reported to the board.

**Note:** Key technology matters include updates on critical systems'' performance, significant IT and cyber incidents, management of technology obsolescence risk, status of patch deployment activities for critical technology infrastructure, proposals for and progress of strategic technology projects, performance of critical technology outsourcing activities, utilisation of the technology budget and competencies for managing technology risks.'),
  ('S 9.1', 9, 'Technology Risk Management', 'Risk Management Framework', 'standard', 'A financial institution must ensure that the TRMF is an integral part of the financial institution''s enterprise risk management framework (ERM).'),
  ('S 9.2', 9, 'Technology Risk Management', 'Risk Management Framework', 'standard', 'The TRMF must include the following:

(a) clear definition of technology risk;

(b) clear responsibilities assigned for the management of technology risk at different levels and across functions, with appropriate governance and reporting arrangements;

(c) the identification of technology risks to which the financial institution is exposed, including risks from the adoption of new or emerging technology (refer Appendix 9 on Guidance on Emerging Technologies);

(d) risk classification of all information assets / systems based on its criticality;

(e) risk measurement and assessment approaches and methodologies;

(f) risk controls and mitigations;

(g) continuous monitoring to timely detect and address any material risks;

(h) effective information system to ensure the technology risk profile remains accurate and up to date;

(i) identification of key resources and interdependencies (including critical third party service providers and their connected parties) which support delivery of critical technology functions;

(j) undertake scenario analysis to strengthen capacity and readiness to resume critical systems under severe conditions; and

(k) effective incident management policies and procedures to minimise the impact of any service disruption on the financial institution and its customers, by restoring the affected service or system to a secure and stable state as quickly as possible.

**Note:** Connected parties refers to Nth party as defined by Basel Committee on Banking Supervision on principles for the sound management of third party risk.'),
  ('S 9.3', 9, 'Technology Risk Management', 'Risk Management Framework', 'standard', 'A financial institution must establish an independent enterprise-wide technology risk management function which is responsible for:

(a) implementing the TRMF and CRF;

(b) advising on critical technology projects and ensuring critical issues that may have an impact on the financial institution''s risk tolerance are adequately deliberated or escalated in a timely manner; and

(c) providing independent views to the board and senior management on third party assessments, where necessary.

**Note:** Relevant third party assessments may include the Data Centre Resilience and Risk Assessment, Network Resilience and Risk Assessment and independent assurance for introduction of new or enhanced digital services.'),
  ('S 9.4', 9, 'Technology Risk Management', 'Designated Chief Information Security Officer', 'standard', 'A financial institution must designate a Chief Information Security Officer (CISO) by whatever name called, to be responsible for the technology risk management function of the financial institution. The financial institution must ensure that the CISO has sufficient authority, independence and resources. The CISO shall:

(a) be independent from day-to-day technology operations;

(b) apprise board and senior management of current and emerging technology risks which could potentially affect the financial institution''s risk profile;

(c) have the requisite technical skills in emerging and core technologies used by the institution, expertise and experience in audit, governance and risk management, strategic planning and execution of IT and cybersecurity programs, and third party risk management; and

(d) be appropriately certified.

**Note:** A financial institution''s CISO may take guidance from the expertise of a group-level CISO, in or outside of Malaysia, and may also hold other roles and responsibilities provided these do not impair the CISO''s independence or competence. Such designated CISO shall be accountable for and serve as the point of contact with the Bank on the financial institution''s technology-related matters, including managing entity-specific risks, supporting prompt incident response and reporting to the financial institution''s board.'),
  ('S 9.5', 9, 'Technology Risk Management', 'Designated Chief Information Security Officer', 'standard', 'The CISO shall be responsible for ensuring that the financial institution''s information assets and technologies are adequately protected, which includes:

(a) formulating appropriate policies for the effective implementation of TRMF and CRF;

(b) enforcing compliance with these policies, frameworks and other technology-related regulatory requirements; and

(c) advising senior management on technology risk and security matters, including developments in the financial institution''s technology security risk profile in relation to its business and operations.'),
  ('S 10.1', 10, 'Technology Operations Management', 'Technology Project Management', 'standard', 'A financial institution must establish appropriate governance requirements commensurate with the risk and complexity of technology projects undertaken. This shall include project oversight roles and responsibilities, authority and reporting structures, and risk assessments throughout the project life cycle.

**Note:** For example, large-scale integration projects or those involving critical systems must be subject to more stringent project governance requirements such as more frequent reporting to the board and senior management, more experienced project managers and sponsors, more frequent milestone reviews and independent quality assurance at major project approval stages.'),
  ('S 10.2', 10, 'Technology Operations Management', 'Technology Project Management', 'standard', 'The risk assessments shall identify and address the key risks arising from the implementation of technology projects. These include the risks that could threaten successful project implementation and the risks that a project failure will lead to a broader impact on the financial institution''s operational capabilities. At a minimum, due regard shall be given to the following areas:

(a) the adequacy and competency of resources including those of the vendor to effectively implement the project. This shall also take into consideration the number, size and duration of significant technology projects already undertaken concurrently by the financial institution;

(b) the complexity of systems to be implemented such as the use of unproven or unfamiliar technology and the corresponding risks of integrating the new technology into existing systems, managing multiple vendor-proprietary technologies, large-scale data migration or cleansing efforts and extensive system customisation;

(c) the adequacy and configuration of security controls throughout the project life cycle to mitigate cybersecurity breaches or exposure of confidential data;

(d) the comprehensiveness of the user requirement specifications to mitigate risks from extensive changes in project scope or deficiencies in meeting business needs;

(e) the robustness of system and user testing strategies to reduce risks of undiscovered system faults and functionality errors;

(f) the appropriateness of system deployment and fallback strategies to mitigate risks from prolonged system stability issues; and

(g) the adequacy of disaster recovery operational readiness following the implementation of new or enhanced systems.'),
  ('S 10.3', 10, 'Technology Operations Management', 'Technology Project Management', 'standard', 'The board and senior management must receive and review timely reports on the management of these risks on an ongoing basis throughout the implementation of significant projects.'),
  ('S 10.4', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'A financial institution must establish a framework to guide the design, planning, implementation, and governance of an enterprise technology architecture. A technology architecture serves as a foundation on which financial institutions plan and structure system development and acquisition strategies to meet business goals. Thus, the financial institution must ensure the framework carry out these functions:

(a) provides a comprehensive view of technology throughout the financial institution, baseline architecture components and key rationale for their use;

(b) is an overall technical design and high-level plan that describes the financial institution''s technology infrastructure, systems'' inter-connectivity and dependencies (e.g. fallback facility), and security controls. The outlined information is critical to support identification of a single point of failure;

(c) contains mapping to supported business functions, organisation units, applications, and data to enable business impact analysis;

(d) defines principles and guideline to govern the design and maintenance of the network infrastructure, related technology controls, and IT security policies; and

(e) outline longer-term priorities to guide its evolution.'),
  ('S 10.5', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'A financial institution must adopt a methodology for an effective and secure implementation of IT systems. Key phases of System Development Life Cycle (SDLC) shall include requirement, design, development, testing, deployment, change management, maintenance and decommissioning, and integrate with:

(a) enterprise architecture to ensure successful execution of business strategy;

(b) risk management policies and practices to achieve business objectives; and

(c) security principles and requirements to ensure confidentiality, integrity, and availability of customer and counterparty information.

**Note:** The security considerations shall include ensuring appropriate segregation of duties throughout the SDLC.'),
  ('S 10.6', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'A financial institution must meet enterprise security, governance and compliance requirements when using rapid system development methodology. Given the dynamic environment can increase likelihood of errors, a financial institution shall automate the IT security compliance review to prevent unauthorised access as well as the discovery and testing of security vulnerabilities to ensure secure release of new IT services.

**Note:** Such as DevOps which is a set of practices for automating the processes between software development and information technology operations teams so that they can build, test, and release software faster and more reliably. The goal is to shorten the systems development life cycle and improve reliability while delivering features, fixes, and updates frequently in close alignment with business objectives.'),
  ('S 10.7', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'A financial institution shall physically segregate the production environment from the development and testing environment to mitigate the risk of unauthorised changes to the production systems. Where a financial institution is relying on a cloud environment, the financial institution shall ensure that these environments are not running on the same virtual host.'),
  ('S 10.8', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'A financial institution must establish a sound methodology for a rigorous system testing prior to deployment. The testing shall ensure that the system meets user requirements and performs robustly. Where sensitive test data is used, the financial institution must ensure proper authorisation procedures and adequate measures to prevent their unauthorised disclosure are in place.'),
  ('G 10.9', 10, 'Technology Operations Management', 'System Development and Acquisition', 'guidance', 'The scope of system testing referred to in paragraph 10.8 may include unit testing, integration testing, user acceptance testing, application security testing, stress and load testing, regression, exception and negative testing, where applicable.'),
  ('S 10.10', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'A financial institution must ensure any changes to the source code of critical systems are subject to adequate source code reviews to ensure code is secure and developed in line with recognised coding practices prior to introducing any system changes.'),
  ('S 10.11', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'A financial institution must establish appropriate procedures to independently review and approve system changes. The financial institution must also establish and test contingency plans in the event of an unsuccessful implementation of material changes to minimise any business disruption.'),
  ('S 10.12', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'In relation to critical systems that are developed or maintained by third party service provider, a financial institution must, through contractual obligations, require third party service provider to:

(a) provide sufficient notice to the financial institution before any changes are undertaken that may impact the IT system;

(b) demonstrate that it adopts secure by design principles in IT system development methodology to mitigate cyber risks from propagating across the supply chain; and

(c) ensure the source code continues to be readily accessible for business continuity.'),
  ('S 10.13', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'When decommissioning critical systems, a financial institution must ensure minimal adverse impact on customers and business operations. This includes establishing and testing contingency plans in the event of unsuccessful system decommissioning.'),
  ('G 10.14', 10, 'Technology Operations Management', 'System Development and Acquisition', 'guidance', 'A financial institution may deploy automated tools for software development, testing, software deployment, change management, code scanning and software version control to facilitate timely security assessment of critical systems in keeping with growing complexity in IT systems and emerging cyber threats.'),
  ('G 10.15', 10, 'Technology Operations Management', 'System Development and Acquisition', 'guidance', 'Where a third party software is used, a financial institution should consider the potential risks and impacts a cyber supply chain incident may pose to its overall business operations and services. A financial institution may consider:

(a) adopting Software-Bill-of-Materials (SBOM) to automate the identification and continuous monitoring of potential security vulnerabilities including security issues associated with third party software components; and

(b) establishing open-source software security policy and procedures. This includes ensuring secure access to source code repositories in third party platforms, regular monitoring to prevent data leakages, adoption of secure coding practices, robust testing of open-source software and timely vulnerability assessment to mitigate security vulnerabilities and propagation of malwares across supply chain.

**Note:** Software-Bill-of-Materials (SBOM) refers to a formal record containing the details, and the various components used in building a software product including its related supply chain relationships. SBOM provides increased transparency, provenance, and speed at which vulnerabilities can be identified and remediated across the SDLC.'),
  ('S 10.16', 10, 'Technology Operations Management', 'System Development and Acquisition', 'standard', 'A financial institution must develop and implement robust policies to identify and reduce shadow IT risks.

**Note:** Shadow IT refers to unauthorised use of hardware, software, or other systems and services within a company, commonly without the IT department''s approval, knowledge, or oversight.'),
  ('S 10.17', 10, 'Technology Operations Management', 'Patch and End-of-Life System Management', 'standard', 'A financial institution must ensure that all systems including digital services are not running with known security vulnerabilities, on outdated platform or end-of-life (EOL) technology systems. In this regard, a financial institution must:

(a) maintain current security baseline for the security hardening of technology components and ensure the security baseline is accurate and up to date;

(b) continuously monitor and implement latest patch releases in a timely manner;

(c) identify, plan and implement remedial action for technology systems that are approaching EOL; and

(d) obtain management approval for any exception permitting the continued use of unsupported or outdated technology. This exception must be substantiated by a thorough risk assessment with clear timeline for phasing out the outdated technology and are regularly reviewed at least on annual basis to ensure associated risks are effectively managed.

**Note:** Known security vulnerability refers to a documented flaw or weakness in a system that are publicly disclosed or catalogued in databases such as the National Vulnerability Database (NVD) or Common Vulnerabilities and Exposures (CVE) list.'),
  ('S 10.18', 10, 'Technology Operations Management', 'Patch and End-of-Life System Management', 'standard', 'A financial institution must establish a patch and EOL management framework which addresses among others the following requirements:

(a) identification and risk assessment of all technology assets for potential vulnerabilities arising from undeployed patches or EOL systems;

(b) formulation of criteria, priority and turnaround time for patch deployment according to the severity of the vulnerabilities identified;

(c) conduct of compatibility testing prior to the deployment of patches to minimise disruption to connected systems;

(d) adherence to the workflow for end-to-end patch deployment processes including approval, testing, monitoring and tracking of activities; and

(e) end-user awareness for orderly transition.'),
  ('S 10.19', 10, 'Technology Operations Management', 'Patch and End-of-Life System Management', 'standard', 'A financial institution must continually monitor the effectiveness and security of the technology in use, incorporating developments in technology that may disrupt existing security controls. A financial institution shall:

(a) ensure its board receives advice on the potential impact to business operation arising from evolving technology landscape;

(b) formulate long-term strategy to address anticipated changes with allocation of competent resources to manage associated risks, including new cyber adversary tactics and techniques; and

(c) establish roadmap for system migration to preserve security and reliability of the technology infrastructure in an orderly manner.

**Note:** Such as quantum computing.'),
  ('S 10.20', 10, 'Technology Operations Management', 'Cryptography', 'standard', 'A financial institution must establish a robust and resilient cryptography policy to promote the adoption of strong cryptographic controls for protection of important data and information. This policy, at a minimum, shall address requirements for:

(a) the adoption of industry standards for encryption algorithms, message authentication, hash functions, digital signatures and random number generation;

(b) the adoption of robust and secure processes in managing cryptographic key lifecycles which include generation, distribution, renewal, usage, storage, recovery, revocation and destruction;

(c) the periodic review, at least annually, of all cryptographic standards and algorithms currently in use for critical systems, external linked or transactional customer-facing applications to prevent exploitation of weakened algorithms or protocols;

(d) the expansion of IT asset inventory to include all cryptographic tools and algorithms in use with pertinent information on the rationale for each cryptographic method employed and its mapping to supported application systems; and

(e) the development and testing of compromise-recovery plans in the event of a cryptographic key compromise. This must set out the escalation process, procedures for keys regeneration, interim measures, changes to business-as-usual protocols and containment strategies or options to minimise the impact of a compromise.'),
  ('S 10.21', 10, 'Technology Operations Management', 'Cryptography', 'standard', 'A financial institution must conduct due diligence and evaluate the cryptographic controls associated with the technology used in order to protect the confidentiality, integrity, authentication, authorisation and non-repudiation of information. Additionally, a financial institution must ensure the following:

(a) except for non-critical systems or applications that do not contain customer information, the financial institution must retain ownership and control of the encryption keys (themselves or with an independent key custodian) to minimize the risk of unauthorised access to the data;

(b) where the financial institution does not generate its own encryption keys, the financial institution shall undertake appropriate measures to ensure robust controls and processes are in place to manage encryption keys securely including adhere to relevant industry standard;

(c) where this involves a reliance on third party assessments, the financial institution shall consider whether such reliance is consistent with the financial institution''s risk appetite and tolerance; and

(d) the financial institution must also give due regard to the system resources required to support the cryptographic controls and the risk of reduced network traffic visibility of data that has been encrypted.

**Note:** For example, where the financial institution is not able to perform its own validation on embedded cryptographic controls due to the proprietary nature of the software or confidentiality constraints.'),
  ('S 10.22', 10, 'Technology Operations Management', 'Cryptography', 'standard', 'A financial institution must ensure cryptographic controls are based on the effective implementation of suitable cryptographic protocols. The protocols shall include secret and public cryptographic key protocols, both of which shall reflect a high degree of protection to the applicable secret or private cryptographic keys. The selection of such protocols must be based on recognised international standards and tested accordingly. Commensurate with the level of risk, secret cryptographic key and private-cryptographic key storage and encryption / decryption computation must be undertaken in a protected environment, supported by a hardware security module (HSM), trusted execution environment (TEE) or similarly secured devices.'),
  ('S 10.23', 10, 'Technology Operations Management', 'Cryptography', 'standard', 'A financial institution shall store public cryptographic keys in a certificate issued by a Certificate Authority, as appropriate to the level of risk. Such certificates associated with customers shall be issued by recognised Certificate Authorities. The financial institution must ensure that the implementation of authentication and signature protocols using such certificates are subject to strong protection to ensure that the use of private cryptographic keys corresponding to the user certificates are legally binding and irrefutable. The initial issuance and subsequent renewal of such certificates must be consistent with industry best practices and applicable legal / regulatory specifications.'),
  ('S 10.24', 10, 'Technology Operations Management', 'Data Centre Resilience', 'standard', 'A financial institution must specify the resilience and availability objectives of its data centres to effectively support its business recovery objectives.'),
  ('S 10.25', 10, 'Technology Operations Management', 'Data Centre Resilience', 'standard', 'A financial institution must ensure data centres have redundant capacity components and multiple distribution paths serving the computer equipment to eliminate any single point of failure for effective achievement of the identified business recovery objectives.'),
  ('S 10.26', 10, 'Technology Operations Management', 'Data Centre Resilience', 'standard', 'A financial institution shall host critical systems in a dedicated space intended for production data centre usage. The dedicated space must be physically secured from unauthorised access and is not located in a disaster-prone area. A financial institution must also ensure there is no single point of failure in the design and connectivity for critical components of the production data centres, including hardware components, electrical utility, thermal management and data centre infrastructure. A financial institution must also ensure adequate maintenance, and holistic and continuous monitoring of these critical components with timely alerts on faults and indicators of potential issues.'),
  ('S 10.27', 10, 'Technology Operations Management', 'Data Centre Resilience', 'standard', 'A financial institution must establish adequate control procedures for its data centre operations, including the deployment of relevant automated tools for batch processing management to ensure timely and accurate batch processes. These control procedures shall also include procedures for implementing changes in the production system, error handling as well as management of other exceptional conditions.'),
  ('S 10.28', 10, 'Technology Operations Management', 'Data Centre Resilience', 'standard', 'A financial institution must segregate incompatible activities in the data centre operations environment to prevent any unauthorised activity. In the case where vendors'' or programmers'' access to the production environment is necessary, these activities must be properly authorised and monitored.

**Note:** For example, system development activities must be segregated from data centre operations.'),
  ('S 10.29', 10, 'Technology Operations Management', 'Service Availability', 'standard', 'A financial institution must ensure its system capacity needs are well-planned and managed with due regard to peak processing period, business growth plans and technology architecture changes.'),
  ('S 10.30', 10, 'Technology Operations Management', 'Service Availability', 'standard', 'A financial institution must establish real-time monitoring mechanisms to track capacity utilisation and performance of key processes and services. These monitoring mechanisms shall be capable of providing actionable alerts to administrators to enable timely detection and resolution of service interruptions. The monitoring scope, metrics and thresholds shall be updated periodically to ensure they remain effective.

**Note:** For example, batch runs and backup processes for the financial institution''s application systems and infrastructure.'),
  ('S 10.31', 10, 'Technology Operations Management', 'Service Availability', 'standard', 'A financial institution shall enhance the resilience of key digital services and delivery channels through the following measures:

(a) implement effective mechanisms by **30 September 2027** to provide early signals or warning of service degradation or intermittent failures. This means the capability to:
   - (i) detect failed transactions and measure service availability more accurately;
   - (ii) monitor the number of affected customers and transaction volumes during service disruptions to measure the extent and severity customer impact; and
   - (iii) immediately escalating to senior management when service disruptions affect 5% or more of expected daily customers or transaction volumes;

(b) conduct regular reviews to identify and mitigate potentially vulnerable IT system interdependencies to prevent simultaneous interruptions to multiple digital services or delivery channels; and

(c) establish stand-in processing arrangement by **30 September 2027** and deploy such arrangement during disruptions to ensure continuity of services during disruptions. A financial institution shall prioritise deployment of this capability for digital services and delivery channels which are least substitutable, and ensure its customers are well informed on the terms of use (such as the transaction limit), associated risks and allocation of responsibilities between parties and mitigation actions against fraud risks.

**Notes:**
- Key digital services include balance enquiry for deposit accounts, domestic interbank fund transfers, DuitNow, FPX, RENTAS, bill payments and overseas fund transfers.
- Key delivery channels include internet banking, mobile banking, debit card or ATM (where relevant).
- For example, financial institutions should be able to distinguish between failed transactions caused by technical problems and scenarios involving customer inactivity or customer decision to abort.
- For example, customers may be unable to use ATM for large-value funds transfers when internet banking is disrupted or easily switch from a debit card to online banking channel for cashless parking payments or closed loop toll payments.'),
  ('S 10.32', 10, 'Technology Operations Management', 'Service Availability', 'standard', 'For critical systems, where there is a reasonable expectation for immediate delivery of service to customers or dealings with counterparties, a financial institution must ensure that these systems are designed for high availability with a **cumulative unplanned downtime affecting the interface with customers or counterparties of not more than 4 hours on a rolling 12 months basis** and a **maximum tolerable downtime of 120 minutes per incident**.'),
  ('G 10.33', 10, 'Technology Operations Management', 'Service Availability', 'guidance', 'Eligible e-money issuers, non-bank registered merchant acquirers and intermediary remittance institutions that have not been designated as a National Critical Information Infrastructure (NCII) entity are encouraged to implement the measures provided in paragraph 10.31.'),
  ('S 10.34', 10, 'Technology Operations Management', 'Service Availability', 'standard', 'A financial institution shall prioritise diversity in technology to enhance resilience by ensuring critical systems infrastructure are not excessively exposed to similar technology risks.

**Note:** Diversity in technology may include the use of different technology architecture designs and applications, technology platforms and network infrastructure.'),
  ('S 10.35', 10, 'Technology Operations Management', 'Service Availability', 'standard', 'During an interruption of digital services or delivery channels, including periods of performance degradation or intermittent failures, a financial institution shall respond promptly and effectively to minimise the impact on its customers. This includes but not limited to:

(a) ensure timely escalation and decision-making to resume services promptly via alternative arrangements and stabilise performance within the timeframe specified in paragraph 10.32 under all plausible scenarios;

(b) define clear accountabilities for managing performance degradation issues and formalise arrangements with third party service providers to ensure effective coordination and timely recovery to normal performance levels;

(c) establish a communication plan for service interruptions to immediately inform affected customers, properly manage a high volume of customer feedback, and provide frequent updates on recovery efforts, as well as actionable information on available alternatives for customers with urgent needs;

(d) provide customers with a convenient means of checking the availability of digital services, which may include publishing real-time availability and performance status of its digital services on the corporate website; and

(e) disclose the track record of service availability on a quarterly basis within 15 calendar days of quarter-end, beginning from **15 October 2027**.'),
  ('S 10.36', 10, 'Technology Operations Management', 'Network Resilience', 'standard', 'A financial institution must design and implement a reliable, scalable and secure enterprise network that is able to support its business activities, including future growth plans.'),
  ('S 10.37', 10, 'Technology Operations Management', 'Network Resilience', 'standard', 'A financial institution must ensure the network services for its critical systems are reliable and have no single point of failure in order to protect the critical systems against potential network faults and cyber threats.'),
  ('G 10.38', 10, 'Technology Operations Management', 'Network Resilience', 'guidance', 'The control measures to prevent from network faults as referred to in paragraph 10.37 are expected to include component redundancy, service diversity and alternate network paths.'),
  ('S 10.39', 10, 'Technology Operations Management', 'Network Resilience', 'standard', 'A financial institution must establish real-time network bandwidth monitoring processes and corresponding network service resilience metrics to flag any over utilisation of bandwidth and system disruptions due to bandwidth congestion and network faults. This includes traffic analysis to detect trends and anomalies.'),
  ('S 10.40', 10, 'Technology Operations Management', 'Network Resilience', 'standard', 'A financial institution must ensure network services supporting critical systems are designed and implemented to ensure the confidentiality, integrity and availability of data.'),
  ('S 10.41', 10, 'Technology Operations Management', 'Network Resilience', 'standard', 'A financial institution must establish and maintain a network design blueprint identifying all of its internal and external network interfaces and connectivity. The blueprint must highlight both physical and logical connectivity between network components and network segmentations.'),
  ('S 10.42', 10, 'Technology Operations Management', 'Network Resilience', 'standard', 'A financial institution must ensure sufficient and relevant network device logs are retained for investigations and forensic purposes for **at least three years**.'),
  ('S 10.43', 10, 'Technology Operations Management', 'Network Resilience', 'standard', 'A financial institution must implement appropriate safeguards to minimise the risk of a system compromise in one entity affecting other entities within the group. Safeguards implemented may include establishing logical network segmentation for the financial institution from other entities within the group.'),
  ('S 10.44', 10, 'Technology Operations Management', 'System Backup and Restoration', 'standard', 'A financial institution must establish a robust backup strategy and procedures to meet business recovery objectives. At a minimum, a financial institution shall:

(a) establish backup and restoration procedures to effectively manage the backup data life cycle;

(b) maintain an adequate number of backup copies of all critical data, the updated version of the operating system software, production programs, system utilities, all master and transaction files and event logs for recovery purposes;

(c) backup media must be stored in an environmentally secure and access-controlled backup site;

(d) secure the storage and transportation of sensitive data in removable media to meet minimum controls as specified in Appendix 1 or equivalent;

(e) test backup and restoration procedures periodically to validate recovery capabilities. Remedial actions shall be taken promptly by the financial institution to fix the root cause of unsuccessful backups; and

(f) undertake an independent risk assessment of its end-to-end backup storage and delivery management to ensure that existing controls are adequate in protecting sensitive data at all times.'),
  ('S 10.45', 10, 'Technology Operations Management', 'System Backup and Restoration', 'standard', 'A financial institution shall establish a tamper-proof backup arrangement and an isolated recovery environment to enable timely resumption of critical banking and payment services within its tolerable level in the event of destructive cyber-attacks such as widespread data loss caused by ransomware.'),
  ('S 10.46', 10, 'Technology Operations Management', 'Third Party Service Provider Management', 'standard', 'The board and senior management of the financial institution must exercise effective oversight and address associated risks when engaging third party service providers for critical technology functions and systems. The financial institution remains accountable for managing all risks that arise from engagement of third party service providers, to ensure security and reliability of technology services in compliance with all relevant regulatory requirements prescribed in this policy document.

**Note:** The financial institution must adhere to the requirements in the policy document on Outsourcing for engagements with third party service providers that meet the definition of outsourcing arrangement as specified in the policy document.'),
  ('S 10.47', 10, 'Technology Operations Management', 'Third Party Service Provider Management', 'standard', 'A financial institution must conduct a due diligence on a third party service provider prior its on-boarding or engagement and throughout the service engagement to ensure achievement of business performance and recovery objectives remain unimpaired, considering the latest risk environment. At the minimum, a financial institution must consider the range of risks outlined in Appendix 8.'),
  ('S 10.48', 10, 'Technology Operations Management', 'Third Party Service Provider Management', 'standard', 'A financial institution must establish a Service Level Agreement (SLA) when engaging third party service provider. At a minimum, the SLA shall contain the following:

(a) access rights for the regulator and any party appointed by the financial institution to examine any activity or entity of the financial institution. This shall include access to any record, file or data of the financial institution, including management information and the minutes of all consultative and decision-making processes;

(b) requirements for the third party service provider to provide sufficient prior notice to financial institutions of any sub-contracting which is substantial;

(c) a written undertaking by the third party service provider on its compliance with secrecy provisions under relevant legislations. The SLA shall further clearly provide for the third party service provider to be bound by integrity and confidentiality provisions stipulated under the contract even after the engagement has ended;

(d) arrangements for disaster recovery and backup capability, where applicable;

(e) service level objectives for uptime or availability;

(f) arrangements to secure business continuity in the event of an exit or termination of the third party service provider, which includes ensuring data residing in third party service providers are recoverable in a timely manner;

(g) responsibility of third party service providers to promptly disclose and notify the financial institution of any service disruptions or cyber incidents that affect the financial institution or its customer data that occur within such service providers'' or sub-contractors'' environment;

(h) requirements for the third party service providers to comply with the relevant internationally recognised standards and ensure their key staff keep their skills up-to-date with the relevant certifications; and

(i) requirements for third party service providers to participate in the financial institution''s security awareness and education program, where appropriate.

**Note:** This enables financial institutions to provide timely updates to the Bank and other relevant regulatory bodies, subject to the applicable secrecy provisions under relevant legislations.'),
  ('S 10.49', 10, 'Technology Operations Management', 'Third Party Service Provider Management', 'standard', 'A financial institution must formulate a roadmap to achieve continuous monitoring of a third party service provider''s cybersecurity posture to obtain real-time insights for effective incident management. The financial institution shall undertake the following:

(a) measure the IT infrastructure footprint and the customer information accessible to third parties, and regularly manage this external stress state exposures to mitigate cyber-attack surfaces;

(b) adopt leading security policies and controls to mitigate product-specific third party risks;

(c) ensure incident response plans incorporate protocols with third party service providers to detect and contain adverse impact of security vulnerabilities resulting from software updates;

(d) define a priority set of security controls that require more frequent assurance assertion from the third party service providers;

(e) monitor technology and cyber incidents information disclosed by third party service providers at a higher frequency;

(f) implement technology solutions to automate metric testing; and

(g) establish processes to respond to breached thresholds, including investigating failed assertions and remedying control gaps.'),
  ('S 10.50', 10, 'Technology Operations Management', 'Cloud Services', 'standard', 'A financial institution must fully understand the inherent risk of adopting cloud services. In this regard, a financial institution shall conduct a comprehensive risk assessment prior to cloud adoption which considers the inherent architecture of cloud services that leverages on the sharing of resources and services across multiple tenants over the Internet. The assessment must specifically address risks associated with the following:

(a) sophistication of the deployment model;

(b) migration of existing systems to cloud infrastructure;

(c) location of cloud infrastructure including potential geo-political risks and legal risks that may impede compliance with any legal or regulatory requirements;

(d) multi-tenancy or data co-mingling;

(e) vendor lock-in and application portability or interoperability;

(f) ability to customise security configurations of the cloud infrastructure to ensure a high level of data and technology system protection;

(g) exposure to cyber-attacks via cloud service providers;

(h) termination of a cloud service provider including the ability to secure the financial institution''s data following the termination;

(i) demarcation of responsibilities, limitations and liability of the cloud service provider; and

(j) ability to meet regulatory requirements and international standards on cloud computing on a continuing basis.'),
  ('G 10.51', 10, 'Technology Operations Management', 'Cloud Services', 'guidance', 'For critical systems hosted on a public cloud, a financial institution is expected to consider common key risks and control measures as specified in Appendix 10. A financial institution that relies on alternative risk management practices that depart from the measures outlined in Appendix 10 is expected to be prepared to explain and demonstrate to the Bank that these alternative practices are at least as effective as, or superior to, the measures in Appendix 10.

**Note:** Refer the Special Publication 800-145 on Definition of Cloud Computing issued by the National Institute of Standards and Technology, U.S. Department of Commerce.'),
  ('S 10.52', 10, 'Technology Operations Management', 'Cloud Services', 'standard', 'A financial institution must implement appropriate safeguards on customer and counterparty information and proprietary data when using cloud services to protect against unauthorised disclosure and access. This shall include retaining ownership, control and management of all data pertaining to customer and counterparty information, proprietary data and services hosted on the cloud, including the relevant cryptographic keys management.'),
  ('S 10.53', 10, 'Technology Operations Management', 'Access Control', 'standard', 'A financial institution must implement an access control policy for the identification, authentication, and authorisation of all users to its IT assets and data. The level of granularity defined in the access control policy shall be commensurate with the level of risk of unauthorised access to its IT assets.'),
  ('S 10.54', 10, 'Technology Operations Management', 'Access Control', 'standard', 'A financial institution shall adhere to the following principles:

(a) adopt a "deny all" access control policy for users by default because all access to IT assets must be explicitly authorised;

(b) employ "least privilege" access rights to ensure IT assets are accessed on a "need-to-have" basis where only the minimum sufficient permissions are granted to legitimate users to perform their roles;

(c) employ time-bound access which restrict access to a specific period based on the nature of work;

(d) employ segregation of incompatible functions where no single person is responsible for an entire operation that may provide the ability to independently modify, circumvent, and disable system security features. This may include a combination of functions such as:
   - (i) system development and technology operations;
   - (ii) security administration and system administration;
   - (iii) network operation and network security; and
   - (iv) IT operations environment;

(e) establish criteria for activities that require dual authorization control; and

(f) adopt robust user authorization and authentication based on criticality of IT assets as follows:
   - (i) stronger authentication for critical activities and higher-risk environment such as remote access;
   - (ii) ensure user credentials provisioned with robust identity verification method to prevent impersonation risks; and
   - (iii) ensure online credential is uniquely linked to a single user to ensure clear accountability in access to confidential IT assets.'),
  ('S 10.55', 10, 'Technology Operations Management', 'Access Control', 'standard', 'A financial institution must employ a multi-factor authentication (MFA) that can defend against social engineering attacks for authenticating user access to critical systems. The MFA must combine two or more of knowledge factors, inherent factors (e.g. biometric characteristics) or possession factors (e.g. security keys, tokens).'),
  ('S 10.56', 10, 'Technology Operations Management', 'Access Control', 'standard', 'A financial institution must establish a user access matrix to outline access rights, user roles or profiles, and the authorising and approving authorities. The access matrix must be periodically reviewed and updated.'),
  ('S 10.57', 10, 'Technology Operations Management', 'Access Control', 'standard', 'A financial institution must ensure:

(a) access controls to enterprise-wide systems are effectively managed and monitored;

(b) anomalies are flagged for prompt investigations to contain any cyber incidents; and

(c) user activities in critical systems are logged for audit and investigations. Activity logs must be maintained for **at least three years** and regularly reviewed in a timely manner.'),
  ('S 11.1', 11, 'Cybersecurity Management', 'Cyber Risk Management', 'standard', 'A financial institution must ensure that there is an enterprise-wide focus on effective cyber risk management to reflect the collective responsibility of business and technology lines for managing cyber risks.'),
  ('S 11.2', 11, 'Cybersecurity Management', 'Cyber Risk Management', 'standard', 'A financial institution must develop a CRF which clearly articulates its governance for managing cyber risks, its cyber resilience objectives and its risk tolerance, with due regard to the evolving cyber threat environment. Objectives of the CRF shall include ensuring operational resilience against extreme but plausible cyber-attacks. The framework must be able to support the effective identification, protection, detection, response, and recovery (IPDRR) of systems and data hosted on-premises or by third party service providers from internal and external cyber-attacks.'),
  ('S 11.3', 11, 'Cybersecurity Management', 'Cyber Risk Management', 'standard', 'The CRF must consist of, at a minimum, the following elements:

(a) development of an institutional understanding of the overall cyber risk context in relation to the financial institution''s business and operations, its exposure to cyber risks and current cybersecurity posture;

(b) identification, classification and prioritisation of critical systems, information, assets and interconnectivity (with internal and external parties) to obtain a complete and accurate view of the financial institution''s information assets, critical systems, interdependencies and cyber risk profile;

(c) identification of cybersecurity threats, vulnerabilities and countermeasures to secure digital services delivery against cyber-attacks and contain reputational damage that can undermine confidence in the financial institution;

(d) enhancing layers of cyber defence with reference to the latest international standards and sound practices such as zero-trust principles, defense-in-depth through micro-segmentation and security by design, to protect its data, infrastructure and assets against evolving cyber threats;

(e) timely detection of cybersecurity incidents through continuous surveillance and monitoring;

(f) detailed incident handling policies and procedures and a crisis response management playbook to support the swift recovery from cyber incidents and contain any damage resulting from a cybersecurity breach;

(g) policies and procedures for timely and secure information sharing and collaboration with other financial institutions and participants in financial market infrastructure to strengthen cyber resilience and fraud prevention;

(h) implement a centralised automated tracking system to manage its technology asset inventory; and

(i) establish a cyber risk management function to analyse actual and potential cyber threats, providing risk assessments and timely escalation of high-risk cyber threats to senior management and the board. This function shall be performed by an in-house dedicated team or by leveraging on the parent or group.

**Note:** Zero-trust principles is a security paradigm designed to prevent data breaches and limit lateral movement of threat actors by requiring all users, whether in or outside the organization''s network, to be authenticated, authorised, and validated before being granted the access.'),
  ('S 11.4', 11, 'Cybersecurity Management', 'Cyber Risk Management', 'standard', 'A financial institution that is designated as a National Critical Information Infrastructure (NCII) entity pursuant to the Cyber Security Act 2024 must ensure compliance to the requirements and guidelines applicable to NCII, including any additional directives and standards issued by the National Cyber Security Agency (NACSA).'),
  ('S 11.5', 11, 'Cybersecurity Management', 'Cyber Risk Management', 'standard', 'A financial institution must adopt robust control measures as outlined in Appendix 5 to enhance its resilience to cyber-attacks.'),
  ('S 11.6', 11, 'Cybersecurity Management', 'Cyber Risk Management', 'standard', 'A financial institution must conduct a realistic "Red Team" simulation attack on its infrastructure **at least once every three years** to proactively identify and manage potential vulnerabilities.

**Note:** A red team exercise involves a controlled attempt to rigorously evaluate an institution''s security defences, resilience, and response capabilities. In this exercise, a team of information security experts known as the "red team" simulates the tactics, techniques, and procedures of potential adversaries to critically assess the effectiveness of the institution''s security measures, with minimal knowledge and impact on operations.'),
  ('G 11.7', 11, 'Cybersecurity Management', 'Cyber Risk Management', 'guidance', 'A financial institution may implement crowdsourced security testing programs as a complement to existing security assessments, in order to thoroughly test the security of their IT environment. The financial institution must engage reputable and credible service providers to facilitate the program.'),
  ('S 11.8', 11, 'Cybersecurity Management', 'Cybersecurity Operations', 'standard', 'A financial institution must establish clear responsibilities for cybersecurity operations which shall include implementing appropriate mitigating measures in the financial institution''s conduct of business that correspond to the following phases of the cyber-attack lifecycle:

(a) reconnaissance;

(b) weaponisation;

(c) delivery;

(d) exploitation;

(e) installation;

(f) command and control; and

(g) exfiltration.'),
  ('S 11.9', 11, 'Cybersecurity Management', 'Cybersecurity Operations', 'standard', 'A financial institution must ensure continuous and proactive monitoring and timely detection of anomalous activities in its technology infrastructure to prevent potential compromise of its security controls or weakening of its security posture. This shall include:

(a) establishing a Security Operations Center (SOC) supported by competent resources and equipped with the necessary tools and technologies for proactive monitoring of its technology security posture;

(b) ensuring the scope of monitoring must cover all critical systems including the supporting infrastructure; and

(c) conducting regular review of its security posture via the conduct of a vulnerability assessment and penetration testing in line with Appendix 5.'),
  ('S 11.10', 11, 'Cybersecurity Management', 'Cybersecurity Operations', 'standard', 'A financial institution must establish a process to collect, analyse and evaluate cyber threat information in relation to its environment ("cyber threat intelligence") to promptly detect cyber threats, including data breach incidents and spread of misleading information in relation to the financial institution over the Internet.

**Note:** This includes the capability to collect and correlate such information from sources such as social media and dark web.'),
  ('S 11.11', 11, 'Cybersecurity Management', 'Cybersecurity Operations', 'standard', 'A financial institution must establish appropriate response to investigate and respond to flagged anomalous activities based on their level of complexity.'),
  ('S 11.12', 11, 'Cybersecurity Management', 'Cyber Response and Recovery', 'standard', 'A financial institution must establish comprehensive cyber crisis management policies and procedures that incorporate cyber-attack scenarios and responses in the organisation''s overall crisis management plan, escalation processes, business continuity and disaster recovery planning. This includes developing a clear communication plan for engaging shareholders, regulatory authorities, customers and employees in the event of a cyber incident.'),
  ('S 11.13', 11, 'Cybersecurity Management', 'Cyber Response and Recovery', 'standard', 'A financial institution must establish and implement a comprehensive Cyber Incident Response Plan (CIRP). The CIRP must address the following:

**(a) Preparedness**
Establish a clear governance process, reporting structure and roles and responsibilities of the Cyber Emergency Response Team (CERT) as well as invocation and escalation procedures in the event of an incident;

**(b) Detection and analysis**
Ensure effective and expedient processes for identifying points of compromise, assessing the extent of damage and preserving sufficient evidence for forensics purposes;

**Note:** This includes competency in handling threat actor claims by confirming the legitimacy and extent of the incident and uncover more details on the threat actor.

**(c) Containment and eradication**
Identify and implement remedial actions to prevent or minimise damage to the financial institution, contain and remove the known threats and resume business activities;

**(d) Recovery**
Implement multiple strategies including contingency plans as part of incident recovery to swiftly resume business operations and significantly enhance redundancy and resilience; and

**(e) Post-incident activity**
Conduct post-incident review incorporating lessons learned and develop long-term risk mitigations.'),
  ('S 11.14', 11, 'Cybersecurity Management', 'Cyber Response and Recovery', 'standard', 'A financial institution must ensure that relevant CERT members are conversant with the incident response plan and handling procedures and remain contactable at all times.'),
  ('S 11.15', 11, 'Cybersecurity Management', 'Cyber Response and Recovery', 'standard', 'A financial institution shall establish a secure and reliable out-of-band communication infrastructure for both internal and external stakeholders to ensure continued coordination and communication if the primary communication infrastructure is compromised or rendered unavailable during a crisis.'),
  ('S 11.16', 11, 'Cybersecurity Management', 'Cyber Response and Recovery', 'standard', 'A financial institution must conduct an **annual cyber drill exercise** to test the effectiveness of its CIRP including the out-of-band communication methods, based on various current and emerging threat scenarios (e.g. social engineering), with the involvement of key stakeholders including members of the board, senior management and relevant third party service providers. The result of the annual cyber drill exercise must be reported to the board in a timely manner. The out-of-band communication methods must also be tested regularly as part of the institutions cyber drill exercises. The test scenarios must include scenarios designed to test:

(a) the effectiveness of escalation, internal and external communication and decision-making processes that correspond to different impact levels of a cyber incident; and

(b) the readiness and effectiveness of CERT and relevant third party service providers in supporting the recovery process.'),
  ('S 11.17', 11, 'Cybersecurity Management', 'Cyber Response and Recovery', 'standard', 'A financial institution shall review its loss provision arrangements to ensure its adequacy to cover cyber incidents based on its scenario analysis of extreme adverse events. Where cyber insurance is adopted to mitigate impact of cyber incidents, the financial institution shall:

(a) ensure that the scope of the insurance policy adequately covers the information security events and types of liability that the financial institution is exposed to;

(b) understand the terms and conditions of the insurance policy in relation to warranties, attestations or any responsibilities of the financial institution, have them reflected in the crisis response policies and procedures as appropriate and ensure that any changes to IT services and control measures do not result in unintended exclusions of cover; and

(c) ensure that any obligations imposed by the insurance policy (such as in relation to appointment of experts and accepting their recommendations during a cyber incident) do not impair its ability to act in the best interest of the financial institution and its customers. The financial institution shall anticipate and adequately manage any conflict of interest that may arise from the objective of the insurer to minimise the cost of its liability under the insurance policy.'),
  ('S 11.18', 11, 'Cybersecurity Management', 'Cyber Reporting and Threat Information Sharing', 'standard', 'A financial institution is required to notify the Bank of cyber incidents in adherence to the Bank''s policy documents on Operational Risk Reporting – Part C, Business Continuity Management – Part C, Merchant Acquiring Services – paragraphs 19.25 to 19.26 and any other relevant policy documents specified by the Bank.'),
  ('S 11.19', 11, 'Cybersecurity Management', 'Cyber Reporting and Threat Information Sharing', 'standard', 'Subject to the applicable data protection laws, a financial institution must share cyber threat intelligence information with the industry on a timely basis via the relevant sharing platforms developed by the Bank, the industry, or law enforcement agencies. In addition, the financial institution must allocate resources to participate in any industry-wide initiatives aimed at improving collective threat intelligence capabilities.'),
  ('S 11.20', 11, 'Cybersecurity Management', 'Cyber Reporting and Threat Information Sharing', 'standard', 'A financial institution shall collaborate and cooperate closely with relevant stakeholders and authorities in combating cyber threats.'),
  ('S 12.1', 12, 'Digital Services', 'Security of Digital Services', 'standard', 'Securing digital services is an integral part of financial institution''s risk management. A financial institution must expand its CRF to implement robust technology security controls in providing digital services which assure the following:

(a) adopt and regularly assess the minimum-security controls for respective delivery channels to ensure confidentiality and integrity of customer and counterparty information and transactions. Refer to Appendices 2, 3, 4 and 11;

(b) proper authentication of users or devices and authorization of transactions to mitigate impersonation and fraud risk. Refer the minimum-security controls in Appendix 3; and

(c) strong physical control and logical control measures.'),
  ('S 12.2', 12, 'Digital Services', 'Security of Digital Services', 'standard', 'In the event that a financial institution has not yet implemented the digital services security controls specified under paragraph 12.1 to 12.9, the financial institution must:

(a) be ready to provide documented explanation of how alternatives measures or mitigations achieve equivalent or superior effectiveness; and

(b) assume the liability of any fraud that occurs due to the gaps arise from the absence of the specified control.'),
  ('S 12.3', 12, 'Digital Services', 'Digital Fraud Management and Customer Awareness', 'standard', 'The complex and fast evolving digital fraud requires financial institutions to be vigilant against new fraud techniques and proactive in strengthening their cyber defence for customer protection. In line with paragraphs 11.2 and 11.3, a financial institution must enhance its CRF as follows:

(a) expand the scope of identification of cybersecurity threats and countermeasures to include customers'' mobile devices and access points;

(b) adopt layered (defense-in-depth) security controls to protect the digital service application deployed to customers'' mobile devices and the relevant banking data contained in it;

(c) perform continuous surveillance and monitoring to detect any exploitation of the digital service application deployed to customers'' mobile devices and ensure the swift upgrade of security controls to mitigate new vulnerabilities;

(d) establish clearly defined and effective incident handling procedures to assist customers to contain the potential damage resulting from a cybersecurity breach involving digital services;

(e) formalise operational arrangement to enable swift coordinated response and rapid upgrade of countermeasures to defend against advanced fraud tactics if a financial institution relies on multiple business functions;

(f) conduct regular review by senior management to ensure the effectiveness of digital fraud management and define threshold for escalation of countermeasures considering the actual impact to victims of digital fraud and emerging fraud environment; and

(g) apprise the board on the outcome of management reviews to preserve public confidence in the security of digital services and mitigate reputation risk to the industry.'),
  ('S 12.4', 12, 'Digital Services', 'Digital Fraud Management and Customer Awareness', 'standard', 'A financial institution must ensure that its fraud detection capabilities and rules are updated in a timely manner upon detection of new fraud modus operandi in order to prevent fraudulent transactions or account takeover using stolen customer credentials. This must be supported by appropriate risk analytics to improve the accuracy of fraud detection, that includes continuous upgrade of fraud detection capabilities as specified in Appendix 11 on Fraud Detection Standards.'),
  ('S 12.5', 12, 'Digital Services', 'Digital Fraud Management and Customer Awareness', 'standard', 'A financial institution must mitigate any attendant risk arising from its delivery of digital services. This shall include:

(a) adopt secure communication channel to mitigate risk of phishing. Compensating controls shall be adopted when using communication channel prone to phishing exploits;

(b) all customers must be properly informed in advance of new controls to ease adoption and minimise inconvenience; and

(c) practical ways for customers to verify the authenticity of calls made by the financial institution or its appointed outsourced service providers.

**Note:** A financial institution must remove any clickable hyperlinks in short messaging service (SMS) messages to customers and create awareness on this change to mitigate risk of phishing.'),
  ('S 12.6', 12, 'Digital Services', 'Digital Fraud Management and Customer Awareness', 'standard', 'A financial institution shall empower customers to mitigate digital fraud risks where it is reasonably practical. This shall include offering customer mechanisms to manage activation and de-activation of payment card for card-not-present and overseas transactions. This shall not absolve the financial institution from its liabilities, responsibilities and duty of care to ensure the security of its digital services.

**Note:** A financial institution must adhere to the relevant requirements of the policy documents, as issued by the Bank, on Debit Card and Debit Card-I, and Credit Card and Credit Card-I in managing opt-in requirement for card-not-present and overseas transactions.'),
  ('S 12.7', 12, 'Digital Services', 'Digital Fraud Management and Customer Awareness', 'standard', 'Consumer competency is essential to strengthening the security of digital services. A financial institution must maintain continuous efforts to review and enhance the effectiveness of its awareness programmes, ensuring customers understand the risks of digital services fraud. This shall include:

(a) continuous and timely updates of practical information on how to identify potential fraud, including specific information about new or common modus operandi;

(b) clear explanation about new and existing security measures, such as how to verify genuine e-banking websites and mobile applications;

(c) real-time alerts of possible risks when security measures are absent or have not yet been implemented; and

(d) measures to further improve customer understanding and familiarisation with fraud risks and controls, such as through interactive simulations of security features etc.'),
  ('S 12.8', 12, 'Digital Services', 'Digital Fraud Management and Customer Awareness', 'standard', 'A financial institution must provide convenient means for customers to report, suspend and re-activate their account swiftly in the event of a suspected fraud, where applicable. This shall require the financial institution to:

(a) offer a secure self-service "kill switch" solution;

(b) ensure that its contact centre is adequately resourced and operating effectively to provide prompt and adequate assistance to customers in distress; and

(c) restore customer access to digital services within a reasonable timeframe upon validation.'),
  ('S 12.9', 12, 'Digital Services', 'Digital Fraud Management and Customer Awareness', 'standard', 'In addition to effective incident handling procedures, a financial institution must adopt additional measures to mitigate risk to customers arising from any incident involving potential fraud or compromise of customer data. This shall include:

(a) heighten monitoring of affected customer accounts;

(b) notify affected customers and provide them with the necessary information to apply mitigating measures and reduce the risk of fraud; and

(c) revoke and re-issue affected user credentials or designated payment instruments, where there is a potential risk of exploitation due to compromised data or other fraudulent activity.'),
  ('S 13.1', 13, 'Technology Audits', 'Audit Function', 'standard', 'A financial institution must ensure that the scope, frequency, and intensity of technology audits are commensurate with the complexity, sophistication and criticality of technology systems and applications.'),
  ('S 13.2', 13, 'Technology Audits', 'Audit Function', 'standard', 'A financial institution must establish annual review on its technology audit plan that provides appropriate frequency and coverage of critical technology services, third party service providers, material external system interfaces, delayed or prematurely terminated critical technology projects and post-implementation review of new or material enhancements of technology services.'),
  ('S 13.3', 13, 'Technology Audits', 'Audit Function', 'standard', 'A financial institution must ensure the internal audit function must have dedicated technology audit resources with specialised competencies and professionally certified. The technology audit resources shall be adequately conversant with the developing sophisticate of the financial institution''s technology systems, delivery channels and have sound knowledge in the areas audited.'),
  ('G 13.4', 13, 'Technology Audits', 'Audit Function', 'guidance', 'The technology audit resources may be enlisted to provide advice on compliance and adequacy of control processes during the planning and development phases of new major products, systems, adoption of third party service providers or technology operations. In such cases, the technology auditors participating in this capacity are expected to carefully consider whether such an advisory or consulting role can materially impair their independence or objectivity in performing post-implementation reviews of the products, systems and operations concerned.'),
  ('S 14.1', 14, 'External Party Assurance', '', 'standard', 'A financial institution shall appoint a technically competent external service provider to carry out a production data centre resilience and risk assessment (DCRA). The assessment must consider all major risks and determine the current level of resilience of the production data centre. A financial institution must ensure the assessment is conducted **at least once every three years** or when there is a material change in the data centre infrastructure, whichever is earlier. The assessment shall, at a minimum, include a consideration of whether the requirements in paragraphs 10.24 to 10.28 have been adhered to. For data centres managed by third party service providers, a financial institution shall only rely on independent third party assurance reports provided such reliance is consistent with the financial institution''s risk appetite and tolerance, and the independent assurance has considered similar risks and meets the requirements in this paragraph for conducting the DCRA. The designated board-level committee specified in paragraph 8.3 must deliberate the outcome of the assessment.'),
  ('S 14.2', 14, 'External Party Assurance', '', 'standard', 'A financial institution shall appoint a technically competent external service provider to carry out regular network resilience and risk assessments (NRA) and set proportionate controls aligned with its risk appetite. The assessment must be conducted **at least once in three years** or whenever there is a material change in the network design, whichever is earlier. The assessment must consider all major risks and determine the current level of resilience. This shall include an assessment of the financial institution''s adherence to the requirements in paragraphs 10.36 to 10.43. The designated board-level committee specified in paragraph 8.3 must deliberate the outcome of the assessment.'),
  ('S 15.1', 15, 'Security Awareness and Education', '', 'standard', 'A financial institution must provide adequate and regular technology and cybersecurity awareness education for all staff in undertaking their respective roles and measure the effectiveness of its education and awareness programs. This cybersecurity awareness education must be conducted **at least annually** and must reflect the evolving cyber threat landscape and emerging risks. Where appropriate, the financial institution shall also include its third party service providers in their relevant training as outlined in paragraph 10.48(i).'),
  ('S 15.2', 15, 'Security Awareness and Education', '', 'standard', 'A financial institution must provide adequate and continuous training for staff involved in technology operations, cybersecurity and risk management in order to ensure that the staff are competent and suitably certified to effectively perform their roles and responsibilities.'),
  ('S 15.3', 15, 'Security Awareness and Education', '', 'standard', 'A financial institution must provide its board members with regular training and information on technology developments to enable the board to effectively discharge its oversight role.'),
  ('S 16.1', 16, 'Notification for Technology-Related Applications', 'Introduction or Enhancement to Digital Services', 'standard', 'A financial institution must notify the Bank in accordance with the requirements in paragraphs 16.2 to 16.7 prior to introducing new digital services or enhancement to existing digital services.'),
  ('S 16.2', 16, 'Notification for Technology-Related Applications', 'Introduction or Enhancement to Digital Services', 'standard', 'A financial institution offering digital services for the first time must undertake measures specified under paragraph 16.4 and submit the following information in the notification to the Bank:

(a) assessment on the risks identified and strategies to manage such risks. This includes specific accountabilities, policies and controls to address risks;

(b) security arrangements and controls;

(c) significant terms and conditions;

(d) client charter;

(e) privacy policy statement; and

(f) any outsourcing or website link arrangements, or strategic alliances or partnerships with third parties that have been finalised.'),
  ('S 16.3', 16, 'Notification for Technology-Related Applications', 'Introduction or Enhancement to Digital Services', 'standard', 'For any enhancements to existing digital services which meet the criteria in Appendix 6, a financial institution shall be subject to a simplified notification requirement and submit the following information in the notification to the Bank:

(a) description of the enhancements to the existing technologies; and

(b) risk assessment of the proposed enhancements, including the impact and measures to mitigate identified risks.'),
  ('S 16.4', 16, 'Notification for Technology-Related Applications', 'Introduction or Enhancement to Digital Services', 'standard', 'For any enhancements to existing digital services which are not subject to the simplified notification requirement under paragraph 16.3, a financial institution is required to undertake the following measures prior to notifying the Bank:

(a) engage an independent external party to provide assurance that the financial institution has addressed the technology risks and security controls associated with the digital services or any material enhancement to the digital services. The format of the assurance shall be as set out in Part A of Appendix 7; and

(b) provide a confirmation by the CISO, senior management officer or the chairman of the board or designated board-level committee specified in paragraph 8.3 of the financial institution''s readiness to provide digital services or implement any material enhancement to the digital services. The format of the confirmation shall be as set out in Part B of Appendix 7.'),
  ('S 16.5', 16, 'Notification for Technology-Related Applications', 'Introduction or Enhancement to Digital Services', 'standard', 'A financial institution must ensure that the independent external party providing the assurance is competent and has a good track record. The assurance shall address the matters covered in, and comply with, Part C and D of Appendix 7.'),
  ('S 16.6', 16, 'Notification for Technology-Related Applications', 'Introduction or Enhancement to Digital Services', 'standard', 'A financial institution shall provide relevant documents for the Bank''s review when required by the Bank.'),
  ('G 16.7', 16, 'Notification for Technology-Related Applications', 'Introduction or Enhancement to Digital Services', 'guidance', 'A financial institution may offer digital services or implement any enhancement to the digital services immediately upon submission of the notification under paragraph 16.1 and compliance with the requirements in paragraphs 16.2 to 16.6.'),
  ('S 17.1', 17, 'Consultation and Notification Related to Cloud Services and Emerging Technology', '', 'standard', 'A financial institution is required to consult the Bank prior to the first-time adoption of a public cloud or emerging technology for critical systems. During the consultation, the financial institution must demonstrate that specific risks associated with the use of these technologies have been adequately considered and addressed to the satisfaction of the Bank, in order to proceed with the adoption of the public cloud for critical systems for the first time. The financial institution shall undertake the following prior to consulting the Bank on its adoption of public cloud for critical systems:

(a) conduct a comprehensive risk assessment of the proposed cloud adoption or emerging technology, including the possible impact and measures to address and mitigate the identified risks. For public cloud, the assessment must follow the risk outlined in paragraph 10.50 and Appendix 10. For emerging technology, it must follow the guideline in Appendix 9. The financial institution shall also adopt the format of the Risk Assessment Report as per Part A of Appendix 7;

(b) provide a confirmation by the CISO, senior management officer or the chairman of the board or designated board-level committee specified in paragraph 8.3 of the financial institution''s readiness to adopt public cloud or emerging technology for critical system. The format of the confirmation shall be as set out in Part B of Appendix 7; and

(c) perform a third party pre-implementation review on public cloud or emerging technology. This review shall encompass the areas set out in Appendix 10 (for public cloud) or Appendix 9 (for emerging technology) and Part C of Appendix 7 for higher-risk services, such as those involving the processing or storage of customer information, or cross-border data transmission.'),
  ('S 17.2', 17, 'Consultation and Notification Related to Cloud Services and Emerging Technology', '', 'standard', 'A financial institution shall notify the Bank on any subsequent adoption of a public cloud or emerging technology for critical system, by submitting the notification together with the necessary updates to all the information required under paragraph 17.1, subject to the financial institution having complied with the following requirements and included documentation and information to demonstrate such compliance in the notification submitted to the Bank that the financial institution:

(a) has consulted the Bank prior to adopting a public cloud or emerging technology for critical systems for the first time in accordance with paragraph 17.1, with no concerns raised by the Bank during the first-time consultation;

(b) has enhanced the technology risk management framework to manage cloud or emerging technology risks;

(c) has established independent assurance on the cloud risk management framework or emerging technology risk management framework; and

(d) has provided assurance to the Bank that the incident response plans are sufficient to cater for adverse or unexpected events.'),
  ('G 17.3', 17, 'Consultation and Notification Related to Cloud Services and Emerging Technology', '', 'guidance', 'For the avoidance of doubt, notification to the Bank under paragraph 17.2 is not required for any enhancement to existing cloud adoption and emerging technology adoption that does not materially alter the prior assessments and representations made by a financial institution to the Bank.'),
  ('S 17.4', 17, 'Consultation and Notification Related to Cloud Services and Emerging Technology', '', 'standard', 'The Bank may at its discretion direct a financial institution to consult the Bank under paragraph 17.1, notify the Bank under paragraph 17.2 or observe any of the guidance in Appendix 10 or Appendix 9 and to explain any deviations from the guidance in Appendix 10 or Appendix 9, including for a non-critical system or when the pre-requisites in the paragraphs 17.1 or 17.2 have not been met. A financial institution must comply with such a directive promptly and to the satisfaction of the Bank.'),
  ('S 17.5', 17, 'Consultation and Notification Related to Cloud Services and Emerging Technology', '', 'standard', 'A financial institution must ensure the roadmap for adoption of cloud services or emerging technology (for critical systems and non-critical systems) is included in the annual outsourcing plan submitted to the Bank in adherence with the requirements in the policy document on Outsourcing or IT Profile reporting. The risk assessment as outlined in paragraph 10.50 for cloud services or Appendix 9 for emerging technology must also be documented and made available for the Bank''s review as and when requested by the Bank.'),
  ('S 18.1', 18, 'Assessment and Gap Analysis', '', 'standard', 'A financial institution must perform a gap analysis of existing practices in managing technology risk against the requirements in this policy document and highlight key implementation gaps. The financial institution must develop an action plan with a clear timeline and key milestones to address the gaps identified. The gap analysis and action plan must be submitted to the Bank **no later than 90 days** after the issuance date of this policy document. Financial institutions that have previously made a submission in accordance with the equivalent provision in the previous version of this policy document are required to maintain continuous compliance by identifying any new gaps against the enhanced or revised requirements in the latest version of this policy document and taking the necessary steps to address such gaps. The updated annual assessment of its level of compliance must be made available to the Bank upon request.'),
  ('S 18.2', 18, 'Assessment and Gap Analysis', '', 'standard', 'The self-assessment, gap analysis and action plan in paragraph 18.1 must be submitted to Jabatan Penyeliaan Konglomerat Kewangan, Jabatan Penyeliaan Perbankan, Jabatan Penyeliaan Insurans dan Takaful or Jabatan Pemantauan Perkhidmatan Pembayaran, as the case may be.



| Requirement | Timeline/Threshold | Reference |
|-------------|-------------------|-----------|
| IT/Cybersecurity Strategic Plans | Minimum 3 years | S 8.2(a) |
| Policy/Framework Review | At least once every 3 years | S 8.2(d) |
| Service Degradation Detection | By 30 September 2027 | S 10.31(a) |
| Stand-in Processing Arrangement | By 30 September 2027 | S 10.31(c) |
| Critical System Max Downtime (Rolling 12 months) | ≤ 4 hours cumulative | S 10.32 |
| Critical System Max Downtime (Per Incident) | ≤ 120 minutes | S 10.32 |
| Network Device Log Retention | At least 3 years | S 10.42 |
| User Activity Log Retention | At least 3 years | S 10.57(c) |
| Red Team Exercise | At least once every 3 years | S 11.6 |
| Cyber Drill Exercise | Annual | S 11.16 |
| DCRA Assessment | At least once every 3 years | S 14.1 |
| Network Resilience Assessment | At least once every 3 years | S 14.2 |
| Cybersecurity Awareness Education | At least annually | S 15.1 |
| Service Availability Disclosure | Quarterly, within 15 days of quarter-end, from 15 October 2027 | S 10.35(e) |
| Gap Analysis Submission | Within 90 days of policy issuance | S 18.1 |


**Document Information:**
- **Source:** Bank Negara Malaysia (BNM)
- **Policy Document:** Risk Management in Technology (RMIT)
- **Issued:** 28 November 2025
- **Total Pages:** 80


*Legend:*
- **S** = Standard (Mandatory requirement)
- **G** = Guidance (Best practice recommendation)')
ON CONFLICT (reference_id) DO NOTHING;
