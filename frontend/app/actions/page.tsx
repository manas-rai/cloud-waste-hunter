'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Detection {
  id: number
  resource_type: string
  resource_id: string
  resource_name: string | null
  region: string
  confidence_score: number
  estimated_monthly_savings_inr: number
  status: string
  approved_by: string | null
  approved_at: string | null
  created_at: string
}

export default function ActionsPage() {
  const [detections, setDetections] = useState<Detection[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [batchProcessing, setBatchProcessing] = useState(false)
  const [stats, setStats] = useState({
    pending: 0,
    approved: 0,
    executed: 0,
    rejected: 0,
    failed: 0,
  })

  const fetchDetections = async (status?: string) => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (status && status !== 'all') {
        params.append('status', status)
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/detections/?${params}`
      )

      if (!response.ok) throw new Error('Failed to fetch detections')

      const data = await response.json()
      setDetections(data.detections || [])
      setTotal(data.total || 0)

      // Calculate stats
      const statusCounts = {
        pending: 0,
        approved: 0,
        executed: 0,
        rejected: 0,
        failed: 0,
      }
      data.detections?.forEach((d: Detection) => {
        const status = d.status.toLowerCase()
        if (status in statusCounts) {
          statusCounts[status as keyof typeof statusCounts]++
        }
      })
      setStats(statusCounts)
    } catch (error) {
      console.error('Failed to fetch detections:', error)
      alert('Failed to load actions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDetections(statusFilter)
  }, [statusFilter])

  const handleApprove = async (detectionId: number) => {
    if (!confirm('Approve this action? This will execute the action on AWS.')) {
      return
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/actions/${detectionId}/approve`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            approved_by: 'user@example.com',
            dry_run: false,
          }),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Approval failed')
      }

      alert('✅ Action approved and executed!')
      fetchDetections(statusFilter)
    } catch (error: any) {
      alert('❌ Approval failed: ' + error.message)
    }
  }

  const handleReject = async (detectionId: number) => {
    if (!confirm('Reject this detection? It will be marked as not actionable.')) {
      return
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/actions/${detectionId}/reject`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            approved_by: 'user@example.com',
          }),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Rejection failed')
      }

      alert('✅ Detection rejected')
      fetchDetections(statusFilter)
    } catch (error: any) {
      alert('❌ Rejection failed: ' + error.message)
    }
  }

  const handleBatchApprove = async () => {
    if (selectedIds.length === 0) {
      alert('Please select at least one detection')
      return
    }

    if (!confirm(`Approve and execute ${selectedIds.length} actions? This will execute them on AWS.`)) {
      return
    }

    setBatchProcessing(true)
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/actions/batch/approve`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            detection_ids: selectedIds,
            approved_by: 'user@example.com',
            dry_run: false,
          }),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Batch approval failed')
      }

      const result = await response.json()
      alert(
        `✅ Batch approval completed!\n\n` +
        `Success: ${result.success}\n` +
        `Failed: ${result.failed}\n` +
        `Total: ${result.total}`
      )

      setSelectedIds([])
      fetchDetections(statusFilter)
    } catch (error: any) {
      alert('❌ Batch approval failed: ' + error.message)
    } finally {
      setBatchProcessing(false)
    }
  }

  const handleBatchReject = async () => {
    if (selectedIds.length === 0) {
      alert('Please select at least one detection')
      return
    }

    if (!confirm(`Reject ${selectedIds.length} detections? They will be marked as not actionable.`)) {
      return
    }

    setBatchProcessing(true)
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/actions/batch/reject`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            detection_ids: selectedIds,
            approved_by: 'user@example.com',
          }),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Batch rejection failed')
      }

      const result = await response.json()
      alert(
        `✅ Batch rejection completed!\n\n` +
        `Success: ${result.success}\n` +
        `Failed: ${result.failed}\n` +
        `Total: ${result.total}`
      )

      setSelectedIds([])
      fetchDetections(statusFilter)
    } catch (error: any) {
      alert('❌ Batch rejection failed: ' + error.message)
    } finally {
      setBatchProcessing(false)
    }
  }

  const toggleSelection = (id: number) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  const toggleSelectAll = () => {
    if (selectedIds.length === detections.filter(d => d.status.toUpperCase() === 'PENDING').length) {
      setSelectedIds([])
    } else {
      setSelectedIds(detections.filter(d => d.status.toUpperCase() === 'PENDING').map(d => d.id))
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      PENDING: 'bg-yellow-100 text-yellow-800',
      APPROVED: 'bg-blue-100 text-blue-800',
      EXECUTED: 'bg-green-100 text-green-800',
      REJECTED: 'bg-gray-100 text-gray-800',
      FAILED: 'bg-red-100 text-red-800',
    }
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800'
  }

  const getResourceTypeLabel = (resourceType: string) => {
    const labels = {
      ec2_instance: '🖥️ EC2 Instance',
      ebs_volume: '💾 EBS Volume',
      ebs_snapshot: '📸 EBS Snapshot',
    }
    return labels[resourceType as keyof typeof labels] || resourceType
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                ⚡ Action Center
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Review and approve detected waste
              </p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-xs font-medium text-gray-500">Pending</h3>
            <p className="text-2xl font-bold text-yellow-600 mt-1">{stats.pending}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-xs font-medium text-gray-500">Approved</h3>
            <p className="text-2xl font-bold text-blue-600 mt-1">{stats.approved}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-xs font-medium text-gray-500">Executed</h3>
            <p className="text-2xl font-bold text-green-600 mt-1">{stats.executed}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-xs font-medium text-gray-500">Rejected</h3>
            <p className="text-2xl font-bold text-gray-600 mt-1">{stats.rejected}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-xs font-medium text-gray-500">Failed</h3>
            <p className="text-2xl font-bold text-red-600 mt-1">{stats.failed}</p>
          </div>
        </div>

        {/* Filter */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Filter by Status</h2>
          <div className="flex flex-wrap gap-2">
            {['all', 'pending', 'approved', 'executed', 'rejected', 'failed'].map((status) => (
              <button
                key={status}
                onClick={() => {
                  setStatusFilter(status)
                  setSelectedIds([]) // Clear selection when changing filter
                }}
                className={`px-4 py-2 rounded-md font-medium transition ${
                  statusFilter === status
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Batch Actions */}
        {selectedIds.length > 0 && (
          <div className="bg-blue-50 border-2 border-blue-200 rounded-lg shadow p-4 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-blue-900">
                  {selectedIds.length} {selectedIds.length === 1 ? 'action' : 'actions'} selected
                </h3>
                <p className="text-sm text-blue-700">
                  Choose a batch operation to apply to all selected detections
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleBatchApprove}
                  disabled={batchProcessing}
                  className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                >
                  {batchProcessing ? '⏳ Processing...' : '✅ Approve All'}
                </button>
                <button
                  onClick={handleBatchReject}
                  disabled={batchProcessing}
                  className="px-6 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                >
                  {batchProcessing ? '⏳ Processing...' : '❌ Reject All'}
                </button>
                <button
                  onClick={() => setSelectedIds([])}
                  disabled={batchProcessing}
                  className="px-6 py-3 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                >
                  Clear Selection
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Actions Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading actions...</p>
            </div>
          ) : detections.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p className="text-lg mb-2">No actions found</p>
              <p className="text-sm">Run a scan to detect wasteful resources</p>
              <Link
                href="/"
                className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
              >
                Go to Dashboard
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <input
                        type="checkbox"
                        checked={
                          detections.filter(d => d.status.toUpperCase() === 'PENDING').length > 0 &&
                          selectedIds.length === detections.filter(d => d.status.toUpperCase() === 'PENDING').length
                        }
                        onChange={toggleSelectAll}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        title="Select all pending"
                      />
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Resource
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Region
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Savings
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Confidence
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {detections.map((detection) => (
                    <tr key={detection.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        {detection.status.toUpperCase() === 'PENDING' ? (
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(detection.id)}
                            onChange={() => toggleSelection(detection.id)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                        ) : (
                          <span className="text-gray-300">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        #{detection.id}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <div className="font-medium text-gray-900">
                          {detection.resource_name || 'Unnamed'}
                        </div>
                        <div className="text-gray-500 font-mono text-xs">
                          {detection.resource_id}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {getResourceTypeLabel(detection.resource_type)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {detection.region}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-green-600">
                        ₹{detection.estimated_monthly_savings_inr.toLocaleString('en-IN')}/mo
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="text-sm font-medium text-gray-900">
                            {Math.round(detection.confidence_score * 100)}%
                          </div>
                          <div className="ml-2 w-16 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${detection.confidence_score * 100}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadge(
                            detection.status
                          )}`}
                        >
                          {detection.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {detection.status.toUpperCase() === 'PENDING' ? (
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleApprove(detection.id)}
                              className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition text-xs"
                            >
                              ✓ Approve
                            </button>
                            <button
                              onClick={() => handleReject(detection.id)}
                              className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition text-xs"
                            >
                              ✗ Reject
                            </button>
                            <Link
                              href={`/actions/${detection.id}`}
                              className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition text-xs"
                            >
                              👁 Details
                            </Link>
                          </div>
                        ) : (
                          <Link
                            href={`/actions/${detection.id}`}
                            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition text-xs inline-block"
                          >
                            👁 View Details
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Info Section */}
        <div className="mt-6 bg-purple-50 border border-purple-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-purple-900 mb-2">
            ℹ️ About Action Center
          </h3>
          <ul className="list-disc list-inside text-purple-800 space-y-2 text-sm">
            <li>
              <strong>Pending:</strong> Detections awaiting your review
            </li>
            <li>
              <strong>Batch Operations:</strong> Select multiple pending detections using checkboxes and approve/reject them all at once
            </li>
            <li>
              <strong>Approve:</strong> Execute the action immediately on AWS
            </li>
            <li>
              <strong>Reject:</strong> Mark as not actionable (won't be executed)
            </li>
            <li>
              <strong>Details:</strong> View full details and preview action impact
            </li>
            <li>
              <strong>Executed:</strong> Actions that have been completed successfully
            </li>
          </ul>
        </div>
      </main>
    </div>
  )
}
