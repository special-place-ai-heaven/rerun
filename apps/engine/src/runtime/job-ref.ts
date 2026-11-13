// A job message opens with `JOB owner/repo#123` or `JOB repo#123` on its first line; the run keeps `repo#123`.
const JOB_LINE = /^JOB (?:[A-Za-z0-9_.-]+\/)?([A-Za-z0-9_.-]+#[1-9][0-9]*)(?:\s.*)?$/

export function parseJobRef(message: string): { jobRef: string } | null {
    const firstLine = message.split(/\r?\n/, 1)[0] ?? ''
    const match = JOB_LINE.exec(firstLine)
    return match ? { jobRef: match[1] } : null
}
