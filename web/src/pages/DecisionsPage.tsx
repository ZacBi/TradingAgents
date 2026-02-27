import { useEffect, useState } from 'react'
import {
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { useNavigate } from 'react-router-dom'

import { type Decision, fetchDecisions } from '../api/client'

function DecisionsPage() {
  const [rows, setRows] = useState<Decision[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    void (async () => {
      try {
        const data = await fetchDecisions({ limit: 50 })
        setRows(data)
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('Failed to load decisions', err)
      }
    })()
  }, [])

  return (
    <>
      <Typography variant="h5" gutterBottom>
        Decisions
      </Typography>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Ticker</TableCell>
              <TableCell>Trade Date</TableCell>
              <TableCell>Final Decision</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((d) => (
              <TableRow key={d.id}>
                <TableCell>{d.id}</TableCell>
                <TableCell>{d.ticker}</TableCell>
                <TableCell>{d.trade_date}</TableCell>
                <TableCell>{d.final_decision}</TableCell>
                <TableCell>{d.confidence != null ? d.confidence.toFixed(2) : '-'}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => navigate(`/decisions/${d.id}`)}>
                    <OpenInNewIcon fontSize="inherit" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {!rows.length && (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  No decisions yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  )
}

export default DecisionsPage

