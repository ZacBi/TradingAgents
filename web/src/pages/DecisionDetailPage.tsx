import { useEffect, useState } from 'react'

import { Box, Card, CardContent, Divider, Typography } from '@mui/material'
import { useParams } from 'react-router-dom'

import { type DecisionDetail, fetchDecisionDetail } from '../api/client'

function Section({ title, content }: { title: string; content?: string }) {
  if (!content) return null
  return (
    <Box mb={2}>
      <Typography variant="subtitle1" gutterBottom>
        {title}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          whiteSpace: 'pre-wrap',
          fontFamily: 'monospace',
        }}
      >
        {content}
      </Typography>
      <Divider sx={{ mt: 1 }} />
    </Box>
  )
}

function DecisionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [detail, setDetail] = useState<DecisionDetail | null>(null)

  useEffect(() => {
    if (!id) return
    void (async () => {
      try {
        const data = await fetchDecisionDetail(Number(id))
        setDetail(data)
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('Failed to load decision detail', err)
      }
    })()
  }, [id])

  if (!id) {
    return <Typography>Invalid decision id.</Typography>
  }

  if (!detail) {
    return <Typography>Loading decision...</Typography>
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Decision #{detail.id} – {detail.ticker} ({detail.trade_date})
      </Typography>
      <Card>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Summary
          </Typography>
          <Typography variant="body2" gutterBottom>
            Final decision: <strong>{detail.final_decision}</strong>{' '}
            {detail.confidence != null && `(${detail.confidence.toFixed(2)})`}
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Section title="Market Report" content={detail.market_report} />
          <Section title="Sentiment Report" content={detail.sentiment_report} />
          <Section title="News Report" content={detail.news_report} />
          <Section title="Fundamentals Report" content={detail.fundamentals_report} />
          <Section title="Valuation Result" content={detail.valuation_result} />
          <Section title="Debate History" content={detail.debate_history} />
          <Section title="Risk Assessment" content={detail.risk_assessment} />
        </CardContent>
      </Card>
    </Box>
  )
}

export default DecisionDetailPage

