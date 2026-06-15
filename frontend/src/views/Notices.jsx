import { Fragment, useState } from 'react'
import { useApi, buildUrl } from '../hooks/useApi.js'
import { Search, ExternalLink, ChevronLeft, ChevronRight, X, Download, Loader, BookmarkPlus, Trash2, FileDown, Cpu } from 'lucide-react'

const COLORS = { IFB: '#00d4aa', REOI: '#7c6fff', 'Contract Award': '#f0a500', Award: '#f0a500' }
const NOTICE_TYPE_OPTIONS = ['IFB', 'REOI', 'Contract Award']
const STATUSES = ['Active', 'Awarded', 'Cancelled', 'Closed', 'Pending']

function Badge({ type }) {
  return (
    <span style={{
      fontSize: 10, fontFamily: 'var(--font-mono)', padding: '2px 7px', borderRadius: 4,
      background: `${COLORS[type] || '#555'}22`, color: COLORS[type] || '#aaa',
      fontWeight: 600, letterSpacing: '0.05em', whiteSpace: 'nowrap'
    }}>{type}</span>
  )
}

function StatusBadge({ status }) {
  const colors = {
    Active: { bg: '#0d2b1e', text: '#00d4aa', border: '#00d4aa' },
    Awarded: { bg: '#1a1a2e', text: '#7c6fff', border: '#7c6fff' },
    Cancelled: { bg: '#2b0d0d', text: '#ff6666', border: '#ff4444' },
    Closed: { bg: '#1a1a1a', text: '#8fa3c0', border: '#3a4a5c' },
    Pending: { bg: '#1a1500', text: '#f0a500', border: '#f0a500' },
  }
  const c = colors[status] || { bg: '#1a2235', text: '#8fa3c0', border: '#3a4a5c' }

  return (
    <span style={{
      fontSize: 10, fontFamily: 'var(--font-mono)', padding: '2px 7px', borderRadius: 4,
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
      fontWeight: 600, letterSpacing: '0.05em', whiteSpace: 'nowrap'
    }}>{status || '--'}</span>
  )
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <label style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)',
          borderRadius: 8, padding: '7px 10px', fontSize: 13, outline: 'none', cursor: 'pointer'
        }}
      >
        <option value="">All</option>
        {options.map(option => <option key={option} value={option}>{option}</option>)}
      </select>
    </div>
  )
}

function FilterTag({ label, onRemove }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 20, padding: '3px 10px 3px 12px', fontSize: 11,
      color: 'var(--text2)', fontFamily: 'var(--font-mono)'
    }}>
      {label}
      <button onClick={onRemove} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text3)', display: 'flex', padding: 0 }}>
        <X size={10} />
      </button>
    </div>
  )
}

function InfoField({ label, value, isEmail = false, color }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 13, color: color || 'inherit' }}>
        {isEmail && value
          ? <a href={`mailto:${value}`} style={{ color: 'var(--accent)' }}>{value}</a>
          : value || '--'}
      </div>
    </div>
  )
}

function stripHtml(html) {
  return html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<\/li>/gi, '\n')
    .replace(/<li>/gi, '- ')
    .replace(/<\/h\d>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;|&ldquo;|&rdquo;/g, '"')
    .replace(/&#39;|&rsquo;|&lsquo;/g, "'")
    .replace(/&ndash;|&mdash;/g, '-')
    .replace(/\r/g, '')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()
}

const AWARD_META_SPECS = [
  { label: 'Project', pattern: /project/i },
  { label: 'Loan / Credit / TF', pattern: /loan\/credit\/tf info/i },
  { label: 'Reference No', pattern: /bid\/contract reference no|reference no/i },
  { label: 'Procurement Method', pattern: /procurement method/i },
  { label: 'Scope of Contract', pattern: /scope of contract/i },
  { label: 'Version No', pattern: /notice version no/i },
  { label: 'Award Date', pattern: /date notification of award issued(?:\s*\(yyyy\/mm\/dd\))?/i },
  { label: 'Duration', pattern: /duration of contract/i },
  { label: 'Contact', pattern: /contact award/i },
]

const AWARD_SECTION_SPECS = [
  { label: 'Awarded Bidder(s)', pattern: /awarded bidder\(s\)/i },
  { label: 'Awarded Firm(s)', pattern: /awarded firm\(s\)/i },
  { label: 'Evaluated Bidder(s)', pattern: /evaluated bidder\(s\)/i },
]

const BIDDER_FIELD_SPECS = [
  { label: 'Country', pattern: /country\s*:?\s*/i },
  { label: 'Bid Price at Opening', pattern: /bid price at opening\s*/i },
  { label: 'Evaluated Bid Price', pattern: /evaluated bid price\s*/i },
  { label: 'Signed Contract Price', pattern: /signed contract price\s*:?\s*/i },
  { label: 'Final Evaluation Price', pattern: /final evaluation price\s*:?\s*/i },
  { label: 'Telephone', pattern: /(?:telephone|tele|tel)\s*:?\s*/i },
  { label: 'Fax', pattern: /fax\s*:?\s*/i },
  { label: 'Email', pattern: /e-?mail\s*:?\s*/i },
  { label: 'P.O. Box', pattern: /p\.?\s*o\.?\s*box\s*:?\s*/i },
]

function normalizeAwardText(text) {
  return text
    .replace(/\s+/g, ' ')
    .replace(/Contract Award\s+Project/i, 'Contract Award Project')
    .replace(/\s+:/g, ':')
    .trim()
}

function extractSequentialSegments(text, specs) {
  const segments = []
  let cursor = 0

  for (let i = 0; i < specs.length; i += 1) {
    const currentSpec = specs[i]
    const currentRegex = new RegExp(currentSpec.pattern.source, currentSpec.pattern.flags)
    const currentSlice = text.slice(cursor)
    const currentMatch = currentSlice.match(currentRegex)

    if (!currentMatch || currentMatch.index === undefined) {
      continue
    }

    const startIndex = cursor + currentMatch.index
    const valueStart = startIndex + currentMatch[0].length

    let valueEnd = text.length
    for (let j = i + 1; j < specs.length; j += 1) {
      const nextRegex = new RegExp(specs[j].pattern.source, specs[j].pattern.flags)
      const nextSlice = text.slice(valueStart)
      const nextMatch = nextSlice.match(nextRegex)
      if (nextMatch && nextMatch.index !== undefined) {
        valueEnd = valueStart + nextMatch.index
        break
      }
    }

    segments.push({
      label: currentSpec.label,
      value: text.slice(valueStart, valueEnd).trim().replace(/^:\s*/, ''),
    })

    cursor = valueStart
  }

  return segments
}

function splitBidderEntries(text) {
  const matches = Array.from(
    text.matchAll(/\b([A-Z][A-Z0-9&.,'/-]*(?:\s+[A-Z][A-Z0-9&.,'/-]*)*\s*\(\d{4,}\))/g)
  )

  if (matches.length === 0) {
    return [text.trim()].filter(Boolean)
  }

  return matches.map((match, index) => {
    const start = match.index ?? 0
    const end = index < matches.length - 1 ? (matches[index + 1].index ?? text.length) : text.length
    return text.slice(start, end).trim()
  }).filter(Boolean)
}

function parseBidderEntry(text) {
  const specs = BIDDER_FIELD_SPECS
  const matches = []

  for (const spec of specs) {
    let match
    const regex = new RegExp(spec.pattern.source, spec.pattern.flags)
    while ((match = regex.exec(text)) !== null) {
      matches.push({
        label: spec.label,
        index: match.index,
        length: match[0].length,
      })
      if (!regex.global) break
    }
  }

  matches.sort((a, b) => a.index - b.index)

  const name = matches.length > 0 ? text.slice(0, matches[0].index).trim() : text.trim()
  const fields = []

  matches.forEach((match, index) => {
    const start = match.index + match.length
    const end = index < matches.length - 1 ? matches[index + 1].index : text.length
    const value = text.slice(start, end).trim().replace(/^:\s*/, '')
    if (value) {
      fields.push({ label: match.label, value })
    }
  })

  return { name, fields }
}

function parseAwardText(text) {
  const normalized = normalizeAwardText(text)
  const heading = normalized.match(/^(contract award)/i)?.[0] || 'Contract Award'
  const body = normalized.replace(/^(contract award)\s*/i, '').trim()
  const firstSectionIndex = AWARD_SECTION_SPECS
    .map(spec => body.search(spec.pattern))
    .filter(index => index >= 0)
    .sort((a, b) => a - b)[0]

  const metaText = firstSectionIndex >= 0 ? body.slice(0, firstSectionIndex).trim() : body
  const sectionText = firstSectionIndex >= 0 ? body.slice(firstSectionIndex).trim() : ''

  const rows = [{ type: 'heading', label: heading }]

  extractSequentialSegments(metaText, AWARD_META_SPECS).forEach(segment => {
    if (segment.value) {
      rows.push({ type: 'field', label: segment.label, value: segment.value })
    }
  })

  if (!sectionText) {
    return rows
  }

  const sectionSegments = extractSequentialSegments(sectionText, AWARD_SECTION_SPECS)
  sectionSegments.forEach(section => {
    rows.push({ type: 'section', label: section.label })
    splitBidderEntries(section.value).forEach(entry => {
      const bidder = parseBidderEntry(entry)
      if (bidder.name || bidder.fields.length) {
        rows.push({ type: 'bidder', section: section.label, ...bidder })
      }
    })
  })

  return rows
}

function isAwardNotice(text, noticeType) {
  const lower = text.toLowerCase()
  return noticeType === 'Award' ||
    noticeType === 'Contract Award' ||
    lower.includes('contract award') ||
    lower.includes('awarded bidder') ||
    lower.includes('awarded firm') ||
    lower.includes('attribution de marche') ||
    lower.includes('adjudicacao')
}

function findRowValue(rows, label) {
  return rows.find(row => row.type === 'field' && row.label === label)?.value || null
}

function cleanProjectValue(value) {
  if (!value) return null
  return value.replace(/^[A-Z]\d{5,}-/, '').trim()
}

function extractEmails(text) {
  return Array.from(
    new Set(
      (text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || []).map(email => email.trim())
    )
  )
}

function extractContactEmail(text) {
  return extractEmails(text)[0] || null
}

function formatNarrativeNotice(text) {
  const normalized = text
    .replace(/\s+([.;:])/g, '$1')
    .replace(/([a-z0-9])\s+([1-9]\.)/g, '$1\n\n$2')
    .replace(/([.;])\s+([A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ])/g, '$1\n\n$2')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  const numberedSections = normalized.match(/(?:^|\n\n)([1-9]\..*?)(?=\n\n[1-9]\.|$)/gs)
  if (numberedSections && numberedSections.length > 0) {
    const firstNumberedIndex = normalized.search(/\b1\./)
    const intro = firstNumberedIndex > 0 ? normalized.slice(0, firstNumberedIndex).trim() : ''

    return {
      intro: intro ? intro.split('\n\n').filter(Boolean) : [],
      sections: numberedSections.map(section => section.trim()),
    }
  }

  return {
    intro: normalized.split('\n\n').filter(Boolean),
    sections: [],
  }
}

function extractNarrativeHighlights(text, notice = {}) {
  const specs = [
    { label: 'Contract Reference', patterns: [/Identifica[cç][aã]o do Contrato No:?\s*([^.\n]+)/i, /Contract No:?\s*([^.\n]+)/i] },
    { label: 'Financing', patterns: [/Cr[eé]dito IDA\s*([0-9A-Z -]+)/i, /Donativo IDA\s*N\.?o\s*([^.\n]+)/i] },
    { label: 'Project Number', patterns: [/Projecto N\.?o\s*([A-Z0-9-]+)/i, /Project N\.?o\s*([A-Z0-9-]+)/i] },
    { label: 'Beneficiary', patterns: [/Benefici[aá]rio:?\s*([^.\n]+)/i, /Beneficiary:?\s*([^.\n]+)/i] },
    { label: 'Bid Submission Deadline', patterns: [/at[eé]\s+[aà]s\s+([0-9:]+)\s+horas\s+do\s+dia\s+([^.]+?202[0-9])/i] },
    { label: 'Bid Opening', patterns: [/abertas .*? [aà]s\s+([0-9:]+)\s+horas\s+do\s+dia\s+([^.]+?202[0-9])/i] },
    { label: 'Bid Validity', patterns: [/v[aá]lidas?\s+pelo\s+per[ií]odo\s+de\s+([^.\n]+)/i] },
    { label: 'Bid Security', patterns: [/Garantia Banc[aá]ria Provis[oó]ria no valor de\s*([^,]+(?:,[^.\n]+)?)/i] },
    { label: 'Office Hours', patterns: [/entre as\s+([0-9:]{1,5}h?)\s+[aà]\s+([0-9:]{1,5}h?)/i] },
    { label: 'Address', patterns: [/O endere[cç]o acima referido:?\s*(.+)$/i] },
  ]

  const highlights = []

  for (const spec of specs) {
    for (const pattern of spec.patterns) {
      const match = text.match(pattern)
      if (!match) continue

      let value = null
      if (spec.label === 'Bid Submission Deadline' || spec.label === 'Bid Opening') {
        value = `${match[1]} on ${match[2].trim()}`
      } else if (spec.label === 'Office Hours') {
        value = `${match[1]} to ${match[2]}`
      } else {
        value = match[1]?.trim()
      }

      if (value) {
        highlights.push({ label: spec.label, value })
        break
      }
    }
  }

  const noticeEmails = extractEmails(text)
  const primaryEmail = notice.contact_email?.trim().toLowerCase()

  if (noticeEmails.length > 0) {
    const alternateEmails = noticeEmails.filter(email => email.toLowerCase() !== primaryEmail)
    if (alternateEmails.length > 0) {
      highlights.push({
        label: alternateEmails.length === 1 ? 'Notice Email' : 'Notice Emails',
        value: alternateEmails.join(', '),
      })
    } else if (!primaryEmail) {
      highlights.push({
        label: noticeEmails.length === 1 ? 'Contact Email' : 'Contact Emails',
        value: noticeEmails.join(', '),
      })
    }
  }

  return highlights
}

function extractProcurementMethod(text, noticeType) {
  const explicitPatterns = [
    /RFQ-Request for Quotations/i,
    /RFB-Request for Bids/i,
    /IFB-Invitation for Bids/i,
    /Request for Quotations/i,
    /Request for Bids/i,
    /Expression of Interest/i,
    /CONCURSO P[ÚU]BLICO(?:\s*\([^)]*\))?/i,
    /convida[^.]{0,120}\bpropostas seladas\b/i,
  ]

  for (const pattern of explicitPatterns) {
    const match = text.match(pattern)
    if (match) return match[0].trim()
  }

  if (noticeType === 'IFB') return 'Invitation for Bids'
  if (noticeType === 'REOI') return 'Expression of Interest'
  return null
}

function getNoticeFallbackDetails(notice) {
  const text = stripHtml(notice.description || '')
  if (!text) {
    return {
      projectName: notice.project_name || null,
      procurementMethod: notice.procurement_method || null,
      contractAmount: notice.contract_amount ? `${notice.currency || ''} ${Number(notice.contract_amount).toLocaleString()}`.trim() : null,
      contactEmail: notice.contact_email || null,
    }
  }

  const awardRows = isAwardNotice(text, notice.notice_type) ? parseAwardText(text) : []
  const fallbackProject = cleanProjectValue(findRowValue(awardRows, 'Project'))
  const fallbackMethod = findRowValue(awardRows, 'Procurement Method') || extractProcurementMethod(text, notice.notice_type)
  const fallbackAmount = findRowValue(awardRows, 'Signed Contract Price') || findRowValue(awardRows, 'Contract Amount')
  const fallbackEmail = extractContactEmail(text)

  return {
    projectName: notice.project_name || fallbackProject,
    procurementMethod: notice.procurement_method || fallbackMethod,
    contractAmount: notice.contract_amount ? `${notice.currency || ''} ${Number(notice.contract_amount).toLocaleString()}`.trim() : fallbackAmount,
    contactEmail: notice.contact_email || fallbackEmail,
  }
}

function StructuredDescription({ html, noticeType, contactEmail }) {
  const text = stripHtml(html || '')

  if (!text) {
    return <div style={{ fontSize: 13, color: 'var(--text2)' }}>No description available.</div>
  }

  if (!isAwardNotice(text, noticeType)) {
    const formatted = formatNarrativeNotice(text)
    const highlights = extractNarrativeHighlights(text, { contact_email: contactEmail })
    return (
      <div style={{ maxWidth: 860 }}>
        {highlights.length > 0 && (
          <div style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: 16,
            marginBottom: 16
          }}>
            <div style={{
              fontSize: 11,
              color: 'var(--accent2)',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: 10
            }}>
              Notice Highlights
            </div>
            {highlights.map((item, index) => (
              <div
                key={index}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '210px 1fr',
                  gap: 12,
                  padding: '6px 0',
                  borderTop: index === 0 ? '1px solid rgba(255,255,255,0.05)' : '1px solid rgba(255,255,255,0.05)'
                }}
              >
                <div style={{
                  fontSize: 11,
                  color: 'var(--text3)',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em'
                }}>
                  {item.label}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6 }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>
        )}

        {formatted.intro.map((block, index) => (
          <div
            key={`intro-${index}`}
            style={{
              fontSize: 13, color: 'var(--text2)', lineHeight: 1.8,
              padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.04)',
              whiteSpace: 'pre-wrap'
            }}
          >
            {block}
          </div>
        ))}

        {formatted.sections.map((section, index) => {
          const numberMatch = section.match(/^([1-9]\.)\s*(.*)$/s)
          const sectionNumber = numberMatch?.[1] || ''
          const sectionBody = numberMatch?.[2] || section

          return (
            <div
              key={`section-${index}`}
              style={{
                display: 'grid',
                gridTemplateColumns: '44px 1fr',
                gap: 14,
                padding: '12px 0',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                alignItems: 'start'
              }}
            >
              <div style={{
                fontSize: 11,
                color: 'var(--accent2)',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                letterSpacing: '0.06em',
                paddingTop: 2
              }}>
                {sectionNumber}
              </div>
              <div style={{
                fontSize: 13,
                color: 'var(--text2)',
                lineHeight: 1.85,
                whiteSpace: 'pre-wrap'
              }}>
                {sectionBody}
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  const rows = parseAwardText(text)

  return (
    <div style={{ maxWidth: 860 }}>
      {rows.map((row, index) => {
        if (row.type === 'heading') {
          return (
            <div key={index} style={{
              fontSize: 13, fontWeight: 700, color: 'var(--accent)',
              padding: '8px 0 4px', borderBottom: '2px solid var(--accent)',
              marginBottom: 8, fontFamily: 'var(--font-head)',
              textTransform: 'uppercase', letterSpacing: '0.06em'
            }}>
              {row.label}
            </div>
          )
        }

        if (row.type === 'section') {
          return (
            <div key={index} style={{
              fontSize: 11, fontWeight: 700, color: 'var(--accent2)',
              padding: '12px 0 4px',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase', letterSpacing: '0.08em',
              borderTop: index > 0 ? '1px solid var(--border)' : 'none',
              marginTop: 4,
            }}>
              {row.label}
            </div>
          )
        }

        if (row.type === 'field') {
          return (
            <div key={index} style={{
              display: 'grid', gridTemplateColumns: '220px 1fr',
              gap: 12, padding: '6px 0',
              borderBottom: '1px solid var(--border)',
            }}>
              <div style={{
                fontSize: 11, color: 'var(--text3)',
                fontFamily: 'var(--font-mono)', fontWeight: 600,
                paddingTop: 1, textTransform: 'uppercase', letterSpacing: '0.04em',
              }}>
                {row.label}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6 }}>
                {row.value || '--'}
              </div>
            </div>
          )
        }

        if (row.type === 'bidder') {
          return (
            <div key={index} style={{
              border: '1px solid var(--border)',
              borderRadius: 12,
              background: 'rgba(255,255,255,0.02)',
              padding: 16,
              margin: '10px 0 0 0'
            }}>
              <div style={{
                fontSize: 13,
                fontWeight: 700,
                color: 'var(--text)',
                marginBottom: row.fields.length ? 12 : 0,
                lineHeight: 1.6
              }}>
                {row.name || '--'}
              </div>

              {row.fields.map((field, fieldIndex) => (
                <div key={fieldIndex} style={{
                  display: 'grid',
                  gridTemplateColumns: '180px 1fr',
                  gap: 12,
                  padding: '5px 0',
                  borderTop: fieldIndex === 0 ? '1px solid rgba(255,255,255,0.05)' : '1px solid rgba(255,255,255,0.05)'
                }}>
                  <div style={{
                    fontSize: 11, color: 'var(--text3)',
                    fontFamily: 'var(--font-mono)', fontWeight: 600,
                    textTransform: 'uppercase', letterSpacing: '0.04em',
                    paddingTop: 1
                  }}>
                    {field.label}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.6 }}>
                    {field.value}
                  </div>
                </div>
              ))}
            </div>
          )
        }

        return (
          <div
            key={index}
            style={{
              fontSize: 13, color: 'var(--text2)', lineHeight: 1.8,
              padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.04)',
              whiteSpace: 'pre-wrap'
            }}
          >
            {row.text}
          </div>
        )
      })}
    </div>
  )
}

function ExportButton({ filters, total }) {
  const noticeFieldOptions = [
    { key: 'country', label: 'Country', width: 15 },
    { key: 'notice_type', label: 'Notice Type', width: 16 },
    { key: 'status', label: 'Status', width: 12 },
    { key: 'title', label: 'Opportunity Title', width: 50 },
    { key: 'project_id', label: 'Project ID', width: 18 },
    { key: 'project_name', label: 'Project Name', width: 40 },
    { key: 'procurement_method', label: 'Procurement Method', width: 25 },
    { key: 'borrower', label: 'Host Institution', width: 35 },
    { key: 'notice_date', label: 'Notice Date', width: 15 },
    { key: 'submission_date', label: 'Submission Deadline', width: 20 },
    { key: 'contract_amount', label: 'Contract Amount', width: 20 },
    { key: 'currency', label: 'Currency', width: 10 },
    { key: 'contact_email', label: 'Contact Email', width: 30 },
    { key: 'url', label: 'World Bank Link', width: 25 },
    { key: 'bidders', label: 'Bidders', width: 40 },
    { key: 'overview', label: 'Overview', width: 60 },
    { key: 'requirements', label: 'Requirements', width: 60 },
    { key: 'description', label: 'Description', width: 60 },
    { key: 'fetched_at', label: 'Fetched Date', width: 18 },
    { key: 'opportunity_id', label: 'Opportunity ID', width: 20 },
    { key: 'is_tech', label: 'Tech Opportunity', width: 14 },
    { key: 'tech_category', label: 'Tech Category', width: 28 },
  ]
  const bidderFieldOptions = [
    { key: 'country', label: 'Country', width: 15 },
    { key: 'notice_type', label: 'Notice Type', width: 16 },
    { key: 'status', label: 'Status', width: 12 },
    { key: 'title', label: 'Opportunity Title', width: 50 },
    { key: 'project_id', label: 'Project ID', width: 18 },
    { key: 'project_name', label: 'Project Name', width: 40 },
    { key: 'procurement_method', label: 'Procurement Method', width: 25 },
    { key: 'borrower', label: 'Host Institution', width: 35 },
    { key: 'notice_date', label: 'Notice Date', width: 15 },
    { key: 'submission_date', label: 'Submission Deadline', width: 20 },
    { key: 'overview', label: 'Overview', width: 60 },
    { key: 'requirements', label: 'Requirements', width: 60 },
    { key: 'bidder_name', label: 'Bidder Name', width: 40 },
    { key: 'bidder_country', label: 'Bidder Country', width: 20 },
    { key: 'bidder_status', label: 'Bidder Status', width: 18 },
    { key: 'won', label: 'Won', width: 10 },
    { key: 'bid_price_at_opening', label: 'Bid Price at Opening', width: 20 },
    { key: 'opening_currency', label: 'Opening Bid Currency', width: 16 },
    { key: 'evaluated_bid_price', label: 'Evaluated Bid Price', width: 20 },
    { key: 'evaluated_bid_currency', label: 'Evaluated Bid Currency', width: 18 },
    { key: 'final_evaluation_price', label: 'Final Evaluation Price', width: 20 },
    { key: 'final_evaluation_currency', label: 'Final Evaluation Currency', width: 18 },
    { key: 'winner_contract_amount', label: 'Contract Amount (Winner Only)', width: 24 },
    { key: 'winner_contract_currency', label: 'Contract Currency', width: 16 },
    { key: 'contact_email', label: 'Contact Email', width: 30 },
    { key: 'url', label: 'World Bank Link', width: 25 },
    { key: 'opportunity_id', label: 'Opportunity ID', width: 20 },
    { key: 'is_tech', label: 'Tech Opportunity', width: 14 },
    { key: 'tech_category', label: 'Tech Category', width: 28 },
  ]
  const noticeDefaultFields = [
    'country', 'notice_type', 'status', 'title', 'project_id',
    'project_name', 'procurement_method', 'borrower', 'notice_date',
    'submission_date', 'contract_amount', 'currency', 'contact_email', 'url'
  ]
  const bidderDefaultFields = [
    'country', 'notice_type', 'title', 'project_id', 'project_name',
    'borrower', 'notice_date', 'bidder_name', 'bidder_country',
    'bidder_status', 'won', 'evaluated_bid_price', 'evaluated_bid_currency',
    'winner_contract_amount', 'winner_contract_currency', 'url'
  ]
  const [state, setState] = useState('idle')
  const [showOptions, setShowOptions] = useState(false)
  const [showFieldSelector, setShowFieldSelector] = useState(false)
  const [pendingExportType, setPendingExportType] = useState('normal')
  const [selectedFields, setSelectedFields] = useState(bidderDefaultFields)
  const [includeTemplateDeadline, setIncludeTemplateDeadline] = useState(false)
  const availableFields = pendingExportType === 'huzalink' ? noticeFieldOptions : bidderFieldOptions

  const exportLabel = pendingExportType === 'huzalink'
    ? 'Huzalink Export'
    : pendingExportType === 'csv_custom'
      ? 'Bidder Custom CSV Export'
      : 'Bidder Custom Excel Export'

  const toggleField = (fieldKey) => {
    setSelectedFields(prev => 
      prev.includes(fieldKey) 
        ? prev.filter(f => f !== fieldKey)
        : [...prev, fieldKey]
    )
  }

  const handleExport = async (type = 'normal') => {
    if (state === 'loading') return

    setState('loading')
    const params = new URLSearchParams()
    if (filters.country) params.set('country', filters.country)
    if (filters.notice_type) params.set('notice_type', filters.notice_type)
    if (filters.status) params.set('status', filters.status)
    if (filters.from_date) params.set('from_date', filters.from_date)
    if (filters.to_date) params.set('to_date', filters.to_date)
    if (filters.search) params.set('search', filters.search)
    if (filters.tech_only) params.set('tech_only', 'true')
    params.set('type', type)
    if ((type === 'template' || type === 'template_by_country') && includeTemplateDeadline) {
      params.set('include_deadline', 'true')
    }
    
    if (type === 'huzalink' || type === 'custom' || type === 'csv_custom') {
      params.set('fields', selectedFields.join(','))
    }

    try {
      const endpoint = type === 'csv' || type === 'csv_custom' ? '/api/export/csv' : '/api/export'
      const res = await fetch(`${endpoint}?${params.toString()}`)
      if (!res.ok) throw new Error()

      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="(.+)"/)
      const filename = match ? match[1] : (type === 'csv' || type === 'csv_custom' ? 'wb_procurement.csv' : 'wb_procurement.xlsx')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')

      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
      setState('idle')
      setShowOptions(false)
      setShowFieldSelector(false)
    } catch {
      setState('error')
      setTimeout(() => {
        setState('idle')
        setShowOptions(false)
        setShowFieldSelector(false)
      }, 3000)
    }
  }

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setShowOptions(!showOptions)}
        disabled={state === 'loading' || total === 0}
        style={{
          background: state === 'error' ? '#2b0d0d' : '#0d2b1e',
          border: `1px solid ${state === 'error' ? '#ff4444' : '#00d4aa'}`,
          color: state === 'error' ? '#ff6666' : '#00d4aa',
          borderRadius: 8, padding: '8px 16px', fontSize: 13, fontWeight: 600,
          cursor: state === 'loading' || total === 0 ? 'not-allowed' : 'pointer',
          opacity: total === 0 ? 0.4 : 1,
          display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.2s', whiteSpace: 'nowrap'
        }}
      >
        {state === 'loading' ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Download size={14} />}
        {state === 'loading' ? 'Exporting...' : state === 'error' ? 'Export Failed' : `Export Options${total > 0 ? ` (${total.toLocaleString()})` : ''}`}
        <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
      </button>

      {/* Dropdown Menu */}
      {showOptions && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          marginTop: 4,
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          zIndex: 1000,
          minWidth: 220
        }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 16px',
            color: 'var(--text2)',
            fontSize: 12,
            cursor: 'pointer',
            borderBottom: '1px solid var(--border)'
          }}>
            <input
              type="checkbox"
              checked={includeTemplateDeadline}
              onChange={event => setIncludeTemplateDeadline(event.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            Include deadline in template
          </label>

          <button
            onClick={() => handleExport('normal')}
            disabled={state === 'loading'}
            style={{
              width: '100%',
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              color: 'var(--text)',
              textAlign: 'left',
              fontSize: 13,
              cursor: state === 'loading' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => {
              if (state !== 'loading') {
                e.target.style.background = 'var(--surface2)'
              }
            }}
            onMouseOut={(e) => {
              e.target.style.background = 'transparent'
            }}
          >
            <Download size={14} />
            Normal Export
          </button>

          <button
            onClick={() => { setPendingExportType('custom'); setSelectedFields(bidderDefaultFields); setShowFieldSelector(true) }}
            disabled={state === 'loading'}
            style={{
              width: '100%',
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              color: 'var(--text)',
              textAlign: 'left',
              fontSize: 13,
              cursor: state === 'loading' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => {
              if (state !== 'loading') e.target.style.background = 'var(--surface2)'
            }}
            onMouseOut={(e) => {
              e.target.style.background = 'transparent'
            }}
          >
            <Download size={14} />
            Bidder Custom Excel Export
          </button>

          <button
            onClick={() => handleExport('template')}
            disabled={state === 'loading'}
            style={{
              width: '100%',
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              color: 'var(--text)',
              textAlign: 'left',
              fontSize: 13,
              cursor: state === 'loading' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => {
              if (state !== 'loading') e.target.style.background = 'var(--surface2)'
            }}
            onMouseOut={(e) => {
              e.target.style.background = 'transparent'
            }}
          >
            <Download size={14} />
            Contractor Template Export
          </button>

          <button
            onClick={() => handleExport('template_by_country')}
            disabled={state === 'loading'}
            style={{
              width: '100%',
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              color: 'var(--text)',
              textAlign: 'left',
              fontSize: 13,
              cursor: state === 'loading' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => {
              if (state !== 'loading') e.target.style.background = 'var(--surface2)'
            }}
            onMouseOut={(e) => {
              e.target.style.background = 'transparent'
            }}
          >
            <Download size={14} />
            Contractor Template by Country
          </button>

          <div style={{ height: 1, background: 'var(--border)', margin: '0 8px' }} />

          <button
            onClick={() => handleExport('csv')}
            disabled={state === 'loading'}
            style={{
              width: '100%',
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              color: 'var(--text)',
              textAlign: 'left',
              fontSize: 13,
              cursor: state === 'loading' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => {
              if (state !== 'loading') {
                e.target.style.background = 'var(--surface2)'
              }
            }}
            onMouseOut={(e) => {
              e.target.style.background = 'transparent'
            }}
          >
            <FileDown size={14} />
            CSV Export
          </button>

          <button
            onClick={() => { setPendingExportType('csv_custom'); setSelectedFields(bidderDefaultFields); setShowFieldSelector(true) }}
            disabled={state === 'loading'}
            style={{
              width: '100%',
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              color: 'var(--text)',
              textAlign: 'left',
              fontSize: 13,
              cursor: state === 'loading' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => {
              if (state !== 'loading') e.target.style.background = 'var(--surface2)'
            }}
            onMouseOut={(e) => {
              e.target.style.background = 'transparent'
            }}
          >
            <FileDown size={14} />
            Bidder Custom CSV Export
          </button>

          <div style={{ height: 1, background: 'var(--border)', margin: '0 8px' }} />
          
          <button
            onClick={() => { setPendingExportType('huzalink'); setSelectedFields(noticeDefaultFields); setShowFieldSelector(true) }}
            disabled={state === 'loading'}
            style={{
              width: '100%',
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              color: 'var(--text)',
              textAlign: 'left',
              fontSize: 13,
              cursor: state === 'loading' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 8,
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => {
              if (state !== 'loading') {
                e.target.style.background = 'var(--surface2)'
              }
            }}
            onMouseOut={(e) => {
              e.target.style.background = 'transparent'
            }}
          >
            <Download size={14} />
            <span>Huzalink Export</span>
            <span style={{ fontSize: 10, color: 'var(--text3)' }}>⚙</span>
          </button>
        </div>
      )}

      {/* Field Selector Modal */}
      {showFieldSelector && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          zIndex: 2000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: 24,
            maxWidth: 600,
            width: '90%',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 20
            }}>
              <h3 style={{ 
                margin: 0, 
                color: 'var(--text)', 
                fontSize: 18, 
                fontWeight: 600 
              }}>
                Select Fields for {exportLabel}
              </h3>
              <button
                onClick={() => setShowFieldSelector(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text3)',
                  fontSize: 20,
                  cursor: 'pointer',
                  padding: 4
                }}
              >
                ×
              </button>
            </div>

            <div style={{ marginBottom: 16 }}>
              <button
                onClick={() => setSelectedFields(availableFields.map(f => f.key))}
                style={{
                  background: '#0d2b1e',
                  color: '#00d4aa',
                  border: '1px solid #00d4aa',
                  borderRadius: 6,
                  padding: '8px 16px',
                  fontSize: 12,
                  cursor: 'pointer',
                  marginRight: 8
                }}
              >
                Select All
              </button>
              <button
                onClick={() => setSelectedFields([])}
                style={{
                  background: '#2b0d0d',
                  color: '#ff6666',
                  border: '1px solid #ff4444',
                  borderRadius: 6,
                  padding: '8px 16px',
                  fontSize: 12,
                  cursor: 'pointer'
                }}
              >
                Clear All
              </button>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
              gap: 8,
              maxHeight: '400px',
              overflowY: 'auto',
              padding: '8px',
              border: '1px solid var(--border)',
              borderRadius: 8
            }}>
              {availableFields.map(field => (
                <label key={field.key} style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '8px',
                  cursor: 'pointer',
                  borderRadius: 4,
                  transition: 'background 0.2s'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'var(--surface2)'
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'transparent'
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedFields.includes(field.key)}
                  onChange={() => toggleField(field.key)}
                  style={{
                    marginRight: 8,
                    cursor: 'pointer'
                  }}
                />
                <span style={{ fontSize: 13 }}>{field.label}</span>
              </label>
              ))}
            </div>

            <div style={{ 
              display: 'flex', 
              justifyContent: 'flex-end', 
              gap: 12, 
              marginTop: 20 
            }}>
              <button
                onClick={() => setShowFieldSelector(false)}
                style={{
                  background: '#2b0d0d',
                  color: 'var(--text3)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  padding: '8px 16px',
                  fontSize: 12,
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => handleExport(pendingExportType)}
                disabled={selectedFields.length === 0 || state === 'loading'}
                style={{
                  background: selectedFields.length > 0 ? '#0d2b1e' : '#1a1a1a',
                  color: selectedFields.length > 0 ? '#00d4aa' : 'var(--text3)',
                  border: `1px solid ${selectedFields.length > 0 ? '#00d4aa' : 'var(--border)'}`,
                  borderRadius: 6,
                  padding: '8px 16px',
                  fontSize: 12,
                  cursor: selectedFields.length > 0 && state !== 'loading' ? 'pointer' : 'not-allowed'
                }}
              >
                {state === 'loading' ? 'Exporting...' : `Export Selected (${selectedFields.length} fields)`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Notices() {
  const [filters, setFilters] = useState({
    country: '', notice_type: '', status: '', search: '',
    from_date: '', to_date: '', tech_only: false, page: 1
  })
  const [expanded, setExpanded] = useState(null)
  const [watchlists, setWatchlists] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('wb_notice_watchlists') || '[]')
    } catch {
      return []
    }
  })

  const url = buildUrl('/api/notices', { ...filters, page_size: 25 })
  const { data, loading } = useApi(url, [url])

  const set = (key, value) => {
    setExpanded(null)
    setFilters(current => ({ ...current, [key]: value, page: 1 }))
  }

  const notices = data?.data || []
  const total = data?.total || 0
  const pages = Math.max(1, Math.ceil(total / 25))
  const countries = data?.available_countries || []
  const hasFilters = filters.country || filters.notice_type || filters.status || filters.search || filters.from_date || filters.to_date || filters.tech_only

  const persistWatchlists = (next) => {
    setWatchlists(next)
    localStorage.setItem('wb_notice_watchlists', JSON.stringify(next))
  }

  const saveWatchlist = () => {
    const name = window.prompt('Watchlist name')
    if (!name) return
    const entry = {
      id: Date.now(),
      name: name.trim(),
      filters: {
        country: filters.country,
        notice_type: filters.notice_type,
        status: filters.status,
        search: filters.search,
        from_date: filters.from_date,
        to_date: filters.to_date,
        tech_only: filters.tech_only,
      }
    }
    persistWatchlists([entry, ...watchlists.filter(item => item.name !== entry.name)].slice(0, 12))
  }

  const loadWatchlist = (watchlist) => {
    setExpanded(null)
    setFilters({ ...watchlist.filters, page: 1 })
  }

  const removeWatchlist = (id) => {
    persistWatchlists(watchlists.filter(item => item.id !== id))
  }

  const clearFilters = () => {
    setExpanded(null)
    setFilters({
      country: '', notice_type: '', status: '', search: '',
      from_date: '', to_date: '', tech_only: false, page: 1
    })
  }

  return (
    <div style={{ padding: '32px' }}>
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 32, fontWeight: 800, letterSpacing: '-1px' }}>Procurement Notices</h1>
          <p style={{ color: 'var(--text2)', marginTop: 6, fontSize: 13 }}>
            {loading ? 'Loading...' : `${total.toLocaleString()} notices found`}
          </p>
        </div>
        <div style={{ paddingTop: 4 }}>
          <ExportButton filters={filters} total={total} />
        </div>
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '16px 20px', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: watchlists.length ? 12 : 0 }}>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text)', fontWeight: 600 }}>Saved Watchlists</div>
            <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)' }}>Reuse important notice searches in one click.</div>
          </div>
          <button onClick={saveWatchlist} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 8, padding: '8px 12px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
            <BookmarkPlus size={14} />
            Save Current Filters
          </button>
        </div>
        {watchlists.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {watchlists.map(watchlist => (
              <div key={watchlist.id} style={{ display: 'flex', alignItems: 'center', gap: 6, border: '1px solid var(--border)', background: 'var(--surface2)', borderRadius: 999, padding: '5px 10px 5px 12px' }}>
                <button onClick={() => loadWatchlist(watchlist)} style={{ background: 'none', border: 'none', color: 'var(--text2)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                  {watchlist.name}
                </button>
                <button onClick={() => removeWatchlist(watchlist.id)} style={{ background: 'none', border: 'none', color: 'var(--text3)', display: 'flex', padding: 0 }}>
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '20px 24px', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 220px', display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Search</label>
            <div style={{ position: 'relative' }}>
              <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text3)' }} />
              <input
                value={filters.search}
                onChange={e => set('search', e.target.value)}
                placeholder="Title, project, description..."
                style={{ width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '7px 10px 7px 30px', fontSize: 13, outline: 'none', boxSizing: 'border-box' }}
              />
            </div>
          </div>
          <FilterSelect label="Country" value={filters.country} onChange={value => set('country', value)} options={countries} />
          <FilterSelect label="Notice Type" value={filters.notice_type} onChange={value => set('notice_type', value)} options={NOTICE_TYPE_OPTIONS} />
          <FilterSelect label="Status" value={filters.status} onChange={value => set('status', value)} options={STATUSES} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>From Date</label>
            <input
              type="date"
              value={filters.from_date}
              onChange={e => set('from_date', e.target.value)}
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '7px 10px', fontSize: 13, outline: 'none' }}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>To Date</label>
            <input
              type="date"
              value={filters.to_date}
              onChange={e => set('to_date', e.target.value)}
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '7px 10px', fontSize: 13, outline: 'none' }}
            />
          </div>
          <button
            onClick={() => set('tech_only', !filters.tech_only)}
            style={{
              background: filters.tech_only ? '#0d2b1e' : 'var(--surface2)',
              border: `1px solid ${filters.tech_only ? '#00d4aa' : 'var(--border)'}`,
              color: filters.tech_only ? '#00d4aa' : 'var(--text2)',
              borderRadius: 8, padding: '7px 12px', fontSize: 13,
              display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
              transition: 'all 0.15s'
            }}
            title="Only show tech-related opportunities"
          >
            <Cpu size={13} />
            {filters.tech_only ? 'Tech Only' : 'All Types'}
          </button>
          {hasFilters && (
            <button onClick={clearFilters} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 8, padding: '7px 14px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <X size={12} /> Clear
            </button>
          )}
        </div>

        {hasFilters && (
          <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
            {filters.country && <FilterTag label={`Country: ${filters.country}`} onRemove={() => set('country', '')} />}
            {filters.notice_type && <FilterTag label={`Type: ${filters.notice_type}`} onRemove={() => set('notice_type', '')} />}
            {filters.status && <FilterTag label={`Status: ${filters.status}`} onRemove={() => set('status', '')} />}
            {filters.search && <FilterTag label={`Search: "${filters.search}"`} onRemove={() => set('search', '')} />}
            {filters.from_date && <FilterTag label={`From: ${filters.from_date}`} onRemove={() => set('from_date', '')} />}
            {filters.to_date && <FilterTag label={`To: ${filters.to_date}`} onRemove={() => set('to_date', '')} />}
            {filters.tech_only && <FilterTag label="Tech Only" onRemove={() => set('tech_only', false)} />}
          </div>
        )}
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        <div style={{ width: '100%', overflowX: 'auto' }}>
        <table style={{ width: '100%', minWidth: 1200, borderCollapse: 'collapse', tableLayout: 'fixed' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface2)' }}>
              {['Tech', 'Country', 'Type', 'Status', 'Title', 'Project ID', 'Borrower', 'Notice Date', 'Deadline', ''].map(header => (
                <th key={header} style={{ textAlign: 'left', padding: '12px 14px', fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', fontWeight: 400, textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={10} style={{ padding: 32, textAlign: 'center', color: 'var(--text3)' }}>Loading notices...</td></tr>}
            {!loading && notices.length === 0 && (
              <tr><td colSpan={10} style={{ padding: 32, textAlign: 'center', color: 'var(--text3)' }}>No notices found. Try different filters or run the fetcher.</td></tr>
            )}
            {notices.map((notice, index) => (
              <Fragment key={notice.id}>
                {(() => {
                  const details = getNoticeFallbackDetails(notice)
                  return (
                    <>
                <tr
                  onClick={() => setExpanded(expanded === notice.id ? null : notice.id)}
                  style={{
                    borderBottom: '1px solid var(--border)',
                    background: expanded === notice.id ? 'var(--surface2)' : index % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
                    cursor: 'pointer', transition: 'background 0.1s'
                  }}
                >
                  <td style={{ padding: '11px 14px', textAlign: 'center' }}>
                    {notice.is_tech ? (
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 3,
                        fontSize: 10, fontFamily: 'var(--font-mono)',
                        background: '#0d2b1e', color: '#00d4aa',
                        padding: '2px 6px', borderRadius: 4,
                        fontWeight: 600, letterSpacing: '0.04em',
                      }} title={notice.tech_category || 'Tech'}>
                        <Cpu size={10} /> TECH
                      </span>
                    ) : (
                      <span style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)' }}>--</span>
                    )}
                  </td>
                  <td style={{ padding: '11px 14px', fontFamily: 'var(--font-mono)', fontSize: 12, whiteSpace: 'nowrap' }}>{notice.country || '--'}</td>
                  <td style={{ padding: '11px 14px' }}><Badge type={notice.notice_type} /></td>
                  <td style={{ padding: '11px 14px' }}><StatusBadge status={notice.status} /></td>
                  <td style={{ padding: '11px 14px', fontSize: 13, lineHeight: 1.45 }}>
                    <div style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }} title={notice.title}>
                      {notice.title || '--'}
                    </div>
                  </td>
                  <td style={{ padding: '11px 14px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent2)' }}>{notice.project_id || '--'}</td>
                  <td style={{ padding: '11px 14px', fontSize: 12, color: 'var(--text2)' }}>
                    <div style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }} title={notice.borrower}>
                      {notice.borrower || '--'}
                    </div>
                  </td>
                  <td style={{ padding: '11px 14px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text2)', whiteSpace: 'nowrap' }}>{notice.notice_date || '--'}</td>
                  <td style={{ padding: '11px 14px', fontFamily: 'var(--font-mono)', fontSize: 12, color: notice.submission_date ? 'var(--warn)' : 'var(--text3)', whiteSpace: 'nowrap' }}>{notice.submission_date || '--'}</td>
                  <td style={{ padding: '11px 14px' }}>
                    {notice.url && <a href={notice.url} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}><ExternalLink size={13} color="var(--text3)" /></a>}
                  </td>
                </tr>

                  {expanded === notice.id && (
                    <tr style={{ background: 'var(--surface2)', borderBottom: '1px solid var(--border)' }}>
                      <td colSpan={10} style={{ padding: '20px 28px' }}>
                      {/* Header with Logo and Title */}
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'flex-start', 
                        gap: 20, 
                        marginBottom: 24, 
                        paddingBottom: 20, 
                        borderBottom: '1px solid var(--border)' 
                      }}>
                        <div style={{ flex: 1 }}>
                          <h3 style={{ 
                            color: 'var(--text)', 
                            fontSize: 20, 
                            fontWeight: 600, 
                            marginBottom: 8, 
                            lineHeight: 1.3 
                          }}>
                            {notice.title || 'Untitled Opportunity'}
                          </h3>
                        </div>
                        {/* Institution Logo */}
                        <div style={{ 
                          width: 100, height: 80, 
                          background: 'var(--surface)', 
                          border: '1px solid var(--border)', 
                          borderRadius: 8, 
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center',
                          color: 'var(--text3)',
                          fontSize: 12,
                          fontWeight: 500
                        }}>
                          <span style={{ textAlign: 'center' }}>World Bank</span>
                        </div>
                      </div>

                      {/* Overview Section */}
                      <div style={{ marginBottom: 24 }}>
                        <h4 style={{ 
                          color: 'var(--text)', fontSize: 14, 
                          fontWeight: 600, marginBottom: 16, 
                          textTransform: 'uppercase', letterSpacing: '0.05em',
                          fontFamily: 'var(--font-mono)',
                          borderBottom: '1px solid var(--border)',
                          paddingBottom: 8
                        }}>
                          Overview
                        </h4>
                        <div style={{ 
                          background: 'var(--surface)', 
                          border: '1px solid var(--border)', 
                          borderRadius: 8, 
                          padding: 16 
                        }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <InfoField label="Country" value={notice.country} />
                            <InfoField label="Deadline" value={notice.submission_date || 'Not specified'} />
                            <InfoField label="Host Institution" value={notice.borrower || 'Not specified'} />
                            <InfoField label="Status" value={notice.status} />
                            <InfoField
                              label="Tech Classification"
                              value={notice.is_tech ? (notice.tech_category || 'Tech Related') : 'Non-Tech'}
                              valueColor={notice.is_tech ? '#00d4aa' : 'var(--text3)'}
                            />
                          </div>
                        </div>
                      </div>

                      {/* Project Details Section */}
                      <div style={{ marginBottom: 24 }}>
                        <h4 style={{ 
                          color: 'var(--text)', fontSize: 14, 
                          fontWeight: 600, marginBottom: 16, 
                          textTransform: 'uppercase', letterSpacing: '0.05em',
                          fontFamily: 'var(--font-mono)',
                          borderBottom: '1px solid var(--border)',
                          paddingBottom: 8
                        }}>
                          Project Details
                        </h4>
                        <div style={{ 
                          background: 'var(--surface)', 
                          border: '1px solid var(--border)', 
                          borderRadius: 8, 
                          padding: 16 
                        }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <InfoField label="Project Name" value={details.projectName} />
                            <InfoField label="Project ID" value={notice.project_id} />
                            <InfoField label="Contract Amount" value={details.contractAmount} />
                            <InfoField label="Currency" value={notice.currency || 'Not specified'} />
                            <InfoField label="Procurement Method" value={details.procurementMethod} />
                            <InfoField label="Contact Email" value={details.contactEmail} isEmail />
                          </div>
                        </div>
                      </div>

                      {/* Key Requirements Section */}
                      <div style={{ marginBottom: 24 }}>
                        <h4 style={{ 
                          color: 'var(--text)', fontSize: 14, 
                          fontWeight: 600, marginBottom: 16, 
                          textTransform: 'uppercase', letterSpacing: '0.05em',
                          fontFamily: 'var(--font-mono)',
                          borderBottom: '1px solid var(--border)',
                          paddingBottom: 8
                        }}>
                          Key Requirements
                        </h4>
                        <div style={{ 
                          background: 'var(--surface)', 
                          border: '1px solid var(--border)', 
                          borderRadius: 8, 
                          padding: 16 
                        }}>
                          <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text)' }}>
                            {notice.description ? (
                              <div>
                                {/* Extract requirements from description */}
                                {(() => {
                                  const desc = notice.description.replace(/<[^>]*>/g, '').toLowerCase();
                                  const requirements = [];
                                  
                                  // Look for common requirement patterns
                                  if (desc.includes('qualification')) requirements.push('Professional qualifications and certifications required');
                                  if (desc.includes('experience')) requirements.push('Relevant work experience in similar projects');
                                  if (desc.includes('financial')) requirements.push('Financial capacity and stability');
                                  if (desc.includes('technical')) requirements.push('Technical capability and expertise');
                                  if (desc.includes('equipment')) requirements.push('Necessary equipment and tools');
                                  
                                  // Add generic requirements if none found
                                  if (requirements.length === 0) {
                                    requirements.push('Compliance with World Bank procurement guidelines');
                                    requirements.push('Valid business registration and licenses');
                                    requirements.push('Proof of previous project completion');
                                    requirements.push('Technical and financial capacity');
                                    requirements.push('Submission deadline adherence');
                                  }
                                  
                                  return requirements.slice(0, 5).map((req, index) => (
                                    <div key={index} style={{ 
                                      marginBottom: 8, 
                                      paddingLeft: 16,
                                      position: 'relative',
                                      fontSize: 12
                                    }}>
                                      <span style={{ 
                                        position: 'absolute', 
                                        left: 0, 
                                        color: 'var(--accent)',
                                        fontWeight: 600
                                      }}>
                                        {index + 1}.
                                      </span>
                                      {req}
                                    </div>
                                  ));
                                })()}
                              </div>
                            ) : (
                              <div style={{ color: 'var(--text3)', fontStyle: 'italic' }}>
                                No specific requirements listed in the description
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Description Section */}
                      {notice.description && (
                        <div style={{ marginBottom: 24 }}>
                          <h4 style={{ 
                            color: 'var(--text)', fontSize: 14, 
                            fontWeight: 600, marginBottom: 16, 
                            textTransform: 'uppercase', letterSpacing: '0.05em',
                            fontFamily: 'var(--font-mono)',
                            borderBottom: '1px solid var(--border)',
                            paddingBottom: 8
                          }}>
                            Description
                          </h4>
                          <div style={{ 
                            background: 'var(--surface)', 
                            border: '1px solid var(--border)', 
                            borderRadius: 8, 
                            padding: 16,
                            maxHeight: 400,
                            overflowY: 'auto'
                          }}>
                            <StructuredDescription html={notice.description} noticeType={notice.notice_type} contactEmail={details.contactEmail} />
                          </div>
                        </div>
                      )}

                      {/* Actions Section */}
                      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 24 }}>
                        <a
                          href={notice.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            background: 'var(--accent)',
                            color: 'white',
                            border: 'none',
                            borderRadius: 8,
                            padding: '12px 24px',
                            fontSize: 14,
                            fontWeight: 600,
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            transition: 'all 0.2s ease'
                          }}
                          onMouseOver={(e) => {
                            e.target.style.background = '#0056b3'
                          }}
                          onMouseOut={(e) => {
                            e.target.style.background = 'var(--accent)'
                          }}
                        >
                          <ExternalLink size={16} />
                          View on World Bank
                        </a>
                      </div>
                    </td>
                  </tr>
                )}
                    </>
                  )
                })()}
              </Fragment>
            ))}
          </tbody>
        </table>
        </div>

        {pages > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', borderTop: '1px solid var(--border)', background: 'var(--surface2)' }}>
            <div style={{ fontSize: 12, color: 'var(--text3)', fontFamily: 'var(--font-mono)' }}>
              Page {filters.page} of {pages} | {total.toLocaleString()} total
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                disabled={filters.page <= 1}
                onClick={() => setFilters(current => ({ ...current, page: current.page - 1 }))}
                style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 6, padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, opacity: filters.page <= 1 ? 0.4 : 1, cursor: filters.page <= 1 ? 'not-allowed' : 'pointer' }}
              >
                <ChevronLeft size={13} /> Prev
              </button>
              <button
                disabled={filters.page >= pages}
                onClick={() => setFilters(current => ({ ...current, page: current.page + 1 }))}
                style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 6, padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, opacity: filters.page >= pages ? 0.4 : 1, cursor: filters.page >= pages ? 'not-allowed' : 'pointer' }}
              >
                Next <ChevronRight size={13} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
