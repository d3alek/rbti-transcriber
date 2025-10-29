/**
 * Transcript Versions API Service
 * 
 * Dedicated service for managing transcript versions with the enhanced editor.
 */

import type { 
  VersionListResponse, 
  TranscriptLoadResponse, 
  VersionSaveRequest,
  ParagraphUpdateRequest
} from '../types/deepgram';

const API_BASE_URL = 'http://localhost:8000/api';

class TranscriptVersionsAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * List all available versions for a transcript
   */
  async listVersions(audioHash: string): Promise<VersionListResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions`);
    if (!response.ok) {
      throw new Error(`Failed to list versions: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Load a specific version of a transcript
   */
  async loadVersion(audioHash: string, version: number): Promise<TranscriptLoadResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions/${version}`);
    if (!response.ok) {
      throw new Error(`Failed to load version ${version}: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Load the latest version of a transcript
   */
  async loadLatestVersion(audioHash: string): Promise<TranscriptLoadResponse> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions/latest`);
    if (!response.ok) {
      throw new Error(`Failed to load latest version: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Save a new version of a transcript
   */
  async saveVersion(audioHash: string, request: VersionSaveRequest): Promise<Response> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`Failed to save version: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Delete a specific version
   */
  async deleteVersion(audioHash: string, version: number): Promise<Response> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/versions/${version}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete version ${version}: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Initialize version 0 from existing cache
   */
  async initializeFromCache(audioHash: string): Promise<Response> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/initialize`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to initialize from cache: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Update a paragraph's text
   */
  async updateParagraph(audioHash: string, paragraphId: string, newText: string): Promise<Response> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/paragraphs/${paragraphId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        paragraph_id: paragraphId,
        new_text: newText
      } as ParagraphUpdateRequest),
    });
    if (!response.ok) {
      throw new Error(`Failed to update paragraph: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get a specific paragraph
   */
  async getParagraph(audioHash: string, paragraphId: string, version?: number): Promise<Response> {
    const url = version !== undefined 
      ? `${this.baseUrl}/transcripts/${audioHash}/paragraphs/${paragraphId}?version=${version}`
      : `${this.baseUrl}/transcripts/${audioHash}/paragraphs/${paragraphId}`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to get paragraph: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get the word being spoken at a specific time
   */
  async getWordAtTime(audioHash: string, time: number, version?: number): Promise<Response> {
    const url = version !== undefined
      ? `${this.baseUrl}/transcripts/${audioHash}/words/at-time/${time}?version=${version}`
      : `${this.baseUrl}/transcripts/${audioHash}/words/at-time/${time}`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to get word at time: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get all words within a time range
   */
  async getWordsInRange(audioHash: string, startTime: number, endTime: number, version?: number): Promise<Response> {
    const params = new URLSearchParams({
      start_time: startTime.toString(),
      end_time: endTime.toString(),
    });
    
    if (version !== undefined) {
      params.append('version', version.toString());
    }
    
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/words/in-range?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to get words in range: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get storage information for a transcript
   */
  async getStorageInfo(audioHash: string): Promise<Response> {
    const response = await fetch(`${this.baseUrl}/transcripts/${audioHash}/storage-info`);
    if (!response.ok) {
      throw new Error(`Failed to get storage info: ${response.statusText}`);
    }
    return response.json();
  }
}

export const transcriptVersionsApi = new TranscriptVersionsAPI();