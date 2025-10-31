import { 
  APIResponse, 
  DirectoryScanResult, 
  TranscriptionResult, 
  TranscriptionStatus 
} from '../types/api';

export class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    // Use empty string for relative URLs in browser (works with webpack dev server proxy)
    // In production, you can set a full URL
    this.baseUrl = baseUrl;
  }

  private async makeRequest<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    try {
      const fullUrl = `${this.baseUrl}${endpoint}`;
      console.log('🌐 Making HTTP request to:', fullUrl);
      console.log('🌐 Request options:', options);
      
      const response = await fetch(fullUrl, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      console.log('🌐 HTTP response status:', response.status, response.statusText);
      console.log('🌐 HTTP response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorText = await response.text();
        console.error('🌐 HTTP error response body:', errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('🌐 HTTP response data type:', typeof data);
      console.log('🌐 HTTP response data keys:', Object.keys(data || {}));
      
      // Check if data is already in APIResponse format
      if (data.success !== undefined || data.error !== undefined) {
        // Already wrapped, return as-is
        return data;
      }
      
      // Data is not wrapped, wrap it in APIResponse format
      console.log('🌐 Wrapping response data in APIResponse format');
      return {
        success: true,
        data: data,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      console.error('🌐 HTTP request failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      return {
        success: false,
        error: errorMessage,
        timestamp: new Date().toISOString(),
      };
    }
  }

  async scanDirectory(directoryPath: string): Promise<APIResponse<DirectoryScanResult>> {
    return this.makeRequest<DirectoryScanResult>('/api/directory/scan', {
      method: 'POST',
      body: JSON.stringify({ directory_path: directoryPath }),
    });
  }

  async startTranscription(audioFilePath: string): Promise<APIResponse<TranscriptionResult>> {
    const encodedPath = encodeURIComponent(audioFilePath);
    return this.makeRequest<TranscriptionResult>(`/api/transcribe/${encodedPath}`, {
      method: 'POST',
    });
  }

  async getTranscriptionStatus(audioFilePath: string): Promise<APIResponse<TranscriptionStatus>> {
    const encodedPath = encodeURIComponent(audioFilePath);
    return this.makeRequest<TranscriptionStatus>(`/api/transcription-status/${encodedPath}`);
  }

  async getTranscript(audioFilePath: string): Promise<APIResponse<any>> {
    console.log('🌐 APIClient.getTranscript called with path:', audioFilePath);
    const encodedPath = encodeURIComponent(audioFilePath);
    console.log('🌐 Encoded path:', encodedPath);
    console.log('🌐 Full URL:', `${this.baseUrl}/api/transcripts/${encodedPath}`);
    
    const result = await this.makeRequest<any>(`/api/transcripts/${encodedPath}`);
    console.log('🌐 APIClient.getTranscript result:', result);
    return result;
  }

  async saveTranscriptCorrections(
    audioFilePath: string, 
    corrections: any
  ): Promise<APIResponse<void>> {
    const encodedPath = encodeURIComponent(audioFilePath);
    return this.makeRequest<void>(`/api/transcripts/${encodedPath}/corrections`, {
      method: 'PUT',
      body: JSON.stringify(corrections),
    });
  }
}

export default APIClient;