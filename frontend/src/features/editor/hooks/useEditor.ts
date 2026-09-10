import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { audioApi } from '../../../shared/lib/audioApi';
import type { AudioAsset, AudioTrack, GainFadeParameters } from '../../../shared/types/editor';
import { AudioEngine } from '../../transport/audioEngine';
import { editorReducer, initialHistory, projectDuration } from '../state/editorReducer';

const colors = ['#8b70ff', '#22c9a7', '#ffb547', '#ff5876'];

export function useEditor() {
  const [history, dispatch] = useReducer(editorReducer, initialHistory);
  const { tracks, selectedId } = history.present;
  const selected = tracks.find(track => track.id === selectedId);
  const [engine] = useState(() => new AudioEngine());
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Import audio to begin.');
  const [connection, setConnection] = useState<'checking' | 'online' | 'offline'>('checking');
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [peak, setPeak] = useState(0);
  const [masterDb, setMasterDb] = useState(0);
  const [normalizeExport, setNormalizeExport] = useState(false);
  const operation = useRef<AbortController | null>(null);
  const mounted = useRef(false);
  const downloads = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  const duration = projectDuration(tracks);

  const checkConnection = useCallback(async (signal?: AbortSignal) => {
    setConnection('checking');
    try { await audioApi.health(signal); if (!signal?.aborted) setConnection('online'); }
    catch { if (!signal?.aborted) setConnection('offline'); }
  }, []);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    void checkConnection(controller.signal);
    return () => {
      mounted.current = false;
      controller.abort();
      operation.current?.abort();
      engine.dispose();
      downloads.current.forEach((timer, url) => { clearTimeout(timer); URL.revokeObjectURL(url); });
      downloads.current.clear();
    };
  }, [engine, checkConnection]);

  useEffect(() => { engine.setVolume(masterDb); }, [engine, masterDb]);
  useEffect(() => {
    engine.seek(Math.min(engine.position, duration));
    setPlaying(false);
    setPosition(engine.position);
    setPeak(0);
  }, [engine, tracks, duration]);

  useEffect(() => {
    if (!playing) return;
    let frame = 0;
    const tick = () => {
      setPosition(engine.position);
      setPeak(engine.meter());
      if (engine.position >= duration || !engine.playing) {
        engine.pause(); setPlaying(false); setPeak(0); return;
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, duration, engine]);

  const pause = () => { engine.pause(); setPlaying(false); setPosition(engine.position); setPeak(0); };
  const seek = async (value: number) => {
    const resume = engine.playing;
    engine.seek(Math.min(duration, Math.max(0, value)));
    setPosition(engine.position);
    if (resume) {
      try { await engine.play(tracks); setPlaying(engine.playing); }
      catch (cause) { setError(String(cause)); setPlaying(false); }
    }
  };
  const togglePlayback = async () => {
    if (engine.playing) { pause(); return; }
    try { await engine.play(tracks); setPlaying(engine.playing); }
    catch { setError('Playback could not start. Check browser audio permissions.'); }
  };

  const run = async (label: string, task: (signal: AbortSignal) => Promise<void>) => {
    if (operation.current) return;
    const controller = new AbortController();
    operation.current = controller;
    pause(); setBusy(label); setError('');
    try {
      await task(controller.signal);
      if (!controller.signal.aborted && mounted.current) { setStatus(`${label} complete.`); setConnection('online'); }
    } catch (cause) {
      if (!controller.signal.aborted && mounted.current) setError(cause instanceof Error ? cause.message : 'Audio operation failed.');
    } finally {
      if (operation.current === controller) operation.current = null;
      if (mounted.current) setBusy('');
    }
  };

  const loadAsset = async (blob: Blob, signal: AbortSignal): Promise<AudioAsset> => {
    const inspection = await audioApi.inspect(blob, signal);
    signal.throwIfAborted();
    const buffer = await engine.decode(blob);
    signal.throwIfAborted();
    return { id: crypto.randomUUID(), blob, buffer, inspection };
  };

  const importFiles = (files: File[]) => run('Import', async signal => {
    if (tracks.length + files.length > 8) throw new Error('This milestone supports up to 8 tracks.');
    const imported: AudioTrack[] = [];
    for (const file of files) {
      if (file.size > 32 * 1024 * 1024) throw new Error(`${file.name} exceeds the 32 MiB file limit.`);
      const asset = await loadAsset(file, signal);
      imported.push({ id: crypto.randomUUID(), name: file.name, color: colors[(tracks.length + imported.length) % colors.length], muted: false, solo: false, gainDb: 0, asset });
    }
    if (!imported.length) return;
    signal.throwIfAborted();
    dispatch({ type: 'commit', document: { tracks: [...tracks, ...imported], selectedId: imported[0].id } });
  });

  const updateTrack = (id: string, patch: Partial<Pick<AudioTrack, 'name' | 'color' | 'muted' | 'solo' | 'gainDb'>>) => {
    if (operation.current) return;
    dispatch({ type: 'commit', document: { tracks: tracks.map(track => track.id === id ? { ...track, ...patch } : track), selectedId } });
  };
  const removeTrack = (id: string) => {
    if (operation.current) return;
    const remaining = tracks.filter(track => track.id !== id);
    dispatch({ type: 'commit', document: { tracks: remaining, selectedId: selectedId === id ? remaining[0]?.id ?? null : selectedId } });
  };
  const replaceSelected = async (blob: Blob, signal: AbortSignal, resetGain: boolean) => {
    if (!selected) return;
    const asset = await loadAsset(blob, signal);
    dispatch({ type: 'commit', document: { tracks: tracks.map(track => track.id === selected.id ? { ...track, asset, gainDb: resetGain ? 0 : track.gainDb } : track), selectedId } });
  };
  const applyGainFade = (params: GainFadeParameters) => run('Gain and fades', async signal => {
    if (selected) await replaceSelected(await audioApi.gainFade(selected.asset.blob, params, signal), signal, true);
  });
  const trim = (start: number, end: number) => run('Trim', async signal => {
    if (selected) await replaceSelected(await audioApi.trim(selected.asset.blob, start, end, signal), signal, false);
  });
  const exportSelected = () => run('Export', async signal => {
    if (!selected) return;
    const blob = await audioApi.export(selected.asset.blob, selected.gainDb + masterDb, normalizeExport, signal);
    signal.throwIfAborted();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${selected.name.replace(/\.[^.]+$/, '')}-soniccraft.wav`;
    document.body.append(anchor); anchor.click(); anchor.remove();
    const timer = setTimeout(() => { URL.revokeObjectURL(url); downloads.current.delete(url); }, 1000);
    downloads.current.set(url, timer);
  });

  return {
    tracks, selected, selectedId, busy, error, status, connection, playing, position, duration, peak,
    masterDb, setMasterDb, normalizeExport, setNormalizeExport, importFiles, updateTrack, removeTrack,
    applyGainFade, trim, exportSelected, seek, togglePlayback,
    canUndo: history.past.length > 0, canRedo: history.future.length > 0,
    select: (id: string) => { if (!operation.current) dispatch({ type: 'select', id }); },
    undo: () => { if (!operation.current) dispatch({ type: 'undo' }); },
    redo: () => { if (!operation.current) dispatch({ type: 'redo' }); },
    cancel: () => { operation.current?.abort(); setStatus('Operation canceled; its result will be discarded.'); },
    dismissError: () => setError(''),
    retryConnection: () => void checkConnection(),
  };
}

export type EditorController = ReturnType<typeof useEditor>;
