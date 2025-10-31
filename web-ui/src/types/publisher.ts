/**
 * Types for local static site publishing functionality
 */

import { CorrectedDeepgramResponse } from './deepgram';
import { TranscriptMetadata } from './api';

export interface PublishBundle {
  htmlFile: string;
  audioFile: string;
  transcriptData: CorrectedDeepgramResponse;
  seminarGroup: string;
  metadata: {
    title: string;
    duration: number;
    publishDate: string;
    fileSize: number;
    compressedSize: number;
    speakerNames?: { [speakerIndex: number]: string };
  };
}

export interface LocalPagesStructure {
  'index.html': string; // Main landing page
  'groups': {
    [groupName: string]: {
      'index.html': string; // Group listing page
      'transcripts': {
        [audioFileName: string]: {
          'index.html': string; // Individual transcript page
          'audio.mp3': Buffer; // Compressed audio
          'transcript.json': CorrectedDeepgramResponse;
        };
      };
    };
  };
}

export interface StaticPageSet {
  transcriptPage: string;
  groupPage: string;
  mainIndex: string;
}

export interface PublishingStatus {
  isPublishing: boolean;
  currentStep: string;
  progress: number;
  error?: string;
  completedFiles: string[];
  totalFiles: number;
}

export interface SiteStructure {
  groups: {
    [groupName: string]: {
      name: string;
      transcriptCount: number;
      lastUpdated: string;
      transcripts: TranscriptMetadata[];
    };
  };
  totalTranscripts: number;
  lastGenerated: string;
}

export interface PublishOptions {
  includeAudio: boolean;
  includeTranscriptJson: boolean;
  generateGroupPages: boolean;
  generateMainIndex: boolean;
  outputDirectory: string;
}

export interface LocalSiteConfig {
  siteName: string;
  description: string;
  baseUrl: string;
  theme: {
    primaryColor: string;
    secondaryColor: string;
    fontFamily: string;
  };
  features: {
    enableSearch: boolean;
    enableDownloads: boolean;
    showConfidenceScores: boolean;
    showSpeakerNames: boolean;
  };
}