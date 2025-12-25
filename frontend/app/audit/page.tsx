'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface AuditLog {
  id: number
  detection_id: number | null
  action_type: string
  resource_type: string
  resource_id: string
  status: string
  executed_by: string
  executed_at: string
  dry_run: boolean
  can_rollback: boolean
  rolled_back_at: string | null
  rolled_back_by: string | null
  error_message: string | null
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    action_type: '',
    status: '',
    resource_id: '',
  })

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filters.action_type) params.append('action_type', filters.action_type)
      if (filters.status) params.append('status', filters.status)
      if (filters.resource_id) params.append('resource_id', filters.resource_id)

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/audit/?${params}`
      )

      if (!response.ok) throw new Error('Failed to fetch audit logs')

      const data = await response.json()
      setLogs(data.logs || [])
      setTotal(data.total || 0)
    } catch (error) {
      console.error('Failed to fetch audit logs:', error)
      alert('Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [])

  const handleRollback = async (logId: number) => {
    if (!confirm('Are you sure you want to rollback this action? This will restart the EC2 instance.')) {
      return
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/audit/${logId}/rollback`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            rolled_back_by: 'user@example.com',
          }),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Rollback failed')
      }

      alert('✅ Rollback successful!')
      fetchLogs()
    } catch (error: any) {
      alert('❌ Rollback failed: ' + error.message)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      SUCCESS: 'bg-green-100 text-green-800',
      FAILED: 'bg-red-100 text-red-800',
      PENDING: 'bg-yellow-100 text-yellow-800',
      ROLLED_BACK: 'bg-blue-100 text-blue-800',
    }
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800'
  }

  const getActionTypeLabel = (actionType: string) => {
    const labels = {
      stop_ec2_instance: '🛑 Stop EC2',
      delete_ebs_volume: '🗑️ Delete EBS',
      delete_ebs_snapshot: '🗑️ Delete Snapshot',
      rollback: '↩️ Rollback',
    }
    return labels[actionType as keyof typeof labels] || actionType
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                📜 Audit Log
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Track all actions and changes
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
        {/* Stats Card */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-sm font-medium text-gray-500">Total Audit Logs</h3>
          <p className="text-3xl font-bold text-gray-900 mt-2">{total}</p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Filters</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Action Type
              </label>
              <select
                value={filters.action_type}
                onChange={(e) => setFilters({ ...filters, action_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="stop_ec2_instance">Stop EC2</option>
                <option value="delete_ebs_volume">Delete EBS</option>
                <option value="delete_ebs_snapshot">Delete Snapshot</option>
                <option value="rollback">Rollback</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Status
              </label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="SUCCESS">Success</option>
                <option value="FAILED">Failed</option>
                <option value="PENDING">Pending</option>
                <option value="ROLLED_BACK">Rolled Back</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Resource ID
              </label>
              <input
                type="text"
                value={filters.resource_id}
                onChange={(e) => setFilters({ ...filters, resource_id: e.target.value })}
                placeholder="e.g., i-1234567890"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            onClick={fetchLogs}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
          >
            Apply Filters
          </button>
        </div>

        {/* Audit Logs Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading audit logs...</p>
            </div>
          ) : logs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No audit logs found. Actions will appear here once executed.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Action
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Resource
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Executed By
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Executed At
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        #{log.id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className="flex items-center">
                          <span className="font-medium">
                            {getActionTypeLabel(log.action_type)}
                          </span>
                          {log.dry_run && (
                            <span className="ml-2 px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                              DRY RUN
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <div className="text-gray-900 font-mono text-xs">
                          {log.resource_id}
                        </div>
                        <div className="text-gray-500 text-xs">
                          {log.resource_type}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadge(
                            log.status
                          )}`}
                        >
                          {log.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {log.executed_by}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(log.executed_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {log.can_rollback && log.status === 'SUCCESS' && !log.rolled_back_at ? (
                          <button
                            onClick={() => handleRollback(log.id)}
                            className="px-3 py-1 bg-orange-600 text-white rounded hover:bg-orange-700 transition text-xs"
                          >
                            ↩️ Rollback
                          </button>
                        ) : log.rolled_back_at ? (
                          <span className="text-xs text-blue-600">
                            Rolled back on {new Date(log.rolled_back_at).toLocaleString()}
                          </span>
                        ) : log.error_message ? (
                          <span className="text-xs text-red-600" title={log.error_message}>
                            ⚠️ Error
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">-</span>
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
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            ℹ️ About Audit Logs
          </h3>
          <ul className="list-disc list-inside text-blue-800 space-y-2 text-sm">
            <li>
              <strong>Every action is tracked:</strong> All resource modifications are logged for compliance
            </li>
            <li>
              <strong>Rollback capability:</strong> EC2 stop actions can be rolled back within 7 days
            </li>
            <li>
              <strong>Dry-run tracking:</strong> Preview actions are also logged (marked as DRY RUN)
            </li>
            <li>
              <strong>Status tracking:</strong> Monitor success, failures, and rollbacks
            </li>
          </ul>
        </div>
      </main>
    </div>
  )
}
