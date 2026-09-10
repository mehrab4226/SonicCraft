import { useState } from 'react';
import { EditorWorkspace } from '../features/editor/components/EditorWorkspace';
import { EffectsPanel } from '../features/inspector/components/EffectsPanel';
import { ProjectSidebar } from '../features/project/components/ProjectSidebar';
import { TransportBar } from '../features/transport/components/TransportBar';
import { TopBar } from '../shared/components/TopBar';
import { useTheme } from '../shared/hooks/useTheme';
import type { EditorTool } from '../shared/types/editor';

export function App() {
  const { theme, toggleTheme } = useTheme();
  const [activeTool, setActiveTool] = useState<EditorTool>('select');
  const [fileName, setFileName] = useState('Midnight Signal.wav');

  return (
    <div className="app-shell">
      <TopBar
        fileName={fileName}
        theme={theme}
        onFileSelect={setFileName}
        onThemeToggle={toggleTheme}
      />
      <main className="editor-layout">
        <ProjectSidebar />
        <EditorWorkspace activeTool={activeTool} onToolChange={setActiveTool} />
        <EffectsPanel />
      </main>
      <TransportBar />
    </div>
  );
}
