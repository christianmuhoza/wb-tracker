// ── StructuredDescription ─────────────────────────────────────────────────────
// Handles 3 notice types × 3 languages = 9 known formats
// Notice types : Contract Award | IFB | REOI
// Languages    : English | French | Portuguese

const FIELD_MAPS = {

  // ── CONTRACT AWARD ──────────────────────────────────────────────────────────

  award_en: [
    'Project:', 'Loan/Credit/TF Info:', 'Bid/Contract Reference No:',
    'Procurement Method:', 'Scope of Contract:', 'Notice Version No:',
    'Date Notification of Award Issued', 'Duration of Contract',
    'Awarded Bidder(s):', 'Awarded Firm(s):', 'Country:',
    'Bid Price at Opening', 'Evaluated Bid Price', 'Signed Contract price',
    'Signed Contract Price:', 'Final Evaluation Price:', 'Evaluated Bidder(s):',
    'Contact award',
  ],

  award_fr: [
    'Projet :', 'Référence du Marché :', 'Méthode de Passation :',
    'Objet du Marché :', 'Version de l\'Avis :', 'Date de Notification',
    'Durée du Contrat', 'Attributaire(s) :', 'Pays :',
    'Prix à l\'Ouverture', 'Prix Évalué', 'Prix du Contrat Signé :',
    'Prix Final Évalué :', 'Soumissionnaires Évalués :',
  ],

  award_pt: [
    'Projeto:', 'Info Empréstimo/Crédito/TF:', 'Nº de Referência da Proposta/Contrato:',
    'Método de Aquisição:', 'Âmbito do Contrato:', 'Nº da Versão do Aviso:',
    'Data da Notificação de Adjudicação', 'Duração do Contrato',
    'Proponente(s) Adjudicatário(s):', 'Empresa(s) Adjudicatária(s):', 'País:',
    'Preço da Proposta na Abertura', 'Preço da Proposta Avaliado',
    'Preço do Contrato Assinado:', 'Preço Final de Avaliação:',
    'Proponente(s) Avaliado(s):', 'Contacto adjudicação',
  ],

  // ── IFB ─────────────────────────────────────────────────────────────────────

  ifb_en: [
    'Project ID', 'Loan No', 'Credit No', 'Grant No',
    'Bid Reference No', 'Bid/Contract Reference No:', 'Contract title',
    'Country:', 'Procurement Method:', 'Scope of Contract:',
    'Bids must be delivered', 'Bid Security', 'Bid Bond',
    'Contact:', 'Address:', 'E-mail:', 'Tel:', 'Phone:',
    'Ministry of', 'Department of',
  ],

  ifb_fr: [
    'Maître d\'Ouvrage:', "Maître d'Ouvrage :",
    'Projet :', 'Intitulé du Marché:', 'Pays:', 'N° du Don :',
    'N° Appel d\'Offres:', "N° Appel d'Offres:", 'Émis le :',
    'Nom de l\'Agence d\'exécution :', "Nom de l'Agence d'exécution :",
    'Nom du responsable :', 'Bureau :', 'Adresse :',
    'Adresse électronique :', 'Lancé le', 'Le Coordonnateur',
    'Les Offres doivent être remises',
  ],

  ifb_pt: [
    'Dono da Obra:', 'Projeto :', 'Título do Contrato:', 'País:',
    'Nº do Donativo:', 'Nº do Concurso:', 'Emitido em:',
    'Nome da Agência de Execução:', 'Nome do Responsável:',
    'Escritório:', 'Endereço:', 'E-mail:', 'Lançado em',
    'As propostas devem ser entregues',
  ],

  // ── REOI ────────────────────────────────────────────────────────────────────

  reoi_en: [
    'Name of Country', 'Name of Project', 'Project ID', 'Loan No',
    'Assignment Title', 'Reference No.', 'Date of Issue',
    'E-Mail:', 'Phone:', 'Copy:', 'The address',
    'Expressions of interest', 'Consulting Services',
  ],

  reoi_fr: [
    'Nom du Pays', 'Nom du Projet', 'ID du Projet', 'Titre de la Mission',
    'Numéro de Référence', 'Date de Publication',
    'E-mail:', 'Téléphone:', 'Manifestations d\'intérêt',
    'Services de Conseil',
  ],

  reoi_pt: [
    'Nome do País', 'Nome do Projeto', 'ID do Projeto',
    'Título da Missão', 'Número de Referência', 'Data de Emissão',
    'E-mail:', 'Telefone:', 'Expressões de Interesse',
    'Serviços de Consultoria',
  ],
}

function detectFormat(text, noticeType) {
  const t = text.toLowerCase()

  // Detect language
  const isFrench = t.includes('appel d\'offres') || t.includes('soumissionnaires') ||
    t.includes('marché') || t.includes('émis le') || t.includes('maître d\'ouvrage') ||
    t.includes('manifestation') || t.includes('république')

  const isPortuguese = t.includes('adjudicatário') || t.includes('proposta') ||
    t.includes('concurso') || t.includes('donativo') || t.includes('emitido em') ||
    t.includes('república') || t.includes('ministério')

  const lang = isFrench ? 'fr' : isPortuguese ? 'pt' : 'en'

  // Detect notice type from prop or text
  const isAward = noticeType === 'Award' ||
    t.includes('award') || t.includes('adjudicatário') ||
    t.includes('attributaire') || t.includes('awarded')

  const isREOI = noticeType === 'REOI' ||
    t.includes('expression of interest') || t.includes('manifestation d\'intérêt') ||
    t.includes('expressões de interesse') || t.includes('reoi')

  const type = isAward ? 'award' : isREOI ? 'reoi' : 'ifb'

  return FIELD_MAPS[`${type}_${lang}`] || FIELD_MAPS[`ifb_en`]
}

function stripHtml(html) {
  return html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<\/li>/gi, '\n')
    .replace(/<li>/gi, '• ')
    .replace(/<strong>(.*?)<\/strong>/gi, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&ndash;/g, '–')
    .replace(/&amp;/g, '&')
    .replace(/&ldquo;|&rdquo;/g, '"')
    .replace(/&rsquo;|&lsquo;/g, "'")
    .replace(/\*{2,}/g, ' ')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export function StructuredDescription({ html, noticeType }) {
  if (!html) return null

  const text     = stripHtml(html)
  const markers  = detectFormat(text, noticeType)

  // Build regex to split on known field markers
  const escaped  = markers.map(m => m.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  const splitter = new RegExp(`(?=${escaped})`, 'g')
  const chunks   = text.split(splitter).map(s => s.trim()).filter(Boolean)

  // Need at least 3 chunks to be worth treating as structured
  if (chunks.length >= 3) {
    return (
      <div style={{ maxWidth: 860 }}>
        {chunks.map((chunk, i) => {
          // Find first colon that looks like a field separator (not too far in)
          const colonIdx = chunk.search(/:\s/)
          if (colonIdx > 0 && colonIdx < 90) {
            const key = chunk.slice(0, colonIdx).trim()
            const val = chunk.slice(colonIdx + 1).trim()
            if (key && val) {
              return (
                <div key={i} style={{
                  display: 'grid',
                  gridTemplateColumns: '220px 1fr',
                  gap: 12,
                  padding: '7px 0',
                  borderBottom: '1px solid var(--border)',
                }}>
                  <div style={{
                    fontSize: 11,
                    color: 'var(--text3)',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 600,
                    paddingTop: 2,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}>
                    {key}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.7 }}>
                    {val}
                  </div>
                </div>
              )
            }
          }
          // Narrative / paragraph chunk
          return (
            <div key={i} style={{
              fontSize: 13,
              color: 'var(--text2)',
              lineHeight: 1.8,
              padding: '6px 0',
              borderBottom: i < chunks.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
            }}>
              {chunk}
            </div>
          )
        })}
      </div>
    )
  }

  // Fallback: clean paragraph rendering for pure narrative text
  const paragraphs = text.split('\n').map(l => l.trim()).filter(Boolean)
  return (
    <div style={{ maxWidth: 860 }}>
      {paragraphs.map((para, i) => (
        <p key={i} style={{
          fontSize: 13,
          color: 'var(--text2)',
          lineHeight: 1.8,
          margin: '0 0 8px 0',
        }}>
          {para}
        </p>
      ))}
    </div>
  )
}