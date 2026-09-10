import type { AudioTrack } from '../../../shared/types/editor';

export interface EditorDocument { tracks: AudioTrack[]; selectedId: string | null }
export interface EditorHistory { past: EditorDocument[]; present: EditorDocument; future: EditorDocument[] }
export type EditorAction =
  | { type: 'commit'; document: EditorDocument }
  | { type: 'select'; id: string }
  | { type: 'undo' }
  | { type: 'redo' };

export const initialHistory: EditorHistory = {
  past: [], present: { tracks: [], selectedId: null }, future: [],
};

export function editorReducer(state: EditorHistory, action: EditorAction): EditorHistory {
  if (action.type === 'select') return { ...state, present: { ...state.present, selectedId: action.id } };
  if (action.type === 'commit') return {
    past: [...state.past, state.present].slice(-20), present: action.document, future: [],
  };
  if (action.type === 'undo' && state.past.length) return {
    past: state.past.slice(0, -1), present: state.past[state.past.length - 1],
    future: [state.present, ...state.future],
  };
  if (action.type === 'redo' && state.future.length) return {
    past: [...state.past, state.present], present: state.future[0], future: state.future.slice(1),
  };
  return state;
}

export function audibleTracks(tracks: AudioTrack[]) {
  const hasSolo = tracks.some(track => track.solo);
  return tracks.filter(track => !track.muted && (!hasSolo || track.solo));
}

export function projectDuration(tracks: AudioTrack[]) {
  return Math.max(0, ...tracks.map(track => track.asset.buffer.duration));
}
