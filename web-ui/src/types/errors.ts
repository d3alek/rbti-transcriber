/**
 * Error handling types and validation schemas
 */

export interface AppError {
  code: string;
  message: string;
  details?: string;
  timestamp: string;
  context?: Record<string, any>;
}

export interface ValidationError extends AppError {
  field: string;
  value: any;
  constraint: string;
}

export interface FileSystemError extends AppError {
  path: string;
  operation: 'read' | 'write' | 'delete' | 'scan' | 'access';
  systemError?: string;
}

export interface TranscriptionError extends AppError {
  audioFile: string;
  service: string;
  apiError?: string;
  retryable: boolean;
}

export interface LocalSiteError extends AppError {
  operation: 'generate' | 'write' | 'copy' | 'template';
  targetPath?: string;
  sourceFile?: string;
}

export interface APIError extends AppError {
  endpoint: string;
  method: string;
  statusCode?: number;
  responseBody?: string;
}

export interface ErrorContext {
  component: string;
  action: string;
  userId?: string;
  sessionId?: string;
  additionalData?: Record<string, any>;
}

export interface RetryStrategy {
  maxRetries: number;
  backoffMultiplier: number;
  retryableErrors: string[];
  onRetryExhausted: (error: AppError) => void;
}

export interface ErrorHandler {
  handleFileSystemError(error: FileSystemError): Promise<void>;
  handleTranscriptionError(audioFile: string, error: TranscriptionError): Promise<void>;
  handleLocalSiteError(bundle: any, error: LocalSiteError): Promise<void>;
  handleAPIError(error: APIError): Promise<void>;
  handleValidationError(error: ValidationError): Promise<void>;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error?: AppError;
  errorInfo?: string;
}

export interface ErrorReportingConfig {
  enableReporting: boolean;
  endpoint?: string;
  includeStackTrace: boolean;
  includeUserContext: boolean;
  maxReportSize: number;
}

// Error codes enum for consistent error handling
export enum ErrorCodes {
  // File System Errors
  FILE_NOT_FOUND = 'FILE_NOT_FOUND',
  DIRECTORY_ACCESS_DENIED = 'DIRECTORY_ACCESS_DENIED',
  DISK_SPACE_INSUFFICIENT = 'DISK_SPACE_INSUFFICIENT',
  FILE_CORRUPTED = 'FILE_CORRUPTED',
  
  // Transcription Errors
  TRANSCRIPTION_API_FAILURE = 'TRANSCRIPTION_API_FAILURE',
  AUDIO_FORMAT_UNSUPPORTED = 'AUDIO_FORMAT_UNSUPPORTED',
  TRANSCRIPTION_TIMEOUT = 'TRANSCRIPTION_TIMEOUT',
  QUOTA_EXCEEDED = 'QUOTA_EXCEEDED',
  
  // Publishing Errors
  PUBLISH_WRITE_FAILURE = 'PUBLISH_WRITE_FAILURE',
  TEMPLATE_GENERATION_FAILURE = 'TEMPLATE_GENERATION_FAILURE',
  ASSET_COPY_FAILURE = 'ASSET_COPY_FAILURE',
  
  // API Errors
  NETWORK_ERROR = 'NETWORK_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  
  // Validation Errors
  INVALID_AUDIO_FILE = 'INVALID_AUDIO_FILE',
  INVALID_DIRECTORY_PATH = 'INVALID_DIRECTORY_PATH',
  INVALID_TRANSCRIPT_DATA = 'INVALID_TRANSCRIPT_DATA',
  MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD',
  
  // General Errors
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
  CONFIGURATION_ERROR = 'CONFIGURATION_ERROR',
  PERMISSION_DENIED = 'PERMISSION_DENIED'
}