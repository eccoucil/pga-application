// ISO 27001:2022 Requirement
export interface ISORequirement {
  id: string
  identifier: string
  title: string
  description: string | null
  clause_type: 'management' | 'domain'
  category: string | null
  category_code: string | null
  key_activities: string[] | null
  is_mandatory_doc: boolean
  parent_identifier: string | null
}

// BNM RMIT Requirement
export interface BNMRequirement {
  id: string
  reference_id: string
  requirement_type: 'standard' | 'guidance'
  section_number: number
  section_title: string
  subsection_title: string | null
  requirement_text: string
  sub_requirements: { key: string; text: string }[] | null
  notes: string | null
  part: string
}

// Union type for controls from either framework
export type FrameworkControl = ISORequirement | BNMRequirement

// Type guard to check if a control is ISO
export function isISORequirement(control: FrameworkControl): control is ISORequirement {
  return 'identifier' in control && 'clause_type' in control
}

// Type guard to check if a control is BNM
export function isBNMRequirement(control: FrameworkControl): control is BNMRequirement {
  return 'reference_id' in control && 'requirement_type' in control
}

// Section filter options for ISO 27001:2022
export const ISO_SECTION_FILTERS = [
  { value: 'all', label: 'All Controls' },
  { value: 'management', label: 'Management Clauses (4-10)' },
  { value: 'A.5', label: 'A.5 Organizational' },
  { value: 'A.6', label: 'A.6 People' },
  { value: 'A.7', label: 'A.7 Physical' },
  { value: 'A.8', label: 'A.8 Technological' },
] as const

// Section filter options for BNM RMIT
export const BNM_SECTION_FILTERS = [
  { value: 'all', label: 'All Requirements' },
  { value: '8', label: 'Section 8: Governance' },
  { value: '9', label: 'Section 9: Technology Risk Management' },
  { value: '10', label: 'Section 10: Technology Operations' },
  { value: '11', label: 'Section 11: Cybersecurity' },
  { value: '12-18', label: 'Sections 12-18: Other' },
] as const

export type ISOSectionFilter = typeof ISO_SECTION_FILTERS[number]['value']
export type BNMSectionFilter = typeof BNM_SECTION_FILTERS[number]['value']
