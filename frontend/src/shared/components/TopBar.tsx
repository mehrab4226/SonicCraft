import { Download, FolderOpen, Moon, Save, Sun, Undo2, Redo2 } from 'lucide-react';
import { useRef } from 'react';
import type { Theme } from '../types/editor';
import { IconButton } from './IconButton';

interface TopBarProps {
  fileName: string;
  theme: Theme;
  onFileSelect: (fileName: string) => void;
  onThemeToggle: () => void;
}

export function TopBar({ fileName, theme, onFileSelect, onThemeToggle }: TopBarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <header className="topbar">
      <div className="brand" aria-label="SonicCraft home">
        <span className="brand-mark" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
          <i />
        </span>
        <span>Sonic<span>Craft</span></span>
      </div>

      <div className="project-title">
        <span className="status-dot" />
        <span>{fileName}</span>
        <small>Saved</small>
      </div>

      <div className="topbar-actions">
        <input
          ref={fileInputRef}
          className="visually-hidden"
          type="file"
          accept="audio/*"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onFileSelect(file.name);
          }}
        />
        <IconButton label="Open audio" onClick={() => fileInputRef.current?.click()}><FolderOpen /></IconButton>
        <IconButton label="Undo"><Undo2 /></IconButton>
        <IconButton label="Redo"><Redo2 /></IconButton>
        <span className="topbar-divider" />
        <IconButton label="Save project"><Save /></IconButton>
        <button type="button" className="export-button"><Download /> Export</button>
        <IconButton label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick={onThemeToggle}>
          {theme === 'dark' ? <Sun /> : <Moon />}
        </IconButton>
      </div>
    </header>
  );
}
