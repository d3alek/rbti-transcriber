/**
 * API service for communicating with the FastAPI backend.
 */

import type { 
  AudioFile, 
  TranscriptionData, 
  TranscriptionRequest, 
  TranscriptionJob,
  PublicationRequest,
  PublicationStatus,
  APIResponse,
  ParagraphData,
  CachedTranscriptionResponse,
  ParagraphUpdateRequest,
  VersionSaveRequest,
  VersionListResponse,
  TranscriptLoadResponse
} from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

class APIService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  // File Management
  async listFiles(): Promise<AudioFile[]> {
    const response = await fetch(`${this.baseUrl}/files/`);
    if (!response.ok) {
      throw new Error(`Failed to list files: ${response.statusText}`);
    }
    return response.json();
  }

  async scanFiles(): Promise<APIResponse> {
    const response = await fetch(`${this.baseUrl}/files/scan`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to scan files: ${response.statusText}`);
    }
    return response.json();
  }

  async getFileInfo(fileId: string): Promise<AudioFile> {
    const response = await fetch(`${this.baseUrl}/files/${fileId}/info`);
    if (!response.ok) {
      throw new Error(`Failed to get file info: ${response.statusText}`);
    }
    return response.json();
  }

  async getTranscription(fileId: string): Promise<TranscriptionData> {
    const response = await fetch(`${this.baseUrl}/files/${fileId}/transcription`);
    if (!response.ok) {
      throw new Error(`Failed to get transcription: ${response.statusText}`);
    }
    return response.json();
  }

  async saveTranscription(fileId: string, transcriptionData: TranscriptionData): Promise<APIResponse> {
    const response = await fetch(`${this.baseUrl}/files/${fileId}/transcription`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(transcriptionData),
    });
    if (!response.ok) {
      throw new Error(`Failed to save transcription: ${response.statusText}`);
    }
    return response.json();
  }

  async deleteTranscription(fileId: string): Promise<APIResponse> {
    const response = await fetch(`${this.baseUrl}/files/${fileId}/transcription`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete transcription: ${response.statusText}`);
    }
    return response.json();
  }

  // Transcription Operations
  async startTranscription(request: TranscriptionRequest): Promise<APIResponse<{ job_id: string }>> {
    const response = await fetch(`${this.baseUrl}/transcribe/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`Failed to start transcription: ${response.statusText}`);
    }
    return response.json();
  }

  async getTranscriptionStatus(jobId: string): Promise<TranscriptionJob> {
    const response = await fetch(`${this.baseUrl}/transcribe/${jobId}/status`);
    if (!response.ok) {
      throw new Error(`Failed to get transcription status: ${response.statusText}`);
    }
    return response.json();
  }

  async cancelTranscription(jobId: string): Promise<APIResponse> {
    const response = await fetch(`${this.baseUrl}/transcribe/${jobId}/cancel`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to cancel transcription: ${response.statusText}`);
    }
    return response.json();
  }

  async listActiveJobs(): Promise<Record<string, TranscriptionJob>> {
    const response = await fetch(`${this.baseUrl}/transcribe/jobs`);
    if (!response.ok) {
      throw new Error(`Failed to list jobs: ${response.statusText}`);
    }
    return response.json();
  }

  async getQueueStatus(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/transcribe/queue/status`);
    if (!response.ok) {
      throw new Error(`Failed to get queue status: ${response.statusText}`);
    }
    return response.json();
  }

  // Export Operations
  async exportTranscription(fileId: string, format: string): Promise<APIResponse<{ export_id: string }>> {
    const response = await fetch(`${this.baseUrl}/export/${fileId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ file_id: fileId, format }),
    });
    if (!response.ok) {
      throw new Error(`Failed to create export: ${response.statusText}`);
    }
    return response.json();
  }

  async downloadExport(exportId: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/export/${exportId}/download`);
    if (!response.ok) {
      throw new Error(`Failed to download export: ${response.statusText}`);
    }
    return response.blob();
  }

  // Publication Operations
  async publishTranscription(fileId: string, request: PublicationRequest): Promise<APIResponse> {
    const response = await fetch(`${this.baseUrl}/publish/${fileId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`Failed to publish transcription: ${response.statusText}`);
    }
    return response.json();
  }

  async unpublishTranscription(fileId: string): Promise<APIResponse> {
    const response = await fetch(`${this.baseUrl}/publish/${fileId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to unpublish transcription: ${response.statusText}`);
    }
    return response.json();
  }

  async getPublicationStatus(fileId: string): Promise<PublicationStatus> {
    const response = await fetch(`${this.baseUrl}/publish/${fileId}/status`);
    if (!response.ok) {
      throw new Error(`Failed to get publication status: ${response.statusText}`);
    }
    return response.json();
  }

  async getSystemStatus(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/publish/status`);
    if (!response.ok) {
      throw new Error(`Failed to get system status: ${response.statusText}`);
    }
    return response.json();
  }

  // Enhanced Transcript Editor Operations

  // Version Management
  async getTranscriptVersions(audioHash: string): Promise<VersionListResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions`);
    if (!response.ok) {
      throw new Error(`Failed to get transcript versions: ${response.statusText}`);
    }
    return response.json();
  }

  async loadTranscriptVersion(audioHash: string, version: number): Promise<TranscriptLoadResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions/${version}`);
    if (!response.ok) {
      throw new Error(`Failed to load transcript version: ${response.statusText}`);
    }
    return response.json();
  }

  async saveTranscriptVersion(audioHash: string, request: VersionSaveRequest): Promise<APIResponse<{ version: number }>> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`Failed to save transcript version: ${response.statusText}`);
    }
    return response.json();
  }

  async deleteTranscriptVersion(audioHash: string, version: number): Promise<APIResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions/${version}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete transcript version: ${response.statusText}`);
    }
    return response.json();
  }

  async loadLatestTranscriptVersion(audioHash: string): Promise<TranscriptLoadResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions/latest`);
    if (!response.ok) {
      throw new Error(`Failed to load latest transcript version: ${response.statusText}`);
    }
    return response.json();
  }

  async initializeFromCache(audioHash: string): Promise<APIResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/initialize`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to initialize from cache: ${response.statusText}`);
    }
    return response.json();
  }

  async getStorageInfo(audioHash: string): Promise<APIResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/storage-info`);
    if (!response.ok) {
      throw new Error(`Failed to get storage info: ${response.statusText}`);
    }
    return response.json();
  }

  // Paragraph Editing
  async updateParagraph(audioHash: string, request: ParagraphUpdateRequest): Promise<APIResponse<ParagraphData>> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/paragraphs/${request.paragraph_id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`Failed to update paragraph: ${response.statusText}`);
    }
    return response.json();
  }

  async getParagraphs(audioHash: string, version?: number): Promise<ParagraphData[]> {
    const url = version !== undefined 
      ? `${this.baseUrl}/transcripts/${audioHash}/paragraphs?version=${version}`
      : `${this.baseUrl}/transcripts/${audioHash}/paragraphs`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to get paragraphs: ${response.statusText}`);
    }
    return response.json();
  }

  // Raw Deepgram Response Access
  async getCachedTranscription(audioHash: string): Promise<CachedTranscriptionResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/cached`);
    if (!response.ok) {
      throw new Error(`Failed to get cached transcription: ${response.statusText}`);
    }
    return response.json();
  }

  async getDeepgramResponse(audioHash: string, version?: number): Promise<any> {
    const url = version !== undefined
      ? `${this.baseUrl}/transcripts/${audioHash}/deepgram?version=${version}`
      : `${this.baseUrl}/transcripts/${audioHash}/deepgram`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to get Deepgram response: ${response.statusText}`);
    }
    return response.json();
  }

  // Audio Operations for Enhanced Editor
  async getAudioUrl(audioHash: string): Promise<string> {
    return `${this.baseUrl}/audio/${audioHash}`;
  }

  async getAudioMetadata(audioHash: string): Promise<{ duration: number; size: number; format: string }> {
    const response = await fetch(`${this.baseUrl}/audio/${audioHash}/metadata`);
    if (!response.ok) {
      throw new Error(`Failed to get audio metadata: ${response.statusText}`);
    }
    return response.json();
  }

  // WebSocket connections
  createTranscriptionWebSocket(jobId: string): WebSocket {
    return new WebSocket(`ws://localhost:8000/ws/transcription/${jobId}`);
  }

  createFilesWebSocket(): WebSocket {
    return new WebSocket(`ws://localhost:8000/ws/files`);
  }

  createTranscriptEditorWebSocket(audioHash: string): WebSocket {
    return new WebSocket(`ws://localhost:8000/ws/transcript/${audioHash}`);
  }
}

export const apiService = new APIService();