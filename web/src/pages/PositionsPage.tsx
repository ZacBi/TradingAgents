import { useEffect, useState } from 'react'
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'

import { fetchPositions, type Position } from '../api/client'

function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([])

  useEffect(() => {
    void (async () => {
      try {
        const data = await fetchPositions()
        setPositions(data)
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('Failed to load positions', err)
      }
    })()
  }, [])

  return (
    <>
      <Typography variant="h5" gutterBottom>
        Positions
      </Typography>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Ticker</TableCell>
              <TableCell align="right">Quantity</TableCell>
              <TableCell align="right">Avg Cost</TableCell>
              <TableCell align="right">Current Price</TableCell>
              <TableCell align="right">Unrealized PnL</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {positions.map((row) => (
              <TableRow key={row.ticker}>
                <TableCell>{row.ticker}</TableCell>
                <TableCell align="right">{row.quantity}</TableCell>
                <TableCell align="right">{row.avg_cost.toFixed(2)}</TableCell>
                <TableCell align="right">{row.current_price.toFixed(2)}</TableCell>
                <TableCell align="right">{row.unrealized_pnl.toFixed(2)}</TableCell>
              </TableRow>
            ))}
            {!positions.length && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No open positions.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  )
}

export default PositionsPage

