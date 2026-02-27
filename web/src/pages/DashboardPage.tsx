import { useEffect, useState } from 'react'
import { Box, Card, CardContent, Typography } from '@mui/material'
import * as echarts from 'echarts'

import { fetchNav, fetchPortfolioSummary, type NavPoint, type PortfolioSummary } from '../api/client'

function DashboardPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [nav, setNav] = useState<NavPoint[]>([])

  useEffect(() => {
    void (async () => {
      try {
        const [s, n] = await Promise.all([fetchPortfolioSummary(), fetchNav(180)])
        setSummary(s)
        setNav(n)
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('Failed to load dashboard data', err)
      }
    })()
  }, [])

  useEffect(() => {
    if (!nav.length) return
    const el = document.getElementById('nav-chart')
    if (!el) return
    const chart = echarts.init(el)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: nav.map((p) => p.date) },
      yAxis: { type: 'value' },
      series: [
        {
          name: 'Total Value',
          type: 'line',
          smooth: true,
          data: nav.map((p) => p.total_value),
        },
      ],
    })
    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [nav])

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Dashboard
      </Typography>
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 2,
          mb: 3,
        }}
      >
        <Card sx={{ flex: '1 1 220px' }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Total Value
            </Typography>
            <Typography variant="h6">
              {summary ? summary.total_value.toFixed(2) : '--'}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: '1 1 220px' }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Positions Value
            </Typography>
            <Typography variant="h6">
              {summary ? summary.positions_value.toFixed(2) : '--'}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: '1 1 220px' }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Daily Return
            </Typography>
            <Typography variant="h6">
              {summary ? `${(summary.daily_return * 100).toFixed(2)}%` : '--'}
            </Typography>
          </CardContent>
        </Card>
      </Box>
      <Card>
        <CardContent>
          <Typography color="text.secondary" gutterBottom>
            NAV (last {nav.length} days)
          </Typography>
          <Box id="nav-chart" sx={{ width: '100%', height: 320 }} />
        </CardContent>
      </Card>
    </Box>
  )
}

export default DashboardPage

