const SECTION_CONFIG = [
  ['professional_insights', '1. Professional Insights'],
  ['interest_insights', '2. Interest Insights'],
  ['knowledge_and_expertise', '3. Knowledge and Expertise'],
  ['company_insights', '4. Company Insights'],
  ['recent_activities', '5. Recent Activities'],
  ['business_insights', '6. Business Insights'],
  ['key_takeaways', '7. Key Takeaways'],
];

function slugifyName(name) {
  return String(name || 'report')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'report';
}

function dateStamp() {
  return new Date().toISOString().slice(0, 10);
}

function csvEscape(val) {
  if (val === null || val === undefined) return '';
  const str = String(val).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  if (/[",\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function toCsvText(headers, rows) {
  const lines = [headers.map(csvEscape).join(',')];
  for (const row of rows) {
    lines.push(headers.map((h) => csvEscape(row[h])).join(','));
  }
  // Prefix UTF-8 BOM so Microsoft Excel renders Unicode characters cleanly
  return '\uFEFF' + lines.join('\r\n');
}

export function triggerBrowserDownload(filename, content, mimeType) {
  if (typeof document === 'undefined' || typeof Blob === 'undefined') return;
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function buildPersonMarkdown({ person, appearances = [], sources = [], insightsReport = null }) {
  if (!person) return '';
  const validApps = (appearances || []).filter((a) => a.identity_status !== 'REJECTED');
  const verifiedCount = validApps.filter((a) => a.identity_status === 'VERIFIED').length;
  const linkedinProf = (person.social_profiles || []).find((p) => p.platform === 'linkedin');
  const experiences = Array.isArray(person.experiences) ? person.experiences : [];
  const education = Array.isArray(person.education) ? person.education : [];
  const projects = Array.isArray(person.projects) ? person.projects : [];
  const skills = Array.isArray(person.skills) ? person.skills : [];
  const certifications = Array.isArray(person.certifications) ? person.certifications : [];

  const md = [];
  md.push(`## ${person.name}`);
  md.push('');
  md.push(`- **Profession / Role:** ${person.profession || 'N/A'}`);
  if (person.headline) md.push(`- **LinkedIn Headline:** ${person.headline}`);
  if (person.occupation) md.push(`- **Current Occupation:** ${person.occupation}`);
  if (person.location) md.push(`- **Location:** ${person.location}`);
  if (linkedinProf?.profile_url) {
    md.push(`- **LinkedIn Profile:** [${linkedinProf.profile_url}](${linkedinProf.profile_url}) (\`${linkedinProf.verification_status}\`)`);
  }
  if (person.follower_count != null || person.connections != null) {
    md.push(
      `- **Network Reach:** Followers: \`${person.follower_count ?? 'N/A'}\` | Connections: \`${person.connections ?? 'N/A'}\``
    );
  }
  md.push(
    `- **Coverage:** Enrichment \`${person.enrichment_status || 'NOT_ENRICHED'}\` | \`${validApps.length}\` Appearances (\`${verifiedCount}\` Verified) | \`${sources.length}\` Sources`
  );
  if (person.biography) md.push(`- **Profile Bio:** ${person.biography}`);
  if (person.summary) md.push(`- **LinkedIn Summary:** ${person.summary}`);
  md.push('');

  if (experiences.length > 0) {
    md.push(`### Career Experience (${experiences.length})`);
    md.push('| Role | Company | Period |');
    md.push('| :--- | :--- | :--- |');
    for (const exp of experiences) {
      const period = `${exp.start_date || '?'} - ${exp.end_date || (exp.is_current ? 'Present' : '?')}`;
      md.push(`| ${exp.title || 'Role'} | ${exp.company || 'Organization'} | ${period} |`);
    }
    md.push('');
  }

  if (education.length > 0) {
    md.push(`### Education (${education.length})`);
    for (const edu of education) {
      const parts = [edu.school, edu.degree_name, edu.field_of_study].filter(Boolean);
      md.push(`- **${parts.join(' — ')}**`);
    }
    md.push('');
  }

  if (projects.length > 0) {
    md.push(`### Projects & Initiatives (${projects.length})`);
    for (const proj of projects) {
      md.push(`- **${proj.title || 'Project'}**${proj.description ? `: ${proj.description}` : ''}`);
    }
    md.push('');
  }

  if (skills.length > 0) {
    md.push(`### Skills`);
    md.push(skills.join(', '));
    md.push('');
  }

  if (certifications.length > 0) {
    md.push(`### Certifications`);
    for (const cert of certifications) {
      md.push(`- ${cert.name || cert.title || 'Certification'}`);
    }
    md.push('');
  }

  const reportPayload = insightsReport?.report;
  if (insightsReport && reportPayload) {
    md.push(
      `### AI Insights Report (\`${insightsReport.model_name}\` | \`${insightsReport.prompt_version}\` | ${insightsReport.source_count} sources | ${insightsReport.generation_time_seconds}s)`
    );
    md.push('');
    if (reportPayload.executive_overview) {
      md.push(`> **Executive Overview:** ${reportPayload.executive_overview}`);
      md.push('');
    }
    for (const [key, label] of SECTION_CONFIG) {
      const sec = reportPayload[key] || {};
      md.push(`#### ${label}`);
      if (sec.summary) md.push(`*${sec.summary}*`);
      if (sec.insufficient_evidence && sec.insufficient_evidence_note) {
        md.push(`- **Insufficient Evidence:** ${sec.insufficient_evidence_note}`);
      }
      for (const item of sec.items || []) {
        const srcs = (item.supporting_sources || []).map((s) => {
          const title = s.title || s.source_type || 'Source';
          const dt = s.published_at ? ` (${s.published_at})` : '';
          return s.url ? `[${title}](${s.url})${dt}` : `${title}${dt}`;
        });
        const srcText = srcs.length > 0 ? ` — Sources: ${srcs.join(', ')}` : '';
        md.push(
          `- **${item.title}** (\`${item.claim_type}\`, \`${item.confidence}\` Confidence): ${item.detail}${srcText}`
        );
      }
      md.push('');
    }
  } else {
    md.push('### AI Insights Report');
    md.push('- *No AI Insights report generated yet for this target.*');
    md.push('');
  }

  if (validApps.length > 0) {
    md.push(`### Public Appearances (${validApps.length})`);
    md.push('| Status | Score | Type | Publisher | Title / Link |');
    md.push('| :--- | :---: | :--- | :--- | :--- |');
    for (const app of validApps) {
      const firstUrl = app.sources?.[0]?.source_url || '';
      const cleanTitle = String(app.title || 'Appearance').replace(/\|/g, '-').trim();
      const titleCell = firstUrl ? `[${cleanTitle}](${firstUrl})` : cleanTitle;
      const cleanPub = String(app.publisher || 'Web').replace(/\|/g, '-');
      md.push(
        `| \`${app.identity_status}\` | \`${app.confidence_score}\` | \`${app.appearance_type}\` | ${cleanPub} | ${titleCell} |`
      );
    }
    md.push('');
  }

  return md.join('\n');
}

const CSV_HEADERS = [
  'Person',
  'Record_Category',
  'Section_or_Type',
  'Status_or_Claim',
  'Confidence_or_Score',
  'Date_or_Period',
  'Organization_or_Publisher',
  'Title',
  'Details',
  'URLs',
];

export function buildPersonCsvRows({ person, appearances = [], insightsReport = null }) {
  if (!person) return [];
  const rows = [];
  const name = person.name || '';
  const validApps = (appearances || []).filter((a) => a.identity_status !== 'REJECTED');
  const linkedinProf = (person.social_profiles || []).find((p) => p.platform === 'linkedin');
  const reportPayload = insightsReport?.report;

  rows.push({
    Person: name,
    Record_Category: 'Profile',
    Section_or_Type: person.profession || '',
    Status_or_Claim: person.enrichment_status || 'NOT_ENRICHED',
    Confidence_or_Score: person.follower_count != null ? `${person.follower_count} followers` : '',
    Date_or_Period: person.location || '',
    Organization_or_Publisher: person.occupation || '',
    Title: person.headline || person.name,
    Details: reportPayload?.executive_overview || person.biography || person.summary || '',
    URLs: linkedinProf?.profile_url || '',
  });

  for (const exp of person.experiences || []) {
    rows.push({
      Person: name,
      Record_Category: 'LinkedIn Experience',
      Section_or_Type: exp.is_current ? 'Current Role' : 'Past Role',
      Status_or_Claim: 'VERIFIED_FACT',
      Confidence_or_Score: '',
      Date_or_Period: `${exp.start_date || '?'} - ${exp.end_date || (exp.is_current ? 'Present' : '?')}`,
      Organization_or_Publisher: exp.company || '',
      Title: exp.title || '',
      Details: exp.description || '',
      URLs: exp.company_linkedin_profile_url || '',
    });
  }

  for (const edu of person.education || []) {
    rows.push({
      Person: name,
      Record_Category: 'LinkedIn Education',
      Section_or_Type: edu.field_of_study || '',
      Status_or_Claim: 'VERIFIED_FACT',
      Confidence_or_Score: '',
      Date_or_Period: `${edu.start_date || ''}${edu.end_date ? ` - ${edu.end_date}` : ''}`,
      Organization_or_Publisher: edu.school || '',
      Title: edu.degree_name || '',
      Details: edu.description || '',
      URLs: edu.school_linkedin_profile_url || '',
    });
  }

  for (const proj of person.projects || []) {
    rows.push({
      Person: name,
      Record_Category: 'LinkedIn Project',
      Section_or_Type: 'Initiative',
      Status_or_Claim: 'VERIFIED_FACT',
      Confidence_or_Score: '',
      Date_or_Period: `${proj.start_date || ''}${proj.end_date ? ` - ${proj.end_date}` : ''}`,
      Organization_or_Publisher: '',
      Title: proj.title || '',
      Details: proj.description || '',
      URLs: proj.url || '',
    });
  }

  if (reportPayload) {
    for (const [key, label] of SECTION_CONFIG) {
      const sec = reportPayload[key];
      if (!sec) continue;
      for (const item of sec.items || []) {
        rows.push({
          Person: name,
          Record_Category: 'AI Insight',
          Section_or_Type: label,
          Status_or_Claim: item.claim_type || '',
          Confidence_or_Score: item.confidence || '',
          Date_or_Period: insightsReport.generated_at ? String(insightsReport.generated_at).slice(0, 10) : '',
          Organization_or_Publisher: item.sub_category || '',
          Title: item.title || '',
          Details: item.detail || '',
          URLs: (item.supporting_sources || []).map((s) => s.url || s.title).filter(Boolean).join(' | '),
        });
      }
    }
  }

  for (const app of validApps) {
    rows.push({
      Person: name,
      Record_Category: 'Public Appearance',
      Section_or_Type: app.appearance_type || '',
      Status_or_Claim: app.identity_status || '',
      Confidence_or_Score: app.confidence_score ?? '',
      Date_or_Period: app.published_at ? String(app.published_at).slice(0, 10) : '',
      Organization_or_Publisher: app.publisher || '',
      Title: app.title || '',
      Details: app.analysis?.summary || app.description || '',
      URLs: (app.sources || []).map((s) => s.source_url).filter(Boolean).join(' | '),
    });
  }

  return rows;
}

export function downloadPersonReport({ format, person, appearances = [], sources = [], insightsReport = null }) {
  if (!person) return;
  const base = `${slugifyName(person.name)}-intelligence-${dateStamp()}`;

  if (format === 'csv') {
    const csv = toCsvText(CSV_HEADERS, buildPersonCsvRows({ person, appearances, insightsReport }));
    triggerBrowserDownload(`${base}.csv`, csv, 'text/csv;charset=utf-8;');
    return;
  }

  if (format === 'md') {
    const md = [
      `# Intelligence Briefing — ${person.name}`,
      `*Exported from Leadzen Intelligence on ${dateStamp()}*`,
      '',
      buildPersonMarkdown({ person, appearances, sources, insightsReport }),
    ].join('\n');
    triggerBrowserDownload(`${base}.md`, md, 'text/markdown;charset=utf-8;');
    return;
  }

  if (format === 'json') {
    const payload = {
      exported_at: new Date().toISOString(),
      person,
      ai_insights: insightsReport,
      appearances: (appearances || []).filter((a) => a.identity_status !== 'REJECTED'),
      sources,
    };
    triggerBrowserDownload(`${base}.json`, JSON.stringify(payload, null, 2), 'application/json;charset=utf-8;');
  }
}

export function downloadAllTargetsReport({ format, bundles = [] }) {
  if (!bundles.length) return;
  const base = `leadzen-all-targets-intelligence-${dateStamp()}`;

  if (format === 'csv') {
    const allRows = bundles.flatMap((b) => buildPersonCsvRows(b));
    triggerBrowserDownload(`${base}.csv`, toCsvText(CSV_HEADERS, allRows), 'text/csv;charset=utf-8;');
    return;
  }

  if (format === 'md') {
    const parts = [
      '# Executive Intelligence Portfolio — All Targets',
      `*Exported from Leadzen Intelligence on ${dateStamp()} across ${bundles.length} profile(s)*`,
      '',
      '| Person | Role / Profession | Enriched | Appearances | AI Insights Model |',
      '| :--- | :--- | :---: | :---: | :--- |',
      ...bundles.map(({ person, appearances = [], insightsReport = null }) => {
        const validCount = appearances.filter((a) => a.identity_status !== 'REJECTED').length;
        return `| **${person.name}** | ${person.profession || 'N/A'} | \`${person.enrichment_status || 'NOT_ENRICHED'}\` | \`${validCount}\` | \`${insightsReport?.model_name || 'Not generated'}\` |`;
      }),
      '',
      '---',
      '',
      ...bundles.map((b) => `${buildPersonMarkdown(b)}\n---\n`),
    ];
    triggerBrowserDownload(`${base}.md`, parts.join('\n'), 'text/markdown;charset=utf-8;');
    return;
  }

  if (format === 'json') {
    const payload = {
      exported_at: new Date().toISOString(),
      total_targets: bundles.length,
      targets: bundles.map(({ person, appearances = [], sources = [], insightsReport = null }) => ({
        person,
        ai_insights: insightsReport,
        appearances: appearances.filter((a) => a.identity_status !== 'REJECTED'),
        sources,
      })),
    };
    triggerBrowserDownload(`${base}.json`, JSON.stringify(payload, null, 2), 'application/json;charset=utf-8;');
  }
}

