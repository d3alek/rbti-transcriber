declare module '@bbc/react-transcript-editor' {
  import { Component } from 'react';

  export interface TranscriptEditorProps {
    transcriptData?: any;
    mediaUrl?: string;
    isEditable?: boolean;
    spellCheck?: boolean;
    sttJsonType?: string;
    handleAnalyticsEvents?: (event: any) => void;
    fileName?: string;
    mediaType?: 'audio' | 'video';
    handleAutoSaveChanges?: (data: any) => void;
    autoSaveContentType?: string;
    title?: string;
  }

  export default class TranscriptEditor extends Component<TranscriptEditorProps> {}
}

