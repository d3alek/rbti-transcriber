import { useState } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Folder as FolderIcon,
  Settings as SettingsIcon,
  Work as JobsIcon,
} from '@mui/icons-material';

import { FileManager } from './components/FileManager';
import { JobManager } from './components/JobManager';
import { TranscriptEditor } from './components/TranscriptEditor';
import type { AudioFile, TranscriptionRequest } from './types';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

type View = 'files' | 'jobs' | 'settings' | 'editor';

function App() {
  const [currentView, setCurrentView] = useState<View>('files');
  const [selectedFile, setSelectedFile] = useState<AudioFile | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(true);

  const handleFileSelect = (file: AudioFile) => {
    setSelectedFile(file);
    setCurrentView('editor');
  };



  const handleTranscriptionStart = (request: TranscriptionRequest) => {
    console.log('Starting transcription:', request);
    // TODO: Start transcription and show progress
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'files':
        return (
          <FileManager
            onFileSelect={handleFileSelect}
            onTranscriptionStart={handleTranscriptionStart}
          />
        );
      case 'jobs':
        return <JobManager />;
      case 'editor':
        return selectedFile ? (
          <TranscriptEditor
            file={selectedFile}
            onError={(error) => console.error('Transcript error:', error)}
          />
        ) : (
          <Box p={3}>
            <Typography>No file selected</Typography>
          </Box>
        );
      case 'settings':
        return (
          <Box p={3}>
            <Typography variant="h4">Settings</Typography>
            <Typography>Settings panel coming soon...</Typography>
          </Box>
        );
      default:
        return null;
    }
  };

  const menuItems = [
    { id: 'files' as View, label: 'Audio Files', icon: <FolderIcon /> },
    { id: 'jobs' as View, label: 'Jobs', icon: <JobsIcon /> },
    { id: 'settings' as View, label: 'Settings', icon: <SettingsIcon /> },
  ];

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex' }}>
        {/* App Bar */}
        <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
          <Toolbar>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={() => setDrawerOpen(!drawerOpen)}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" noWrap component="div">
              Audio Transcription Manager
            </Typography>
          </Toolbar>
        </AppBar>

        {/* Sidebar - Hide in editor mode */}
        {currentView !== 'editor' && (
          <Drawer
            variant="persistent"
            anchor="left"
            open={drawerOpen}
            sx={{
              width: 240,
              flexShrink: 0,
              '& .MuiDrawer-paper': {
                width: 240,
                boxSizing: 'border-box',
              },
            }}
          >
            <Toolbar />
            <Box sx={{ overflow: 'auto' }}>
              <List>
                {menuItems.map((item) => (
                  <ListItem
                    key={item.id}
                    onClick={() => setCurrentView(item.id)}
                    sx={{ 
                      cursor: 'pointer',
                      backgroundColor: currentView === item.id ? 'action.selected' : 'transparent'
                    }}
                  >
                    <ListItemIcon>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.label} />
                  </ListItem>
                ))}
              </List>
            </Box>
          </Drawer>
        )}

        {/* Main Content */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: currentView === 'editor' ? 0 : 3,
            transition: (theme) => theme.transitions.create('margin', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
            marginLeft: currentView === 'editor' ? 0 : (drawerOpen ? 0 : '-240px'),
          }}
        >
          {currentView !== 'editor' && <Toolbar />}
          {currentView === 'editor' ? (
            renderCurrentView()
          ) : (
            <Container maxWidth="xl">
              {renderCurrentView()}
            </Container>
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App
