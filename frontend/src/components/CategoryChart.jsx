import React from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { getCategoryName, CATEGORY_COLORS } from '../utils/categories.js'

const FALLBACK_COLORS = ['#1a73e8', '#34a853', '#ea4335', '#7c3aed', '#f59e0b', '#06b6d4', '#ec4899', '#84cc16']

export default function CategoryChart({ data = [] }) {
  if (!data.length) return (
    <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data</div>
  )

  const chartData = data.map((d) => ({
    name: getCategoryName(d.id || d.category || d.name),
    value: d.count || d.value || 0,
    _code: d.id || d.category || d.name,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={110}
          paddingAngle={3}
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={index} fill={CATEGORY_COLORS[entry._code] || FALLBACK_COLORS[index % FALLBACK_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value, name) => [value.toLocaleString(), name]}
          contentStyle={{
            backgroundColor: 'var(--tw-bg-opacity, #fff)',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '12px',
          }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value) => <span style={{ fontSize: 12, color: 'inherit' }}>{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
