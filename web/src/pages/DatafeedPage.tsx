import { useEffect, useState } from 'react'

import {
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material'

import { type DatafeedItem, fetchDatafeed } from '../api/client'

function DatafeedPage() {
  const [items, setItems] = useState<DatafeedItem[]>([])
  const [type, setType] = useState<string>('')
  const [ticker, setTicker] = useState<string>('')

  const load = async (nextType?: string, nextTicker?: string) => {
    try {
      const data = await fetchDatafeed({
        type: nextType || undefined,
        ticker: nextTicker || undefined,
        limit: 100,
      })
      setItems(data)
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to load datafeed', err)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleTypeChange = (event: any) => {
    const v = String(event.target.value)
    setType(v)
    void load(v || undefined, ticker || undefined)
  }

  const handleTickerBlur = () => {
    const nextTicker = ticker.trim() || undefined
    void load(type || undefined, nextTicker)
  }

  return (
    <>
      <Typography variant="h5" gutterBottom>
        Datafeed
      </Typography>
      <Toolbar disableGutters sx={{ gap: 2 }}>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="type-label">Type</InputLabel>
          <Select
            labelId="type-label"
            label="Type"
            value={type}
            onChange={handleTypeChange}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="market">Market</MenuItem>
            <MenuItem value="news">News</MenuItem>
          </Select>
        </FormControl>
        <TextField
          size="small"
          label="Ticker"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          onBlur={handleTickerBlur}
        />
      </Toolbar>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>Ticker</TableCell>
              <TableCell>Source</TableCell>
              <TableCell>Title</TableCell>
              <TableCell>Published At</TableCell>
              <TableCell>Fetched At</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item, idx) => (
              <TableRow key={`${item.type}-${item.ticker}-${idx}`}>
                <TableCell>{item.type}</TableCell>
                <TableCell>{item.ticker || '-'}</TableCell>
                <TableCell>{item.source}</TableCell>
                <TableCell>{item.title || '-'}</TableCell>
                <TableCell>{item.published_at || '-'}</TableCell>
                <TableCell>{item.fetched_at}</TableCell>
              </TableRow>
            ))}
            {!items.length && (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  No datafeed items.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  )
}

export default DatafeedPage

