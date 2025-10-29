/**
 * VersionManager Component
 * 
 * Manages transcript versions with history, saving, and switching capabilities.
 */

import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Button,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Divider,
  Badge
} from '@mui/material';
import {
  Save as SaveIcon,
  History as HistoryIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as RadioButtonUncheckedIcon,
  Delete as DeleteIcon,
  Info as InfoIcon,

} from '@mui/icons-material';
import type { DeepgramVersion, VersionManagerProps } from '../types/deepgram';

interface VersionManagerComponentProps extends VersionManagerProps {
  onDeleteVersion?: (version: number) => void;
  onViewVersionInfo?: (version: DeepgramVersion) => void;
}

const VersionManager: React.FC<VersionManagerComponentProps> = ({
  versions,
  currentVersion,
  onVersionSelect,
  onSaveVersion,
  canSave,
  isLoading = false,
  onDeleteVersion
}) => {
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveDescription, setSaveDescription] = useState('');
  const [infoDialogOpen, setInfoDialogOpen] = useState(false);
  const [selectedVersionInfo, setSelectedVersionInfo] = useState<DeepgramVersion | null>(null);

  const handleSaveClick = useCallback(() => {
    setSaveDialogOpen(true);
    setSaveDescription('');
  }, []);

  const handleSaveConfirm = useCallback(() => {
    onSaveVersion();
    setSaveDialogOpen(false);
    setSaveDescription('');
  }, [onSaveVersion]);

  const handleSaveCancel = useCallback(() => {
    setSaveDialogOpen(false);
    setSaveDescription('');
  }, []);

  const handleVersionClick = useCallback((version: number) => {
    if (version !== currentVersion) {
      onVersionSelect(version);
    }
  }, [currentVersion, onVersionSelect]);

  const handleDeleteVersion = useCallback((version: number, event: React.MouseEvent) => {
    event.stopPropagation();
    
    if (version === 0) {
      alert('Cannot delete the original version (version 0)');
      return;
    }

    const confirmDelete = window.confirm(
      `Are you sure you want to delete version ${version}? This action cannot be undone.`
    );
    
    if (confirmDelete) {
      onDeleteVersion?.(version);
    }
  }, [onDeleteVersion]);

  const handleViewInfo = useCallback((version: DeepgramVersion, event: React.MouseEvent) => {
    event.stopPropagation();
    setSelectedVersionInfo(version);
    setInfoDialogOpen(true);
  }, []);

  const formatTimestamp = useCallback((timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch {
      return timestamp;
    }
  }, []);

  const getVersionLabel = useCallback((version: DeepgramVersion) => {
    if (version.version === 0) {
      return 'Original';
    }
    return `Version ${version.version}`;
  }, []);

  const getVersionDescription = useCallback((version: DeepgramVersion) => {
    if (version.changes) {
      return version.changes;
    }
    if (version.version === 0) {
      return 'Original Deepgram transcription';
    }
    return 'No description provided';
  }, []);

  const sortedVersions = [...versions].sort((a, b) => b.version - a.version);

  return (
    <Paper sx={{ p: 2, height: 'fit-content' }}>
      {/* Header */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Typography variant="h6" display="flex" alignItems="center" gap={1}>
          <HistoryIcon />
          Version History
        </Typography>
        
        <Badge badgeContent={canSave ? '!' : 0} color="warning">
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSaveClick}
            disabled={!canSave || isLoading}
            size="small"
          >
            Save Version
          </Button>
        </Badge>
      </Box>

      {/* Unsaved Changes Warning */}
      {canSave && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          You have unsaved changes. Save a new version to preserve your edits.
        </Alert>
      )}

      {/* Version List */}
      <List dense sx={{ maxHeight: '400px', overflow: 'auto' }}>
        {sortedVersions.length === 0 ? (
          <ListItem>
            <ListItemText
              primary="No versions available"
              secondary="Transcribe an audio file to create the first version"
            />
          </ListItem>
        ) : (
          sortedVersions.map((version) => (
            <ListItem
              key={version.version}
              disablePadding
              sx={{
                border: version.version === currentVersion ? '2px solid' : '1px solid transparent',
                borderColor: version.version === currentVersion ? 'primary.main' : 'transparent',
                borderRadius: 1,
                mb: 1,
                backgroundColor: version.version === currentVersion ? 'action.selected' : 'transparent'
              }}
            >
              <ListItemButton
                onClick={() => handleVersionClick(version.version)}
                disabled={isLoading}
              >
                <ListItemIcon>
                  {version.version === currentVersion ? (
                    <CheckCircleIcon color="primary" />
                  ) : (
                    <RadioButtonUncheckedIcon />
                  )}
                </ListItemIcon>
                
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="subtitle2">
                        {getVersionLabel(version)}
                      </Typography>
                      {version.version === currentVersion && (
                        <Chip label="Current" size="small" color="primary" />
                      )}
                      {version.version === 0 && (
                        <Chip label="Original" size="small" variant="outlined" />
                      )}
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="caption" display="block">
                        {getVersionDescription(version)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatTimestamp(version.timestamp)}
                      </Typography>
                    </Box>
                  }
                />

                {/* Action Buttons */}
                <Box display="flex" alignItems="center" gap={0.5}>
                  <Tooltip title="View details">
                    <IconButton
                      size="small"
                      onClick={(e) => handleViewInfo(version, e)}
                    >
                      <InfoIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  
                  {version.version !== 0 && (
                    <Tooltip title="Delete version">
                      <IconButton
                        size="small"
                        onClick={(e) => handleDeleteVersion(version.version, e)}
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </Box>
              </ListItemButton>
            </ListItem>
          ))
        )}
      </List>

      {/* Version Statistics */}
      {versions.length > 0 && (
        <>
          <Divider sx={{ my: 2 }} />
          <Box>
            <Typography variant="caption" color="text.secondary">
              Total versions: {versions.length} | 
              Current: Version {currentVersion}
            </Typography>
          </Box>
        </>
      )}

      {/* Save Version Dialog */}
      <Dialog open={saveDialogOpen} onClose={handleSaveCancel} maxWidth="sm" fullWidth>
        <DialogTitle>Save New Version</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Describe the changes you made in this version for future reference.
          </Typography>
          <TextField
            autoFocus
            fullWidth
            multiline
            rows={3}
            label="Version Description"
            placeholder="e.g., Fixed speaker labels, corrected technical terms..."
            value={saveDescription}
            onChange={(e) => setSaveDescription(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleSaveCancel}>Cancel</Button>
          <Button 
            onClick={handleSaveConfirm} 
            variant="contained"
            disabled={!saveDescription.trim()}
          >
            Save Version
          </Button>
        </DialogActions>
      </Dialog>

      {/* Version Info Dialog */}
      <Dialog 
        open={infoDialogOpen} 
        onClose={() => setInfoDialogOpen(false)} 
        maxWidth="md" 
        fullWidth
      >
        <DialogTitle>
          Version {selectedVersionInfo?.version} Details
        </DialogTitle>
        <DialogContent>
          {selectedVersionInfo && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Description
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {getVersionDescription(selectedVersionInfo)}
              </Typography>

              <Typography variant="subtitle2" gutterBottom>
                Created
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {formatTimestamp(selectedVersionInfo.timestamp)}
              </Typography>

              <Typography variant="subtitle2" gutterBottom>
                File Information
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                Filename: {selectedVersionInfo.filename}
              </Typography>

              {selectedVersionInfo.version === 0 && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  This is the original version created from the Deepgram transcription.
                  It cannot be deleted.
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInfoDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default VersionManager;