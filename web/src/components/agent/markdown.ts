import MarkdownIt from 'markdown-it'

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
})

markdown.validateLink = (url) => {
  const normalized = url.trim().toLowerCase()
  return !/^(javascript|vbscript|file|data):/.test(normalized)
}

const defaultLinkOpen = markdown.renderer.rules.link_open
markdown.renderer.rules.link_open = (tokens, index, options, env, self) => {
  const token = tokens[index]
  token.attrSet('target', '_blank')
  token.attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen
    ? defaultLinkOpen(tokens, index, options, env, self)
    : self.renderToken(tokens, index, options)
}

function plainHeading(value: string) {
  return value
    .replace(/^\s{0,3}#{1,6}\s*/, '')
    .replace(/^\s*>\s*/, '')
    .replace(/[*_`~]/g, '')
    .trim()
}

function stripDuplicatedSummary(text: string, summary?: string | null) {
  const source = text.trim()
  const normalizedSummary = summary?.trim()
  if (!normalizedSummary || !source) return source

  const lines = source.split(/\r?\n/)
  if (lines.length && plainHeading(lines[0]) === plainHeading(normalizedSummary)) {
    return lines.slice(1).join('\n').trim()
  }
  if (source.startsWith(normalizedSummary)) {
    return source.slice(normalizedSummary.length).trim()
  }
  return source
}

export function renderAgentMarkdown(text: string, summary?: string | null) {
  const source = stripDuplicatedSummary(text, summary)
    .replace(/^•\s+/gm, '- ')
    .trim()
  return source ? markdown.render(source) : ''
}
