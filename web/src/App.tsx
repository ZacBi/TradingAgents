import { AppBar, Box, Container, CssBaseline, Drawer, List, ListItemButton, ListItemText, Toolbar, Typography } from '@mui/material'
import { useNavigate, Routes, Route } from 'react-router-dom'
import './App.css'

import DashboardPage from './pages/DashboardPage'
import PositionsPage from './pages/PositionsPage'
import DecisionsPage from './pages/DecisionsPage'
import DecisionDetailPage from './pages/DecisionDetailPage'
import DatafeedPage from './pages/DatafeedPage'

const drawerWidth = 220

const menuItems = [
  { label: 'Dashboard', path: '/' },
  { label: 'Positions', path: '/positions' },
  { label: 'Decisions', path: '/decisions' },
  { label: 'Datafeed', path: '/datafeed' },
]

function App() {
  const navigate = useNavigate()

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            TradingAgents Dashboard
          </Typography>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            {menuItems.map((item) => (
              <ListItemButton key={item.path} onClick={() => navigate(item.path)}>
                <ListItemText primary={item.label} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          ml: `${drawerWidth}px`,
        }}
      >
        <Toolbar />
        <Container maxWidth="lg">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/positions" element={<PositionsPage />} />
            <Route path="/decisions" element={<DecisionsPage />} />
            <Route path="/decisions/:id" element={<DecisionDetailPage />} />
            <Route path="/datafeed" element={<DatafeedPage />} />
          </Routes>
        </Container>
      </Box>
    </Box>
  )
}

export default App
