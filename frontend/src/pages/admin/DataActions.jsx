import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api'
import {
  PrimaryButton,
  SectionHeader,
  SecondaryButton,
  StatusMessage,
  SurfaceCard,
} from '../../components/forms-ui'
import { useAuth } from '../../context/AuthContext'
import { adminDashboardPath, adminLoginPath } from '../../paths'

export default function DataActions() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [notice, setNotice] = useState(null)
  const [error, setError] = useState(null)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    if (!token) {
      navigate(adminLoginPath(), { replace: true })
    }
  }, [token, navigate])

  async function downloadExport() {
    setExporting(true)
    setError(null)
    setNotice(null)
    try {
      const response = await api.get('/responses/export', { responseType: 'blob' })
      const exportedCount = response.headers['x-exported-count']
      const blob = new Blob([response.data], {
        type: 'application/vnd.ms-excel.sheet.macroEnabled.12',
      })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `hatecrime-export-${new Date().toISOString().slice(0, 10)}.xlsm`
      anchor.click()
      URL.revokeObjectURL(url)
      setNotice(
        exportedCount
          ? `Exported ${exportedCount} submission(s) as Excel (.xlsm).`
          : 'Export downloaded as Excel (.xlsm).',
      )
    } catch (err) {
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text()
          const parsed = JSON.parse(text)
          setError(parsed?.detail || 'Export failed.')
          return
        } catch {
          /* fall through */
        }
      }
      setError(err?.response?.data?.detail || err?.message || 'Export failed.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Data"
        title="Data actions"
        description="Export submissions for reporting or update analytics."
      />

      <SurfaceCard className="max-w-3xl space-y-4">
        <div className="flex flex-wrap gap-3">
          <PrimaryButton type="button" onClick={downloadExport} disabled={exporting}>
            {exporting ? 'Exporting…' : 'Export all responses (Xlsm)'}
          </PrimaryButton>
          <SecondaryButton type="button" onClick={() => navigate(adminDashboardPath('analytics'))}>
            Update analytics dashboard
          </SecondaryButton>
        </div>

        {notice && <StatusMessage tone="success">{notice}</StatusMessage>}
        {error && <StatusMessage tone="error">{error}</StatusMessage>}
      </SurfaceCard>
    </div>
  )
}
