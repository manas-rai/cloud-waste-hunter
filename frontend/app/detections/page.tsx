'use client'

import { useEffect, useState } from 'react'
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
  created_at: string
  metadata?: {
    size_gb?: number
    volume_type?: string
    days_unattached?: number
    availability_zone?: string
    avg_cpu_percent?: number
    age_days?: number
    [key: string]: unknown
  }
}

export default function DetectionsPage() {
  const [detections, setDetections] = useState<Detection[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    fetch(`${apiUrl}/api/v1/detections/`)
      .then(res => res.json())
      .then(data => {
        setDetections(data.detections || [])
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch detections:', err)
        setLoading(false)
      })
  }, [])

  const filteredDetections = filter === 'all'
    ? detections
    : detections.filter(d => d.status === filter)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'approved': return 'bg-blue-100 text-blue-800'
      case 'executed': return 'bg-green-100 text-green-800'
      case 'rejected': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getResourceTypeLabel = (type: string) => {
    switch (type) {
      case 'ec2_instance': return 'EC2 Instance'
      case 'ebs_volume': return 'EBS Volume'
      case 'ebs_snapshot': return 'EBS Snapshot'
      default: return type
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link href="/" className="text-primary-600 hover:text-primary-700">
            ← Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">
            Detections
          </h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex gap-2">
            {['all', 'pending', 'approved', 'executed', 'rejected'].map(status => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`px-4 py-2 rounded-md ${filter === status
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Detections Table */}
        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Loading detections...</p>
          </div>
        ) : filteredDetections.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-500">No detections found</p>
            <Link
              href="/"
              className="mt-4 inline-block px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
            >
              Run Scan
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
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
                    Details
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Confidence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Savings
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
                {filteredDetections.map((detection) => (
                  <tr key={detection.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {detection.resource_name || detection.resource_id}
                      </div>
                      <div className="text-sm text-gray-500">
                        {detection.resource_id}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {getResourceTypeLabel(detection.resource_type)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {detection.region}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {detection.resource_type === 'ebs_volume' && detection.metadata ? (
                        <div className="space-y-0.5">
                          {detection.metadata.volume_type && (
                            <div><span className="font-medium">Vol type:</span> {detection.metadata.volume_type}</div>
                          )}
                          {detection.metadata.size_gb !== undefined && (
                            <div><span className="font-medium">Size:</span> {detection.metadata.size_gb} GB</div>
                          )}
                          {detection.metadata.days_unattached !== undefined && (
                            <div><span className="font-medium">Unattached:</span> {detection.metadata.days_unattached}d</div>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900">
                        {(detection.confidence_score * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-600">
                      ₹{detection.estimated_monthly_savings_inr.toLocaleString('en-IN')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(detection.status)}`}>
                        {detection.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {detection.status === 'pending' && (
                        <Link
                          href={`/actions/${detection.id}`}
                          className="text-primary-600 hover:text-primary-900"
                        >
                          Review
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
