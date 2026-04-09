'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

export default function Home() {
  const [stats, setStats] = useState({
    totalDetections: 0,
    totalSavings: 0,
    pendingActions: 0,
  })
  const [natGwStats, setNatGwStats] = useState({
    total: 0,
    idleCount: 0,
  })
  const [scanning, setScanning] = useState(false)

  const fetchStats = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    // Fetch dashboard stats
    fetch(`${apiUrl}/api/v1/detections/`)
      .then(res => res.json())
      .then(data => {
        const totalSavings = data.detections?.reduce(
          (sum: number, d: any) => sum + (d.estimated_monthly_savings_inr || 0),
          0
        ) || 0
        const pending = data.detections?.filter(
          (d: any) => d.status === 'pending'
        ).length || 0

        setStats({
          totalDetections: data.total || 0,
          totalSavings,
          pendingActions: pending,
        })
      })
      .catch(err => console.error('Failed to fetch stats:', err))

    // Fetch NAT Gateway stats
    fetch(`${apiUrl}/api/v1/detections/nat-gateways`)
      .then(res => res.json())
      .then(data => {
        const detections = data.detections || []
        const idleCount = detections.filter((d: any) => d.is_idle).length
        setNatGwStats({ total: data.total || 0, idleCount })
      })
      .catch(err => console.error('Failed to fetch NAT Gateway stats:', err))
  }

  useEffect(() => {
    fetchStats()
  }, [])

  const runScan = async (resourceTypes?: string[]) => {
    setScanning(true)
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    try {
      const response = await fetch(
        `${apiUrl}/api/v1/detections/scan`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(
            resourceTypes ? { resource_types: resourceTypes } : {}
          ),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Scan failed')
      }

      const result = await response.json()
      alert(
        `✅ Scan completed!\n\n` +
        `Found ${result.total_detections} detections\n` +
        `Potential savings: ₹${result.total_savings_inr.toLocaleString('en-IN')}/month`
      )
      fetchStats() // Refresh stats
    } catch (err: any) {
      alert('❌ Scan failed: ' + err.message)
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            Cloud Waste Hunter 🎯
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Automated AWS Cost Optimization
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Total Detections</h3>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {stats.totalDetections}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Potential Savings</h3>
            <p className="text-3xl font-bold text-green-600 mt-2">
              ₹{stats.totalSavings.toLocaleString('en-IN')}
            </p>
            <p className="text-xs text-gray-500 mt-1">per month</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Pending Actions</h3>
            <p className="text-3xl font-bold text-orange-600 mt-2">
              {stats.pendingActions}
            </p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/detections"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
            >
              📋 View Detections
            </Link>
            <Link
              href="/actions"
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition"
            >
              ⚡ Action Center
            </Link>
            <Link
              href="/audit"
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition"
            >
              📜 Audit Log
            </Link>
          </div>
        </div>

        {/* Scan Options */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Run Resource Scan</h2>
          <p className="text-sm text-gray-600 mb-4">
            Detect wasteful AWS resources to optimize costs
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => runScan()}
              disabled={scanning}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {scanning ? '🔄 Scanning...' : '🚀 Scan All Resources'}
            </button>
            <button
              onClick={() => runScan(['ec2_instance'])}
              disabled={scanning}
              className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              🖥️ EC2 Only
            </button>
            <button
              onClick={() => runScan(['ebs_volume'])}
              disabled={scanning}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              💾 EBS Only
            </button>
            <button
              onClick={() => runScan(['ebs_snapshot'])}
              disabled={scanning}
              className="px-4 py-2 bg-pink-600 text-white rounded-md hover:bg-pink-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              📸 Snapshots Only
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            💡 Tip: Choose specific resource types for faster scans, or scan all to get complete insights
          </p>
        </div>

        {/* Info Section */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            ℹ️ Getting Started
          </h3>
          <p className="text-blue-800 mb-4">
            Cloud Waste Hunter automatically detects wasteful AWS resources and helps you eliminate them safely.
          </p>
          <ul className="list-disc list-inside text-blue-800 space-y-2">
            <li>
              <strong>Run Scan:</strong> Detect idle EC2 instances, unattached EBS volumes, and old snapshots
            </li>
            <li>
              <strong>Review Detections:</strong> View all findings with confidence scores and estimated savings
            </li>
            <li>
              <strong>Preview Actions:</strong> Use dry-run mode to see impact before approval
            </li>
            <li>
              <strong>Approve & Execute:</strong> Safely eliminate waste with audit trail
            </li>
            <li>
              <strong>Rollback (EC2):</strong> Restart stopped instances within 7 days if needed
            </li>
          </ul>
        </div>

        {/* NAT Gateway Summary Card */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">🌐 NAT Gateway Overview</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-500">Total Detected</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{natGwStats.total}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Idle Candidates</p>
              <p className="text-2xl font-bold text-orange-600 mt-1">{natGwStats.idleCount}</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            Idle = &lt; 1 GB total traffic over 7 days
          </p>
          <Link
            href="/detections/nat-gateways"
            className="mt-3 inline-block text-sm text-blue-600 hover:text-blue-800"
          >
            View NAT Gateway detections →
          </Link>
        </div>

        {/* Resource Types Info */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-2">🖥️ EC2 Instances</h4>
            <p className="text-sm text-gray-600">
              Detects idle instances with CPU &lt; 5% for 7+ days using ML algorithms
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-2">💾 EBS Volumes</h4>
            <p className="text-sm text-gray-600">
              Finds unattached volumes available for 30+ days
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-2">📸 Snapshots</h4>
            <p className="text-sm text-gray-600">
              Identifies old snapshots (&gt;90 days) with no associated AMI
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-2">🌐 NAT Gateways</h4>
            <p className="text-sm text-gray-600">
              Flags gateways with &lt; 1 GB traffic over 7 days as idle
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
