import { describe, expect, it } from 'vitest';
import { stripEmojiDeep, stripEmojiText } from './strip-emoji';

describe('stripEmoji', () => {
  it('removes pictographs from assistant text', () => {
    expect(stripEmojiText('CPU \u{1F9E0} พร้อมใช้งาน \u2705')).toBe('CPU  พร้อมใช้งาน ');
  });

  it('cleans nested saved results without changing the original', () => {
    const original = { summary: 'ดี \u{1F680}', parts: [{ reason: 'เร็ว \u26A1' }] };
    expect(stripEmojiDeep(original)).toEqual({ summary: 'ดี ', parts: [{ reason: 'เร็ว ' }] });
    expect(original.summary).toBe('ดี \u{1F680}');
  });
});
