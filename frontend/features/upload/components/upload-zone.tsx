/**
 * UploadZone Component
 *
 * Drag-and-drop area for file upload.
 * Supports click-to-browse and multi-file drop.
 */

'use client';

import { useCallback, useState, useRef } from 'react';
import { UPLOAD_ACCEPTED_TYPES, MAX_UPLOAD_SIZE_MB } from '../types';

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export function UploadZone({ onFilesSelected, disabled = false }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const acceptedExtensions = Object.values(UPLOAD_ACCEPTED_TYPES).flat().join(',');

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragOver(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (disabled) return;

    const dropped = Array.from(e.dataTransfer.files);
    if (dropped.length > 0) onFilesSelected(dropped);
  }, [disabled, onFilesSelected]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    if (selected.length > 0) onFilesSelected(selected);
    // Reset input so same file can be re-selected
    e.target.value = '';
  }, [onFilesSelected]);

  const handleClick = useCallback(() => {
    if (!disabled) inputRef.current?.click();
  }, [disabled]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') handleClick();
  }, [handleClick]);

  return (
    <div
      id="upload-drop-zone"
      role="button"
      tabIndex={0}
      aria-label="Upload document files"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className={`
        relative flex flex-col items-center justify-center
        w-full min-h-48 rounded-2xl border-2 border-dashed
        cursor-pointer select-none transition-all duration-200
        ${isDragOver
          ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
          : 'border-white/20 bg-white/5 hover:border-white/40 hover:bg-white/8'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      {/* Background gradient on drag */}
      {isDragOver && (
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 pointer-events-none" />
      )}

      <div className="flex flex-col items-center gap-3 p-8 text-center pointer-events-none">
        {/* Upload icon */}
        <div className={`
          w-14 h-14 rounded-2xl flex items-center justify-center text-2xl
          transition-transform duration-200
          ${isDragOver ? 'bg-indigo-500/30 scale-110' : 'bg-white/10'}
        `}>
          {isDragOver ? '📂' : '📁'}
        </div>

        <div>
          <p className="text-base font-semibold text-white">
            {isDragOver ? 'Drop files here' : 'Drop files or click to browse'}
          </p>
          <p className="text-sm text-white/50 mt-1">
            PDF, DOCX, PPTX, XLSX, TXT, CSV, PNG, JPG, TIFF
          </p>
          <p className="text-xs text-white/30 mt-1">
            Maximum size: {MAX_UPLOAD_SIZE_MB} MB per file
          </p>
        </div>

        <span className="px-4 py-1.5 rounded-full bg-indigo-600/80 text-xs font-medium text-white/90">
          Select Files
        </span>
      </div>

      <input
        ref={inputRef}
        type="file"
        id="upload-file-input"
        multiple
        accept={acceptedExtensions}
        onChange={handleInputChange}
        className="hidden"
        disabled={disabled}
        aria-hidden="true"
      />
    </div>
  );
}
