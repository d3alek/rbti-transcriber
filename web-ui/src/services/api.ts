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
  APIResponse 
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

  // WebSocket connections
  createTranscriptionWebSocket(jobId: string): WebSocket {
    return new WebSocket(`ws://localhost:8000/ws/transcription/${jobId}`);
  }

  createFilesWebSocket(): WebSocket {
    return new WebSocket(`ws://localhost:8000/ws/files`);
  }
}

export const apiService = new APIService();