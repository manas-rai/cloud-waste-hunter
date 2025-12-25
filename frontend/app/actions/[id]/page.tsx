'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'

interface Detection {
  id: number
  resource_type: string
  resource_id: string
  resource_name: string
  region: string
  confidence_score: number
  estimated_monthly_savings_inr: number
  status: string
  metadata: any
}

interface Preview {
  action: string
  resource_id: string
  resource_type: string
  dry_run: boolean
  impact: any
  risks: string[]
  recommendations: string[]
}

export default function ActionPage() {
  const params = useParams()
  const router = useRouter()
  const detectionId = params.id as string

  const [detection, setDetection] = useState<Detection | null>(null)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [loading, setLoading] = useState(true)
  const [approving, setApproving] = useState(false)

  useEffect(() => {
    // Fetch detection
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/detections/${detectionId}`)
      .then(res => res.json())
      .then(data => {
        setDetection(data)
        setLoading(false)

        // Fetch preview
        return fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/detections/${detectionId}/preview`, {
          method: 'POST',
        })
      })
      .then(res => res.json())
      .then(data => setPreview(data))
      .catch(err => {
        console.error('Failed to fetch:', err)
        setLoading(false)
      })
  }, [detectionId])

  const handleApprove = async (dryRun: boolean = false) => {
    if (!detection) return

    setApproving(true)
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/actions/${detectionId}/approve`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            approved_by: 'user@example.com', // TODO: Get from auth
            dry_run: dryRun,
          }),
        }
      )

      const result = await response.json()
      if (result.status === 'success') {
        alert(dryRun ? 'Dry run successful!' : 'Action executed successfully!')
        router.push('/detections')
      } else {
        alert('Action failed: ' + (result.action_result?.error || 'Unknown error'))
      }
    } catch (err: any) {
      alert('Failed to approve: ' + err.message)
    } finally {
      setApproving(false)
    }
  }

  const handleReject = async () => {
    if (!detection) return

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/actions/${detectionId}/reject?approved_by=user@example.com`,
        {
          method: 'POST',
        }
      )

      if (response.ok) {
        alert('Detection rejected')
        router.push('/detections')
      }
    } catch (err: any) {
      alert('Failed to reject: ' + err.message)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    )
  }

  if (!detection) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Detection not found</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link href="/detections" className="text-primary-600 hover:text-primary-700">
            ← Back to Detections
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">
            Action Center
          </h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Detection Info */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Detection Details</h2>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">Resource ID</dt>
              <dd className="mt-1 text-sm text-gray-900">{detection.resource_id}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Resource Type</dt>
              <dd className="mt-1 text-sm text-gray-900">{detection.resource_type}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Region</dt>
              <dd className="mt-1 text-sm text-gray-900">{detection.region}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Confidence Score</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {(detection.confidence_score * 100).toFixed(1)}%
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-sm font-medium text-gray-500">Estimated Monthly Savings</dt>
              <dd className="mt-1 text-2xl font-bold text-green-600">
                ₹{detection.estimated_monthly_savings_inr.toLocaleString('en-IN')}
              </dd>
            </div>
          </dl>
        </div>

        {/* Preview */}
        {preview && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Action Preview</h2>

            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Impact</h3>
              <div className="bg-gray-50 rounded p-4">
                <pre className="text-sm text-gray-800 whitespace-pre-wrap">
                  {JSON.stringify(preview.impact, null, 2)}
                </pre>
              </div>
            </div>

            {preview.risks && preview.risks.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-red-700 mb-2">Risks</h3>
                <ul className="list-disc list-inside text-sm text-red-600 space-y-1">
                  {preview.risks.map((risk, i) => (
                    <li key={i}>{risk}</li>
                  ))}
                </ul>
              </div>
            )}

            {preview.recommendations && preview.recommendations.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-blue-700 mb-2">Recommendations</h3>
                <ul className="list-disc list-inside text-sm text-blue-600 space-y-1">
                  {preview.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        {detection.status === 'pending' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
            <div className="flex gap-4">
              <button
                onClick={() => handleApprove(true)}
                disabled={approving}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {approving ? 'Processing...' : 'Dry Run'}
              </button>
              <button
                onClick={() => handleApprove(false)}
                disabled={approving}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {approving ? 'Processing...' : 'Approve & Execute'}
              </button>
              <button
                onClick={handleReject}
                disabled={approving}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
