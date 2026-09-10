import { test, expect } from '@playwright/test';
import { audibleTracks, editorReducer, initialHistory } from '../src/features/editor/state/editorReducer';
import type { AudioAsset, AudioTrack } from '../src/shared/types/editor';

const asset = { id: 'shared' } as AudioAsset;
const track: AudioTrack = { id: '1', name: 'tone', muted: false, solo: false, color: '#abcdef', gainDb: 0, asset };

test('undo/redo restore immutable assets; branching drops stale redo and caps retained history', () => {
  const imported = editorReducer(initialHistory, { type: 'commit', document: { tracks: [track], selectedId: '1' } });
  const changed = editorReducer(imported, { type: 'commit', document: { tracks: [{ ...track, gainDb: -6 }], selectedId: '1' } });
  const undone = editorReducer(changed, { type: 'undo' });
  expect(undone.present.tracks[0].gainDb).toBe(0);
  expect(editorReducer(undone, { type: 'redo' }).present.tracks[0].gainDb).toBe(-6);
  expect(changed.present.tracks[0].asset).toBe(imported.present.tracks[0].asset);
  let branched = editorReducer(undone, { type: 'commit', document: { tracks: [{ ...track, name: 'renamed' }], selectedId: '1' } });
  expect(branched.future).toEqual([]);
  for (let i = 0; i < 30; i++) branched = editorReducer(branched, { type: 'commit', document: { tracks: [{ ...track, name: String(i) }], selectedId: '1' } });
  expect(branched.past).toHaveLength(20);
  expect(initialHistory.present.tracks).toEqual([]);
});

test('mute and solo precedence selects the correct playback tracks', () => {
  const second = { ...track, id: '2' };
  expect(audibleTracks([track, second])).toHaveLength(2);
  expect(audibleTracks([{ ...track, solo: true }, second]).map(item => item.id)).toEqual(['1']);
  expect(audibleTracks([{ ...track, solo: true, muted: true }, second])).toEqual([]);
  expect(audibleTracks([{ ...track, muted: true }, second]).map(item => item.id)).toEqual(['2']);
});
