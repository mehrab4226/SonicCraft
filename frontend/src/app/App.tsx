import { useEffect, useRef } from 'react';
import { EditorWorkspace } from '../features/editor/components/EditorWorkspace';
import { useEditor } from '../features/editor/hooks/useEditor';
import { EffectsPanel } from '../features/inspector/components/EffectsPanel';
import { ProjectSidebar } from '../features/project/components/ProjectSidebar';
import { TransportBar } from '../features/transport/components/TransportBar';
import { TopBar } from '../shared/components/TopBar';
import { useTheme } from '../shared/hooks/useTheme';

export function App() {
  const { theme, toggleTheme } = useTheme();
  const editor = useEditor();
  const input = useRef<HTMLInputElement>(null);
  const onImport = () => input.current?.click();

  useEffect(() => {
    const keyboard = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest('input, textarea, select, button, [role="button"], [contenteditable="true"]') || editor.busy) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
        event.preventDefault();
        if (event.shiftKey) editor.redo(); else editor.undo();
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'y') {
        event.preventDefault(); editor.redo();
      } else if (event.code === 'Space' && editor.tracks.length) {
        event.preventDefault(); void editor.togglePlayback();
      }
    };
    window.addEventListener('keydown', keyboard);
    return () => window.removeEventListener('keydown', keyboard);
  }, [editor]);

  useEffect(() => {
    if (!editor.tracks.length) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [editor.tracks.length]);

  return <div className="app-shell">
    <input ref={input} aria-label="Import audio files" className="visually-hidden" type="file" accept="audio/*,.wav,.flac,.ogg,.mp3" multiple onChange={event => {
      const files = Array.from(event.target.files ?? []); event.target.value = '';
      if (files.length) void editor.importFiles(files);
    }} />
    <TopBar editor={editor} theme={theme} onImport={onImport} onThemeToggle={toggleTheme} />
    <div className="session-status">
      <span className={`connection-${editor.connection}`}>Audio service: {editor.connection}</span>
      {editor.connection === 'offline' && <button type="button" onClick={editor.retryConnection}>Retry connection</button>}
      <span role="status">{editor.busy ? `${editor.busy}…` : editor.status}</span>
      {editor.busy && <button type="button" onClick={editor.cancel}>Cancel</button>}
      {editor.error && <div role="alert" className="error-message">{editor.error}<button type="button" aria-label="Dismiss error" onClick={editor.dismissError}>Dismiss</button></div>}
    </div>
    <main className="editor-layout" aria-busy={!!editor.busy}>
      <ProjectSidebar editor={editor} onImport={onImport} />
      <EditorWorkspace editor={editor} onImport={onImport} />
      <EffectsPanel editor={editor} />
    </main>
    <TransportBar editor={editor} />
  </div>;
}
