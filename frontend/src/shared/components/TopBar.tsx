import { Download, FolderOpen, Moon, Save, Sun, Undo2, Redo2 } from 'lucide-react';
import type { Theme } from '../types/editor';
import type { EditorController } from '../../features/editor/hooks/useEditor';
import { IconButton } from './IconButton';

interface TopBarProps {
  editor: EditorController;
  theme: Theme;
  onImport: () => void;
  onThemeToggle: () => void;
}

export function TopBar({ editor, theme, onImport, onThemeToggle }: TopBarProps) {
  return (
    <header className="topbar">
      <div className="brand" aria-label="SonicCraft">
        <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /><i /></span>
        <span>Sonic<span>Craft</span></span>
      </div>
      <div className="project-title">
        <span title={editor.selected?.name}>{editor.selected?.name ?? 'Untitled session'}</span>
        <small>In memory · export to keep audio</small>
      </div>
      <div className="topbar-actions">
        <IconButton label="Open audio" onClick={onImport} disabled={!!editor.busy}><FolderOpen /></IconButton>
        <IconButton label="Undo" disabled={!editor.canUndo || !!editor.busy} onClick={editor.undo}><Undo2 /></IconButton>
        <IconButton label="Redo" disabled={!editor.canRedo || !!editor.busy} onClick={editor.redo}><Redo2 /></IconButton>
        <span className="topbar-divider" />
        <IconButton label="Save project (planned; export audio to keep your work)" disabled><Save /></IconButton>
        <button type="button" className="export-button" disabled={!editor.selected || !!editor.busy} onClick={() => void editor.exportSelected()}><Download /> Export track</button>
        <IconButton label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick={onThemeToggle}>{theme === 'dark' ? <Sun /> : <Moon />}</IconButton>
      </div>
    </header>
  );
}
