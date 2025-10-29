/**
 * Service for managing transcript versions and file operations.
 */

import type {
  DeepgramVersion,
  DeepgramResponse,
  VersionMetadata,
  TranscriptError
} from '../types';
import { ErrorType } from '../types';
import { apiService } from './api';

export class VersionManager {
  private cache = new Map<string, DeepgramVersion[]>();
  private currentVersions = new Map<string, number>();

  /**
   * Load all versions for a transcript.
   */
  async loadVersions(audioHash: string): Promise<DeepgramVersion[]> {
    try {
      const response = await apiService.getTranscriptVersions(audioHash);
      
      const versions: DeepgramVersion[] = [];
      
      for (const versionInfo of response.versions) {
        try {
          const versionResponse = await apiService.loadTranscriptVersion(audioHash, versionInfo.version);
          
          versions.push({
            version: versionInfo.version,
            filename: versionInfo.filename,
            timestamp: versionInfo.timestamp,
            changes: versionInfo.changes,
            response: versionResponse as any // TODO: Fix typing
          });
        } catch (error) {
          console.warn(`Failed to load version ${versionInfo.version}:`, error);
        }
      }

      // Sort versions by version number
      versions.sort((a, b) => a.version - b.version);
      
      // Cache the versions
      this.cache.set(audioHash, versions);
      this.currentVersions.set(audioHash, response.current_version);
      
      return versions;
    } catch (error) {
      throw this.createError(
        ErrorType.FILE_SYSTEM,
        `Failed to load versions for ${audioHash}`,
        error,
        true
      );
    }
  }

  /**
   * Save a new version of the transcript.
   */
  async saveVersion(
    audioHash: string,
    response: DeepgramResponse,
    changes: string
  ): Promise<DeepgramVersion> {
    try {
      const saveRequest = {
        changes,
        response
      };

      const result = await apiService.saveTranscriptVersion(audioHash, saveRequest);
      
      if (!result.success || !result.data) {
        throw new Error(result.message || 'Failed to save version');
      }

      const newVersion: DeepgramVersion = {
        version: result.data.version,
        filename: `v${result.data.version}.json`,
        timestamp: new Date().toISOString(),
        changes,
        response
      };

      // Update cache
      const cachedVersions = this.cache.get(audioHash) || [];
      cachedVersions.push(newVersion);
      cachedVersions.sort((a, b) => a.version - b.version);
      this.cache.set(audioHash, cachedVersions);
      this.currentVersions.set(audioHash, newVersion.version);

      return newVersion;
    } catch (error) {
      throw this.createError(
        ErrorType.FILE_SYSTEM,
        `Failed to save version for ${audioHash}`,
        error,
        true
      );
    }
  }

  /**
   * Get a specific version of the transcript.
   */
  async getVersion(audioHash: string, version: number): Promise<DeepgramVersion | null> {
    try {
      // Check cache first
      const cachedVersions = this.cache.get(audioHash);
      if (cachedVersions) {
        const cachedVersion = cachedVersions.find(v => v.version === version);
        if (cachedVersion) {
          return cachedVersion;
        }
      }

      // Load from API
      const response = await apiService.loadTranscriptVersion(audioHash, version);
      
      const versionData: DeepgramVersion = {
        version,
        filename: `v${version}.json`,
        timestamp: response.version?.toString() || new Date().toISOString(),
        changes: 'Loaded from file',
        response: response as any // TODO: Fix typing
      };

      return versionData;
    } catch (error) {
      console.warn(`Failed to load version ${version} for ${audioHash}:`, error);
      return null;
    }
  }

  /**
   * Delete a specific version.
   */
  async deleteVersion(audioHash: string, version: number): Promise<void> {
    try {
      await apiService.deleteTranscriptVersion(audioHash, version);
      
      // Update cache
      const cachedVersions = this.cache.get(audioHash);
      if (cachedVersions) {
        const filteredVersions = cachedVersions.filter(v => v.version !== version);
        this.cache.set(audioHash, filteredVersions);
      }
    } catch (error) {
      throw this.createError(
        ErrorType.FILE_SYSTEM,
        `Failed to delete version ${version} for ${audioHash}`,
        error,
        false
      );
    }
  }

  /**
   * Get the current version number for a transcript.
   */
  getCurrentVersion(audioHash: string): number {
    return this.currentVersions.get(audioHash) || 0;
  }

  /**
   * Set the current version for a transcript.
   */
  setCurrentVersion(audioHash: string, version: number): void {
    this.currentVersions.set(audioHash, version);
  }

  /**
   * Get version metadata without loading full responses.
   */
  async getVersionMetadata(audioHash: string): Promise<VersionMetadata> {
    try {
      const response = await apiService.getTranscriptVersions(audioHash);
      
      return {
        versions: response.versions,
        currentVersion: response.current_version,
        lastModified: new Date().toISOString()
      };
    } catch (error) {
      throw this.createError(
        ErrorType.FILE_SYSTEM,
        `Failed to get version metadata for ${audioHash}`,
        error,
        true
      );
    }
  }

  /**
   * Check if there are unsaved changes.
   */
  hasUnsavedChanges(audioHash: string, currentResponse: DeepgramResponse): boolean {
    const cachedVersions = this.cache.get(audioHash);
    if (!cachedVersions || cachedVersions.length === 0) {
      return true;
    }

    const currentVersion = this.getCurrentVersion(audioHash);
    const latestVersion = cachedVersions.find(v => v.version === currentVersion);
    
    if (!latestVersion) {
      return true;
    }

    // Simple comparison - in practice, this would be more sophisticated
    return JSON.stringify(currentResponse) !== JSON.stringify(latestVersion.response);
  }

  /**
   * Generate a hash for the audio file (used as identifier).
   */
  generateAudioHash(audioFile: string): string {
    // Simple hash generation - in practice, use a proper hash function
    return btoa(audioFile).replace(/[^a-zA-Z0-9]/g, '').substring(0, 16);
  }

  /**
   * Clear cache for a specific transcript.
   */
  clearCache(audioHash?: string): void {
    if (audioHash) {
      this.cache.delete(audioHash);
      this.currentVersions.delete(audioHash);
    } else {
      this.cache.clear();
      this.currentVersions.clear();
    }
  }

  /**
   * Get cached versions without API call.
   */
  getCachedVersions(audioHash: string): DeepgramVersion[] {
    return this.cache.get(audioHash) || [];
  }

  /**
   * Validate version data integrity.
   */
  validateVersion(version: DeepgramVersion): boolean {
    try {
      // Basic validation
      if (!version.response || !version.response.metadata || !version.response.results) {
        return false;
      }

      // Check required fields
      if (typeof version.version !== 'number' || version.version < 0) {
        return false;
      }

      if (!version.timestamp || !version.filename) {
        return false;
      }

      // Validate Deepgram response structure
      const channels = version.response.results.channels;
      if (!Array.isArray(channels) || channels.length === 0) {
        return false;
      }

      return true;
    } catch (error) {
      console.warn('Version validation failed:', error);
      return false;
    }
  }

  /**
   * Create a standardized error object.
   */
  private createError(
    type: typeof ErrorType[keyof typeof ErrorType],
    message: string,
    originalError: any,
    recoverable: boolean
  ): TranscriptError {
    return {
      type,
      message,
      details: originalError,
      recoverable,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Get version statistics.
   */
  getVersionStats(audioHash: string): {
    totalVersions: number;
    currentVersion: number;
    oldestVersion: number;
    newestVersion: number;
  } {
    const versions = this.getCachedVersions(audioHash);
    
    if (versions.length === 0) {
      return {
        totalVersions: 0,
        currentVersion: 0,
        oldestVersion: 0,
        newestVersion: 0
      };
    }

    const versionNumbers = versions.map(v => v.version).sort((a, b) => a - b);
    
    return {
      totalVersions: versions.length,
      currentVersion: this.getCurrentVersion(audioHash),
      oldestVersion: versionNumbers[0],
      newestVersion: versionNumbers[versionNumbers.length - 1]
    };
  }
}

export const versionManager = new VersionManager();